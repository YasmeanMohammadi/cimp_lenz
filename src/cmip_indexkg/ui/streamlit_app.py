"""Streamlit upload-and-review prototype for Phase 2."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from cmip_indexkg.config import TARGET_ENTITY_TYPES
from cmip_indexkg.extraction.baseline import load_target_vocab
from cmip_indexkg.ui.review_service import (
    DEFAULT_REVIEWER_ID,
    DEFAULT_UPLOAD_RUNS_DIR,
    create_manual_annotation,
    create_uploaded_paper_record,
    generate_run_id,
    group_annotations,
    load_existing_predictions,
    run_baseline_on_pdf_record,
    save_existing_review,
    save_upload_review,
    save_uploaded_pdf,
    search_vocab,
    selected_entity_payload,
    serialize_reviewed_annotation,
    vocab_option_label,
)

DEFAULT_VOCAB = Path("data/vocab/climatekg_vocab.jsonl")
DEFAULT_CANONICAL_MAPPINGS = Path("config/canonical_mappings.json")
DEFAULT_EXISTING_PREDICTIONS = Path("dataset/data/annotations/predictions_clean.jsonl")


@st.cache_data(show_spinner=False)
def cached_vocab(vocab_path: str) -> list[dict[str, Any]]:
    return load_target_vocab(vocab_path)


@st.cache_data(show_spinner=False)
def cached_predictions(predictions_path: str) -> list[dict[str, Any]]:
    return load_existing_predictions(predictions_path)


def ensure_paths(vocab_path: Path, canonical_mappings_path: Path) -> bool:
    ok = True
    if not vocab_path.exists():
        st.error(f"Vocabulary file is missing: {vocab_path}")
        ok = False
    if not canonical_mappings_path.exists():
        st.error(f"Canonical mapping file is missing: {canonical_mappings_path}")
        ok = False
    return ok


def evidence_block(annotation: dict[str, Any]) -> None:
    evidence = annotation.get("evidence") or []
    if not evidence:
        st.caption("No evidence stored.")
        return
    for item in evidence[:3]:
        page = item.get("page_number")
        sentence_id = item.get("sentence_id")
        text = item.get("sentence_text") or item.get("text") or ""
        st.markdown(f"**Evidence:** page `{page}`, sentence `{sentence_id}`")
        st.write(text)


def correction_selector(vocab: list[dict[str, Any]], annotation: dict[str, Any], key_prefix: str) -> dict[str, Any] | None:
    entity_type = str(annotation.get("entity_type") or "")
    query = st.text_input("Correction search", value=str(annotation.get("canonical_label") or ""), key=f"{key_prefix}_correction_query")
    results = search_vocab(vocab, query, entity_type=entity_type, limit=50)
    if not results:
        st.warning("No correction candidates found.")
        return None
    selected = st.selectbox(
        "Corrected KG entity",
        options=results,
        format_func=vocab_option_label,
        key=f"{key_prefix}_correction_select",
    )
    return selected_entity_payload(selected)


def review_annotation_card(annotation: dict[str, Any], vocab: list[dict[str, Any]], key_prefix: str) -> dict[str, Any]:
    title = annotation.get("canonical_label") or annotation.get("canonical_id") or annotation.get("kg_entity_id")
    with st.expander(f"{title} | {annotation.get('entity_type')} | confidence {annotation.get('confidence')}", expanded=False):
        st.write({
            "canonical_id": annotation.get("canonical_id"),
            "canonical_label": annotation.get("canonical_label"),
            "entity_type": annotation.get("entity_type"),
            "kg_entity_id": annotation.get("kg_entity_id"),
            "mention_count": annotation.get("mention_count"),
            "matched_texts": annotation.get("matched_texts"),
            "mapping_method": annotation.get("mapping_method"),
        })
        evidence_block(annotation)
        status = st.selectbox(
            "Review status",
            options=["suggested", "accepted", "rejected", "corrected", "unresolved"],
            index=0,
            key=f"{key_prefix}_status",
        )
        notes = st.text_area("Notes", key=f"{key_prefix}_notes")
        corrected_to = correction_selector(vocab, annotation, key_prefix) if status == "corrected" else None
        return serialize_reviewed_annotation(
            annotation,
            review_status=status,
            review_notes=notes,
            reviewer_id=DEFAULT_REVIEWER_ID,
            corrected_to=corrected_to,
        )


def manual_add_panel(vocab: list[dict[str, Any]], key_prefix: str) -> list[dict[str, Any]]:
    st.subheader("Manual Annotation Add")
    entity_type = st.selectbox("Entity type", options=list(TARGET_ENTITY_TYPES), key=f"{key_prefix}_manual_type")
    query = st.text_input("Search KG vocabulary", key=f"{key_prefix}_manual_query")
    results = search_vocab(vocab, query, entity_type=entity_type, limit=50)
    if not results:
        st.caption("Enter a search term to find KG entities.")
        return []
    selected = st.selectbox("Manual KG entity", options=results, format_func=vocab_option_label, key=f"{key_prefix}_manual_select")
    note = st.text_input("Manual note", key=f"{key_prefix}_manual_note")
    if st.button("Add manual annotation", key=f"{key_prefix}_manual_add"):
        state_key = f"{key_prefix}_manual_annotations"
        st.session_state.setdefault(state_key, [])
        st.session_state[state_key].append(create_manual_annotation(selected, note=note, reviewer_id=DEFAULT_REVIEWER_ID))
    return list(st.session_state.get(f"{key_prefix}_manual_annotations", []))


def review_prediction(prediction: dict[str, Any], vocab: list[dict[str, Any]], key_prefix: str) -> list[dict[str, Any]]:
    st.markdown(f"### Paper `{prediction.get('pdf_number')}`")
    paper = prediction.get("paper") or {}
    if paper.get("title"):
        st.write(paper.get("title"))
    annotations = prediction.get("annotations") or prediction.get("predicted_annotations") or []
    if not annotations:
        st.warning("Extraction returned zero annotations.")
    reviewed: list[dict[str, Any]] = []
    grouped = group_annotations(annotations)
    for entity_type in TARGET_ENTITY_TYPES:
        items = grouped.get(entity_type, [])
        st.subheader(f"{entity_type} ({len(items)})")
        for index, annotation in enumerate(items):
            reviewed.append(review_annotation_card(annotation, vocab, f"{key_prefix}_{entity_type}_{index}"))
    reviewed.extend(manual_add_panel(vocab, key_prefix))
    return reviewed


def existing_predictions_mode(vocab: list[dict[str, Any]], predictions_path: Path) -> None:
    st.header("Review Existing Clean-Seed Predictions")
    if not predictions_path.exists():
        st.error(f"Existing predictions file is missing: {predictions_path}")
        return
    predictions = cached_predictions(str(predictions_path))
    if not predictions:
        st.warning("No prediction records found.")
        return
    labels = [f"{item.get('pdf_number')} | {(item.get('paper') or {}).get('title', '')[:80]}" for item in predictions]
    selected_label = st.selectbox("Select paper", labels)
    prediction = predictions[labels.index(selected_label)]
    reviewed = review_prediction(prediction, vocab, f"existing_{prediction.get('pdf_number')}")
    if st.button("Save reviewed annotations", key="save_existing_review"):
        record = {
            "pdf_number": prediction.get("pdf_number"),
            "paper": prediction.get("paper") or {},
            "reviewed_annotations": reviewed,
        }
        try:
            annotations_path, summary_path = save_existing_review([record])
        except Exception as exc:
            st.error(f"Failed to save review: {exc}")
            return
        st.success(f"Saved reviewed annotations to {annotations_path}")
        st.info(f"Saved review summary to {summary_path}")


def upload_mode(vocab: list[dict[str, Any]], vocab_path: Path, canonical_mappings_path: Path) -> None:
    st.header("Upload PDF and Run Extraction")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    title = st.text_input("Title")
    doi = st.text_input("DOI")
    year = st.text_input("Year")
    authors = st.text_input("Authors", help="Separate multiple authors with commas or semicolons.")
    source_url = st.text_input("Source URL")
    if uploaded_file is None:
        return

    if st.button("Run extraction", key="run_upload_extraction"):
        try:
            run_id = generate_run_id(uploaded_file.name)
            pdf_path = save_uploaded_pdf(uploaded_file, run_id)
            run_dir = DEFAULT_UPLOAD_RUNS_DIR / run_id
            paper_record = create_uploaded_paper_record(run_id, pdf_path, title=title, doi=doi, year=year, authors=authors, source_url=source_url)
            parsed, prediction = run_baseline_on_pdf_record(paper_record, vocab_path, canonical_mappings_path, run_dir)
        except Exception as exc:
            st.error(f"Upload extraction failed: {exc}")
            return
        st.session_state["upload_run_id"] = run_id
        st.session_state["upload_prediction"] = prediction
        st.session_state["upload_parsed_sentence_count"] = len(parsed.get("sentences") or [])
        st.success(f"Saved uploaded PDF to {pdf_path}")
        st.info(f"Parsed {len(parsed.get('pages') or [])} pages and {len(parsed.get('sentences') or [])} sentences.")

    prediction = st.session_state.get("upload_prediction")
    run_id = st.session_state.get("upload_run_id")
    if prediction and run_id:
        reviewed = review_prediction(prediction, vocab, f"upload_{run_id}")
        if st.button("Save reviewed annotations", key="save_upload_review"):
            try:
                annotations_path, summary_path = save_upload_review(run_id, reviewed, prediction)
            except Exception as exc:
                st.error(f"Failed to save review: {exc}")
                return
            st.success(f"Saved reviewed annotations to {annotations_path}")
            st.info(f"Saved review summary to {summary_path}")


def main() -> None:
    st.set_page_config(page_title="CIMPIndexKG Review", layout="wide")
    st.title("CIMPIndexKG Upload-and-Review Prototype")
    st.caption("Local Streamlit prototype. ClimateKG is read-only; reviewed annotations are saved as local JSON/JSONL only.")

    st.sidebar.header("Configuration")
    mode = st.sidebar.selectbox("Mode", ["Review existing clean-seed predictions", "Upload PDF and run extraction"])
    vocab_path = Path(st.sidebar.text_input("Vocabulary JSONL", value=str(DEFAULT_VOCAB)))
    canonical_mappings_path = Path(st.sidebar.text_input("Canonical mappings JSON", value=str(DEFAULT_CANONICAL_MAPPINGS)))
    predictions_path = Path(st.sidebar.text_input("Existing predictions JSONL", value=str(DEFAULT_EXISTING_PREDICTIONS)))

    if not ensure_paths(vocab_path, canonical_mappings_path):
        return
    try:
        vocab = cached_vocab(str(vocab_path))
    except Exception as exc:
        st.error(f"Failed to load vocabulary: {exc}")
        return
    st.sidebar.info(f"Loaded {len(vocab)} vocabulary records.")

    if mode == "Review existing clean-seed predictions":
        existing_predictions_mode(vocab, predictions_path)
    else:
        upload_mode(vocab, vocab_path, canonical_mappings_path)


if __name__ == "__main__":
    main()
