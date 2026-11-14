# CytoZoe frontend release report (Frontend Design BRD v2)

**Branch:** `Mustafa`, on top of backend v3 commit `fa63ed8` · **Date:** 14 November 2026 · **Status:** ready for PM review. Not merged into `main`.

The visual direction is "Aerospace Precision 2.0":
- a cinematic navy introduction;
- a midnight navigation shell;
- bright, readable working pages;
- a dark Mission Intelligence panel.

The backend is still the only source of every number.

---

## 1. What changed

| Area | Change |
|---|---|
| **Design system** | New tokens in `styles/tokens.css`: navy `#061525`/`#0B1F32`, canvas `#F3F6F9`, teal `#087F8C` for actions, cyan `#35E1D5` only on dark, amber for "outside supplied range" and red only for real errors. Typography is Inter (bundled locally) plus a system mono. The serif face was removed. Sizes: 216 px sidebar, 1440 px content width, 44 px controls, focus ring `#2458D3`. |
| **Brand** | Original crescent-and-orbit SVG mark (`components/icons.tsx` → `BrandMark`) and a new favicon. No NASA logo or insignia anywhere. |
| **App shell** | Dark navigation with numbered routes, a cyan active indicator, live recent reviews, a live-sync status and an "About & photo credits" link. On phones it becomes a collapsible menu. |
| **Landing `/`** (new, `pages/Landing.tsx`) | Headline "Understand the change. Keep the evidence.", **Launch Workspace** and **Explore the system**, three propositions, "How it works" (links into the 4 real routes), two case-study cards kept visibly apart, a scientific-integrity section and an accessible **Photo & data credits** footer. It makes **no API calls**. |
| **Routes** | `/overview`, `/health`, `/environment` and `/reviews` are unchanged and work as direct links. `/` used to redirect to `/overview`; it now shows the introduction. |
| **Health Overview** | Metric cards now have a value-in-range track. It is presentation only: the backend's value is drawn against the backend's bounds. Supplied-range text, a phase chip, a "Results to review" action list, the replay panel, a dataset and saved-review summary, and the new **Mission Health Intelligence Brief** panel (`components/MissionBrief.tsx`). |
| **Mission Brief** | Renders `GET /api/mission/brief?participant&sample&mode=historical` exactly as returned. For each finding it shows: observed, compared with, source (row, file line, column, raw value), why flagged, limitations, next step, then "Record follow-up" and "Inspect evidence". It also shows a table of other markers, missing markers, provenance, SHA-256, validation status, dataset limitations and the case-separation text. It uses no severity ranking and no frontend wording for findings. |
| **Health Trends** | New **Baseline comparison** card. It shows the *retrospective preflight mean* (`/api/health/trend`) next to the baseline *known before this visit* (`/api/replay/health`: `baseline_so_far`, `n_so_far`, `baseline_visits`), each labelled separately. The chart is recoloured; no data logic changed. |
| **Radiation Review** | The persistent "Separate case study · ISS Columbus · DosTel1 · 1 March 2022 · Not linked…" banner is now a navy strip. The quality strip, both charts, the gap breaks and the conflict cards are restyled; no calculation changed. |
| **Review Log & Export** | Restyled. Behaviour is unchanged: filters, history, version-conflict handling, and HTML/JSON downloads. |
| **Evidence drawer** | Narrowed to 480 px on desktop (full screen on phones), with a navy header. Its sections are renamed to the BRD names: **Observation · Calculation · Source & quality · Limitations · Follow-up**. Source now shows the **provenance** (`source.provenance`). |

### Backend change (minimal, tested)
**Gap found:** this Windows Python's `mimetypes` returns no type for `.webp`. The app sends `X-Content-Type-Options: nosniff`, so the browser would refuse the bundled WebP images.

**Fix:** `backend/app/main.py` now registers `image/webp`, `image/avif`, `font/woff2` and `image/svg+xml`. It is additive and changes no API.

**Tests:** `backend/tests/test_static_media.py` has 5 tests: content types, `nosniff`, and path traversal still blocked.

## 2. NASA imagery
Two photos, the maximum the BRD allows. Both were downloaded once from the official pages, resized and encoded to AVIF and WebP, and served from `/media/`. Credits and rights are recorded in [`frontend/public/media/README.md`](../frontend/public/media/README.md).

| Use | Item | Largest file |
|---|---|---|
| Landing hero | ISS067-E-245176, sunrise over Earth's limb (JSC Earth Science & Remote Sensing Unit) | 18.9 KB WebP / 10.8 KB AVIF at 2400 px; phone crop 6.3 KB |
| Case-study card (not behind any plot) | iss073e0257211, city lights and lightning below the ISS (NASA JSC) | 36.5 KB WebP at 1600 px |

The JSC conditions of use were checked: the credit line is shown in the footer, and no endorsement is implied. The images are decorative, are labelled "decorative context, not study data", and fall back to a CSS gradient if missing.

## 3. Test results (all actually run, 14 Nov 2026, Windows 11, Edge)

| Suite | Before (baseline at `fa63ed8`) | After |
|---|---|---|
| Backend `pytest` | 56 passed | **61 passed** (+5 media tests) |
| TypeScript strict | 0 errors | **0 errors** |
| Frontend unit (`vitest`) | 4 passed | **4 passed** (evidence-section names updated to the BRD names) |
| Production build | OK | **OK**: JS 770 kB (225 kB gzip), CSS 49 kB |
| Browser E2E (Playwright, Edge) | 11 passed, **1 failed** (T20 restart: "server did not start"; started in 1.5 s by hand; one-off environment issue) | **16 passed, 0 failed** in one full run (1.5 min, `frontend-v2-e2e-final.log`) |

New E2E specs (`frontend/e2e/frontend-v2.spec.ts`):
1. **Landing:**
   - every `/media/` response is 200 with `image/avif` or `image/webp`;
   - the hero image actually decodes;
   - 0 axe violations (WCAG 2.0/2.1/2.2 A/AA);
   - **0 `/api` calls**;
   - 0 external requests;
   - the CTA opens the workspace.
2. **Mission Brief for all 28 samples:**
   - for each one, the panel's summary, finding count, values, "compared with" text, source row, file line and column, other-marker rows and SHA-256 match `/api/mission/brief`;
   - every finding's value and source row also equal `/api/evidence/{id}`.
3. **Brief → follow-up:** opens the shared drawer with focus on the note field, shows provenance, and Escape returns focus to the button.
4. **Two baselines:**
   - C001 L-3 creatinine shows retrospective **1.2367 mg/dL (n = 3 · L-92, L-44, L-3)** and known-before-visit **1.17 mg/dL (n = 2 · L-92, L-44)**;
   - at L-92 the replay baseline shows "Not available · no earlier preflight visit" (no leakage).

The existing specs still pass after the redesign:
- the journey now starts on the landing page;
- axe on all 4 routes and the drawer;
- the keyboard focus trap and restore;
- 390/768/1024/1440 px with no horizontal scroll;
- service-down and no-data states;
- 409 conflict;
- radiation replay and pause;
- timeline replay;
- live sync;
- restart persistence.

Logs: `docs/test-logs/frontend-v2-*.log`. Screenshots:
- `docs/screenshots/{overview,health,environment,reviews}-{390,768,1024,1440}.png`, regenerated by the E2E run;
- `docs/screenshots/frontend-v2-*.png` (landing, overview, health, radiation, reviews).

During this work I hit one bug, in my own new test: a regex for visit labels with `+` was wrong. I fixed it and re-ran the test.

## 4. BRD milestone checklist

| Milestone | Gate evidence | Result |
|---|---|---|
| F0 Audit | API contract, example payload, OpenAPI fields and all components read; baseline suites run and logged | ✅ |
| F1 Visual foundation | Tokens, logo, shell, status components; 4 widths with no overflow; keyboard nav and axe pass | ✅ |
| F2 Overview + Brief | C001/L-3 values match the backend; all 28 samples match the API; errors shown with retry | ✅ |
| F3 Trends + evidence + replay | Two baselines labelled; no leakage at L-92 and L-3; no NaN shown (fallbacks are "Not available" or "—") | ✅ |
| F4 Radiation + Reviews + Export | Separate-case labelling, units and gaps unchanged and still tested; restart persistence and export spec pass | ✅ |
| F5 Release QA | Automated suites, axe, keyboard and responsive done. **Not done: physical Wi-Fi-off run on the demo laptop, manual screen-reader pass, manual 200 % zoom pass, 3-minute human walkthrough** | ⚠️ partly |
| F6 Presentation polish | Landing built; static image with reduced-motion fallback (all animation off under `prefers-reduced-motion`); no WebGL or 3D added on purpose | ✅ (no 3D) |

## 5. Limitations and open items
- **Offline:** verified only by blocking every non-loopback request in Playwright, with 0 external requests recorded. The team still needs to switch off Wi-Fi on the demo laptop and run the journey.
- The landing page's "How it works" and case-study cards are fixed copy (structure facts like 4 participants and 7 visits), not live numbers. Live numbers stay on the workspace screens.
- The landing headline uses gradient text. axe cannot measure contrast on gradients, so it reports them as "needs review", not as failures. Visually the text is white or pale cyan on near-black.
- The `@fontsource-variable/source-serif-4` package is no longer imported. It is still in `package.json` so the lockfile is not changed in this PR; it can be removed afterwards.
- The JS bundle is still about 770 kB because of Recharts; this does not matter for a local app.
- Raw NASA CSVs were re-fetched (hash-verified) only to run the tests and are deleted again afterwards, as requested.

## 6. PM merge checklist
- [ ] Review the screenshots in `docs/screenshots/frontend-v2-*.png`.
- [ ] `npm run setup` → `npm run data` → `npm run dev`; open `/`, click Launch Workspace, walk through C001 L-3 creatinine.
- [ ] Wi-Fi-off run on the demo laptop (RELEASE_CHECKLIST.md).
- [ ] Confirm the photo credits in the footer.
- [ ] Merge `Mustafa` → `main` via PR once satisfied.
