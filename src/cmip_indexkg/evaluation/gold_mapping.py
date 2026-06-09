"""Map CMIP website gold labels to exported ClimateKG vocabulary records."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from cmip_indexkg.config import TARGET_ENTITY_TYPES
from cmip_indexkg.evaluation.gold_schema import load_gold_jsonl
from cmip_indexkg.extraction.normalization import compact_key, normalize_text
from cmip_indexkg.kg.vocabulary_export import read_jsonl, write_jsonl

DEFAULT_CANONICAL_MAPPINGS_PATH = Path("config/canonical_mappings.json")


def load_canonical_mappings(path: str | Path | None = DEFAULT_CANONICAL_MAPPINGS_PATH) -> dict[str, dict[str, str]]:
    """Load manually reviewed equivalent-label mappings by entity type."""

    if path is None:
        return {entity_type: {} for entity_type in TARGET_ENTITY_TYPES}

    mapping_path = Path(path)
    if not mapping_path.exists():
        return {entity_type: {} for entity_type in TARGET_ENTITY_TYPES}

    with mapping_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    mappings: dict[str, dict[str, str]] = {}
    for entity_type in TARGET_ENTITY_TYPES:
        entity_mappings = raw.get(entity_type, {})
        if not isinstance(entity_mappings, dict):
            raise ValueError(f"Canonical mappings for {entity_type} must be an object")
        mappings[entity_type] = {str(key): str(value) for key, value in entity_mappings.items()}
    return mappings


def _canonical_lookup(mappings: dict[str, dict[str, str]]) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for entity_type, entity_mappings in mappings.items():
        for source_label, canonical_label in entity_mappings.items():
            for key in (source_label, normalize_text(source_label), compact_key(source_label)):
                if key:
                    lookup[(entity_type, key)] = canonical_label
    return lookup


def _manual_canonical_label(canonical_lookup: dict[tuple[str, str], str], entity_type: str, value: object) -> str | None:
    text = str(value or "")
    for key in (text, normalize_text(text), compact_key(text)):
        if key and (entity_type, key) in canonical_lookup:
            return canonical_lookup[(entity_type, key)]
    return None


def build_vocab_lookup(vocab_records: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    lookup: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in vocab_records:
        entity_type = record.get("entity_type")
        if entity_type not in TARGET_ENTITY_TYPES:
            continue
        keys = set(record.get("normalized_aliases") or []) | set(record.get("compact_aliases") or [])
        keys.add(normalize_text(record.get("label", "")))
        keys.add(compact_key(record.get("label", "")))
        keys.add(normalize_text(record.get("canonical_id", "")))
        keys.add(compact_key(record.get("canonical_id", "")))
        for key in keys:
            if key:
                lookup[(entity_type, key)].append(record)
    return lookup


def _match_label(lookup: dict[tuple[str, str], list[dict[str, Any]]], category: str, label: str) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for key in (normalize_text(label), compact_key(label)):
        for record in lookup.get((category, key), []):
            candidates[record["kg_entity_id"]] = record
    return list(candidates.values())


def _match_labels(lookup: dict[tuple[str, str], list[dict[str, Any]]], category: str, labels: list[str]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for label in labels:
        for record in _match_label(lookup, category, label):
            candidates[record["kg_entity_id"]] = record
    return list(candidates.values())


def _candidate_payload(match: dict[str, Any]) -> dict[str, Any]:
    return {
        "kg_entity_id": match["kg_entity_id"],
        "canonical_id": match["canonical_id"],
        "label": match["label"],
        "kg_node_label": match["kg_node_label"],
    }


def _candidate_canonical_label(
    match: dict[str, Any],
    entity_type: str,
    canonical_lookup: dict[tuple[str, str], str],
) -> tuple[str, bool]:
    for value in (match.get("canonical_id"), match.get("label")):
        manual_label = _manual_canonical_label(canonical_lookup, entity_type, value)
        if manual_label:
            return manual_label, True
    return str(match["canonical_id"]), False


def _mapped_record(
    base: dict[str, Any],
    primary: dict[str, Any],
    canonical_label: str,
    mapping_method: str,
    candidates: list[dict[str, Any]],
    source_config: str | None,
) -> dict[str, Any]:
    return base | {
        "kg_entity_id": primary["kg_entity_id"],
        "canonical_id": canonical_label,
        "canonical_label": canonical_label,
        "label": primary["label"],
        "kg_node_label": primary["kg_node_label"],
        "mapping_status": "mapped",
        "mapping_method": mapping_method,
        "source_config": source_config,
        "matched_candidates": [_candidate_payload(item) for item in candidates],
    }


def map_gold_to_vocab(
    gold_path: str | Path,
    vocab_path: str | Path,
    output_dir: str | Path,
    canonical_mappings_path: str | Path | None = DEFAULT_CANONICAL_MAPPINGS_PATH,
) -> dict[str, int]:
    gold_records = load_gold_jsonl(gold_path)
    vocab_records = read_jsonl(vocab_path)
    lookup = build_vocab_lookup(vocab_records)
    canonical_lookup = _canonical_lookup(load_canonical_mappings(canonical_mappings_path))
    source_config = str(canonical_mappings_path) if canonical_mappings_path else None

    mapped: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []

    for record in gold_records:
        pdf_number = record["pdf_number"]
        for category in TARGET_ENTITY_TYPES:
            for website_label in record["gold_annotations"][category]:
                raw_canonical_label = _manual_canonical_label(canonical_lookup, category, website_label)
                match_labels = [website_label]
                mapping_method_hint = "alias_lookup"
                if raw_canonical_label:
                    match_labels.append(raw_canonical_label)
                    mapping_method_hint = "manual_alias_mapping"
                matches = _match_labels(lookup, category, match_labels)
                base = {
                    "pdf_number": pdf_number,
                    "entity_type": category,
                    "website_label": website_label,
                    "raw_label": website_label,
                }

                if len(matches) == 1:
                    match = matches[0]
                    candidate_canonical_label, candidate_used_manual = _candidate_canonical_label(match, category, canonical_lookup)
                    canonical_label = raw_canonical_label or candidate_canonical_label
                    mapping_method = "manual_canonical_mapping" if candidate_used_manual else mapping_method_hint
                    mapped.append(_mapped_record(base, match, canonical_label, mapping_method, [match], source_config))
                    continue

                if not matches:
                    unresolved.append(base | {
                        "mapping_status": "unresolved",
                        "mapping_method": "manual_alias_mapping" if raw_canonical_label else "alias_lookup",
                        "source_config": source_config,
                        "canonical_label": raw_canonical_label,
                        "normalized_label": normalize_text(website_label),
                        "compact_label": compact_key(website_label),
                    })
                    continue

                grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
                used_manual = bool(raw_canonical_label)
                for match in matches:
                    candidate_canonical_label, candidate_used_manual = _candidate_canonical_label(match, category, canonical_lookup)
                    used_manual = used_manual or candidate_used_manual
                    grouped[raw_canonical_label or candidate_canonical_label].append(match)

                if len(grouped) == 1:
                    canonical_label, collapsed_matches = next(iter(grouped.items()))
                    mapping_method = "manual_canonical_mapping" if used_manual else "collapsed_same_canonical_id"
                    mapped.append(_mapped_record(base, collapsed_matches[0], canonical_label, mapping_method, collapsed_matches, source_config))
                else:
                    ambiguous.append(base | {
                        "mapping_status": "ambiguous",
                        "mapping_method": "manual_alias_mapping" if raw_canonical_label else "alias_lookup",
                        "source_config": source_config,
                        "canonical_label": raw_canonical_label,
                        "candidate_count": len(matches),
                        "canonical_target_count": len(grouped),
                        "candidates": [_candidate_payload(item) for item in matches],
                    })

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(mapped, out_dir / "gold_mapped.jsonl")
    write_jsonl(unresolved, out_dir / "gold_unresolved.jsonl")
    write_jsonl(ambiguous, out_dir / "gold_ambiguous.jsonl")
    summary = {"mapped": len(mapped), "unresolved": len(unresolved), "ambiguous": len(ambiguous)}
    (out_dir / "gold_mapping_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
