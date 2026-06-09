"""CMIP vocabulary label normalization."""

from __future__ import annotations

import re
import unicodedata

_SEPARATORS_RE = re.compile(r"[\s_\-./]+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_text(value: object) -> str:
    """Normalize a website/KG label for deterministic lookup."""
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    text = text.replace("–", "-").replace("—", "-")
    text = _SEPARATORS_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return " ".join(text.split())


def compact_key(value: object) -> str:
    """Normalize and remove spaces for hyphen/space-insensitive matching."""
    return normalize_text(value).replace(" ", "")
