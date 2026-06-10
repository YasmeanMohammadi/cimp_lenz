import json
from datetime import datetime, timezone
from pathlib import Path

from cmip_indexkg.ui.review_service import (
    create_manual_annotation,
    create_uploaded_paper_record,
    generate_review_summary,
    generate_run_id,
    run_baseline_on_pdf_record,
    search_vocab,
    serialize_reviewed_annotation,
)


def vocab_record(entity_type="Activity", canonical_id="CMIP", kg_id="kg:cmip", aliases=None):
    return {
        "kg_entity_id": kg_id,
        "kg_node_label": entity_type,
        "entity_type": entity_type,
        "canonical_id": canonical_id,
        "label": canonical_id,
        "aliases": aliases or [canonical_id],
        "source_properties": {"name": canonical_id},
    }


def write_jsonl(path: Path, records):
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def write_mappings(path: Path):
    path.write_text(json.dumps({
        "Activity": {},
        "Experiment": {},
        "Frequency": {},
        "Source": {},
        "Realm": {},
        "Variable": {},
    }) + "\n", encoding="utf-8")


def make_pdf(path: Path, text: str):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_run_id_generation_is_sanitized_and_timestamped():
    now = datetime(2026, 6, 10, 12, 30, tzinfo=timezone.utc)

    assert generate_run_id("My Paper (draft).pdf", now=now) == "20260610T123000Z_My-Paper-draft"


def test_uploaded_paper_record_creation_preserves_metadata(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    record = create_uploaded_paper_record(
        "run-1",
        pdf,
        title="A title",
        doi="10.example/test",
        year="2025",
        authors="A. One; B. Two",
        source_url="https://example.test",
    )

    assert record["pdf_number"] == "run-1"
    assert record["paper"]["local_pdf_path"] == str(pdf)
    assert record["paper"]["year"] == 2025
    assert record["paper"]["authors"] == ["A. One", "B. Two"]
    assert set(record["gold_annotations"]) == {"Activity", "Experiment", "Frequency", "Source", "Realm", "Variable"}


def test_reviewed_annotation_serialization_preserves_prediction_fields():
    annotation = {
        "entity_type": "Experiment",
        "kg_entity_id": "kg:ssp245",
        "canonical_id": "ssp245",
        "canonical_label": "ssp245",
        "matched_texts": ["SSP2-4.5"],
        "mention_count": 1,
        "confidence": 0.9,
        "mapping_method": "alias_lookup",
        "evidence": [{"page_number": 1, "sentence_id": "p1-s1", "sentence_text": "SSP2-4.5 was used."}],
    }
    corrected_to = {"kg_entity_id": "kg:ssp585", "canonical_id": "ssp585", "canonical_label": "ssp585", "entity_type": "Experiment"}

    reviewed = serialize_reviewed_annotation(annotation, review_status="corrected", review_notes="wrong scenario", corrected_to=corrected_to, reviewed_at="2026-06-10T00:00:00+00:00")

    assert reviewed["kg_entity_id"] == "kg:ssp245"
    assert reviewed["review_status"] == "corrected"
    assert reviewed["review_notes"] == "wrong scenario"
    assert reviewed["corrected_to"] == corrected_to
    assert reviewed["original_annotation"] == annotation


def test_review_summary_counts_status_and_entity_type():
    reviewed = [
        {"review_status": "accepted", "entity_type": "Activity"},
        {"review_status": "rejected", "entity_type": "Activity"},
        {"review_status": "manual", "entity_type": "Experiment"},
    ]

    summary = generate_review_summary(reviewed, {"pdf_number": "003"})

    assert summary["pdf_number"] == "003"
    assert summary["total_reviewed_annotations"] == 3
    assert summary["status_counts"] == {"accepted": 1, "manual": 1, "rejected": 1}
    assert summary["entity_type_counts"] == {"Activity": 2, "Experiment": 1}


def test_vocab_search_supports_entity_type_canonical_id_and_label():
    records = [
        vocab_record("Experiment", "ssp245", "kg:ssp245", ["SSP2-4.5"]),
        vocab_record("Source", "ACCESS-CM2", "kg:access", ["ACCESS CM2"]),
    ]

    assert [record["canonical_id"] for record in search_vocab(records, "SSP2", entity_type="Experiment")] == ["ssp245"]
    assert [record["canonical_id"] for record in search_vocab(records, "ACCESS", entity_type="Source")] == ["ACCESS-CM2"]
    assert search_vocab(records, "ACCESS", entity_type="Experiment") == []


def test_manual_annotation_serialization_uses_selected_entity():
    manual = create_manual_annotation(vocab_record("Source", "ACCESS-CM2", "kg:access"), note="missing model")

    assert manual["review_status"] == "manual"
    assert manual["entity_type"] == "Source"
    assert manual["kg_entity_id"] == "kg:access"
    assert manual["review_notes"] == "missing model"
    assert manual["evidence"] == []


def test_run_baseline_on_pdf_record_without_streamlit_rendering(tmp_path):
    pdf = tmp_path / "paper.pdf"
    make_pdf(pdf, "This paper analyzes CMIP simulations.")
    vocab = tmp_path / "vocab.jsonl"
    mappings = tmp_path / "canonical.json"
    run_dir = tmp_path / "run"
    write_jsonl(vocab, [vocab_record("Activity", "CMIP", "kg:cmip", ["CMIP"])])
    write_mappings(mappings)
    record = create_uploaded_paper_record("upload-1", pdf, title="Uploaded")

    parsed, prediction = run_baseline_on_pdf_record(record, vocab, mappings, run_dir)

    assert parsed["pdf_number"] == "upload-1"
    assert (run_dir / "parsed_document.json").exists()
    assert (run_dir / "predictions.json").exists()
    assert prediction["annotations"][0]["kg_entity_id"] == "kg:cmip"
    assert prediction["annotations"][0]["evidence"][0]["page_number"] == 1
