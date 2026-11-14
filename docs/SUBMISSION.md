# Space Apps 2026 submission pack

> Nothing here has been submitted. The team must submit through the **Project tab of the CytoZoe team page** while logged in. Creating a GitHub repo does not count as submitting. The official form fields, resources tab, terms and AI-disclosure rules could not be checked by automated tools; read them in the portal.

## Copy-ready text
- **Project title:** CytoZoe — Understand the change. Keep the evidence.
- **Challenge:** Create Health Monitoring Software for Astronauts on Space Missions
- **Tagline:** Offline-first astronaut health evidence and review, grounded in real NASA research data.
- **Elevator pitch (30 words):** CytoZoe transforms historical astronaut biomarker records into traceable comparisons and saved follow-ups, while separately revealing ISS radiation data-quality issues—an offline-first foundation for future autonomous crew health review.

**Problem.** On deep-space missions, crews may need to review health information while Earth is delayed or unreachable. A table of numbers doesn't show what changed, which source supports a finding, how uncertain it is, or what follow-up was decided.

**Solution.** A local workspace that:
- compares real NASA Inspiration4 blood markers (OSD-575) with each person's own preflight samples and the supplied laboratory range;
- links every number to its exact source row and hash;
- explains results with fixed, verified templates;
- saves reviewer follow-ups with an audit trail, and exports a printable evidence packet — all without internet.

A separate ISS DosTel1 radiation case shows transparent handling of real conflicting sensor readings.

**How it works.** React/TypeScript + FastAPI + SQLite on 127.0.0.1. There are three deterministic engines:
- ingestion & quality (SHA-256 verification, schema checks, conflict quarantine);
- health comparison (retrospective preflight mean, strict range rule);
- sensor-dose integration (trapezoid over covered intervals only).

There is no trained model and no cloud dependency.

**Impact.** Demonstrates a complete review-to-handoff workflow that keeps working during communication blackouts and makes uncertainty visible. This is a plausible benefit, not a measured clinical outcome.

**Limitations.**
- Historical data only, from 4 participants.
- No diagnosis, prediction or personal dose.
- The health and radiation data cannot be paired.
- A research demo, not flight or clinical software.

**NASA data used.**
- OSD-575 (https://osdr.nasa.gov/bio/repo/data/studies/OSD-575)
- NASA OSDR RadLab DosTel1 (https://visualization.osdr.nasa.gov/radlab/gui/data-api/)

**Tools.** Python, FastAPI, pandas, SQLite, React, Vite, Recharts, Playwright. The code was written with an AI coding assistant (Claude Code); the app uses no AI at runtime. *Confirm the required AI-disclosure wording in the 2026 rules.*

## Checklist (tick only with observed proof)
- [ ] Log in; confirm the CytoZoe team, its members (≤ 6) and the selected challenge.
- [ ] Read the challenge **Resources** and **Details** tabs, participant Terms, AI-disclosure, licensing and media rules.
- [ ] Confirm the deadline in the team's **local time zone** (global window closes 15 Nov 2026, 11:59 PM local per the event site).
- [ ] Push the repo to GitHub (team decision on visibility). Check it from a logged-out browser. Do not commit `runtime/` or `data/raw/`.
- [ ] Record a 2–3 minute video of the real running app, following [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Do a physical Wi-Fi-off test on camera.
- [ ] Fill in the Project tab, save a draft early, submit, reopen the public preview, and save a screenshot as a receipt.
- [ ] Record team contributions accurately.
