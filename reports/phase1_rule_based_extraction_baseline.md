# Phase 1 Rule-Based KG-Grounded Extraction Baseline

## Scope

Phase 1 implements the first deterministic extraction baseline for CIMPIndexKG using only the clean seed dataset:

```text
dataset/data/gold_seed_clean.jsonl
```

The implemented milestone is:

```text
PDF in -> page-level text -> sentence-level evidence chunks -> KG vocabulary mention detection -> evidence-backed annotation predictions -> clean-seed evaluation
```

This phase does not mutate ClimateKG, write annotations back to Neo4j, use LLMs, use embeddings, build a UI, or manually create new KG entities.

## Inputs

- `dataset/data/gold_seed_clean.jsonl`
- `dataset/data/raw/*.pdf`
- `data/vocab/climatekg_vocab.jsonl`
- `config/canonical_mappings.json`
- `config/entity_types.json`

Only the six target entity types are used:

- `Activity`
- `Experiment`
- `Frequency`
- `Source`
- `Realm`
- `Variable`

## CLI Command

Run the Phase 1 baseline with:

```bash
cmip-lens run-baseline-extraction \
  --gold dataset/data/gold_seed_clean.jsonl \
  --vocab data/vocab/climatekg_vocab.jsonl \
  --canonical-mappings config/canonical_mappings.json \
  --parsed-output-dir dataset/data/processed/documents \
  --predictions-output dataset/data/annotations/predictions_clean.jsonl \
  --metrics-output dataset/data/evaluation/baseline_clean_metrics.json \
  --errors-output dataset/data/evaluation/baseline_clean_errors.jsonl
```

Last verified command result:

```text
Baseline extraction complete: parsed=5/5 micro_f1=0.4362
```

## Outputs

Parsed document JSON files:

- `dataset/data/processed/documents/003.parsed.json`
- `dataset/data/processed/documents/004.parsed.json`
- `dataset/data/processed/documents/005.parsed.json`
- `dataset/data/processed/documents/006.parsed.json`
- `dataset/data/processed/documents/007.parsed.json`

Other outputs:

- `dataset/data/processed/documents/parse_summary_clean.json`
- `dataset/data/annotations/predictions_clean.jsonl`
- `dataset/data/evaluation/baseline_clean_metrics.json`
- `dataset/data/evaluation/baseline_clean_errors.jsonl`

## Files Created or Modified

Implementation files:

- `src/cmip_indexkg/ingestion/document_model.py`
- `src/cmip_indexkg/ingestion/pdf_parser.py`
- `src/cmip_indexkg/extraction/baseline.py`
- `src/cmip_indexkg/evaluation/baseline_metrics.py`
- `src/cmip_indexkg/cli/main.py`
- `pyproject.toml`

Test file:

- `tests/test_phase1_baseline.py`

Documentation/report files:

- `README.md`
- `reports/phase1_rule_based_extraction_baseline.md`

Generated data files:

- `dataset/data/processed/documents/*.parsed.json`
- `dataset/data/processed/documents/parse_summary_clean.json`
- `dataset/data/annotations/predictions_clean.jsonl`
- `dataset/data/evaluation/baseline_clean_metrics.json`
- `dataset/data/evaluation/baseline_clean_errors.jsonl`

## PDF Parsing Summary

All five clean-seed PDFs were found and parsed.

| PDF | Pages | Sentences | Warnings |
| --- | ---: | ---: | --- |
| `003` | 10 | 461 | none |
| `004` | 14 | 1031 | none |
| `005` | 23 | 866 | none |
| `006` | 30 | 1305 | none |
| `007` | 22 | 1035 | none |

Aggregate parse summary:

```json
{
  "total_papers_requested": 5,
  "total_parsed_successfully": 5,
  "total_failed": 0
}
```

Each parsed document includes:

- paper metadata copied from the gold record;
- `pdf_number`;
- SHA-256 `pdf_hash`;
- source PDF path;
- page-level text with page numbers;
- sentence-level evidence chunks with IDs such as `p4-s12`;
- parser metadata.

## Prediction Output Schema

`dataset/data/annotations/predictions_clean.jsonl` contains one JSON object per paper. Each object includes:

- `pdf_number`
- `paper`
- `paper_id`
- `pdf_hash`
- `annotations`

Each annotation includes:

- `entity_type`
- `kg_entity_id`
- `canonical_id`
- `canonical_label`
- `matched_texts`
- `mention_count`
- `confidence`
- `mapping_method`
- `evidence`

Evidence entries include:

- `page_number`
- `sentence_id`
- `text`

## Predicted Annotation Counts

| PDF | Total Predictions | Activity | Experiment | Frequency | Realm | Source | Variable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `003` | 14 | 0 | 5 | 3 | 5 | 1 | 0 |
| `004` | 17 | 2 | 4 | 3 | 5 | 3 | 0 |
| `005` | 27 | 1 | 9 | 2 | 5 | 9 | 1 |
| `006` | 23 | 3 | 7 | 2 | 3 | 7 | 1 |
| `007` | 18 | 0 | 6 | 4 | 3 | 4 | 1 |

Total predicted annotations: `99`.

## Evaluation Results

Evaluation was run against `dataset/data/gold_seed_clean.jsonl` using the Phase 0 canonicalization/mapping logic.

Micro metrics:

```json
{
  "tp": 41,
  "fp": 58,
  "fn": 48,
  "precision": 0.41414141414141414,
  "recall": 0.4606741573033708,
  "f1": 0.4361702127659574
}
```

Macro metrics:

```json
{
  "precision": 0.34693420378904255,
  "recall": 0.3538095238095238,
  "f1": 0.32810282810282815
}
```

Per-entity metrics:

| Entity Type | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Activity | 3 | 3 | 4 | 0.5000 | 0.4286 | 0.4615 |
| Experiment | 16 | 15 | 9 | 0.5161 | 0.6400 | 0.5714 |
| Frequency | 5 | 9 | 2 | 0.3571 | 0.7143 | 0.4762 |
| Realm | 0 | 21 | 0 | 0.0000 | 0.0000 | 0.0000 |
| Source | 17 | 7 | 33 | 0.7083 | 0.3400 | 0.4595 |
| Variable | 0 | 3 | 0 | 0.0000 | 0.0000 | 0.0000 |

Paper-level exact set match:

```json
{
  "matched_papers": 0,
  "total_papers": 5,
  "accuracy": 0.0
}
```

Gold mapping note:

- `HadCM3` in `pdf_number=007` remains unresolved against the exported `Source` vocabulary and is tracked in the metrics file under `unresolved_or_ambiguous_gold_labels`.

## Major Errors Observed

The baseline is intentionally deterministic and high-transparency, not yet high-quality.

Main observed error categories:

- `Source` recall is limited because exact/alias matching misses many model/source mentions when the paper surface form differs from the KG canonical form.
- `Realm` false positives occur because terms such as land, ocean, sea, and ice are common scientific words and are not always indexing-worthy mentions.
- `Frequency` false positives occur because words such as day and month are often descriptive text rather than controlled CMIP frequency labels.
- `Experiment` false positives occur for KG terms that appear in methodological/background language but are not necessarily paper indexing labels.
- `Variable` handling is conservative for short aliases, but generic variable-like KG terms can still appear as ordinary words.
- References/background sections are not yet fully filtered, so some mentions may be counted even when they appear outside the paper's actual data-use context.

## Implementation Notes

PDF parsing:

- Uses PyMuPDF through the `fitz` module.
- Preserves page-level provenance.
- Splits text into deterministic sentence chunks.
- Computes a SHA-256 PDF hash for each input PDF.

Vocabulary loading and aliasing:

- Reads `data/vocab/climatekg_vocab.jsonl` only.
- Does not query or mutate Neo4j during Phase 1 extraction.
- Uses the six configured target entity types only.
- Builds an external alias index from KG labels, canonical IDs, exported aliases, reviewed canonical mappings, and controlled CMIP aliases.
- Keeps raw KG properties in the exported vocabulary unchanged.

Mention detection:

- Uses deterministic exact, normalized, compact, and manual alias matching.
- Uses token boundaries to avoid matching short aliases inside ordinary words.
- Aggregates multiple mentions of the same KG entity into one paper-level annotation.
- Keeps up to three evidence sentences per annotation.

Evaluation:

- Compares predicted KG-linked labels against clean-seed gold labels.
- Uses Phase 0 canonicalization logic so manual reviewed mappings remain reproducible.
- Writes TP/FP/FN rows to `baseline_clean_errors.jsonl` for error analysis.

## Known Limitations

- Sentence segmentation is rule-based and can split imperfectly around abbreviations, citations, table text, and equations.
- Table extraction is not handled as a first-class structure yet.
- Section detection is minimal; references are not reliably excluded.
- Alias matching is deterministic and does not perform semantic disambiguation.
- No embeddings, rerankers, or LLM checks are used.
- The baseline does not decide whether a mention is central to the paper or merely background text.
- No annotations are written back to Neo4j or any production persistence layer.

## Verification

Tests:

```text
23 passed in 0.30s
```

Phase 1 acceptance criteria status:

- `run-baseline-extraction` runs on `dataset/data/gold_seed_clean.jsonl`: satisfied.
- Parsed JSON files are created for PDFs `003`, `004`, `005`, `006`, and `007`: satisfied.
- `predictions_clean.jsonl` is created: satisfied.
- `baseline_clean_metrics.json` is created: satisfied.
- Evidence includes `page_number` and `sentence_id`: satisfied.
- Predictions are linked to KG entities through `kg_entity_id`: satisfied.
- ClimateKG was not modified: satisfied.
- Tests pass: satisfied.
