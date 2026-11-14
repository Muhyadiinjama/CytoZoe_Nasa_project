# Sources and attribution

| ID | Source | Used for | Terms |
|---|---|---|---|
| S4 | NASA OSDR OSD-575, `LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv` — https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 | Health pages | Study page lists CC0-1.0. Cite NASA OSDR OSD-575 (Inspiration4). |
| S5 | NASA OSDR RadLab data API — https://visualization.osdr.nasa.gov/radlab/gui/data-api/ ; DosTel1 — https://visualization.osdr.nasa.gov/radlab/gui/knowledgebase/DosTel1 | Radiation page | Public export. Redistribution terms **not verified**; check before publishing the raw file. |
| S1 | Space Apps 2026 challenge — https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/ | Scope | Resources/Details tabs not verified by tooling; team must read them logged in. |
| S2 | NASA xEHR concept (2023) — https://ntrs.nasa.gov/citations/20230003216 | Problem context | Background only. |
| S3 | NASA clinical decision support for Earth-independent operations (2024) — https://www.nasa.gov/centers-and-facilities/ames/ames-science/ames-space-biosciences/a-clinical-decision-support-system-for-earth-independent-medical-operations/ | Problem context | Background only. |
| S6 | Ollama API — https://docs.ollama.com/api/introduction | Optional local wording | Optional; not required. |

Exact bytes used (also in `data/manifests/sources.json`, checked by `scripts/verify_data.py`):
- OSD-575 CMP: SHA-256 `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9`
- RadLab DosTel1 2022-03-01: SHA-256 `d3f64e7f483c3ae2f08bb5e6633bae5091e661a988c434205ce6bb78c050f7e1`

Not used on purpose: synthetic crew/vitals files, BIDMC, GLDS-174, STS-51-G digitised figures (PRD 0.4).
Third-party code/assets: React 19 (MIT), Starlette/uvicorn (BSD-3), Pydantic (MIT), pandas (BSD-3), esbuild (MIT), Inter font (OFL-1.1).
