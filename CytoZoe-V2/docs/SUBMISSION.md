# Submission draft (check the official Project tab form and limits before pasting)

**Project title:** CytoZoe — Understand the change. Keep the evidence.
**Challenge:** Create Health Monitoring Software for Astronauts on Space Missions
**Tagline:** Offline-first astronaut health evidence and review, grounded in real NASA research data.

**30-word pitch:** CytoZoe transforms historical astronaut biomarker records into traceable comparisons and saved follow-ups,
while separately revealing ISS radiation data-quality issues — an offline-first foundation for future autonomous crew health review.

**Problem.** On long missions crews may need to review health information without Earth support. A spreadsheet of
measurements doesn't show what changed, which source supports it, how uncertain it is, or what follow-up was decided.

**Solution.** A local app with four pages. It compares each real Inspiration4 blood measurement (NASA OSD-575) with the
lab range in the source and with the person's own preflight average, shows the exact source row and file hash, explains the
calculation, and lets the reviewer save a follow-up with full history and export a review packet. A separate page reviews one
day of ISS radiation data (NASA RadLab DosTel1), exposing four conflicting timestamps and estimating sensor dose only over
covered intervals.

**How it works.** Python service (Starlette, Pydantic, pandas, SQLite) on 127.0.0.1 with three deterministic engines
(ingestion/quality, health comparisons, radiation integration); React + TypeScript interface with accessible SVG charts.
108 automated checks (34 backend, 74 browser) plus an accessibility audit. No internet needed after setup.

**Impact.** Shows how a crew reviewer could go from measurement to evidence to recorded action independently. A
demonstration, not a measured clinical outcome.

**Limitations.** Historical data only; four people; no diagnosis, health scores, personal dose or radiation–health
link (the two datasets are different people, missions and dates). Future work needs matched onboard data and validation.

**NASA data used.** OSD-575 (https://osdr.nasa.gov/bio/repo/data/studies/OSD-575); RadLab DosTel1
(https://visualization.osdr.nasa.gov/radlab/gui/data-api/).

**AI use disclosure (draft — adapt to the official wording required).** The team used Anthropic's Claude as a coding
assistant to help write and test the software and documentation, under the team's direction and review. The submitted app
does not call any cloud AI service. An optional, off-by-default feature can use a locally installed language model to
reword already-verified explanations; it cannot change numbers or save anything by itself.

**Links to fill in:** GitHub repository · demo video (2–3 min, real app) · team page.

## Before submitting (PRD 22.4)
1. Logged in: confirm team, challenge, members, local event and deadline (15 Nov 2026, 11:59 PM local time).
2. Read the challenge **Resources** and **Details** tabs and the 2026 participant terms (AI disclosure, licences, media).
3. Fill the Project tab early and save a draft; check each link in a logged-out browser; keep the receipt.
