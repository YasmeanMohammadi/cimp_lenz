"""Rule-based KG-grounded extraction for Phase 1 clean-seed baseline."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from cmip_indexkg.config import TARGET_ENTITY_TYPES
from cmip_indexkg.evaluation.gold_mapping import load_canonical_mappings
from cmip_indexkg.evaluation.gold_schema import load_gold_jsonl
from cmip_indexkg.extraction.normalization import compact_key, normalize_text
from cmip_indexkg.ingestion.pdf_parser import parse_gold_pdfs, parse_pdf_record
from cmip_indexkg.kg.vocabulary_export import read_jsonl, write_jsonl

SHORT_VARIABLE_ALIASES = {"pr", "tas", "ua", "va"}
SAFE_VARIABLE_ALIASES = {
    "precipitation",
    "near surface air temperature",
    "eastward wind",
    "northward wind",
}
SAFE_EXTRA_ALIASES: dict[str, dict[str, set[str]]] = {
    "Frequency": {
        "mon": {"Monthly", "monthly", "mon"},
        "day": {"Daily", "daily", "day"},
        "1hr": {"1-hourly", "1 hourly", "1hr"},
        "3hr": {"3-hourly", "3 hourly", "3hr"},
    },
    "Experiment": {
        "ssp119": {"ssp119", "SSP119", "SSP1-1.9", "SSP1 1.9", "ssp1-1.9"},
        "ssp126": {"ssp126", "SSP126", "SSP1-2.6", "SSP1 2.6", "ssp1-2.6"},
        "ssp245": {"ssp245", "SSP245", "SSP2-4.5", "SSP2 4.5", "ssp2-4.5"},
        "ssp370": {"ssp370", "SSP370", "SSP3-7.0", "SSP3 7.0", "ssp3-7.0"},
        "ssp585": {"ssp585", "SSP585", "SSP5-8.5", "SSP5 8.5", "ssp5-8.5"},
    },
}


@dataclass(frozen=True)
class AliasCandidate:
    alias: str
    entity: dict[str, Any]
    method: str
    normalized_alias: str
    compact_alias: str


@dataclass(frozen=True)
class Mention:
    pdf_number: str
    entity_type: str
    kg_entity_id: str
    canonical_id: str
    canonical_label: str
    canonical_label_source: str
    matched_text: str
    sentence_id: str
    page_number: int
    char_start: int
    char_end: int
    sentence_text: str
    mapping_method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdf_number": self.pdf_number,
            "entity_type": self.entity_type,
            "kg_entity_id": self.kg_entity_id,
            "canonical_id": self.canonical_id,
            "canonical_label": self.canonical_label,
            "canonical_label_source": self.canonical_label_source,
            "matched_text": self.matched_text,
            "sentence_id": self.sentence_id,
            "page_number": self.page_number,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "sentence_text": self.sentence_text,
            "mapping_method": self.mapping_method,
        }


def _string_values(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    text = str(value).strip()
    if not text:
        return set()
    values = {text}
    if text.startswith("[") and text.endswith("]") and len(text) <= 500:
        inner = text[1:-1]
        values.update(part.strip().strip("'\"") for part in inner.split(",") if part.strip())
    return {item for item in values if item}


def _is_phase1_alias_usable(entity_type: str, alias: object) -> bool:
    raw = str(alias or "").strip()
    if not raw or len(raw) > 240:
        return False
    normalized = normalize_text(alias)
    if not normalized:
        return False
    if len(normalized) > 120 or len(normalized.split()) > 14:
        return False
    if entity_type == "Variable" and len(normalized) > 80:
        return False
    return True


def load_target_vocab(vocab_path: str | Path) -> list[dict[str, Any]]:
    """Load the read-only ClimateKG vocabulary for the six target entity types."""
    records: list[dict[str, Any]] = []
    for record in read_jsonl(vocab_path):
        if record.get("entity_type") not in TARGET_ENTITY_TYPES:
            continue
        records.append({
            "kg_entity_id": record["kg_entity_id"],
            "entity_type": record["entity_type"],
            "kg_node_label": record.get("kg_node_label", record["entity_type"]),
            "canonical_id": record.get("canonical_id") or record.get("label") or record["kg_entity_id"],
            "label": record.get("label") or record.get("canonical_id") or record["kg_entity_id"],
            "aliases": [alias for alias in list(record.get("aliases") or []) if _is_phase1_alias_usable(str(record["entity_type"]), alias)],
            "source_properties": dict(record.get("source_properties") or {}),
        })
    return records


def _manual_lookup(canonical_mappings_path: str | Path | None) -> dict[tuple[str, str], str]:
    mappings = load_canonical_mappings(canonical_mappings_path)
    lookup: dict[tuple[str, str], str] = {}
    for entity_type, values in mappings.items():
        for source, target in values.items():
            for key in {source, normalize_text(source), compact_key(source)}:
                if key:
                    lookup[(entity_type, key)] = target
    return lookup


def canonical_label_for(entity: dict[str, Any], manual_lookup: dict[tuple[str, str], str]) -> tuple[str, str]:
    entity_type = str(entity["entity_type"])
    for value in (entity.get("canonical_id"), entity.get("label")):
        for key in {str(value or ""), normalize_text(value), compact_key(value)}:
            if key and (entity_type, key) in manual_lookup:
                return manual_lookup[(entity_type, key)], "manual_canonical_mapping"
    return str(entity.get("canonical_id") or entity.get("label") or entity["kg_entity_id"]), "canonical_id"


def aliases_for_entity(entity: dict[str, Any], canonical_mappings: dict[str, dict[str, str]]) -> set[str]:
    entity_type = str(entity["entity_type"])
    aliases: set[str] = set()
    aliases.update(_string_values(entity.get("label")))
    aliases.update(_string_values(entity.get("canonical_id")))
    aliases.update(_string_values(entity.get("aliases")))
    props = entity.get("source_properties") or {}
    for key in ("alias", "aliases", "name", "names", "long_name", "standard_name", "cf_standard_name", "short_name", "variable_long_name", "experiment_title"):
        aliases.update(_string_values(props.get(key)))

    for source, target in canonical_mappings.get(entity_type, {}).items():
        if target in aliases or normalize_text(target) in {normalize_text(item) for item in aliases} or compact_key(target) in {compact_key(item) for item in aliases}:
            aliases.add(source)
            aliases.add(target)

    for key, safe_aliases in SAFE_EXTRA_ALIASES.get(entity_type, {}).items():
        if key == compact_key(entity.get("canonical_id")) or key == compact_key(entity.get("label")):
            aliases.update(safe_aliases)

    expanded = set(aliases)
    for alias in aliases:
        if "-" in alias:
            expanded.add(alias.replace("-", " "))
        if "_" in alias:
            expanded.add(alias.replace("_", " "))
    filtered: set[str] = set()
    for alias in expanded:
        alias = alias.strip()
        normalized = normalize_text(alias)
        if not alias or not normalized:
            continue
        if not _is_phase1_alias_usable(entity_type, alias):
            continue
        filtered.add(alias)
    return filtered


def build_alias_index(vocab_records: list[dict[str, Any]], canonical_mappings_path: str | Path | None) -> list[AliasCandidate]:
    """Build an external alias index and drop aliases that point to competing KG entities."""
    canonical_mappings = load_canonical_mappings(canonical_mappings_path)
    grouped: dict[tuple[str, str], list[AliasCandidate]] = defaultdict(list)
    for entity in vocab_records:
        entity_type = str(entity["entity_type"])
        for alias in aliases_for_entity(entity, canonical_mappings):
            normalized_alias = normalize_text(alias)
            if not normalized_alias:
                continue
            compact_alias = compact_key(alias)
            if entity_type == "Variable":
                is_safe_short_variable = compact_alias in SHORT_VARIABLE_ALIASES
                is_descriptive_variable = normalized_alias in SAFE_VARIABLE_ALIASES
                if not (is_safe_short_variable or is_descriptive_variable):
                    continue
            key = (entity_type, normalized_alias)
            grouped[key].append(
                AliasCandidate(
                    alias=alias,
                    entity=entity,
                    method="alias_lookup",
                    normalized_alias=normalized_alias,
                    compact_alias=compact_alias,
                )
            )

    candidates: list[AliasCandidate] = []
    seen: set[tuple[str, str]] = set()
    for (_entity_type, _alias_key), items in grouped.items():
        canonical_targets = {str(item.entity.get("canonical_id")) for item in items}
        if len(canonical_targets) > 1:
            continue
        for item in items:
            key = (item.alias, item.entity["kg_entity_id"])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(item)
    candidates.sort(key=lambda item: (-len(item.alias), item.entity["entity_type"], item.alias.lower(), item.entity["kg_entity_id"]))
    return candidates


@lru_cache(maxsize=8192)
def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def find_mentions_in_sentence(
    sentence: dict[str, Any],
    pdf_number: str,
    alias_index: Iterable[AliasCandidate],
    manual_lookup: dict[tuple[str, str], str],
) -> list[Mention]:
    text = str(sentence.get("text") or "")
    normalized_text = normalize_text(text)
    compact_text = compact_key(text)
    mentions: list[Mention] = []
    seen: set[tuple[str, int, int]] = set()
    for candidate in alias_index:
        if candidate.normalized_alias not in normalized_text and candidate.compact_alias not in compact_text:
            continue
        for match in _alias_pattern(candidate.alias).finditer(text):
            dedupe_key = (candidate.entity["kg_entity_id"], match.start(), match.end())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            canonical_label, label_source = canonical_label_for(candidate.entity, manual_lookup)
            mentions.append(Mention(
                pdf_number=pdf_number,
                entity_type=candidate.entity["entity_type"],
                kg_entity_id=candidate.entity["kg_entity_id"],
                canonical_id=str(candidate.entity.get("canonical_id") or ""),
                canonical_label=canonical_label,
                canonical_label_source=label_source,
                matched_text=match.group(0),
                sentence_id=str(sentence["sentence_id"]),
                page_number=int(sentence["page_number"]),
                char_start=match.start(),
                char_end=match.end(),
                sentence_text=text,
                mapping_method=candidate.method,
            ))
    return mentions


def find_mentions(parsed_document: dict[str, Any], alias_index: Iterable[AliasCandidate], canonical_mappings_path: str | Path | None) -> list[Mention]:
    manual_lookup = _manual_lookup(canonical_mappings_path)
    mentions: list[Mention] = []
    for sentence in parsed_document.get("sentences") or []:
        mentions.extend(find_mentions_in_sentence(sentence, str(parsed_document["pdf_number"]), alias_index, manual_lookup))
    return mentions


def aggregate_mentions(parsed_document: dict[str, Any], mentions: list[Mention]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[Mention]] = defaultdict(list)
    for mention in mentions:
        grouped[(mention.entity_type, mention.kg_entity_id)].append(mention)

    annotations: list[dict[str, Any]] = []
    for (_entity_type, _kg_entity_id), entity_mentions in sorted(grouped.items(), key=lambda item: (item[0][0], item[1][0].canonical_label, item[0][1])):
        first = entity_mentions[0]
        evidence = []
        seen_sentences: set[str] = set()
        for mention in entity_mentions:
            if mention.sentence_id in seen_sentences:
                continue
            seen_sentences.add(mention.sentence_id)
            evidence.append({
                "page_number": mention.page_number,
                "sentence_id": mention.sentence_id,
                "matched_text": mention.matched_text,
                "char_start": mention.char_start,
                "char_end": mention.char_end,
                "sentence_text": mention.sentence_text,
            })
            if len(evidence) == 3:
                break
        annotations.append({
            "pdf_number": first.pdf_number,
            "entity_type": first.entity_type,
            "kg_entity_id": first.kg_entity_id,
            "canonical_id": first.canonical_id,
            "canonical_label": first.canonical_label,
            "canonical_label_source": first.canonical_label_source,
            "matched_texts": sorted({mention.matched_text for mention in entity_mentions}, key=lambda item: (item.lower(), item)),
            "mention_count": len(entity_mentions),
            "confidence": min(0.99, 0.65 + 0.08 * min(len(entity_mentions), 4)),
            "mapping_method": first.mapping_method,
            "evidence": evidence,
        })

    return {
        "pdf_number": parsed_document["pdf_number"],
        "paper": parsed_document.get("paper") or {},
        "paper_id": parsed_document.get("paper_id"),
        "pdf_hash": parsed_document.get("pdf_hash"),
        "annotations": annotations,
    }


def extract_predictions_from_parsed(
    gold_path: str | Path,
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
    parsed_output_dir: str | Path,
    predictions_output: str | Path,
) -> list[dict[str, Any]]:
    gold_records = load_gold_jsonl(gold_path)
    vocab = load_target_vocab(vocab_path)
    alias_index = build_alias_index(vocab, canonical_mappings_path)
    predictions: list[dict[str, Any]] = []
    parsed_dir = Path(parsed_output_dir)
    for record in gold_records:
        parsed_path = parsed_dir / f"{record['pdf_number']}.parsed.json"
        parsed_document = json.loads(parsed_path.read_text(encoding="utf-8"))
        mentions = find_mentions(parsed_document, alias_index, canonical_mappings_path)
        predictions.append(aggregate_mentions(parsed_document, mentions))
    write_jsonl(predictions, predictions_output)
    return predictions


def run_baseline_on_document(
    parsed_document: dict[str, Any],
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
) -> dict[str, Any]:
    """Run Phase 1 matching on one parsed document dictionary."""
    vocab = load_target_vocab(vocab_path)
    alias_index = build_alias_index(vocab, canonical_mappings_path)
    mentions = find_mentions(parsed_document, alias_index, canonical_mappings_path)
    return aggregate_mentions(parsed_document, mentions)


def run_baseline_on_pdf(
    paper_record: dict[str, Any],
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
    parsed_output_path: str | Path | None = None,
    predictions_output_path: str | Path | None = None,
    gold_path: str | Path = ".",
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Parse and extract predictions for one paper record without batch gold files."""
    parsed_document = parse_pdf_record(paper_record, gold_path=gold_path, repo_root=repo_root)
    parsed_dict = parsed_document.to_dict()
    prediction = run_baseline_on_document(parsed_dict, vocab_path, canonical_mappings_path)

    if parsed_output_path:
        parsed_path = Path(parsed_output_path)
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_path.write_text(json.dumps(parsed_dict, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if predictions_output_path:
        prediction_path = Path(predictions_output_path)
        prediction_path.parent.mkdir(parents=True, exist_ok=True)
        prediction_path.write_text(json.dumps(prediction, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return prediction


def run_baseline_extraction(
    gold_path: str | Path,
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
    parsed_output_dir: str | Path,
    predictions_output: str | Path,
    metrics_output: str | Path,
    errors_output: str | Path,
) -> dict[str, Any]:
    from cmip_indexkg.evaluation.baseline_metrics import evaluate_predictions

    parse_summary = parse_gold_pdfs(
        gold_path=gold_path,
        output_dir=parsed_output_dir,
        summary_output=Path(parsed_output_dir) / "parse_summary_clean.json",
    )
    if parse_summary["total_failed"]:
        failed = [
            f"{paper['pdf_number']}: {paper.get('error')}"
            for paper in parse_summary["papers"]
            if paper.get("status") != "parsed"
        ]
        raise RuntimeError(f"PDF parsing failed for {parse_summary['total_failed']} papers: {'; '.join(failed)}")
    predictions = extract_predictions_from_parsed(
        gold_path=gold_path,
        vocab_path=vocab_path,
        canonical_mappings_path=canonical_mappings_path,
        parsed_output_dir=parsed_output_dir,
        predictions_output=predictions_output,
    )
    metrics = evaluate_predictions(
        gold_path=gold_path,
        vocab_path=vocab_path,
        canonical_mappings_path=canonical_mappings_path,
        predictions=predictions,
        metrics_output=metrics_output,
        errors_output=errors_output,
    )
    return {"parse_summary": parse_summary, "metrics": metrics}
