"""CLI entry point for CMIPIndexKG Phase 0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cmip_indexkg.evaluation.gold_mapping import DEFAULT_CANONICAL_MAPPINGS_PATH, map_gold_to_vocab
from cmip_indexkg.evaluation.gold_schema import GoldValidationError, validate_gold_jsonl
from cmip_indexkg.kg.neo4j_client import ClimateKGClient
from cmip_indexkg.kg.vocabulary_export import DEFAULT_VOCAB_PATH, export_vocabulary, inspect_schema

DEFAULT_CONFIG_PATH = Path("config/entity_types.json")


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def inspect_climatekg_schema(args: argparse.Namespace) -> int:
    try:
        with ClimateKGClient() as client:
            client.verify_connectivity()
            summary = inspect_schema(client, args.config, sample_limit=args.sample_limit)
    except Exception as exc:
        print(f"ClimateKG schema inspection failed: {exc}", file=sys.stderr)
        return 1
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote schema inspection to {output}")
    else:
        _print_json(summary)
    return 0


def build_vocab(args: argparse.Namespace) -> int:
    try:
        with ClimateKGClient() as client:
            client.verify_connectivity()
            records = export_vocabulary(client, args.config, args.output)
    except Exception as exc:
        print(f"Vocabulary export failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(records)} vocabulary records to {args.output}")
    return 0


def validate_gold(args: argparse.Namespace) -> int:
    try:
        count, _records = validate_gold_jsonl(args.gold)
    except GoldValidationError as exc:
        print(f"Gold validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {count} gold JSONL records from {args.gold}")
    return 0


def map_gold(args: argparse.Namespace) -> int:
    try:
        summary = map_gold_to_vocab(args.gold, args.vocab, args.output_dir, args.canonical_mappings)
    except (GoldValidationError, ValueError, FileNotFoundError) as exc:
        print(f"Gold mapping failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Wrote mapping outputs to {args.output_dir}: "
        f"mapped={summary['mapped']} unresolved={summary['unresolved']} ambiguous={summary['ambiguous']}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cmip-lens", description="CMIPIndexKG Phase 0 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-climatekg-schema", help="Inspect target ClimateKG labels and sample properties")
    inspect_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to entity type config JSON")
    inspect_parser.add_argument("--sample-limit", type=int, default=5, help="Sample node count per label")
    inspect_parser.add_argument("--output", help="Optional JSON output path")
    inspect_parser.set_defaults(func=inspect_climatekg_schema)

    vocab_parser = subparsers.add_parser("build-vocab-index", help="Export target ClimateKG instances to JSONL vocabulary")
    vocab_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to entity type config JSON")
    vocab_parser.add_argument("--output", default=DEFAULT_VOCAB_PATH, help="Vocabulary JSONL output path")
    vocab_parser.set_defaults(func=build_vocab)

    validate_parser = subparsers.add_parser("validate-gold", help="Validate CMIP website gold JSONL annotations")
    validate_parser.add_argument("--gold", default="data/evaluation/gold_seed.example.jsonl", help="Gold JSONL path")
    validate_parser.set_defaults(func=validate_gold)

    map_parser = subparsers.add_parser("map-gold-to-vocab", help="Map gold website labels to exported ClimateKG vocabulary")
    map_parser.add_argument("--gold", default="data/evaluation/gold_seed.example.jsonl", help="Gold JSONL path")
    map_parser.add_argument("--vocab", default=DEFAULT_VOCAB_PATH, help="Vocabulary JSONL path")
    map_parser.add_argument("--output-dir", default="data/evaluation/mapping", help="Directory for mapped/unresolved/ambiguous JSONL outputs")
    map_parser.add_argument("--canonical-mappings", default=DEFAULT_CANONICAL_MAPPINGS_PATH, help="Manual canonical mapping JSON path")
    map_parser.set_defaults(func=map_gold)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
