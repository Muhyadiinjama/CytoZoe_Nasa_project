# Three-minute demo script

**Before you start:**
- Run `scripts/start.ps1` (or `start.sh`) and open http://127.0.0.1:8000.
- Use a clean `runtime/` database, or one prepared for the demo.
- Keep a pre-recorded backup video ready.

| Time | Say | Do |
|---|---|---|
| 0:00–0:25 | "On a deep-space mission Earth may be minutes or hours away. A crew reviewer still has to understand what changed, check the evidence and record a decision. CytoZoe is a local-first workspace for exactly that." | Show Health Overview. Point at the "Historical research data · OSD-575" badge and "Local service connected". |
| 0:15–0:25 (optional) | "Here are the real blood draws arriving one by one." | Press **Play timeline replay** (Fast): the cards update visit by visit, and the creatinine flag appears at L-3. |
| 0:25–1:10 | "These are real Inspiration4 blood samples from NASA's open repository, not a simulated vital-sign stream. For crew member C001, three days before launch, creatinine was 1.37 mg/dL. The lab range in the source file tops out at 1.35, so CytoZoe flags it for review. Because it was preflight, it says plainly that this cannot be a spaceflight effect, and it does not diagnose anything." | Click **Inspect result**. Click **Explain this result**. Scroll to Source: data row 1, exact column, SHA-256. Click **Did radiation cause this?** to show the honest refusal. |
| 1:10–1:50 | "Understanding has to end in a recorded action." | Type "Request repeat measurement / discuss with qualified medical staff", set **Follow-up requested**, then **Save follow-up** ("Saved locally"). Open **Review Log** and show the row and its history. |
| 1:50–2:20 | "Environmental monitoring needs transparent data-quality rules. This is a separate ISS case: the DosTel1 sensor in Columbus on 1 April 2022, deliberately not linked to any crew member. NASA's export reports three timestamps twice with different values. We don't guess. We quarantine all six rows, break the charts there, and show exactly what was excluded." | Open **Radiation Review**. Press **Start replay** at 3600×: the readings stream in, and at about 09:15 the conflict appears in the event feed as it happens. Then show the quality strip, then **Why excluded?**, then **Inspect & review** at 09:15. Show the estimate: 289.60 µGy at the sensor over 98.05% coverage, not a personal dose. |
| 2:20–2:45 | "None of this needs the internet." | Turn Wi-Fi off. Refresh the Review Log: the note is still there. Click **Download HTML** to show the packet with sources, hashes and the note. (The server must stay running.) |
| 2:45–3:00 | "It is a modest, honest foundation. Next come matched onboard vitals and personal dosimetry, only with validation and permission." | Back to Overview. |

## Approved answers to judge questions
- **Is this live astronaut data?** No. These are real historical NASA research records, kept separate. Live sensors are future scope.
- **Can it prove radiation affected blood markers?** No. The data cover different missions, times and people, so there is no person-level join.
- **Where's the AI/ML?** The core is transparent deterministic analysis. Training a predictor on four people would be scientifically indefensible. A local language model could later rephrase explanations, but it could never change numbers.
- **Why is this better than a dashboard?** It covers the full chain — measurement → calculation → evidence → saved follow-up → export — with uncertainty visible and everything offline.
- **On a spacecraft?** This is a laptop proof of concept. Flight use needs validated sensors, cybersecurity, clinical workflow design and qualification.
