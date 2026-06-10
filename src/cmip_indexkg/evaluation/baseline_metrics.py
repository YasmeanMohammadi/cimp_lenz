"""Evaluation for Phase 1 clean-seed baseline predictions."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from cmip_indexkg.config import TARGET_ENTITY_TYPES
from cmip_indexkg.evaluation.gold_mapping import _candidate_canonical_label, _canonical_lookup, _match_labels, _manual_canonical_label, build_vocab_lookup, load_canonical_mappings
from cmip_indexkg.evaluation.gold_schema import load_gold_jsonl
from cmip_indexkg.kg.vocabulary_export import read_jsonl, write_jsonl

EvalKey = tuple[str, str, str]


def _gold_keys(gold_path: str | Path, vocab_path: str | Path, canonical_mappings_path: str | Path | None) -> tuple[set[EvalKey], list[dict[str, Any]]]:
    gold_records = load_gold_jsonl(gold_path)
    vocab_lookup = build_vocab_lookup(read_jsonl(vocab_path))
    canonical_lookup = _canonical_lookup(load_canonical_mappings(canonical_mappings_path))
    keys: set[EvalKey] = set()
    unresolved: list[dict[str, Any]] = []

    for record in gold_records:
        pdf_number = record["pdf_number"]
        for entity_type in TARGET_ENTITY_TYPES:
            for website_label in record["gold_annotations"][entity_type]:
                raw_canonical = _manual_canonical_label(canonical_lookup, entity_type, website_label)
                match_labels = [website_label] + ([raw_canonical] if raw_canonical else [])
                matches = _match_labels(vocab_lookup, entity_type, match_labels)
                if not matches:
                    unresolved.append({
                        "pdf_number": pdf_number,
                        "entity_type": entity_type,
                        "website_label": website_label,
                        "status": "unresolved_gold_label",
                    })
                    keys.add((pdf_number, entity_type, raw_canonical or website_label))
                    continue
                canonical_labels = set()
                for match in matches:
                    candidate_canonical, _used_manual = _candidate_canonical_label(match, entity_type, canonical_lookup)
                    canonical_labels.add(raw_canonical or candidate_canonical)
                if len(canonical_labels) == 1:
                    keys.add((pdf_number, entity_type, next(iter(canonical_labels))))
                else:
                    unresolved.append({
                        "pdf_number": pdf_number,
                        "entity_type": entity_type,
                        "website_label": website_label,
                        "status": "ambiguous_gold_label",
                        "canonical_labels": sorted(canonical_labels),
                    })
                    for label in canonical_labels:
                        keys.add((pdf_number, entity_type, label))
    return keys, unresolved


def _prediction_keys(predictions: list[dict[str, Any]]) -> set[EvalKey]:
    keys: set[EvalKey] = set()
    for paper in predictions:
        pdf_number = str(paper["pdf_number"])
        for annotation in paper.get("annotations") or []:
            keys.add((pdf_number, str(annotation["entity_type"]), str(annotation["canonical_label"])))
    return keys


def _prf(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def evaluate_prediction_sets(gold_keys: set[EvalKey], prediction_keys: set[EvalKey], unresolved_gold: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_type: dict[str, dict[str, int]] = {entity_type: {"tp": 0, "fp": 0, "fn": 0} for entity_type in TARGET_ENTITY_TYPES}
    errors: list[dict[str, Any]] = []

    for key in sorted(gold_keys & prediction_keys):
        pdf_number, entity_type, canonical_label = key
        by_type[entity_type]["tp"] += 1
        errors.append({"pdf_number": pdf_number, "entity_type": entity_type, "canonical_label": canonical_label, "status": "TP"})
    for key in sorted(prediction_keys - gold_keys):
        pdf_number, entity_type, canonical_label = key
        by_type[entity_type]["fp"] += 1
        errors.append({"pdf_number": pdf_number, "entity_type": entity_type, "canonical_label": canonical_label, "status": "FP"})
    for key in sorted(gold_keys - prediction_keys):
        pdf_number, entity_type, canonical_label = key
        by_type[entity_type]["fn"] += 1
        errors.append({"pdf_number": pdf_number, "entity_type": entity_type, "canonical_label": canonical_label, "status": "FN"})

    per_type = {entity_type: _prf(**counts) for entity_type, counts in by_type.items()}
    total_tp = sum(counts["tp"] for counts in by_type.values())
    total_fp = sum(counts["fp"] for counts in by_type.values())
    total_fn = sum(counts["fn"] for counts in by_type.values())
    macro_types = list(per_type.values())
    exact_by_pdf: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"gold": set(), "predicted": set()})
    for pdf, entity_type, label in gold_keys:
        exact_by_pdf[pdf]["gold"].add(f"{entity_type}:{label}")
    for pdf, entity_type, label in prediction_keys:
        exact_by_pdf[pdf]["predicted"].add(f"{entity_type}:{label}")
    exact_matches = sum(1 for sets in exact_by_pdf.values() if sets["gold"] == sets["predicted"])

    metrics = {
        "per_entity_type": per_type,
        "micro": _prf(total_tp, total_fp, total_fn),
        "macro": {
            "precision": sum(float(item["precision"]) for item in macro_types) / len(macro_types),
            "recall": sum(float(item["recall"]) for item in macro_types) / len(macro_types),
            "f1": sum(float(item["f1"]) for item in macro_types) / len(macro_types),
        },
        "exact_paper_set_match": {
            "matched_papers": exact_matches,
            "total_papers": len(exact_by_pdf),
            "accuracy": exact_matches / len(exact_by_pdf) if exact_by_pdf else 0.0,
        },
        "unresolved_or_ambiguous_gold_labels": unresolved_gold or [],
    }
    return metrics, errors


def evaluate_predictions(
    gold_path: str | Path,
    vocab_path: str | Path,
    canonical_mappings_path: str | Path | None,
    predictions: list[dict[str, Any]] | None = None,
    predictions_path: str | Path | None = None,
    metrics_output: str | Path | None = None,
    errors_output: str | Path | None = None,
) -> dict[str, Any]:
    if predictions is None:
        if predictions_path is None:
            raise ValueError("predictions or predictions_path is required")
        predictions = read_jsonl(predictions_path)
    gold_keys, unresolved_gold = _gold_keys(gold_path, vocab_path, canonical_mappings_path)
    prediction_keys = _prediction_keys(predictions)
    metrics, errors = evaluate_prediction_sets(gold_keys, prediction_keys, unresolved_gold)
    if metrics_output:
        output = Path(metrics_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors_output:
        write_jsonl(errors, errors_output)
    return metrics
