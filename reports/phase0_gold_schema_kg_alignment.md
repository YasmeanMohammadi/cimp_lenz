# Phase 0 Report: Gold Schema and KG Alignment

## Scope Implemented

Implemented only Phase 0 support for aligning CMIP website gold labels with ClimateKG vocabulary instances under the six KG-backed categories:

- Activity
- Experiment
- Frequency
- Source
- Realm
- Variable

No PDF parsing, paper annotation, UI, embedding logic, LLM logic, or Neo4j write-back was implemented.

## Files Created or Modified

- `.env.example`
- `README.md`
- `pyproject.toml`
- `.gitignore`
- `config/entity_types.json`
- `config/canonical_mappings.json`
- `data/evaluation/gold_seed.example.jsonl`
- `src/cmip_indexkg/__init__.py`
- `src/cmip_indexkg/cli/__init__.py`
- `src/cmip_indexkg/cli/main.py`
- `src/cmip_indexkg/config.py`
- `src/cmip_indexkg/evaluation/__init__.py`
- `src/cmip_indexkg/evaluation/gold_mapping.py`
- `src/cmip_indexkg/evaluation/gold_schema.py`
- `src/cmip_indexkg/extraction/__init__.py`
- `src/cmip_indexkg/extraction/aliases.py`
- `src/cmip_indexkg/extraction/normalization.py`
- `src/cmip_indexkg/kg/__init__.py`
- `src/cmip_indexkg/kg/neo4j_client.py`
- `src/cmip_indexkg/kg/vocabulary_export.py`
- `tests/test_aliases.py`
- `tests/test_gold_mapping.py`
- `tests/test_gold_schema.py`

## CLI Commands Added

- `cmip-lens inspect-climatekg-schema`
- `cmip-lens build-vocab-index`
- `cmip-lens validate-gold`
- `cmip-lens map-gold-to-vocab`

## How to Run Phase 0

Install the package and test dependencies:

```bash
python -m pip install -e '.[dev]'
```

Set Neo4j environment variables for live ClimateKG commands in the shell or in a local `.env` file. The CLI includes a small `.env` loader that does not print secrets and does not override already-exported variables:

```bash
export NEO4J_URI=bolt://localhost:8687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=change-me
export NEO4J_DATABASE=neo4j
```

Inspect the KG schema:

```bash
cmip-lens inspect-climatekg-schema --sample-limit 5 --output reports/climatekg_schema_summary.json
```

Build the vocabulary export:

```bash
cmip-lens build-vocab-index --output data/vocab/climatekg_vocab.jsonl
```

Validate the seed gold JSONL:

```bash
cmip-lens validate-gold --gold data/evaluation/gold_seed.example.jsonl
```

Map gold labels to vocabulary entities with reviewed canonical-equivalence mappings:

```bash
cmip-lens map-gold-to-vocab \
  --gold data/evaluation/gold_seed.example.jsonl \
  --vocab data/vocab/climatekg_vocab.jsonl \
  --output-dir data/evaluation/mapping \
  --canonical-mappings config/canonical_mappings.json
```

Run tests:

```bash
pytest
```

## Live Verification Results

The Phase 0 commands were verified against the configured Neo4j connection after loading `.env`.

Commands run:

```bash
.venv/bin/cmip-lens inspect-climatekg-schema --sample-limit 3 --output reports/climatekg_schema_summary.json
.venv/bin/cmip-lens build-vocab-index --output data/vocab/climatekg_vocab.jsonl
.venv/bin/cmip-lens validate-gold --gold data/evaluation/gold_seed.example.jsonl
.venv/bin/cmip-lens map-gold-to-vocab \
  --gold data/evaluation/gold_seed.example.jsonl \
  --vocab data/vocab/climatekg_vocab.jsonl \
  --output-dir data/evaluation/mapping \
  --canonical-mappings config/canonical_mappings.json
.venv/bin/python -m pytest -q
```

Observed results:

- Schema inspection completed and wrote `reports/climatekg_schema_summary.json`.
- Vocabulary export completed and wrote `6987` records to `data/vocab/climatekg_vocab.jsonl`.
- Seed gold validation completed for `5` JSONL records.
- Gold-to-vocab mapping with canonical equivalence produced `39` mapped labels, `0` unresolved labels, and `0` ambiguous labels.
- Tests passed: `11 passed`.

The verified local connection is `bolt://localhost:8687` with credentials supplied through `.env`. Secrets are not printed by the CLI.

Observed target label counts in the corrected KG:

- `Activity`: 26
- `Experiment`: 481
- `Frequency`: 16
- `Source`: 394
- `Realm`: 14
- `Variable`: 6056

## canonical_id and label Assumptions

The KG property schema may vary by node label, so canonical ID selection is configurable in `config/entity_types.json`.

The exporter selects `canonical_id` from the first non-empty configured field for the entity type. Candidate fields include properties such as `id`, `canonical_id`, `source_id`, `experiment_id`, `frequency`, `realm`, `variable_id`, `standard_name`, `short_name`, `Name`, `UUID`, `name`, `label`, and `title`, depending on entity type.

The display `label` is selected from configured label fields such as `label`, `name`, `Name`, `title`, `long_name`, `standard_name`, `short_name`, `id`, and `UUID`. If no configured field exists, the exporter falls back to `canonical_id`, then `elementId(n)`.

`kg_entity_id` is populated from `elementId(n)` for local KG lookup. It is preserved, but it is not assumed to be the only stable long-term canonical identifier.

Raw KG properties are preserved in each vocabulary record as `source_properties`.

## Unresolved KG Schema Issues

- The earlier missing-label issue was caused by querying the wrong database endpoint. Against the corrected local KG, all six Phase 0 labels exist exactly as configured.
- The target category-to-node-label mapping is confirmed for Phase 0: `Activity -> Activity`, `Experiment -> Experiment`, `Frequency -> Frequency`, `Source -> Source`, `Realm -> Realm`, and `Variable -> Variable`.
- The observed target nodes primarily use lowercase `name`, `names`, and `uuid` properties. `Experiment` also uses `experiment_title`; `Variable` also uses `cf_standard_name`, `variable_long_name`, and `variable_units`.
- The export query no longer orders by generic optional properties in Cypher, avoiding missing-property warnings. Export records are sorted deterministically in Python by entity type, canonical ID, and `kg_entity_id`.
- Duplicate or near-duplicate KG instances may produce ambiguous gold mappings; the mapper writes these to `gold_ambiguous.jsonl` rather than choosing silently.

## Gold-Label Mapping Issues

- With the corrected KG endpoint, the seed gold labels have `0` unresolved labels.
- The prior seed ambiguity for `abrupt-4xCO2` is resolved by `config/canonical_mappings.json`, which maps both `abrupt-4xCO2` and `abrupt4xCO2` to canonical evaluation label `abrupt-4xCO2`.
- Website labels may use display strings such as `Monthly` while the KG may use compact identifiers such as `mon`; aliases handle common examples in the corrected vocabulary export.
- Short variables such as `pr`, `tas`, `ua`, and `va` are intentionally normalized conservatively because they are ambiguous in prose.
- Unmatched website labels are written to `gold_unresolved.jsonl` for manual review.

## Canonical Equivalence Mapping

`config/canonical_mappings.json` stores manually reviewed canonical-equivalence mappings by entity type. The mapping layer is intentionally separate from the exported KG vocabulary so it can document website/KG equivalence decisions without mutating ClimateKG.

Current reviewed mapping:

- `Experiment`: `abrupt-4xCO2 -> abrupt-4xCO2`
- `Experiment`: `abrupt4xCO2 -> abrupt-4xCO2`

During `map-gold-to-vocab`, matched KG candidates are grouped by the manual canonical label when a mapping exists. If all candidates collapse to one canonical target, the output is written to `gold_mapped.jsonl` with `mapping_method: manual_canonical_mapping` and all candidate KG nodes preserved in `matched_candidates`. If candidates still resolve to multiple canonical targets, the label remains in `gold_ambiguous.jsonl`.

## Note for Future Canonicalization Issues

When future website labels or KG aliases produce ambiguous mappings, do not drop candidates or mutate the KG during Phase 0. Instead:

1. Inspect `data/evaluation/mapping/gold_ambiguous.jsonl` and confirm whether candidates are true equivalents or genuinely different entities.
2. Add only reviewed equivalences to `config/canonical_mappings.json` under the relevant entity type.
3. Rerun `cmip-lens map-gold-to-vocab --canonical-mappings config/canonical_mappings.json`.
4. Keep unresolved labels in `gold_unresolved.jsonl` until a real KG entity or intentional evaluation policy is confirmed.

This keeps canonicalization auditable and prevents accidental conflation of distinct ClimateKG entities.


## External Alias and Canonicalization Policy

ClimateKG is read-only. CMIPIndexKG must not mutate, merge, delete, create, or update KG nodes or relationships to resolve website-label alignment issues. All aliasing and canonicalization happens outside the KG through `config/canonical_mappings.json`, exported vocabulary JSONL, and the gold-to-vocab mapping layer.

The mapper preserves raw website labels and raw KG candidate provenance. Mapped rows include `pdf_number`, `entity_type`, `website_label`, `raw_label`, `canonical_label`, `kg_entity_id`, `mapping_status`, `mapping_method`, `matched_candidates`, and `source_config` when a mapping config is supplied. Unresolved and ambiguous rows also preserve raw labels, status, method, and source config so unresolved cases remain auditable.

Manual mappings are reviewed equivalence or alias decisions only. They must not silently merge unrelated KG entities. If multiple KG candidates collapse to one reviewed canonical label, all candidates remain in `matched_candidates`. If candidates still represent multiple canonical targets, the label remains ambiguous.

Reviewed aliases/equivalences now configured:

- `Experiment`: `abrupt-4xCO2 -> abrupt-4xCO2`
- `Experiment`: `abrupt4xCO2 -> abrupt-4xCO2`
- `Frequency`: `1-hourly -> 1hr`
- `Frequency`: `3-hourly -> 3hr`

No `Source` canonical mappings were added in this cleanup. CMIP5 Source labels from `pdf_number=002` remain intentionally unresolved pending manual KG/schema review.

## Live Dataset Mapping Numbers

Commands run with `--canonical-mappings config/canonical_mappings.json`:

| Dataset | Output dir | Mapped | Unresolved | Ambiguous | Unresolved by type |
| --- | --- | ---: | ---: | ---: | --- |
| Full seed, `dataset/data/gold_seed_6.jsonl` | `dataset/data/mapping` | 100 | 64 | 0 | Source: 64 rows, 63 unique labels |
| Clean split, `dataset/data/gold_seed_clean.jsonl` | `dataset/data/mapping_clean` | 88 | 1 | 0 | Source: 1 row, 1 unique label (`HadCM3`) |
| Coverage challenge, `dataset/data/gold_seed_coverage_challenge.jsonl` | `dataset/data/mapping_challenge` | 12 | 63 | 0 | Source: 63 rows, 63 unique labels |

The reviewed Frequency mappings resolved `1-hourly` and `3-hourly` from `pdf_number=005`; both rows map with `mapping_method: manual_alias_mapping`. Remaining unresolved labels are Source labels only.
