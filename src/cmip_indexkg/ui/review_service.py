"""Service helpers for the Phase 2 upload-and-review prototype."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from cmip_indexkg.config import TARGET_ENTITY_TYPES
from cmip_indexkg.extraction.baseline import (
    aggregate_mentions,
    build_alias_index,
    find_mentions,
    load_target_vocab,
)
from cmip_indexkg.extraction.normalization import normalize_text
from cmip_indexkg.ingestion.pdf_parser import parse_pdf_record
from cmip_indexkg.kg.vocabulary_export import read_jsonl, write_jsonl

DEFAULT_UPLOAD_DIR = Path("dataset/data/uploads")
DEFAULT_UPLOAD_RUNS_DIR = Path("dataset/data/upload_runs")
DEFAULT_REVIEW_DIR = Path("dataset/data/review")
DEFAULT_REVIEWER_ID = "local_user"
REVIEW_STATUSES = ("suggested", "accepted", "rejected", "corrected", "unresolved")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_filename(value: str) -> str:
    stem = Path(value or "uploaded_pdf").stem or "uploaded_pdf"
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-_")
    return sanitized[:80] or "uploaded_pdf"


def generate_run_id(filename: str, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return f"{current.strftime('%Y%m%dT%H%M%SZ')}_{sanitize_filename(filename)}"


def _parse_authors(authors: str | list[str] | None) -> list[str]:
    if authors is None:
        return []
    if isinstance(authors, list):
        return [str(author).strip() for author in authors if str(author).strip()]
    return [part.strip() for part in re.split(r"\s*;\s*|\s*,\s*", str(authors)) if part.strip()]


def create_uploaded_paper_record(
    run_id: str,
    pdf_path: str | Path,
    title: str = "",
    doi: str = "",
    year: int | str | None = None,
    authors: str | list[str] | None = None,
    source_url: str = "",
) -> dict[str, Any]:
    parsed_year: int | None
    try:
        parsed_year = int(year) if year not in (None, "") else None
    except (TypeError, ValueError):
        parsed_year = None
    return {
        "pdf_number": run_id,
        "paper": {
            "title": title.strip(),
            "doi": doi.strip(),
            "source_url": source_url.strip(),
            "pdf_url": "",
            "local_pdf_path": str(pdf_path),
            "year": parsed_year,
            "authors": _parse_authors(authors),
        },
        "gold_annotations": {entity_type: [] for entity_type in TARGET_ENTITY_TYPES},
        "notes": "uploaded_via_phase2_ui",
    }


def save_uploaded_pdf(uploaded_file: Any, run_id: str, upload_dir: str | Path = DEFAULT_UPLOAD_DIR) -> Path:
    output_dir = Path(upload_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_id}.pdf"
    with output_path.open("wb") as fh:
        if hasattr(uploaded_file, "getbuffer"):
            fh.write(bytes(uploaded_file.getbuffer()))
        elif hasattr(uploaded_file, "read"):
            data = uploaded_file.read()
            fh.write(data if isinstance(data, bytes) else bytes(data))
        else:
            raise TypeError("uploaded_file must provide getbuffer() or read()")
    return output_path


def run_baseline_on_document(
    parsed_document: dict[str, Any],
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
) -> dict[str, Any]:
    vocab = load_target_vocab(vocab_path)
    alias_index = build_alias_index(vocab, canonical_mappings_path)
    mentions = find_mentions(parsed_document, alias_index, canonical_mappings_path)
    return aggregate_mentions(parsed_document, mentions)


def run_baseline_on_pdf_record(
    paper_record: dict[str, Any],
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
    run_dir: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    # parse_pdf_record only needs gold_path for relative path resolution. The uploaded
    # record stores an absolute or repo-relative PDF path, so a synthetic path is enough.
    parsed = parse_pdf_record(paper_record, gold_path=run_path / "uploaded_record.jsonl")
    parsed_dict = parsed.to_dict()
    prediction = run_baseline_on_document(parsed_dict, vocab_path, canonical_mappings_path)
    (run_path / "parsed_document.json").write_text(json.dumps(parsed_dict, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_path / "predictions.json").write_text(json.dumps(prediction, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return parsed_dict, prediction


def load_existing_predictions(path: str | Path) -> list[dict[str, Any]]:
    return list(read_jsonl(path))


def group_annotations(annotations: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {entity_type: [] for entity_type in TARGET_ENTITY_TYPES}
    for annotation in annotations:
        grouped.setdefault(str(annotation.get("entity_type") or "Unknown"), []).append(annotation)
    return grouped


def _vocab_search_text(record: dict[str, Any]) -> str:
    parts = [
        record.get("entity_type"),
        record.get("canonical_id"),
        record.get("label"),
        record.get("kg_entity_id"),
    ]
    parts.extend(record.get("aliases") or [])
    return normalize_text(" ".join(str(part) for part in parts if part))


def search_vocab(
    vocab_records: list[dict[str, Any]],
    query: str,
    entity_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query_key = normalize_text(query)
    results: list[dict[str, Any]] = []
    for record in vocab_records:
        if entity_type and record.get("entity_type") != entity_type:
            continue
        if query_key and query_key not in _vocab_search_text(record):
            continue
        results.append(record)
        if len(results) >= limit:
            break
    return results


def vocab_option_label(record: dict[str, Any]) -> str:
    return f"{record.get('entity_type')} | {record.get('canonical_id')} | {record.get('label')} | {record.get('kg_entity_id')}"


def selected_entity_payload(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    return {
        "kg_entity_id": record.get("kg_entity_id"),
        "entity_type": record.get("entity_type"),
        "canonical_id": record.get("canonical_id"),
        "canonical_label": record.get("label") or record.get("canonical_id"),
        "label": record.get("label"),
    }


def serialize_reviewed_annotation(
    annotation: dict[str, Any],
    review_status: str = "suggested",
    review_notes: str = "",
    reviewer_id: str = DEFAULT_REVIEWER_ID,
    corrected_to: dict[str, Any] | None = None,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    if review_status not in REVIEW_STATUSES and review_status != "manual":
        raise ValueError(f"Unsupported review status: {review_status}")
    reviewed = dict(annotation)
    reviewed.update({
        "review_status": review_status,
        "reviewed_at": reviewed_at or utc_now_iso(),
        "reviewer_id": reviewer_id or DEFAULT_REVIEWER_ID,
        "review_notes": review_notes,
        "corrected_to": corrected_to if review_status == "corrected" else None,
    })
    if review_status in {"corrected", "rejected"}:
        reviewed["original_annotation"] = dict(annotation)
    return reviewed


def create_manual_annotation(
    entity: dict[str, Any],
    note: str = "",
    reviewer_id: str = DEFAULT_REVIEWER_ID,
) -> dict[str, Any]:
    payload = selected_entity_payload(entity) or {}
    annotation = {
        "entity_type": payload.get("entity_type"),
        "kg_entity_id": payload.get("kg_entity_id"),
        "canonical_id": payload.get("canonical_id"),
        "canonical_label": payload.get("canonical_label"),
        "matched_texts": [],
        "mention_count": 0,
        "confidence": None,
        "mapping_method": "manual_review_add",
        "evidence": [],
    }
    return serialize_reviewed_annotation(annotation, review_status="manual", review_notes=note, reviewer_id=reviewer_id)


def generate_review_summary(reviewed_annotations: list[dict[str, Any]], prediction: dict[str, Any] | None = None) -> dict[str, Any]:
    status_counts = Counter(str(item.get("review_status") or "suggested") for item in reviewed_annotations)
    type_counts = Counter(str(item.get("entity_type") or "Unknown") for item in reviewed_annotations)
    return {
        "generated_at": utc_now_iso(),
        "pdf_number": prediction.get("pdf_number") if prediction else None,
        "total_reviewed_annotations": len(reviewed_annotations),
        "status_counts": dict(sorted(status_counts.items())),
        "entity_type_counts": dict(sorted(type_counts.items())),
    }


def save_upload_review(run_id: str, reviewed_annotations: list[dict[str, Any]], prediction: dict[str, Any], upload_runs_dir: str | Path = DEFAULT_UPLOAD_RUNS_DIR) -> tuple[Path, Path]:
    run_dir = Path(upload_runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    annotations_path = run_dir / "reviewed_annotations.json"
    summary_path = run_dir / "review_summary.json"
    annotations_path.write_text(json.dumps({
        "run_id": run_id,
        "pdf_number": prediction.get("pdf_number"),
        "paper": prediction.get("paper") or {},
        "reviewed_annotations": reviewed_annotations,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(generate_review_summary(reviewed_annotations, prediction), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return annotations_path, summary_path


def save_existing_review(
    paper_review_records: list[dict[str, Any]],
    review_dir: str | Path = DEFAULT_REVIEW_DIR,
) -> tuple[Path, Path]:
    output_dir = Path(review_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    annotations_path = output_dir / "reviewed_annotations_clean.jsonl"
    summary_path = output_dir / "review_session_summary.json"
    write_jsonl(paper_review_records, annotations_path)
    all_annotations = [ann for record in paper_review_records for ann in record.get("reviewed_annotations", [])]
    summary = generate_review_summary(all_annotations)
    summary.update({"paper_count": len(paper_review_records)})
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return annotations_path, summary_path


def copy_pdf_to_uploads(source_pdf: str | Path, run_id: str, upload_dir: str | Path = DEFAULT_UPLOAD_DIR) -> Path:
    output_dir = Path(upload_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_id}.pdf"
    shutil.copyfile(source_pdf, output_path)
    return output_path
