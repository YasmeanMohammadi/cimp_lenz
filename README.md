# CMIPIndexKG

KG-grounded automatic indexing utilities for CMIP publications.

This repository currently implements **Phase 0: Gold Schema and KG Alignment** only. It does not parse PDFs, annotate papers, run embeddings or LLMs, provide a UI, or write annotations back to Neo4j.

## Target KG-Backed Categories

The Phase 0 target categories are configured in `config/entity_types.json`:

- Activity
- Experiment
- Frequency
- Source
- Realm
- Variable

These categories are entity types. The actual matching targets are KG instances under those labels, such as `ssp245`, `ACCESS-CM2`, `Monthly`, `tas`, or `ocean`.

## Setup

```bash
python -m pip install -e '.[dev]'
```

For live ClimateKG commands, set Neo4j connection variables in the shell or in a local `.env` file:

```bash
export NEO4J_URI=bolt://localhost:8687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=change-me
export NEO4J_DATABASE=neo4j
```

See `.env.example` for the same variables. The CLI loads simple `KEY=VALUE` entries from `.env` when present, does not print secrets, and does not override variables already exported in the shell.
If the Neo4j deployment uses no password, keep `NEO4J_PASSWORD=` present with an empty value.

## Phase 0 Commands

Inspect the target ClimateKG labels and sample raw properties:

```bash
cmip-lens inspect-climatekg-schema --sample-limit 5 --output reports/climatekg_schema_summary.json
```

Export all instances of the six target labels into JSONL:

```bash
cmip-lens build-vocab-index --output data/vocab/climatekg_vocab.jsonl
```

Validate the seed CMIP website gold annotation JSONL:

```bash
cmip-lens validate-gold --gold data/evaluation/gold_seed.example.jsonl
```

Map website gold labels to the exported KG vocabulary, applying reviewed canonical-equivalence mappings when present:

```bash
cmip-lens map-gold-to-vocab \
  --gold data/evaluation/gold_seed.example.jsonl \
  --vocab data/vocab/climatekg_vocab.jsonl \
  --output-dir data/evaluation/mapping \
  --canonical-mappings config/canonical_mappings.json
```

The mapping command writes:

- `data/evaluation/mapping/gold_mapped.jsonl`
- `data/evaluation/mapping/gold_unresolved.jsonl`
- `data/evaluation/mapping/gold_ambiguous.jsonl`
- `data/evaluation/mapping/gold_mapping_summary.json`

Manual canonical-equivalence mappings live in `config/canonical_mappings.json`. They collapse reviewed equivalent KG labels or website labels to one evaluation canonical label, for example `abrupt4xCO2 -> abrupt-4xCO2`. This prevents known equivalent KG nodes from being reported as ambiguous while preserving all matched candidates in `gold_mapped.jsonl`.

## Gold JSONL Shape

Each record must contain `pdf_number` and all six target categories under `gold_annotations`, even when a category has no labels.

```json
{
  "pdf_number": "001",
  "paper": {
    "title": "Example paper",
    "doi": "10.example/example",
    "source_url": "https://cmip-publications.llnl.gov/..."
  },
  "gold_annotations": {
    "Activity": ["CMIP"],
    "Experiment": ["ssp245"],
    "Frequency": ["Monthly"],
    "Source": ["ACCESS-CM2"],
    "Realm": [],
    "Variable": []
  }
}
```

Website labels are preserved as observed. Mapping to KG vocabulary is reported separately so unresolved labels are not dropped.

## Vocabulary JSONL Shape

`data/vocab/climatekg_vocab.jsonl` records include:

```json
{
  "kg_entity_id": "...",
  "kg_node_label": "Experiment",
  "entity_type": "Experiment",
  "canonical_id": "ssp245",
  "label": "ssp245",
  "aliases": ["ssp245", "SSP2-4.5"],
  "normalized_aliases": ["ssp245", "ssp2 4 5"],
  "compact_aliases": ["ssp245"],
  "source_properties": {}
}
```

`kg_entity_id` uses `elementId(n)` for local lookup. It is not treated as the only long-term canonical identifier. Raw KG properties are preserved in `source_properties`.

## Tests

```bash
pytest
```


## Dataset V1 Validation and Mapping

ClimateKG / Neo4j is read-only for this project. Do not mutate, merge, create, delete, or update KG nodes or relationships from CMIPIndexKG. Website/KG label alignment is handled externally in `config/canonical_mappings.json`, exported vocabulary indexes, and mapping logic.

Validate all dataset splits:

```bash
cmip-lens validate-gold --gold dataset/data/gold_seed_6.jsonl
cmip-lens validate-gold --gold dataset/data/gold_seed_clean.jsonl
cmip-lens validate-gold --gold dataset/data/gold_seed_coverage_challenge.jsonl
```

Map all dataset splits with reviewed canonical mappings:

```bash
cmip-lens map-gold-to-vocab   --gold dataset/data/gold_seed_6.jsonl   --vocab data/vocab/climatekg_vocab.jsonl   --output-dir dataset/data/mapping   --canonical-mappings config/canonical_mappings.json

cmip-lens map-gold-to-vocab   --gold dataset/data/gold_seed_clean.jsonl   --vocab data/vocab/climatekg_vocab.jsonl   --output-dir dataset/data/mapping_clean   --canonical-mappings config/canonical_mappings.json

cmip-lens map-gold-to-vocab   --gold dataset/data/gold_seed_coverage_challenge.jsonl   --vocab data/vocab/climatekg_vocab.jsonl   --output-dir dataset/data/mapping_challenge   --canonical-mappings config/canonical_mappings.json
```

Reviewed mappings currently include `Experiment` equivalence for `abrupt4xCO2 -> abrupt-4xCO2` and `Frequency` aliases `1-hourly -> 1hr`, `3-hourly -> 3hr`. No `Source` mappings have been added. Expected unresolved labels are Source labels, primarily CMIP5-era labels from `pdf_number=002` in the coverage-challenge split.
