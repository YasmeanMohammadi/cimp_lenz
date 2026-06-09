"""ClimateKG vocabulary export and lookup construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cmip_indexkg.config import EntityTypeConfig, load_entity_type_config
from cmip_indexkg.extraction.aliases import generate_aliases
from cmip_indexkg.extraction.normalization import compact_key, normalize_text
from cmip_indexkg.kg.neo4j_client import ClimateKGClient

DEFAULT_VOCAB_PATH = Path("data/vocab/climatekg_vocab.jsonl")


def pick_first_property(properties: dict[str, Any], fields: list[str] | tuple[str, ...]) -> str | None:
    for field in fields:
        value = properties.get(field)
        if isinstance(value, list):
            for item in value:
                if item is not None and str(item).strip():
                    return str(item).strip()
            continue
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def build_vocab_record(raw_node: dict[str, Any], config: EntityTypeConfig, label_fields: list[str]) -> dict[str, Any]:
    properties = dict(raw_node.get("properties") or {})
    canonical_id = pick_first_property(properties, config.canonical_id_fields)
    label = pick_first_property(properties, label_fields) or canonical_id or raw_node["kg_entity_id"]
    if canonical_id is None:
        canonical_id = label
    aliases = generate_aliases(config.category, label, canonical_id, properties)
    return {
        "kg_entity_id": raw_node["kg_entity_id"],
        "kg_node_label": config.kg_node_label,
        "entity_type": config.category,
        "canonical_id": canonical_id,
        "label": label,
        "aliases": aliases,
        "normalized_aliases": sorted({normalize_text(alias) for alias in aliases if normalize_text(alias)}),
        "compact_aliases": sorted({compact_key(alias) for alias in aliases if compact_key(alias)}),
        "source_properties": properties,
        "kg_labels": raw_node.get("labels", []),
    }


def write_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}: {exc}") from exc
    return records


def export_vocabulary(client: ClimateKGClient, config_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    entity_configs, label_fields = load_entity_type_config(config_path)
    records: list[dict[str, Any]] = []
    for entity_config in entity_configs:
        for raw_node in client.export_nodes(entity_config.kg_node_label):
            records.append(build_vocab_record(raw_node, entity_config, label_fields))
    records.sort(key=lambda item: (item["entity_type"], item["canonical_id"].lower(), item["kg_entity_id"]))
    write_jsonl(records, output_path)
    return records


def inspect_schema(client: ClimateKGClient, config_path: str | Path, sample_limit: int = 5) -> list[dict[str, Any]]:
    entity_configs, _ = load_entity_type_config(config_path)
    summary: list[dict[str, Any]] = []
    counts = {row["kg_node_label"]: row["count"] for row in client.count_by_label(item.kg_node_label for item in entity_configs)}
    for entity_config in entity_configs:
        samples = client.sample_nodes(entity_config.kg_node_label, limit=sample_limit)
        property_names = sorted({key for sample in samples for key in (sample.get("properties") or {}).keys()})
        summary.append({
            "category": entity_config.category,
            "kg_node_label": entity_config.kg_node_label,
            "count": counts.get(entity_config.kg_node_label, 0),
            "configured_canonical_id_fields": list(entity_config.canonical_id_fields),
            "sample_property_names": property_names,
            "sample_nodes": samples,
        })
    return summary
