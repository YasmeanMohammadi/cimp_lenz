import json
from pathlib import Path

from cmip_indexkg.evaluation.baseline_metrics import evaluate_prediction_sets
from cmip_indexkg.extraction.baseline import (
    aggregate_mentions,
    build_alias_index,
    find_mentions,
    load_target_vocab,
)
from cmip_indexkg.ingestion.pdf_parser import make_sentence_id, resolve_pdf_path


def vocab_record(entity_type, canonical_id, aliases=None, kg_id=None):
    return {
        "kg_entity_id": kg_id or f"kg:{entity_type}:{canonical_id}",
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
        "Frequency": {"1-hourly": "1hr", "3-hourly": "3hr"},
        "Source": {},
        "Realm": {},
        "Variable": {},
    }) + "\n", encoding="utf-8")


def parsed_doc(text):
    return {
        "pdf_number": "001",
        "paper": {"title": "Example"},
        "paper_id": "sha256:test",
        "pdf_hash": "test",
        "sentences": [{"sentence_id": "p1-s1", "page_number": 1, "text": text}],
    }


def test_pdf_path_resolution_from_gold_jsonl(tmp_path):
    dataset = tmp_path / "dataset"
    raw = dataset / "data" / "raw"
    raw.mkdir(parents=True)
    pdf = raw / "003.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    gold = dataset / "data" / "gold_seed_clean.jsonl"
    gold.write_text("", encoding="utf-8")

    resolved = resolve_pdf_path("data/raw/003.pdf", gold_path=gold, repo_root=tmp_path)

    assert resolved == pdf


def test_sentence_id_generation():
    assert make_sentence_id(3, 12) == "p3-s12"


def test_alias_index_frequency_safe_alias_matching(tmp_path):
    mapping = tmp_path / "canonical.json"
    write_mappings(mapping)
    index = build_alias_index([vocab_record("Frequency", "mon", ["mon"])], mapping)
    doc = parsed_doc("Monthly model output was analyzed, but monsoon text should not trigger mon.")

    mentions = find_mentions(doc, index, mapping)

    assert [mention.matched_text for mention in mentions] == ["Monthly", "mon"]
    assert all(mention.canonical_label == "mon" for mention in mentions)


def test_ssp_alias_matching(tmp_path):
    mapping = tmp_path / "canonical.json"
    write_mappings(mapping)
    index = build_alias_index([vocab_record("Experiment", "ssp245", ["ssp245"])], mapping)

    mentions = find_mentions(parsed_doc("The SSP2-4.5 scenario was used."), index, mapping)

    assert len(mentions) == 1
    assert mentions[0].canonical_label == "ssp245"
    assert mentions[0].matched_text == "SSP2-4.5"


def test_short_variable_boundary_behavior(tmp_path):
    mapping = tmp_path / "canonical.json"
    write_mappings(mapping)
    index = build_alias_index([vocab_record("Variable", "pr", ["pr", "precipitation"])], mapping)

    mentions = find_mentions(parsed_doc("The project used pr and precipitation data."), index, mapping)

    assert [mention.matched_text for mention in mentions] == ["precipitation", "pr"]


def test_aggregation_multiple_mentions_one_annotation(tmp_path):
    mapping = tmp_path / "canonical.json"
    write_mappings(mapping)
    index = build_alias_index([vocab_record("Experiment", "ssp585", ["ssp585"])], mapping)
    doc = {
        "pdf_number": "001",
        "paper": {"title": "Example"},
        "paper_id": "sha256:test",
        "pdf_hash": "test",
        "sentences": [
            {"sentence_id": "p1-s1", "page_number": 1, "text": "ssp585 appears here."},
            {"sentence_id": "p2-s1", "page_number": 2, "text": "SSP5-8.5 appears here."},
        ],
    }

    prediction = aggregate_mentions(doc, find_mentions(doc, index, mapping))

    assert len(prediction["annotations"]) == 1
    annotation = prediction["annotations"][0]
    assert annotation["mention_count"] == 2
    assert {item["sentence_id"] for item in annotation["evidence"]} == {"p1-s1", "p2-s1"}


def test_evaluation_tp_fp_fn_calculation():
    gold = {("001", "Experiment", "ssp245"), ("001", "Frequency", "mon")}
    predicted = {("001", "Experiment", "ssp245"), ("001", "Source", "CanESM5")}

    metrics, errors = evaluate_prediction_sets(gold, predicted)

    assert metrics["micro"] == {"tp": 1, "fp": 1, "fn": 1, "precision": 0.5, "recall": 0.5, "f1": 0.5}
    assert {error["status"] for error in errors} == {"TP", "FP", "FN"}


def test_load_target_vocab_preserves_required_fields(tmp_path):
    vocab_path = tmp_path / "vocab.jsonl"
    write_jsonl(vocab_path, [vocab_record("Activity", "CMIP", ["CMIP"], "kg:cmip")])

    records = load_target_vocab(vocab_path)

    assert records == [{
        "kg_entity_id": "kg:cmip",
        "entity_type": "Activity",
        "kg_node_label": "Activity",
        "canonical_id": "CMIP",
        "label": "CMIP",
        "aliases": ["CMIP"],
        "source_properties": {"name": "CMIP"},
    }]
