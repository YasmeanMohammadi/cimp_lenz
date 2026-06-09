"""Alias generation for exported ClimateKG vocabulary instances."""

from __future__ import annotations

import re
from collections.abc import Iterable

from cmip_indexkg.extraction.normalization import compact_key, normalize_text

_FREQUENCY_ALIASES = {
    "monthly": {"Monthly", "monthly", "mon"},
    "mon": {"Monthly", "monthly", "mon"},
    "daily": {"Daily", "daily", "day"},
    "day": {"Daily", "daily", "day"},
}

_VARIABLE_LABEL_ALIASES = {
    "tas": {"tas", "near-surface air temperature"},
    "pr": {"pr", "precipitation"},
    "tos": {"tos", "sea surface temperature"},
    "psl": {"psl", "sea level pressure"},
    "ua": {"ua", "eastward wind"},
    "va": {"va", "northward wind"},
}


def _string_values(values: Iterable[object]) -> set[str]:
    aliases: set[str] = set()
    for value in values:
        if isinstance(value, str) and value.strip():
            aliases.add(value.strip())
    return aliases


def _experiment_aliases(label: str) -> set[str]:
    aliases: set[str] = set()
    match = re.fullmatch(r"ssp(\d)(\d)(\d)", label.lower())
    if match:
        family, forcing_a, forcing_b = match.groups()
        aliases.update({
            label.lower(),
            label.upper(),
            f"SSP{family}-{forcing_a}.{forcing_b}",
            f"SSP{family} {forcing_a}.{forcing_b}",
            f"ssp{family}-{forcing_a}.{forcing_b}",
        })
    return aliases


def generate_aliases(entity_type: str, label: str, canonical_id: str | None = None, source_properties: dict[str, object] | None = None) -> list[str]:
    """Generate conservative aliases for a vocabulary entity.

    Variable aliases are intentionally limited because short variable IDs are ambiguous in prose.
    """
    props = source_properties or {}
    aliases = _string_values([label, canonical_id])

    for key in (
        "alias",
        "aliases",
        "alt_label",
        "altLabels",
        "names",
        "long_name",
        "standard_name",
        "cf_standard_name",
        "short_name",
        "variable_long_name",
        "experiment_title",
    ):
        value = props.get(key)
        if isinstance(value, str):
            aliases.add(value)
        elif isinstance(value, list):
            aliases.update(_string_values(value))

    for alias in list(aliases):
        if "-" in alias:
            aliases.add(alias.replace("-", " "))
        if "_" in alias:
            aliases.add(alias.replace("_", " "))

    if entity_type == "Experiment":
        for alias in list(aliases):
            aliases.update(_experiment_aliases(alias))

    if entity_type == "Frequency":
        for alias in list(aliases):
            aliases.update(_FREQUENCY_ALIASES.get(normalize_text(alias), set()))
            aliases.update(_FREQUENCY_ALIASES.get(compact_key(alias), set()))

    if entity_type == "Variable":
        variable_aliases: set[str] = set()
        for alias in list(aliases):
            key = compact_key(alias)
            if key in _VARIABLE_LABEL_ALIASES:
                variable_aliases.update(_VARIABLE_LABEL_ALIASES[key])
        aliases.update(variable_aliases)

    return sorted(aliases, key=lambda item: (item.lower(), item))
