# Phase 2 Upload-and-Review UI Prototype

## Scope

Phase 2 adds a local Streamlit review prototype on top of the Phase 1 deterministic KG-grounded extraction baseline.

The implemented workflow is:

```text
Upload or load predictions -> inspect KG-linked annotations -> accept/reject/correct/mark unresolved -> optionally add manual annotations -> save reviewed JSON/JSONL locally
```

This phase does not mutate ClimateKG, write reviewed annotations back to Neo4j, create KG nodes, use LLMs, or use embeddings.

## Project Policy

ClimateKG / Neo4j is read-only for CIMPIndexKG.

Phase 2 uses only:

- exported vocabulary JSONL;
- local canonical mapping config;
- local PDF files;
- local prediction JSON/JSONL;
- local reviewed annotation JSON/JSONL.

The UI never writes to Neo4j and never modifies KG vocabulary records.

## UI Entry Points

Direct Streamlit command:

```bash
streamlit run src/cmip_indexkg/ui/streamlit_app.py
```

CLI wrapper:

```bash
cmip-lens review-ui
```

The wrapper runs:

```bash
python -m streamlit run src/cmip_indexkg/ui/streamlit_app.py
```

## UI Modes

### Mode A: Review Existing Clean-Seed Predictions

Loads existing Phase 1 predictions from:

```text
dataset/data/annotations/predictions_clean.jsonl
```

The user can select one clean-seed paper, inspect predicted annotations grouped by entity type, change review status, add notes, correct predictions to another KG vocabulary entity, add manual annotations, and save reviewed output.

Outputs:

```text
dataset/data/review/reviewed_annotations_clean.jsonl
dataset/data/review/review_session_summary.json
```

### Mode B: Upload PDF and Run Extraction

The user uploads a PDF directly from the UI. The UI creates a `run_id`, saves the uploaded PDF locally, creates an in-memory paper record, runs the existing Phase 1 extraction functions on that one uploaded PDF, and displays extracted KG-linked annotations for review.

Outputs for uploaded PDFs:

```text
dataset/data/uploads/{run_id}.pdf
dataset/data/upload_runs/{run_id}/parsed_document.json
dataset/data/upload_runs/{run_id}/predictions.json
dataset/data/upload_runs/{run_id}/reviewed_annotations.json
dataset/data/upload_runs/{run_id}/review_summary.json
```

## Input Files

Required:

- `data/vocab/climatekg_vocab.jsonl`
- `config/canonical_mappings.json`
- `config/entity_types.json`

Optional for existing-review mode:

- `dataset/data/annotations/predictions_clean.jsonl`

Optional for debugging outside the UI:

- `dataset/data/gold_seed_clean.jsonl`

## Implementation Files

Added:

- `src/cmip_indexkg/ui/__init__.py`
- `src/cmip_indexkg/ui/review_service.py`
- `src/cmip_indexkg/ui/streamlit_app.py`
- `tests/test_phase2_review_service.py`
- `reports/phase2_upload_review_ui.md`

Modified:

- `README.md`
- `pyproject.toml`
- `src/cmip_indexkg/cli/main.py`

## Code Reuse

The UI does not duplicate Phase 1 extraction logic. It calls service helpers that reuse:

- `parse_pdf_record` from `src/cmip_indexkg/ingestion/pdf_parser.py`;
- `load_target_vocab`, `build_alias_index`, `find_mentions`, and `aggregate_mentions` from `src/cmip_indexkg/extraction/baseline.py`.

The service layer in `src/cmip_indexkg/ui/review_service.py` provides testable functions for:

- `generate_run_id`;
- `create_uploaded_paper_record`;
- `save_uploaded_pdf`;
- `run_baseline_on_document`;
- `run_baseline_on_pdf_record`;
- `search_vocab`;
- `serialize_reviewed_annotation`;
- `create_manual_annotation`;
- `generate_review_summary`;
- `save_upload_review`;
- `save_existing_review`.

## Upload Workflow

1. User selects `Upload PDF and run extraction`.
2. User uploads a PDF through `st.file_uploader`.
3. User optionally enters metadata:

- title;
- DOI;
- year;
- authors;
- source URL.

4. UI generates a run ID using UTC timestamp and sanitized filename.
5. Uploaded PDF is saved to:

```text
dataset/data/uploads/{run_id}.pdf
```

6. UI creates a paper record with:

- `pdf_number` set to `run_id`;
- `paper.local_pdf_path` set to the saved upload path;
- empty gold annotation arrays for all six target entity types.

7. UI parses the PDF and runs deterministic extraction.
8. Parsed document and predictions are saved under:

```text
dataset/data/upload_runs/{run_id}/
```

9. Extracted annotations are displayed for review.

## Review Workflow

Predictions are grouped by the six target entity types:

- `Activity`
- `Experiment`
- `Frequency`
- `Source`
- `Realm`
- `Variable`

Each annotation card shows:

- `canonical_label`;
- `canonical_id`;
- `entity_type`;
- `kg_entity_id`;
- `confidence`;
- `mention_count`;
- `matched_texts`;
- `mapping_method`;
- evidence text;
- page number;
- sentence ID.

Each annotation has review controls:

- `suggested`;
- `accepted`;
- `rejected`;
- `corrected`;
- `unresolved`.

The default status is `suggested`.

Reviewers can add notes. For `corrected`, the UI provides local KG vocabulary search scoped to the annotation entity type and stores the selected replacement in `corrected_to`.

Manual annotation add supports:

- choosing an entity type;
- searching the exported KG vocabulary;
- selecting a KG entity;
- adding an optional note;
- saving with `review_status = manual`.

Manual annotations currently store empty evidence.

## Review Schema

Reviewed annotations preserve original prediction fields:

- `kg_entity_id`;
- `canonical_id`;
- `canonical_label`;
- `entity_type`;
- `matched_texts`;
- `evidence`;
- `confidence`;
- `mapping_method`;
- `mention_count`.

Reviewed annotations add:

- `review_status`;
- `reviewed_at`;
- `reviewer_id`;
- `review_notes`;
- `corrected_to`, when status is `corrected`;
- `original_annotation`, when status is `corrected` or `rejected`.

Example reviewed annotation shape:

```json
{
  "entity_type": "Experiment",
  "kg_entity_id": "...",
  "canonical_id": "ssp245",
  "canonical_label": "ssp245",
  "matched_texts": ["SSP2-4.5"],
  "mention_count": 3,
  "confidence": 0.89,
  "mapping_method": "alias_lookup",
  "evidence": [
    {
      "page_number": 4,
      "sentence_id": "p4-s12",
      "sentence_text": "The simulations use SSP2-4.5."
    }
  ],
  "review_status": "accepted",
  "reviewed_at": "2026-06-10T12:00:00+00:00",
  "reviewer_id": "local_user",
  "review_notes": ""
}
```

## Error Handling

The UI displays errors when:

- the vocabulary file is missing;
- the canonical mappings file is missing;
- existing predictions are missing;
- the uploaded PDF cannot be saved or parsed;
- extraction fails;
- saving reviewed annotations fails.

If extraction returns zero annotations, the UI shows a warning and still allows manual annotation add.

## Verification

Dependency installation was updated with:

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

Streamlit was installed and verified:

```text
Streamlit, version 1.58.0
```

CLI wrapper help was verified:

```bash
.venv/bin/cmip-lens review-ui --help
```

Streamlit app import was verified:

```text
streamlit_import_ok 1.58.0 True
```

Headless startup was verified with a short timeout:

```bash
timeout 8s .venv/bin/streamlit run src/cmip_indexkg/ui/streamlit_app.py --server.headless true --server.port 8899
```

The command started successfully and was intentionally stopped by `timeout` after startup:

```text
Uvicorn server started on 0.0.0.0:8899
You can now view your Streamlit app in your browser.
Stopping...
```

The exit code was `124` because `timeout` stopped the server after the startup check. This is expected for the verification command and is not an app failure.

Tests:

```text
30 passed in 0.99s
```

## Limitations

- This is a local prototype, not a production app.
- No authentication or multi-user review state is implemented.
- Existing clean-seed review currently saves the selected paper review session to `reviewed_annotations_clean.jsonl`; it does not maintain an append-only multi-session audit log yet.
- Manual annotations do not require evidence selection yet.
- Correction search is simple substring search over exported vocabulary fields.
- Streamlit rendering itself is not covered by automated tests; service-layer behavior is tested instead.
- No KG mutation, Neo4j write-back, embeddings, or LLM logic are included.

## Acceptance Criteria Status

- UI runs locally: satisfied.
- User can upload a PDF: implemented.
- Uploaded PDF is saved under `dataset/data/uploads`: implemented.
- Baseline extraction runs on the uploaded PDF: implemented through `run_baseline_on_pdf_record`.
- Extracted annotations are displayed grouped by entity type: implemented.
- Evidence sentence and page number are shown: implemented.
- User can accept, reject, correct, or mark unresolved: implemented.
- User can manually add an annotation: implemented.
- Save review writes `reviewed_annotations.json` for upload mode: implemented.
- Save review writes `review_summary.json` for upload mode: implemented.
- Existing clean-seed predictions can be reviewed: implemented.
- Existing Phase 1 CLI still works: preserved.
- Tests pass: satisfied.
- ClimateKG is not modified: satisfied.
