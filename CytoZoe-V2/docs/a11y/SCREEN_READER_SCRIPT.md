# Manual screen-reader pass (about 15 minutes)

The automated audit checks names, roles, focus and contrast. It cannot tell whether the result **sounds** right.
Do this once before the demo with NVDA + Firefox or Chrome (Windows) or VoiceOver + Safari (Mac). Tick each line.

Start: run `scripts/start.sh` (or `scripts\start.ps1`) and open http://127.0.0.1:8000/overview. NVDA: Insert+Space toggles browse/focus mode. VoiceOver: Cmd+F5 on; VO = Ctrl+Option.

| # | Do | You should hear | OK? |
|---|---|---|---|
| 1 | Press Tab once | "Skip to main content, link" | |
| 2 | Press Enter | "Health overview, heading level 1" | |
| 3 | NVDA: D / VO: VO+U → Landmarks | "navigation Main", "main" | |
| 4 | Tab to Participant | "Participant, combo box, C001" | |
| 5 | Tab to Visit | "Visit (actual sample), combo box, L-3 · Preflight" | |
| 6 | Tab to "Inspect Creatinine result", press Enter | "Evidence: Creatinine, C001 L-3, dialog" | |
| 7 | Read down (NVDA: arrow down / VO: VO+Right) | Observed 1.370 mg/dL … "Outside supplied range (above)" … Compared with … Source … Limits | |
| 8 | Tab through the dialog to the end | Focus stays in the dialog; it wraps to Close | |
| 9 | Press "Explain this result" | The explanation is read out without moving focus | |
| 10 | Type a note, Tab to Record follow-up, Enter | "Saved locally · Follow-up requested …" is announced | |
| 11 | Press Escape | Focus returns to "Inspect Creatinine result, button" | |
| 12 | Go to Health trends (nav link 2) | Heading "Health trends"; tab list "Blood marker" | |
| 13 | On the Creatinine tab press Right arrow | "Calcium, tab, selected" | |
| 14 | Tab into the chart | "L-92: 1.240 mg/dL, not outside supplied range, toggle button" | |
| 15 | Radiation review, Tab to the rate chart, press Right arrow | A reading with time, value and source row is announced | |
| 16 | Review log: Tab to a review title, Enter | Detail opens; focus lands in "Follow-up note" | |

Write down anything confusing, too long, or read twice. Current known behaviour: the hidden data tables under each
chart are collapsed by default ("Show data table") and must be expanded to be read.
