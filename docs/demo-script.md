# Demo script

Part of the [BoneAge AI](../README.md) documentation set. A 3–4 minute walkthrough for judges, using the seeded demo cases (`backend/scripts/seed_demo_data.py`: BA-1037..BA-1042). See also: [testing.md](testing.md#demo-script) for the earlier, more exploratory version of this script and [safety-and-ethics.md](safety-and-ethics.md) for the disclaimer language referenced throughout.

Sign in as the demo doctor (`doctor@boneage.ai` / `demo-password`) before judges arrive, and have the dashboard open.

## 0. Open with the disclaimer (15s)

> "BoneAge AI is decision support only — it never diagnoses anything. It estimates a child's bone age from a hand X-ray, compares it to their chronological age, and flags cases a doctor should look at. The doctor always makes the final call."

## 1. Dashboard (20s)

- Point out the summary cards and the bone age vs. chronological age chart, populated from the seeded demo cases.
- Mention the data: trained on the RSNA Pediatric Bone Age Challenge dataset (~14k hand X-rays); the growth review agent's flagging behaviour is checked against the Digital Hand Atlas and/or RHPE datasets, which carry real chronological age (RSNA doesn't). See [data.md](data.md).

## 2. A normal case (30s)

- Open **BA-1040** (within range, auto-cleared) from Patients or the dashboard's case preview.
- Show the case report: X-ray + heatmap, predicted bone age close to chronological age, status labelled "within expected range" (not just a colour).
- Note it never entered the review queue because auto-clear is enabled — but it's still fully visible and searchable here.

## 3. A delayed flag (45s)

- Open **BA-1042** (flagged, delayed — bone age behind chronological age).
- Walk through the case report: the Grad-CAM heatmap overlay, the measurements panel (chronological age, predicted bone age, gap, model uncertainty), and the growth review agent's reasoning panel.
- Read the doctor note aloud — point out it names a direction and magnitude and lists "possible causes to check" (e.g. constitutional delay, hypothyroidism) **as possibilities, never a diagnosis** — and that the flag decision itself came from a deterministic rule (`compare_gap`), not an LLM guess. See [AGENTS.md](../AGENTS.md#the-growth-review-agent).

## 4. An advanced flag (30s)

- Open **BA-1041** (flagged, advanced — bone age ahead of chronological age).
- Same panel, opposite direction — enough to show the agent isn't hard-coded to one outcome.

## 5. The doctor confirms a flag (30s)

- On **BA-1042** (or **BA-1037**, already confirmed, if you want to show the "after" state instead), use the decision controls: select **Confirm flag**, optionally add a note, save.
- Point out the other two options — **within expected range** (doctor overrides the agent) and **model looks wrong, re-read manually** (doctor overrides the model) — and that either way, the doctor's recorded decision is what's authoritative, not the model or the agent.

## 6. PDF export (15s)

- From the same case, click **Export PDF** and show the generated report (X-ray, heatmap, measurements, agent note, doctor decision, disclaimer).

## 7. Review queue (20s)

- Go to the **Review queue**: show status tabs, the sex filter, search, and sort — filter down to flagged cases, open one from the table.

## 8. Settings + theme (20s)

- Open **Settings**: point out the flagging rule (fixed ± months vs. SD-based, both admin-configurable, no hard-coded clinical numbers in code) and the auto-clear toggle.
- Toggle light/dark theme to show full theming coverage.

## 9. Model performance (15s)

- Open **Model performance**: MAE breakdowns and the model card are shown as `[TBD]` — be upfront that no real training run has happened yet, this screen is wired end-to-end and will populate once it has (see [model.md](model.md)).

## 10. Close (15s)

> "Every flagged case still needs a doctor to open it, read it, and decide — the model and the agent never act on their own. That's deliberate: this is a prototype, not a cleared medical device, and keeping a clinician in the loop is the whole point."

---

## If something breaks

- **Backend/model unavailable:** fall back to the local copy (`uvicorn app.main:app --reload` + `npm run dev`, see [README.md](../README.md#setup)) rather than fighting the live deployment in front of judges.
- **No trained checkpoint / download failed:** the "Demo model" chip on a result means you're seeing the mock predictor, not a real prediction — say so plainly if asked; the flagging logic and UI flow are still real.
- **Render free-tier cold start:** the backend may take ~30–60s to wake up after idling; open the dashboard a minute before you're called up.
