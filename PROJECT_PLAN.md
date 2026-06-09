# KG-Grounded Automatic Indexing of CMIP Publications

## 1. Project Goal

The goal of this project is to build an automatic and semi-automatic indexing system for CMIP-relevant scientific publications.

Given a paper PDF and the existing Climate Knowledge Graph, the system should automatically identify CMIP-related vocabulary instances mentioned or used in the paper, link them to canonical ClimateKG entities, provide supporting evidence from the paper, and allow a user to validate or correct the suggested annotations.

The core task is **not keyword tagging**. It is **KG-grounded entity linking for scientific document indexing**.

The system should answer:

```text
Which ClimateKG vocabulary entities should this paper be indexed with?
```

For Version 1, the focus is on KG-backed indexing categories that are also visible on the CMIP publications website:

- Activity
- Experiment
- Frequency
- Source
- Realm
- Variable

The CMIP publications website will be used as the gold standard for evaluation. The website provides human-curated annotations for papers, and these annotations can be collected into a JSON benchmark dataset.

## 2. Key Clarification: Entity Types vs. Entity Instances

The CMIP website organizes annotations by entity type/category, such as:

```text
Activity
Experiment
Frequency
Source
Realm
Variable
```

However, these entity types are not the objects the system directly matches in the paper. The system should match the **values/instances** belonging to each entity type.

Examples:

```text
Entity type: Activity
Instances: CMIP, ScenarioMIP, DAMIP, ...

Entity type: Experiment
Instances: historical, ssp245, ssp585, piControl, ...

Entity type: Frequency
Instances: Monthly, Daily, mon, day, 3hr, ...

Entity type: Source
Instances: ACCESS-CM2, CESM2, MIROC6, MRI-ESM2-0, ...

Entity type: Realm
Instances: atmos, ocean, land, seaIce, ...

Entity type: Variable
Instances: tas, pr, tos, psl, ua, va, ...
```

Therefore, the system should not output only:

```text
Paper X -> Experiment
```

It should output:

```text
Paper X -> uses/discusses -> ssp245
Type: Experiment
Evidence: "The simulations are based on CMIP6 projections under SSP2-4.5."
Page: 4
Confidence: 0.91
```

The entity instance is the extraction and linking target. The entity type is used for grouping, display, validation, and evaluation.

## 3. Version 1 Scope

### 3.1 In Scope

Version 1 focuses on automatic KG-backed indexing for the following ClimateKG node labels:

| Website category | ClimateKG node label | Example instances |
| --- | --- | --- |
| Activity | `Activity` | CMIP, ScenarioMIP, DAMIP |
| Experiment | `Experiment` | historical, ssp245, ssp585 |
| Frequency | `Frequency` | Monthly, Daily, mon, day |
| Source | `Source` | ACCESS-CM2, CESM2, MIROC6 |
| Realm | `Realm` | atmos, ocean, land, seaIce |
| Variable | `Variable` | tas, pr, tos, psl |

Version 1 includes:

- PDF ingestion.
- PDF text extraction with page-level provenance.
- Sentence-level evidence extraction.
- ClimateKG vocabulary export for the six target node labels.
- Alias and normalization rules for vocabulary instances.
- Candidate mention detection from paper text.
- KG entity linking to canonical ClimateKG entities.
- Evidence-backed annotation suggestions.
- JSON output for predictions.
- JSON gold benchmark format.
- Evaluation against CMIP website gold labels.
- Simple human validation workflow.

### 3.2 Out of Scope for Version 1

The following are intentionally out of scope for the first implementation:

- Metadata-only website categories such as Year, Status, and Type.
- Fully automated KG mutation without human review.
- Perfect table extraction from arbitrary PDFs.
- Full PDF highlighting UI.
- Multi-user authentication.
- Multi-reviewer adjudication.
- Creating new KG vocabulary nodes.
- Training a custom large language model.
- Production-scale deployment.

Metadata fields such as Year, Status, and Type can be handled later through paper metadata extraction, but they are not part of the first KG indexing baseline.

### 3.3 Version 1 Definition of Done

Version 1 is complete when the system can:

1. Parse a paper PDF into page-numbered, sentence-level evidence candidates.
2. Export and index ClimateKG vocabulary instances for Activity, Experiment, Frequency, Source, Realm, and Variable.
3. Detect candidate mentions in the paper using high-precision aliases, normalization rules, and CMIP-specific patterns.
4. Link mentions to canonical ClimateKG entities.
5. Produce evidence-backed annotation JSON grouped by the six target categories.
6. Compare predicted category-instance sets against CMIP website gold annotations.
7. Present suggestions in a simple human review workflow.

The first milestone is:

```text
PDF in
KG-backed annotations with evidence out
Evaluation against CMIP website gold labels
```

## 4. ClimateKG Schema Summary

The current ClimateKG contains approximately 55K nodes.

Important node labels include:

```text
Activity: 26
Experiment: 481
Frequency: 16
Source: 394
Realm: 14
Variable: 6056
GridLabel: 17
Institute: 132
Project: 37
MIPEra: 4
ExperimentFamily: 9
SubExperiment: 63
Ensemble: 578
Member: 5929
SourceComponent: 173
SourceType: 16
Forcing: 204
Resolution: 15
Domain: 39
```

Version 1 should focus only on the six KG-backed website indexing categories:

```text
Activity
Experiment
Frequency
Source
Realm
Variable
```

Other node labels may later be used for disambiguation or extended indexing.

## 5. Gold Standard Dataset

The CMIP publications website will be used to construct the gold standard. Each benchmark item should correspond to one paper PDF and its human-curated website annotations.

The gold dataset should be stored in JSON or JSONL format. The benchmark should use sets of labels per category. Evaluation will compare predicted sets against gold sets.

Example gold record:

```json
{
  "pdf_number": "001",
  "paper": {
    "title": "Multi-decadal streamflow projections for catchments in Brazil based on CMIP6 multi-model simulations and neural network embeddings for linear regression models",
    "doi": "10.5194/hess-29-5099-2025",
    "source_url": "https://cmip-publications.llnl.gov/..."
  },
  "gold_annotations": {
    "Activity": ["CMIP"],
    "Experiment": ["ssp245"],
    "Frequency": ["Monthly"],
    "Source": [
      "ACCESS-CM2",
      "BCC-CSM2-MR",
      "CESM2",
      "CMCC-ESM2",
      "CNRM-CM6-1",
      "CNRM-ESM2-1",
      "EC-Earth3-CC",
      "GFDL-ESM4",
      "HadGEM3-GC31-LL",
      "IITM-ESM",
      "INM-CM4-8",
      "INM-CM5-0",
      "IPSL-CM6A-LR",
      "KACE-1-0-G",
      "KIOST-ESM",
      "MIROC-ES2L",
      "MIROC6",
      "MPI-ESM1-2-LR",
      "MRI-ESM2-0",
      "NESM3",
      "NorESM2-MM",
      "UKESM1-0-LL"
    ],
    "Realm": [],
    "Variable": []
  }
}
```

Gold dataset requirements:

- Store every target category, even when the category has no labels.
- Treat category values as sets for evaluation.
- Preserve website labels as observed.
- Add canonical ClimateKG IDs where they can be mapped.
- Track unresolved website labels separately rather than dropping them.
- Preserve paper identifiers such as `pdf_number`, DOI, title, and website URL.

## 6. Prediction Output Format

The system output should also be JSON or JSONL.

Each predicted annotation should include:

- paper identifier;
- KG entity identifier;
- canonical entity label;
- entity type/category;
- matched text from the paper;
- confidence;
- extraction method;
- evidence text;
- page number;
- validation status.

Example prediction record:

```json
{
  "pdf_number": "001",
  "paper": {
    "paper_id": "sha256:...",
    "title": "Example paper title",
    "doi": "10.xxxx/example",
    "pdf_path": "data/raw/example.pdf"
  },
  "predicted_annotations": [
    {
      "annotation_id": "uuid",
      "kg_entity_id": "climatekg:...",
      "canonical_id": "ssp245",
      "label": "ssp245",
      "entity_type": "Experiment",
      "kg_node_label": "Experiment",
      "matched_text": "SSP2-4.5",
      "confidence": 0.91,
      "status": "suggested",
      "extraction_method": "alias_regex_v1",
      "evidence": [
        {
          "evidence_id": "uuid",
          "text": "The simulations are based on CMIP6 projections under SSP2-4.5.",
          "page_number": 4,
          "section_title": "Methods",
          "sentence_id": "p4-s12"
        }
      ]
    },
    {
      "annotation_id": "uuid",
      "kg_entity_id": "climatekg:...",
      "canonical_id": "ACCESS-CM2",
      "label": "ACCESS-CM2",
      "entity_type": "Source",
      "kg_node_label": "Source",
      "matched_text": "ACCESS-CM2",
      "confidence": 0.88,
      "status": "suggested",
      "extraction_method": "alias_regex_v1",
      "evidence": [
        {
          "evidence_id": "uuid",
          "text": "The ensemble includes ACCESS-CM2, CESM2, and MRI-ESM2-0.",
          "page_number": 6,
          "section_title": "Data"
        }
      ]
    }
  ]
}
```

For evaluation, this can be reduced to a category-to-set structure:

```json
{
  "pdf_number": "001",
  "predicted_sets": {
    "Activity": ["CMIP"],
    "Experiment": ["ssp245"],
    "Frequency": ["Monthly"],
    "Source": ["ACCESS-CM2", "CESM2", "MRI-ESM2-0"],
    "Realm": ["land"],
    "Variable": ["pr"]
  }
}
```

## 7. Data Model

### 7.1 Core Objects

#### Paper

Represents a scientific publication.

Suggested fields:

```json
{
  "paper_id": "sha256:...",
  "pdf_number": "001",
  "doi": "10.xxxx/example",
  "title": "Example title",
  "authors": [],
  "year": 2025,
  "journal": "Example Journal",
  "source_url": "https://cmip-publications.llnl.gov/...",
  "pdf_path": "data/raw/example.pdf",
  "pdf_hash": "...",
  "ingested_at": "...",
  "metadata_source": "pdf_or_website"
}
```

#### ClimateEntity

Represents a KG-backed vocabulary instance.

Suggested fields:

```json
{
  "kg_entity_id": "...",
  "kg_node_label": "Experiment",
  "entity_type": "Experiment",
  "canonical_id": "ssp245",
  "label": "ssp245",
  "aliases": ["ssp245", "SSP2-4.5", "SSP245"],
  "source_vocabulary": "CMIP",
  "source_properties": {}
}
```

#### Annotation

Represents a proposed, accepted, rejected, corrected, manually added, or unresolved indexing decision.

Suggested fields:

```json
{
  "annotation_id": "uuid",
  "paper_id": "sha256:...",
  "kg_entity_id": "...",
  "canonical_id": "ssp245",
  "label": "ssp245",
  "entity_type": "Experiment",
  "kg_node_label": "Experiment",
  "matched_text": "SSP2-4.5",
  "confidence": 0.91,
  "status": "suggested",
  "extraction_method": "alias_regex_v1",
  "model_version": "baseline-v1",
  "created_at": "...",
  "updated_at": "...",
  "validated_by": null,
  "validated_at": null,
  "notes": null
}
```

Allowed status values:

```text
suggested
accepted
rejected
corrected
manual
unresolved
```

#### EvidenceSpan

Represents supporting evidence from the paper.

Version 1 fields:

```json
{
  "evidence_id": "uuid",
  "paper_id": "sha256:...",
  "text": "The simulations are based on CMIP6 projections under SSP2-4.5.",
  "page_number": 4,
  "section_title": "Methods",
  "sentence_id": "p4-s12",
  "extraction_source": "pdf_text"
}
```

Later fields can include paragraph ID, table ID, caption ID, character offsets, and bounding boxes.

## 8. Recommended Graph Representation

For long-term persistence, use explicit annotation nodes rather than direct `Paper -> ClimateEntity` edges.

Recommended graph model:

```cypher
(:Paper)-[:HAS_ANNOTATION]->(:Annotation)
(:Annotation)-[:LINKS_TO]->(:ClimateEntity)
(:Annotation)-[:SUPPORTED_BY]->(:EvidenceSpan)
(:User)-[:VALIDATED]->(:Annotation)
```

This is preferable because:

- evidence is required;
- confidence scores need to be stored;
- human validation status changes over time;
- rejected suggestions should be preserved for model improvement;
- corrected annotations need provenance;
- model versions and extraction methods should be auditable.

A derived direct edge can be materialized later for simple querying:

```cypher
(:Paper)-[:INDEXED_WITH {
  source: "validated_annotation",
  annotation_id: "...",
  status: "accepted"
}]->(:ClimateEntity)
```

## 9. System Architecture

The system has the following components:

1. PDF ingestion and parsing.
2. ClimateKG vocabulary export.
3. Vocabulary normalization and alias generation.
4. Candidate mention detection.
5. KG entity retrieval.
6. Entity linking and confidence scoring.
7. Evidence selection.
8. Annotation JSON generation.
9. Human validation interface.
10. Evaluation pipeline.

Recommended initial stack:

```text
Backend: Python
PDF parsing: PyMuPDF
Sentence segmentation: spaCy or simple rule-based segmentation
KG access: Neo4j Python driver
UI prototype: Streamlit
Storage: JSON/JSONL first; Neo4j annotation subgraph later
Evaluation: Python scripts
```

FastAPI and React can be considered later if the review UI needs to become production-grade.

### 9.1 Initial Repository Layout

Recommended layout once implementation begins:

```text
CMIPIndexKG/
  README.md
  PROJECT_PLAN.md
  pyproject.toml
  .env.example
  config/
    settings.example.yaml
    entity_types.yaml
  data/
    raw/
    processed/
    vocab/
    annotations/
    evaluation/
  src/
    cmip_indexkg/
      __init__.py
      cli/
        main.py
      config.py
      ingestion/
        pdf_parser.py
        document_model.py
      kg/
        neo4j_client.py
        vocabulary_export.py
        vocabulary_index.py
      extraction/
        normalization.py
        aliases.py
        patterns.py
        mention_detector.py
      linking/
        candidate_generator.py
        ranker.py
        linker.py
      annotation/
        models.py
        serializer.py
        repository.py
      evaluation/
        canonicalize.py
        metrics.py
        benchmark.py
      ui/
        streamlit_app.py
  tests/
    test_pdf_parser.py
    test_aliases.py
    test_mention_detector.py
    test_linker.py
    test_metrics.py
```

## 10. Pipeline Design

### Step 1: PDF Ingestion

Input:

- PDF file.
- Optional DOI, title, source URL, or website paper ID.

Output:

- paper record;
- page-level text;
- sentence-level chunks;
- basic metadata;
- PDF hash for deduplication.

Version 1 should use PyMuPDF and preserve page numbers.

### Step 2: ClimateKG Vocabulary Export

Export all instances from the six target node labels:

```cypher
MATCH (n:Activity)
RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties;

MATCH (n:Experiment)
RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties;

MATCH (n:Frequency)
RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties;

MATCH (n:Source)
RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties;

MATCH (n:Realm)
RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties;

MATCH (n:Variable)
RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties;
```

Each exported vocabulary record should include:

```json
{
  "kg_entity_id": "...",
  "kg_node_label": "Source",
  "entity_type": "Source",
  "canonical_id": "ACCESS-CM2",
  "label": "ACCESS-CM2",
  "aliases": ["ACCESS-CM2", "ACCESS CM2"],
  "source_properties": {}
}
```

### Step 3: Alias and Normalization Rules

For each entity instance, generate matchable surface forms.

Examples:

```text
ssp245 -> ssp245, SSP245, SSP2-4.5, SSP2 4.5
ssp585 -> ssp585, SSP585, SSP5-8.5, SSP5 8.5
ACCESS-CM2 -> ACCESS-CM2, ACCESS CM2
Monthly -> Monthly, monthly, mon
Daily -> Daily, daily, day
```

For variables, use more conservative rules because many variable names are short and ambiguous.

Examples:

```text
tas -> tas, near-surface air temperature
pr -> pr, precipitation
tos -> tos, sea surface temperature
```

Variable matching should require stronger context than source or experiment matching.

### Step 4: Candidate Mention Detection

Use high-precision matching first:

1. exact alias matching;
2. normalized alias matching;
3. CMIP-specific regex patterns;
4. conservative variable matching;
5. optional embedding retrieval later.

Version 1 should prioritize precision and explainability.

Important patterns include:

```text
CMIP phases/activities: CMIP5, CMIP6, CMIP7, ScenarioMIP, DAMIP
Experiments/scenarios: historical, ssp245, ssp585, piControl, abrupt-4xCO2
Sources: ACCESS-CM2, CESM2, MIROC6, MRI-ESM2-0
Frequencies: monthly, daily, mon, day, 3hr, 6hr
Realms: atmos, ocean, land, seaIce
Variables: tas, pr, tos, psl, ua, va
```

### Step 5: Entity Linking and Ranking

For each mention, retrieve candidate ClimateKG entities and rank them.

Version 1 ranking can be deterministic.

Suggested confidence features:

```text
exact alias match
normalized alias match
entity type reliability
context support
mention frequency
nearby CMIP terms
KG relationship support
```

Example confidence formula:

```text
confidence =
  0.50 exact_or_normalized_alias_score
  0.20 entity_type_pattern_score
  0.15 context_score
  0.10 repeated_evidence_score
  0.05 KG_neighbor_support_score
```

Later, embeddings, rerankers, or LLM-assisted disambiguation can be added.

### Step 6: Evidence Selection

Each annotation should include evidence copied from the paper.

Evidence priority:

1. sentence containing the exact mention;
2. paragraph containing the exact mention;
3. abstract mention;
4. table or caption mention, later;
5. metadata field, if relevant.

Version 1 evidence fields:

```text
evidence_text
page_number
section_title, if available
sentence_id
```

### Step 7: Annotation Creation

Create one annotation per resolved KG entity per paper.

If an entity appears multiple times:

- deduplicate at paper level;
- keep the best evidence span;
- optionally store mention count;
- optionally keep top-k evidence spans later.

Example:

```text
Paper X -> uses/discusses -> ssp245
Type: Experiment
Evidence: "The simulations are based on CMIP6 projections under SSP2-4.5."
Page: 4
Confidence: 0.91
Status: suggested
```

### Step 8: Human Validation

The user should be able to:

- accept a suggestion;
- reject a suggestion;
- correct a suggestion by selecting another KG entity;
- add a missing annotation;
- mark an annotation unresolved;
- add notes.

Validation should not overwrite the original suggestion. The system should preserve the original prediction, confidence, evidence, extraction method, and model version.

## 11. Human Review UI

The review UI should be grouped by the six KG-backed categories:

```text
Activity
Experiment
Frequency
Source
Realm
Variable
```

Each suggestion should show:

```text
checkbox or status selector
canonical label
entity type
matched text
confidence
evidence snippet
page number
correction search box
notes
```

Suggested flow:

```text
Upload PDF
  -> Parse PDF
  -> Run KG indexing
  -> Show grouped suggestions
  -> User validates/corrects suggestions
  -> Save reviewed annotations
  -> Export JSON
```

Use Streamlit for the first prototype.

## 12. Evaluation Plan

### 12.1 Evaluation Input

Evaluation uses two JSON/JSONL files:

1. Gold annotations collected from the CMIP website.
2. Predicted annotations produced by the system.

Gold example:

```json
{
  "pdf_number": "001",
  "gold_annotations": {
    "Activity": ["CMIP"],
    "Experiment": ["ssp245"],
    "Frequency": ["Monthly"],
    "Source": ["ACCESS-CM2", "CESM2"],
    "Realm": ["land"],
    "Variable": ["pr"]
  }
}
```

Prediction example:

```json
{
  "pdf_number": "001",
  "predicted_annotations": {
    "Activity": ["CMIP"],
    "Experiment": ["ssp245", "ssp585"],
    "Frequency": ["Monthly"],
    "Source": ["ACCESS-CM2", "CESM2", "MIROC6"],
    "Realm": [],
    "Variable": ["pr", "tas"]
  }
}
```

### 12.2 Metrics

Evaluate each category as a set-matching problem.

For each paper and category:

```text
true positives = predicted intersect gold
false positives = predicted - gold
false negatives = gold - predicted
```

Report:

- precision by category;
- recall by category;
- F1 by category;
- macro average across categories;
- micro average across all category-instance pairs;
- exact paper-level match rate, optional.

Primary metrics:

```text
Activity F1
Experiment F1
Frequency F1
Source F1
Realm F1
Variable F1
Macro-F1
Micro-F1
```

### 12.3 Evaluation Notes

The website annotations may not always map perfectly to ClimateKG entities. Therefore, maintain a mapping layer between website labels and KG canonical IDs.

Evaluation should be performed on canonicalized labels whenever possible.

Example:

```text
Website label: Monthly
KG canonical label: mon
Evaluation label: Monthly or mon, depending on chosen canonical policy
```

The evaluation script should track unresolved labels separately.

## 13. Error Analysis

Track errors by category.

Important error types:

```text
missed alias
wrong canonical entity
wrong entity type
ambiguous short variable
false positive from references
false positive from background discussion
PDF extraction error
website label not found in KG
KG duplicate entity
gold label inconsistency
```

Variable extraction should receive special attention because short variables such as `pr`, `tas`, `ua`, and `va` can produce false positives.

Mitigation for variable false positives:

```text
require climate context
require exact token boundaries
use case-sensitive matching for risky variables
look for nearby units, table IDs, realms, or CMIP/source terms
lower confidence when context is weak
```

## 14. Risks and Mitigations

### 14.1 Gold Label to KG Mapping Gaps

Risk:

Website labels may not map cleanly to existing ClimateKG entities or may use display names that differ from KG canonical IDs.

Mitigation:

- Maintain a website-label-to-KG mapping layer.
- Preserve original website labels.
- Track unresolved labels separately.
- Evaluate on canonicalized labels once the mapping policy is stable.

### 14.2 Ambiguous Short Variables

Risk:

Short variable identifiers such as `pr`, `tas`, `ua`, and `va` can be false positives in prose, references, author names, or unrelated abbreviations.

Mitigation:

- Require exact token boundaries.
- Require climate, CMIP, model, table, unit, or realm context.
- Use case-sensitive matching for risky aliases.
- Lower confidence for weak context.
- Inspect variable errors separately in evaluation.

### 14.3 PDF Extraction Quality

Risk:

PDF parsing may drop text, merge columns, corrupt tables, or lose section structure.

Mitigation:

- Preserve page-level raw text.
- Keep extraction source and page number on every evidence span.
- Start with sentence-level evidence only.
- Add table, caption, paragraph, and bounding-box support later.

### 14.4 Over-Broad Matching

Risk:

Mentions in references, literature review, or background discussion may not indicate that a paper should be indexed with the entity.

Mitigation:

- Prefer evidence from abstract, methods, data, results, and model-description sections.
- Add negative filters for references and bibliography sections.
- Use repeated evidence and nearby CMIP terms as confidence features.
- Keep human validation in the loop.

### 14.5 KG Schema Variability

Risk:

Properties for the six target node labels may not be uniform, and canonical IDs may not be obvious.

Mitigation:

- Inspect example nodes before implementation.
- Preserve raw KG properties in vocabulary JSONL.
- Make canonical ID selection configurable.
- Avoid relying on Neo4j internal IDs as the only stable identifier.

## 15. Phased Implementation Plan

### Phase 0: Gold Schema and KG Alignment

Goal:

Align the ClimateKG vocabulary with the CMIP website gold-standard categories.

Tasks:

- Confirm ClimateKG connection.
- Inspect properties for `Activity`, `Experiment`, `Frequency`, `Source`, `Realm`, and `Variable`.
- Decide canonical identifier fields.
- Export example nodes for each target label.
- Define alias-generation rules.
- Collect 5 to 10 CMIP website papers with gold annotations.
- Store gold annotations in JSON/JSONL.
- Check whether website labels map to KG entities.

Deliverables:

- KG schema summary.
- Target entity list.
- Category-to-node-label mapping.
- Canonical ID policy.
- Gold JSON schema.
- Seed benchmark file.
- Mapping report for website labels to KG entities.

Acceptance criteria:

- Six target node labels are confirmed.
- Vocabulary instances can be exported from Neo4j.
- At least 5 papers have gold annotations in JSON.
- Most gold labels map to KG entities, or unresolved cases are documented.

### Phase 1: Project Scaffold and PDF Parsing

Goal:

Create the basic Python project and parse PDFs into evidence-ready text.

Tasks:

- Create Python package.
- Add configuration loading.
- Add PDF parser using PyMuPDF.
- Extract page-level text.
- Segment text into sentences.
- Preserve page numbers.
- Store parsed output as JSON.
- Add CLI command:

```bash
cmip-lens parse path/to/paper.pdf
```

Deliverables:

- Working parser.
- Parsed document JSON.
- Unit tests.

Acceptance criteria:

- A sample PDF can be parsed.
- Output includes page numbers and sentence-level evidence candidates.
- Parser handles extraction failures gracefully.

### Phase 2: Vocabulary Export and Indexing

Goal:

Build a searchable vocabulary index from ClimateKG.

Tasks:

- Add Neo4j connection module.
- Export all nodes from:
  - `Activity`
  - `Experiment`
  - `Frequency`
  - `Source`
  - `Realm`
  - `Variable`
- Normalize labels and identifiers.
- Generate aliases.
- Build exact and normalized lookup tables.
- Store vocabulary index as JSONL.
- Add CLI command:

```bash
cmip-lens build-vocab-index
```

Deliverables:

- Vocabulary JSONL.
- Alias index.
- Normalization module.
- Tests for alias generation.

Acceptance criteria:

- Known terms such as `SSP2-4.5`, `ssp245`, `ACCESS-CM2`, `Monthly`, and `tas` resolve to candidate KG entities.
- The index preserves original KG identifiers and properties.

### Phase 3: Rule-Based Candidate Detection and Linking

Goal:

Create a high-precision baseline for automatic indexing.

Tasks:

- Implement exact alias matcher.
- Implement normalized alias matcher.
- Implement regex patterns.
- Implement conservative variable matching.
- Implement candidate generation.
- Implement deterministic confidence scoring.
- Select best evidence sentence.
- Deduplicate repeated mentions into paper-level annotations.
- Add CLI command:

```bash
cmip-lens annotate path/to/paper.pdf
```

Deliverables:

- Evidence-backed annotation JSON.
- Baseline linker.
- Tests for matching and linking.

Acceptance criteria:

- A sample paper produces annotation suggestions grouped by:
  - Activity
  - Experiment
  - Frequency
  - Source
  - Realm
  - Variable
- Each suggestion includes:
  - KG entity ID
  - canonical label
  - entity type
  - matched text
  - confidence
  - evidence text
  - page number
- False positives can be inspected through evidence.

### Phase 4: Evaluation

Goal:

Evaluate predictions against CMIP website gold annotations.

Tasks:

- Implement gold JSON loader.
- Implement prediction JSON loader.
- Canonicalize labels.
- Compare predicted and gold sets by category.
- Compute precision, recall, and F1.
- Report metrics per category and overall.
- Generate error analysis files.

Deliverables:

- Evaluation script.
- Metrics report.
- Error report.

Acceptance criteria:

- Evaluation can run from CLI.
- Precision, recall, and F1 are reported for all six categories.
- Unresolved gold labels are tracked.
- Top error types are documented.

CLI example:

```bash
cmip-lens evaluate \
  --gold data/evaluation/gold.jsonl \
  --pred data/annotations/predictions.jsonl
```

### Phase 5: Human Review UI

Goal:

Allow users to validate and correct annotation suggestions.

Tasks:

- Build Streamlit upload page.
- Display paper metadata.
- Display grouped annotation suggestions.
- Show evidence and confidence.
- Add accept/reject controls.
- Add correction search over KG vocabulary.
- Add manual annotation search.
- Save reviewed annotations as JSON.
- Optionally write reviewed annotations to Neo4j.

Deliverables:

- Streamlit review UI.
- Reviewed annotation JSON format.
- UI documentation.

Acceptance criteria:

- A user can upload a PDF.
- The system runs indexing.
- The user can accept, reject, correct, or add annotations.
- The reviewed output is saved.

### Phase 6: Annotation Persistence

Goal:

Persist suggestions and validation decisions in a more durable format.

Tasks:

- Decide storage target:
  - JSON/JSONL only;
  - Neo4j annotation subgraph;
  - SQLite/Postgres app database;
  - hybrid approach.
- Implement annotation repository.
- Add status update operations.
- Add correction operation.
- Add export operation.

Deliverables:

- Persistence API.
- Storage schema.
- Export scripts.

Acceptance criteria:

- Suggested and reviewed annotations are stored.
- Evidence remains linked to annotations.
- Validation decisions are auditable.

### Phase 7: Improved Retrieval and Disambiguation

Goal:

Improve recall and reduce ambiguity after the baseline.

Tasks:

- Add embedding-based retrieval.
- Add context-aware reranking.
- Add KG-neighborhood features.
- Add section-aware heuristics.
- Add negative filters for references and background mentions.
- Optionally use LLM-assisted reranking with strict JSON output.

Deliverables:

- Improved linker.
- Method comparison report.
- Model-version provenance.

Acceptance criteria:

- Recall improves without unacceptable precision loss.
- Variable and acronym disambiguation improves.
- Evaluation shows improvement over the rule-based baseline.

### Phase 8: Production Hardening

Goal:

Prepare the system for routine curator use.

Tasks:

- Add batch upload.
- Add job queue.
- Add logging.
- Add backup/export process.
- Add Docker Compose.
- Add authentication if needed.
- Add reviewer roles if needed.

Deliverables:

- Deployable service.
- Operational documentation.
- Batch processing support.

Acceptance criteria:

- The system can process multiple papers reliably.
- Curator actions are auditable.
- Data can be exported and backed up.

## 16. Immediate Implementation Order

The immediate order should be:

1. Create the gold JSON schema.
2. Collect 5 to 10 CMIP website annotated papers.
3. Export ClimateKG instances for Activity, Experiment, Frequency, Source, Realm, and Variable.
4. Build the vocabulary JSONL index.
5. Parse 5 to 10 PDFs.
6. Implement exact/alias matching.
7. Produce evidence-backed annotation JSON.
8. Evaluate against the gold JSON.
9. Inspect errors manually.
10. Add the Streamlit review UI.

This order keeps the first prototype focused and testable.

Only after this baseline works should we add a more complex UI, persistence layer, embeddings, or LLM-based reranking.

## 17. Open Questions

The following decisions should be resolved during Phase 0 and early Phase 1:

1. Which ClimateKG property should be the stable `canonical_id` for each of the six target node labels?
2. Are website labels available through an API, database export, structured HTML, or manual collection?
3. What canonicalization policy should evaluation use when website labels and KG labels differ, such as `Monthly` versus `mon`?
4. Should a paper be indexed with entities mentioned only in background or references, or only entities used in the paper's data, methods, or analysis?
5. Should multiple evidence spans be stored in Version 1, or only the highest-confidence evidence span per annotation?
6. What minimum precision is required before suggestions are shown as high-confidence in the review UI?
7. Should reviewed annotations be written to Neo4j in Phase 5, or should Neo4j persistence wait until Phase 6?
