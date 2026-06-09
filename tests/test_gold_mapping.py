import json
from pathlib import Path

from cmip_indexkg.evaluation.gold_mapping import load_canonical_mappings, map_gold_to_vocab
from cmip_indexkg.kg.vocabulary_export import write_jsonl


def write_gold(path: Path, experiment_labels: list[str], frequency_labels: list[str] | None = None, source_labels: list[str] | None = None):
    record = {
        "pdf_number": "001",
        "gold_annotations": {
            "Activity": [],
            "Experiment": experiment_labels,
            "Frequency": frequency_labels or [],
            "Source": source_labels or [],
            "Realm": [],
            "Variable": [],
        },
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def vocab_record(kg_entity_id: str, canonical_id: str, aliases: list[str] | None = None, entity_type: str = "Experiment"):
    aliases = aliases or [canonical_id]
    return {
        "kg_entity_id": kg_entity_id,
        "kg_node_label": entity_type,
        "entity_type": entity_type,
        "canonical_id": canonical_id,
        "label": canonical_id,
        "aliases": aliases,
        "normalized_aliases": [alias.lower().replace("-", " ") for alias in aliases],
        "compact_aliases": ["".join(ch.lower() for ch in alias if ch.isalnum()) for alias in aliases],
        "source_properties": {},
    }


def write_canonical_mappings(path: Path, experiment_mappings: dict[str, str], frequency_mappings: dict[str, str] | None = None):
    path.write_text(
        json.dumps({
            "Activity": {},
            "Experiment": experiment_mappings,
            "Frequency": frequency_mappings or {},
            "Source": {},
            "Realm": {},
            "Variable": {},
        })
        + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_manual_canonical_equivalence_resolves_ambiguity(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    vocab_path = tmp_path / "vocab.jsonl"
    mapping_path = tmp_path / "canonical.json"
    output_dir = tmp_path / "mapping"
    write_gold(gold_path, ["abrupt-4xCO2"])
    write_jsonl(
        [
            vocab_record("kg:abrupt-hyphen", "abrupt-4xCO2", ["abrupt-4xCO2"]),
            vocab_record("kg:abrupt-compact", "abrupt4xCO2", ["abrupt4xCO2", "abrupt-4xCO2"]),
        ],
        vocab_path,
    )
    write_canonical_mappings(mapping_path, {"abrupt-4xCO2": "abrupt-4xCO2", "abrupt4xCO2": "abrupt-4xCO2"})

    summary = map_gold_to_vocab(gold_path, vocab_path, output_dir, mapping_path)

    assert summary == {"mapped": 1, "unresolved": 0, "ambiguous": 0}
    mapped = read_jsonl(output_dir / "gold_mapped.jsonl")
    assert mapped[0]["raw_label"] == "abrupt-4xCO2"
    assert mapped[0]["canonical_label"] == "abrupt-4xCO2"
    assert mapped[0]["mapping_method"] == "manual_canonical_mapping"
    assert len(mapped[0]["matched_candidates"]) == 2


def test_ambiguity_remains_without_canonical_collapse(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    vocab_path = tmp_path / "vocab.jsonl"
    mapping_path = tmp_path / "canonical.json"
    output_dir = tmp_path / "mapping"
    write_gold(gold_path, ["shared alias"])
    write_jsonl(
        [
            vocab_record("kg:a", "experiment-a", ["shared alias"]),
            vocab_record("kg:b", "experiment-b", ["shared alias"]),
        ],
        vocab_path,
    )
    write_canonical_mappings(mapping_path, {})

    summary = map_gold_to_vocab(gold_path, vocab_path, output_dir, mapping_path)

    assert summary == {"mapped": 0, "unresolved": 0, "ambiguous": 1}
    ambiguous = read_jsonl(output_dir / "gold_ambiguous.jsonl")
    assert ambiguous[0]["candidate_count"] == 2
    assert ambiguous[0]["canonical_target_count"] == 2


def test_normal_exact_mapping_still_works(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    vocab_path = tmp_path / "vocab.jsonl"
    mapping_path = tmp_path / "canonical.json"
    output_dir = tmp_path / "mapping"
    write_gold(gold_path, ["ssp245"])
    write_jsonl([vocab_record("kg:ssp245", "ssp245", ["ssp245", "SSP2-4.5"])], vocab_path)
    write_canonical_mappings(mapping_path, {})

    summary = map_gold_to_vocab(gold_path, vocab_path, output_dir, mapping_path)

    assert summary == {"mapped": 1, "unresolved": 0, "ambiguous": 0}
    mapped = read_jsonl(output_dir / "gold_mapped.jsonl")
    assert mapped[0]["canonical_label"] == "ssp245"
    assert mapped[0]["mapping_method"] == "alias_lookup"


def test_unresolved_mapping_still_works(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    vocab_path = tmp_path / "vocab.jsonl"
    mapping_path = tmp_path / "canonical.json"
    output_dir = tmp_path / "mapping"
    write_gold(gold_path, ["unknown-exp"])
    write_jsonl([vocab_record("kg:ssp245", "ssp245")], vocab_path)
    write_canonical_mappings(mapping_path, {})

    summary = map_gold_to_vocab(gold_path, vocab_path, output_dir, mapping_path)

    assert summary == {"mapped": 0, "unresolved": 1, "ambiguous": 0}
    unresolved = read_jsonl(output_dir / "gold_unresolved.jsonl")
    assert unresolved[0]["raw_label"] == "unknown-exp"


def test_frequency_manual_alias_mapping_resolves_external_alias(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    vocab_path = tmp_path / "vocab.jsonl"
    mapping_path = tmp_path / "canonical.json"
    output_dir = tmp_path / "mapping"
    write_gold(gold_path, [], frequency_labels=["1-hourly"])
    write_jsonl([vocab_record("kg:1hr", "1hr", ["1hr"], entity_type="Frequency")], vocab_path)
    write_canonical_mappings(mapping_path, {}, {"1-hourly": "1hr"})

    summary = map_gold_to_vocab(gold_path, vocab_path, output_dir, mapping_path)

    assert summary == {"mapped": 1, "unresolved": 0, "ambiguous": 0}
    mapped = read_jsonl(output_dir / "gold_mapped.jsonl")
    assert mapped[0]["website_label"] == "1-hourly"
    assert mapped[0]["raw_label"] == "1-hourly"
    assert mapped[0]["canonical_label"] == "1hr"
    assert mapped[0]["kg_entity_id"] == "kg:1hr"
    assert mapped[0]["mapping_status"] == "mapped"
    assert mapped[0]["mapping_method"] == "manual_alias_mapping"
    assert mapped[0]["source_config"] == str(mapping_path)
    assert mapped[0]["matched_candidates"] == [
        {"kg_entity_id": "kg:1hr", "canonical_id": "1hr", "label": "1hr", "kg_node_label": "Frequency"}
    ]


def test_external_mapping_does_not_resolve_unreviewed_source(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    vocab_path = tmp_path / "vocab.jsonl"
    mapping_path = tmp_path / "canonical.json"
    output_dir = tmp_path / "mapping"
    write_gold(gold_path, [], source_labels=["ACCESS1.0"])
    write_jsonl([vocab_record("kg:access-cm2", "ACCESS-CM2", ["ACCESS-CM2"], entity_type="Source")], vocab_path)
    write_canonical_mappings(mapping_path, {}, {"1-hourly": "1hr"})

    summary = map_gold_to_vocab(gold_path, vocab_path, output_dir, mapping_path)

    assert summary == {"mapped": 0, "unresolved": 1, "ambiguous": 0}
    unresolved = read_jsonl(output_dir / "gold_unresolved.jsonl")
    assert unresolved[0]["entity_type"] == "Source"
    assert unresolved[0]["raw_label"] == "ACCESS1.0"
    assert unresolved[0]["canonical_label"] is None
    assert unresolved[0]["mapping_status"] == "unresolved"
    assert unresolved[0]["source_config"] == str(mapping_path)


def test_repository_canonical_mappings_keep_source_empty():
    mappings = load_canonical_mappings("config/canonical_mappings.json")
    assert mappings["Experiment"]["abrupt4xCO2"] == "abrupt-4xCO2"
    assert mappings["Frequency"]["1-hourly"] == "1hr"
    assert mappings["Frequency"]["3-hourly"] == "3hr"
    assert mappings["Source"] == {}


def test_dataset_split_files_preserve_expected_pdf_numbers():
    clean = read_jsonl(Path("dataset/data/gold_seed_clean.jsonl"))
    challenge = read_jsonl(Path("dataset/data/gold_seed_coverage_challenge.jsonl"))
    assert [record["pdf_number"] for record in clean] == ["003", "004", "005", "006", "007"]
    assert [record["pdf_number"] for record in challenge] == ["002"]
