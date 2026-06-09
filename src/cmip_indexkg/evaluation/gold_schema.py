"""Manual validator for CMIP website gold annotation JSON/JSONL records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cmip_indexkg.config import TARGET_ENTITY_TYPES


class GoldValidationError(ValueError):
    """Raised when a gold annotation record violates the Phase 0 schema."""


def _validate_string_list(record_path: str, value: Any) -> list[str]:
    if not isinstance(value, list):
        raise GoldValidationError(f"{record_path} must be a list of strings")
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise GoldValidationError(f"{record_path}[{index}] must be a string")
    # Preserve website spelling while deduplicating exact duplicates.
    return list(dict.fromkeys(value))


def validate_gold_record(record: dict[str, Any], line_number: int | None = None) -> dict[str, Any]:
    prefix = f"line {line_number}: " if line_number else ""
    if not isinstance(record, dict):
        raise GoldValidationError(f"{prefix}record must be an object")
    if not isinstance(record.get("pdf_number"), str) or not record["pdf_number"].strip():
        raise GoldValidationError(f"{prefix}pdf_number is required and must be a non-empty string")
    paper = record.get("paper")
    if paper is not None and not isinstance(paper, dict):
        raise GoldValidationError(f"{prefix}paper must be an object when provided")
    annotations = record.get("gold_annotations")
    if not isinstance(annotations, dict):
        raise GoldValidationError(f"{prefix}gold_annotations is required and must be an object")

    annotation_keys = set(annotations)
    expected = set(TARGET_ENTITY_TYPES)
    missing = sorted(expected - annotation_keys)
    extra = sorted(annotation_keys - expected)
    if missing or extra:
        raise GoldValidationError(f"{prefix}gold_annotations must contain exactly {sorted(expected)}; missing={missing}, extra={extra}")

    cleaned = dict(record)
    cleaned_annotations: dict[str, list[str]] = {}
    for category in TARGET_ENTITY_TYPES:
        cleaned_annotations[category] = _validate_string_list(f"{prefix}gold_annotations.{category}", annotations[category])
    cleaned["gold_annotations"] = cleaned_annotations
    return cleaned


def load_gold_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GoldValidationError(f"line {line_number}: invalid JSON: {exc}") from exc
            records.append(validate_gold_record(record, line_number=line_number))
    return records


def validate_gold_jsonl(path: str | Path) -> tuple[int, list[dict[str, Any]]]:
    records = load_gold_jsonl(path)
    return len(records), records
