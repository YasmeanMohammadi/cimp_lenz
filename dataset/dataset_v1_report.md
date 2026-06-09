# Dataset V1 Report: Gold Labels and ClimateKG Mapping Issues

## Dataset Files

- Source seed file: `dataset/gold_seed_10.jsonl`
- Clean JSONL file: `dataset/data/gold_seed_6.jsonl`
- Mapping output directory: `dataset/data/mapping/`
- KG vocabulary export: `data/vocab/climatekg_vocab.jsonl`

## Executive Summary

The V1 seed dataset contains 6 CMIP publication records with `pdf_number` values `002` through `007`. The dataset is valid JSONL and passes `cmip-lens validate-gold`. It is primarily a CMIP/ScenarioMIP/HighResMIP indexing seed, but the largest source of mapping failures is a CMIP5-heavy paper (`pdf_number=002`) whose website gold labels contain many older CMIP5 model/source IDs. The current ClimateKG `Source` vocabulary contains 394 source records, but many older CMIP5 source IDs are not present as exact KG `Source` labels. Some exist only as institution-prefixed, scenario-suffixed, or otherwise expanded variants.

Current mapping result for `dataset/data/gold_seed_6.jsonl`:

- Mapped labels: 100
- Unresolved labels: 64
- Ambiguous labels: 0

The unresolved labels are not evenly distributed. They are concentrated in `Source` labels from `pdf_number=002`, with the reviewed frequency aliases from `pdf_number=005` now resolved externally.

## Gold Dataset Composition

| Category | Gold label rows | Unique labels |
| --- | ---: | ---: |
| Activity | 8 | 3 |
| Experiment | 30 | 15 |
| Frequency | 8 | 4 |
| Source | 118 | 103 |
| Realm | 0 | 0 |
| Variable | 0 | 0 |

## Paper-Level Summary

| PDF | Year | Activity | Experiments | Frequency | Source count | Notes |
| --- | ---: | --- | --- | --- | ---: | --- |
| 002 | 2023 | CMIP | amip, hist-GHG, hist-nat, historical, piControl | Monthly | 68 | CMIP5-heavy: Drivers of low-frequency Sahel precipitation variability: comparing CMIP5 and CMIP6 ensemble means with observations |
| 003 | 2022 | CMIP, ScenarioMIP | historical, piControl, ssp245 | Monthly | 30 | : The contribution of climate change to increasing extreme ocean warming around Japan |
| 004 | 2023 | ScenarioMIP | ssp119, ssp126, ssp245, ssp370, ssp585 | Monthly | 4 | : Predicted changes to the rate of human decomposition due to climate change during the 21st century |
| 005 | 2023 | CMIP, HighResMIP | highres-future, highresSST-present, historical, ssp126, ssp245, ssp370, ssp585 | 1-hourly, 3-hourly, Daily | 8 | HighResMIP frequency aliases: A warming-induced reduction in snow fraction amplifies rainfall extremes |
| 006 | 2023 | ScenarioMIP | historical, piControl, ssp126, ssp585, ssp585-bgc | Monthly | 6 | : Impact of deoxygenation and warming on global marine species in the 21st century |
| 007 | 2023 | CMIP | historical, rcp45-cmip5, rcp85-cmip5, ssp245, ssp585 | Daily | 2 | : Climate projections of precipitation and temperature in cities from ABC Paulista, in the Metropolitan Region of São Paulo—Brazil |

## ClimateKG Vocabulary Coverage

| Entity type | KG vocab records |
| --- | ---: |
| Activity | 26 |
| Experiment | 481 |
| Frequency | 16 |
| Source | 394 |
| Realm | 14 |
| Variable | 6056 |

The current Phase 0 KG-backed categories exist in the corrected ClimateKG endpoint. The main remaining issue is not a missing category label. It is mismatch between website gold label surface forms and KG source entity naming/coverage.

## Unresolved Mapping Summary

| Entity type | Unresolved rows | Unique unresolved labels | Main affected PDFs |
| --- | ---: | ---: | --- |
| Source | 64 | 63 | 002, 007 |

### Resolved Frequency Labels

The frequency labels `1-hourly` and `3-hourly` are now resolved through reviewed external mappings in `config/canonical_mappings.json`:

| Gold label | Canonical KG label | Mapping method |
| --- | --- | --- |
| `1-hourly` | `1hr` | `manual_alias_mapping` |
| `3-hourly` | `3hr` | `manual_alias_mapping` |

These mappings are maintained in the CMIPIndexKG layer only. The KG was not modified.

### Unresolved Source Labels

The unresolved source labels are mostly CMIP5-era model/source IDs from `pdf_number=002`, a paper comparing CMIP5 and CMIP6 ensemble means. This strongly suggests the dataset includes older CMIP5 source vocabulary that is not represented exactly in the current KG `Source` export, which appears more CMIP6/derived-product oriented in many places.

Unique unresolved Source labels:

- `ACCESS1.0` -> no close compact containment match found
- `ACCESS1.3` -> possible KG near match(es): `ACCESS1-3-rcp85-1-0`
- `BCC-CSM1.1` -> no close compact containment match found
- `BCC-CSM1.1-m` -> no close compact containment match found
- `BESM-OA2.3` -> no close compact containment match found
- `BNU-ESM` -> no close compact containment match found
- `CCSM4` -> possible KG near match(es): `CCSM4-rcp26-1-0, CCSM4-rcp85-1-0`
- `CCSM4-RSMAS` -> no close compact containment match found
- `CESM-BGC` -> no close compact containment match found
- `CESM1-CAM5` -> possible KG near match(es): `CESM1-CAM5-SE-HR, CESM1-CAM5-SE-LR`
- `CESM1-CAM5.1.FV2` -> no close compact containment match found
- `CESM1-FASTCHEM` -> no close compact containment match found
- `CESM1-WACCM` -> possible KG near match(es): `CESM1-WACCM-SC`
- `CFSv2-2011` -> no close compact containment match found
- `CMCC-CESM` -> no close compact containment match found
- `CMCC-CM` -> possible KG near match(es): `CMCC-CM2-HR4, CMCC-CM2-SR5, CMCC-CM2-VHR4, CMCC-CMCC-CM`
- `CMCC-CMS` -> no close compact containment match found
- `CNRM-CM5` -> possible KG near match(es): `CNRM-CERFACS-CNRM-CM5`
- `CNRM-CM5-2` -> no close compact containment match found
- `CSIRO-Mk3.6.0` -> possible KG near match(es): `CSIRO-MK3-6-0-rcp85-1-0, CSIRO-QCCCE-CSIRO-Mk3-6-0`
- `CanAM4` -> no close compact containment match found
- `CanCM4` -> no close compact containment match found
- `CanESM2` -> possible KG near match(es): `CCCma-CanESM2`
- `FGOALS-g2` -> no close compact containment match found
- `FGOALS-gl` -> no close compact containment match found
- `FGOALS-s2` -> no close compact containment match found
- `FIO-ESM` -> possible KG near match(es): `FIO-ESM-2-0`
- `GEOS-5` -> no close compact containment match found
- `GFDL-CM2.1` -> no close compact containment match found
- `GFDL-CM3` -> no close compact containment match found
- `GFDL-ESM2G` -> possible KG near match(es): `NOAA-GFDL-GFDL-ESM2G`
- `GFDL-HIRAM-C180` -> no close compact containment match found
- `GFDL-HIRAM-C360` -> no close compact containment match found
- `GISS-E2-H` -> no close compact containment match found
- `GISS-E2-H-CC` -> no close compact containment match found
- `GISS-E2-R` -> no close compact containment match found
- `GISS-E2-R-CC` -> no close compact containment match found
- `GISS-E2CS-H` -> no close compact containment match found
- `GISS-E2CS-R` -> no close compact containment match found
- `HadCM3` -> no close compact containment match found
- `HadCM3Q` -> no close compact containment match found
- `HadGEM2-A` -> no close compact containment match found
- `HadGEM2-AO` -> no close compact containment match found
- `HadGEM2-CC` -> no close compact containment match found
- `HiGEM1.2` -> no close compact containment match found
- `INM-CM4` -> possible KG near match(es): `INM-CM4-8, LOCA2--INM-CM4-8`
- `IPSL-CM5A-LR` -> possible KG near match(es): `IPSL-IPSL-CM5A-LR`
- `IPSL-CM5A-MR` -> possible KG near match(es): `IPSL-CM5A-MR-rcp26-1-0, IPSL-CM5A-MR-rcp85-1-0, IPSL-IPSL-CM5A-MR`
- `IPSL-CM5B-LR` -> no close compact containment match found
- `MIROC-ESM` -> possible KG near match(es): `MIROC-ESM-CHEM-rcp26-1-0, MIROC-ESM-CHEM-rcp85-1-0`
- `MIROC-ESM-CHEM` -> possible KG near match(es): `MIROC-ESM-CHEM-rcp26-1-0, MIROC-ESM-CHEM-rcp85-1-0`
- `MIROC4h` -> no close compact containment match found
- `MIROC4m` -> no close compact containment match found
- `MIROC5` -> possible KG near match(es): `MIROC-MIROC5, MIROC5-rcp26-1-0, MIROC5-rcp85-1-0`
- `MPI-ESM-HR` -> no close compact containment match found
- `MPI-ESM-LR` -> possible KG near match(es): `MPI-M-MPI-ESM-LR`
- `MPI-ESM-MR` -> possible KG near match(es): `MPI-M-MPI-ESM-MR`
- `MPI-ESM-P` -> no close compact containment match found
- `MRI-CGCM3` -> no close compact containment match found
- `MRI-ESM1` -> no close compact containment match found
- `NICAM.09` -> no close compact containment match found
- `NorESM1-M` -> possible KG near match(es): `NCC-NorESM1-M, NCC-NorESM1-ME, NorESM1-M-rcp26-1-0, NorESM1-M-rcp85-1-0`
- `NorESM1-ME` -> possible KG near match(es): `NCC-NorESM1-ME`

## Is This Mostly CMIP5?

Yes, the unresolved `Source` problem is mostly CMIP5-related in this seed dataset. Evidence:

- `pdf_number=002` is titled "Drivers of low-frequency Sahel precipitation variability: comparing CMIP5 and CMIP6 ensemble means with observations".
- `pdf_number=002` contributes 63 of the 64 unresolved Source rows.
- Many unresolved source IDs are known CMIP5-era model names or CMIP5-style labels, for example `ACCESS1.0`, `BCC-CSM1.1`, `CCSM4`, `CNRM-CM5`, `CSIRO-Mk3.6.0`, `GISS-E2-R`, `HadCM3`, `IPSL-CM5A-LR`, `MIROC5`, `MPI-ESM-LR`, and `NorESM1-M`.
- The KG contains some related entries, but many are prefixed or suffixed, such as `CCCma-CanESM2`, `NOAA-GFDL-GFDL-ESM2G`, `IPSL-IPSL-CM5A-LR`, `MPI-M-MPI-ESM-LR`, and `NCC-NorESM1-M`.

This means the failure mode is not simply lowercasing, hyphen removal, or punctuation normalization. For many Source labels, the KG lacks the exact canonical website form. Some can likely be recovered through manually reviewed equivalence mappings; others may require adding missing CMIP5 source vocabulary to the KG or exporting a different KG node/property set.

## Alias Mismatch Patterns

### 1. Frequency Descriptive Form vs CMIP Frequency Code

- Website: `1-hourly`, `3-hourly`
- KG: `1hr`, `3hr`
- Risk: low. These are direct controlled-vocabulary aliases.
- Recommended handling: alias generation or canonical mapping.

### 2. Institution-Prefixed Source IDs

- Website: `CanESM2`
- KG near match: `CCCma-CanESM2`
- Website: `GFDL-ESM2G`
- KG near match: `NOAA-GFDL-GFDL-ESM2G`
- Website: `IPSL-CM5A-LR`
- KG near match: `IPSL-IPSL-CM5A-LR`
- Website: `MPI-ESM-LR`
- KG near match: `MPI-M-MPI-ESM-LR`
- Website: `NorESM1-M`
- KG near match: `NCC-NorESM1-M`

Risk: medium. Prefix stripping can create false matches if done globally. Use manual canonical mappings or a reviewed source-alias table rather than silent automatic prefix stripping.

### 3. Scenario/Product-Suffixed Source IDs

- Website: `CCSM4`
- KG near matches: `CCSM4-rcp26-1-0`, `CCSM4-rcp85-1-0`
- Website: `MIROC5`
- KG near matches: `MIROC5-rcp26-1-0`, `MIROC5-rcp85-1-0`, `MIROC-MIROC5`
- Website: `ACCESS1.3`
- KG near match: `ACCESS1-3-rcp85-1-0`

Risk: high. A scenario-suffixed source may represent a data product or specific run rather than the base model/source. These should not be automatically collapsed without schema review.

### 4. Dot/Hyphen/Punctuation Differences

- Website: `CSIRO-Mk3.6.0`
- KG near matches: `CSIRO-MK3-6-0-rcp85-1-0`, `CSIRO-QCCCE-CSIRO-Mk3-6-0`

Risk: medium. Existing compact normalization handles punctuation, but not semantic prefix/suffix differences. Punctuation normalization alone is not enough.

## Recommended Resolution Strategy

1. Treat `Frequency` unresolved labels as straightforward alias additions after review.
2. Do not silently map all unresolved `Source` labels by prefix/suffix heuristics.
3. Create a reviewed `Source` canonical mapping table for known CMIP5 equivalences.
4. Separate base source IDs from scenario-specific/product-specific source-like nodes in KG if possible.
5. Consider expanding the KG vocabulary export to include a CMIP5 source vocabulary source if those nodes/properties exist elsewhere in ClimateKG.
6. Keep unresolved labels visible in `gold_unresolved.jsonl` until manually resolved.
7. Track every manual mapping in `config/canonical_mappings.json` or a dedicated source mapping config so evaluation remains reproducible.

## Practical Next Checks

- Query the KG for CMIP5 source IDs outside the `Source` label, if such vocabulary exists under another label or property.
- Inspect whether `Source` nodes with suffixes like `-rcp85-1-0` have relationships to base source/model nodes.
- Decide whether website gold `Source` should evaluate against base model/source IDs only, or whether prefixed/suffixed product IDs should be accepted as equivalent.
- Add frequency aliases for `1-hourly` and `3-hourly` if approved.
- Build a reviewed CMIP5 source equivalence list for the 63 unique unresolved source labels before using this dataset as a strict benchmark.

## Current Unresolved Labels

### Frequency

- `1-hourly`
- `3-hourly`

### Source

- `ACCESS1.0`
- `ACCESS1.3`
- `BCC-CSM1.1`
- `BCC-CSM1.1-m`
- `BESM-OA2.3`
- `BNU-ESM`
- `CCSM4`
- `CCSM4-RSMAS`
- `CESM-BGC`
- `CESM1-CAM5`
- `CESM1-CAM5.1.FV2`
- `CESM1-FASTCHEM`
- `CESM1-WACCM`
- `CFSv2-2011`
- `CMCC-CESM`
- `CMCC-CM`
- `CMCC-CMS`
- `CNRM-CM5`
- `CNRM-CM5-2`
- `CSIRO-Mk3.6.0`
- `CanAM4`
- `CanCM4`
- `CanESM2`
- `FGOALS-g2`
- `FGOALS-gl`
- `FGOALS-s2`
- `FIO-ESM`
- `GEOS-5`
- `GFDL-CM2.1`
- `GFDL-CM3`
- `GFDL-ESM2G`
- `GFDL-HIRAM-C180`
- `GFDL-HIRAM-C360`
- `GISS-E2-H`
- `GISS-E2-H-CC`
- `GISS-E2-R`
- `GISS-E2-R-CC`
- `GISS-E2CS-H`
- `GISS-E2CS-R`
- `HadCM3`
- `HadCM3Q`
- `HadGEM2-A`
- `HadGEM2-AO`
- `HadGEM2-CC`
- `HiGEM1.2`
- `INM-CM4`
- `IPSL-CM5A-LR`
- `IPSL-CM5A-MR`
- `IPSL-CM5B-LR`
- `MIROC-ESM`
- `MIROC-ESM-CHEM`
- `MIROC4h`
- `MIROC4m`
- `MIROC5`
- `MPI-ESM-HR`
- `MPI-ESM-LR`
- `MPI-ESM-MR`
- `MPI-ESM-P`
- `MRI-CGCM3`
- `MRI-ESM1`
- `NICAM.09`
- `NorESM1-M`
- `NorESM1-ME`



## Dataset Split

The six-record seed remains available as `dataset/data/gold_seed_6.jsonl`. It has been split into two derived JSONL files without changing paper fields, labels, notes, or `pdf_number` values:

- Clean split: `dataset/data/gold_seed_clean.jsonl` contains `pdf_number` values `003`, `004`, `005`, `006`, and `007`.
- Coverage challenge split: `dataset/data/gold_seed_coverage_challenge.jsonl` contains `pdf_number` `002`.

The challenge split isolates the CMIP5-heavy paper whose unresolved labels are almost entirely older Source labels. These are intentionally left unresolved because no reviewed Source mappings have been added.

## Updated Mapping Results After Frequency Alias Cleanup

All mapping runs used `--canonical-mappings config/canonical_mappings.json`.

| Dataset | Mapped | Unresolved | Ambiguous | Remaining unresolved |
| --- | ---: | ---: | ---: | --- |
| Full seed | 100 | 64 | 0 | Source only: 64 rows, 63 unique labels |
| Clean split | 88 | 1 | 0 | Source only: `HadCM3` |
| Coverage challenge | 12 | 63 | 0 | Source only: 63 unique CMIP5-era labels |

## Frequency Alias Resolution

Reviewed external Frequency mappings were added:

- `1-hourly -> 1hr`
- `3-hourly -> 3hr`

Both labels now resolve in the full and clean mappings with `mapping_method: manual_alias_mapping`. Raw website labels are preserved as `website_label` and `raw_label`; the resolved target appears as `canonical_label`.

## Intentional Unresolved CMIP5 Source Labels

No Source mappings were added in this cleanup. The unresolved Source labels from `pdf_number=002` remain in `dataset/data/mapping_challenge/gold_unresolved.jsonl` for future manual review. This is deliberate: many are CMIP5-era model IDs, institution-prefixed variants, or scenario/product-suffixed near matches. They should not be collapsed automatically or written back to ClimateKG.
