# Sources and provenance

All source definitions are pinned in `data/manifests/sources.json`. Raw files are fetched once, by `scripts/fetch_data.py`, from the allow-listed hosts `osdr.nasa.gov` and `visualization.osdr.nasa.gov` over HTTPS. Each fetch also writes `data/raw/<key>.fetch.json`, recording the retrieval time, byte count, SHA-256 and original header.

| ID | Source | SHA-256 (verified 2026-11-14) | Rows | Licence / terms |
|---|---|---|---|---|
| OSD-575-CMP | [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575), `LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv` | `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9` | 28 | CC0-1.0 per study page |
| RADLAB-DOSTEL1-2022-03-01 | [RadLab API](https://visualization.osdr.nasa.gov/radlab/gui/data-api/), DosTel1, 2022-03-01 | `d3f64e7f483c3ae2f08bb5e6633bae5091e661a988c434205ce6bb78c050f7e1` | 1,202 | Public API; redistribution not verified, so not committed |

Both hashes matched the PRD's previously inspected snapshots byte-for-byte on 14 November 2026.

**If a future download differs:** `fetch_data.py` reports `[CHANGED]`, and `verify_data.py --strict` exits non-zero. The importer refuses different bytes for an already-loaded dataset (HTTP 409 `DATASET_VERSION_CHANGE`) unless `import_data.py --allow-new-version` is run deliberately. Nothing is substituted or patched.

## Background references (context only)
- [S1] Challenge: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
- [S2] NASA exploration EHR concept (2023): https://ntrs.nasa.gov/citations/20230003216
- [S3] NASA Earth-independent clinical decision support (2024): https://www.nasa.gov/centers-and-facilities/ames/ames-science/ames-space-biosciences/a-clinical-decision-support-system-for-earth-independent-medical-operations/
- DosTel1 instrument: https://visualization.osdr.nasa.gov/radlab/gui/knowledgebase/DosTel1

These references establish the operational need. They do not show that NASA lacks such tools, and they do not endorse CytoZoe.

## Not used
GLDS-174 (deferred future molecular context) and BIDMC (explicitly excluded). See the README section "Datasets" for the reasons.
