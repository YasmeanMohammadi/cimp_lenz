import pytest

from cmip_indexkg.evaluation.gold_schema import GoldValidationError, load_gold_jsonl, validate_gold_record


def valid_record():
    return {
        "pdf_number": "001",
        "paper": {"title": "Example"},
        "gold_annotations": {
            "Activity": ["CMIP"],
            "Experiment": ["ssp245"],
            "Frequency": ["Monthly"],
            "Source": ["ACCESS-CM2"],
            "Realm": [],
            "Variable": ["tas"],
        },
    }


def test_validate_gold_record_accepts_required_categories():
    cleaned = validate_gold_record(valid_record())
    assert cleaned["gold_annotations"]["Activity"] == ["CMIP"]


def test_validate_gold_record_rejects_missing_category():
    record = valid_record()
    del record["gold_annotations"]["Variable"]
    with pytest.raises(GoldValidationError):
        validate_gold_record(record)


def test_load_seed_gold_jsonl():
    records = load_gold_jsonl("data/evaluation/gold_seed.example.jsonl")
    assert len(records) == 5
