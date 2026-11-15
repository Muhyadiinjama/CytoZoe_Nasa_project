# Known limitations

## Scientific
- The data are historical: Inspiration4 (2021) serum samples and one ISS day (1 April 2022). Nothing is live.
- There are 4 participants with 7 sparse visits each. The data cannot support validation, prediction or a disease label.
- The supplied ranges are the laboratory bounds recorded in the source. They are not CytoZoe's clinical thresholds.
- The sensor-dose estimate covers accepted intervals at the instrument only (98.05% of the recorded span). It is not personal, organ or effective dose, and it is not mission-certified.
- The source timestamp timezone is not verified, so times are shown as exported.
- The health and radiation cases cannot be paired, and no causal claim is possible.

## Product
- The optional local LLM wording adapter (P1 AI-01) is **not implemented**. Ollama is not installed on the build machine, so only deterministic "Verified explanation" templates exist.
- Speech read-out (P2) is not implemented.
- "Real time" means **replay** of recorded data at accelerated speed, plus live sync between windows. There is no live sensor feed, and the app never presents replayed data as live.
- The typed-question assistant uses keyword routing to five fixed answers. It does not understand open-ended questions; anything else gets an explicit "unsupported" reply.
- The visual design no longer uses the PRD §5 navy/teal palette (changed at the team's request).
- The app needs the local server running. It is not an offline-capable PWA and does not work once the server is stopped.
- The audit trail is a local log, not a tamper-proof compliance record. There is no authentication; this is a single-user local tool.
- The JS bundle is about 726 kB (214 kB gzip) because Recharts ships in one chunk. This is acceptable on localhost but not code-split.

## Verification gaps
- The offline proof used browser-level network isolation (Playwright aborts every non-loopback request; 0 attempted). A physical Wi-Fi-off test on the demo laptop has **not** been performed and should be done by the team.
- Accessibility was checked with automated axe rules (WCAG 2.0/2.1/2.2 A/AA tags), a scripted keyboard-only journey and focus checks. Manual screen-reader testing (NVDA/VoiceOver) and a manual 200% zoom pass were **not** performed.
- E2E ran on Microsoft Edge (Chromium) on Windows 11 only.
- The first-run usability timing (T31) is not measured with a real user. The scripted journey time is recorded in TEST_REPORT.md, but it is not a human measurement.
