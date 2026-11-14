# Three-minute demo (PRD 21.1)

Before: `scripts/start.sh`, open http://127.0.0.1:8000/overview, close other tabs, browser at 100% zoom. Optional: a
fresh database (`CYTOZOE_DATA_DIR=$(mktemp -d) scripts/start.sh`) so the Review log starts empty. Have the recorded
backup video ready.

| Time | Say | Do |
|---|---|---|
| 0:00–0:25 | "On a deep-space mission, Earth isn't always on the line. A crew reviewer needs to understand what changed, check the evidence and record a follow-up — on their own." | Overview: point at "Historical research sample" and the NASA OSD-575 badge. |
| 0:25–1:10 | "This is a real Inspiration4 blood sample, not a simulated vital sign. C001, three days before launch: creatinine 1.37 against the lab's upper bound of 1.35." | *Inspect result* on Creatinine. Show source line 2 + SHA-256, then the retrospective preflight mean 1.2367 (n=3). "It's preflight, so it can't be a spaceflight effect, and the app says so." Press *How was this calculated?* |
| 1:10–1:50 | "Understanding has to end in an action." | Type "Request repeat measurement / discuss with qualified medical staff", status *Follow-up requested*, *Record follow-up* → "Saved locally". Open **Review log**; show history. |
| 1:50–2:20 | "Environmental monitoring needs honest data quality, not a fake diagnosis. This is a separate ISS case — never linked to these people." | **Radiation review**: banner, then *Why excluded?* — four timestamps with two different readings each. "We don't average or guess; both rows are kept and left out, and the charts break there." |
| 2:20–2:45 | "Everything works without the internet." | Turn Wi-Fi off. Refresh, open the review, *Export review packet* → *Download HTML*. |
| 2:45–3:00 | "Next: matched onboard data — personal dosimetry, time-aligned vitals — only with permission and validation." | Stop on the Review log or the exported packet. |

Judge answers (PRD 21.2): live data? No — real historical NASA records, kept separate. Radiation caused it? Can't be
shown: different people, missions and dates. Where is AI? The core is transparent calculation; an optional local model may
only reword verified facts. Training a model on four people would not be valid.
