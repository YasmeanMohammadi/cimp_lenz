"""Configuration for Phase 0 target ClimateKG entity types."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_ENTITY_TYPES = ("Activity", "Experiment", "Frequency", "Source", "Realm", "Variable")
DEFAULT_CONFIG_PATH = Path("config/entity_types.json")
DEFAULT_ENV_PATH = Path(".env")


@dataclass(frozen=True)
class EntityTypeConfig:
    category: str
    kg_node_label: str
    canonical_id_fields: tuple[str, ...]


def load_entity_type_config(path: str | Path = DEFAULT_CONFIG_PATH) -> tuple[list[EntityTypeConfig], list[str]]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)

    entity_types = [
        EntityTypeConfig(
            category=item["category"],
            kg_node_label=item["kg_node_label"],
            canonical_id_fields=tuple(item.get("canonical_id_fields", [])),
        )
        for item in raw.get("target_entity_types", [])
    ]
    categories = [item.category for item in entity_types]
    missing = sorted(set(TARGET_ENTITY_TYPES) - set(categories))
    extra = sorted(set(categories) - set(TARGET_ENTITY_TYPES))
    if missing or extra:
        raise ValueError(f"Entity config must contain exactly {TARGET_ENTITY_TYPES}; missing={missing}, extra={extra}")
    return entity_types, list(raw.get("label_fields", []))


def config_by_category(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, EntityTypeConfig]:
    entity_types, _ = load_entity_type_config(path)
    return {item.category: item for item in entity_types}


def load_dotenv(path: str | Path = DEFAULT_ENV_PATH) -> None:
    """Load simple KEY=VALUE entries without overriding existing environment values."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value
