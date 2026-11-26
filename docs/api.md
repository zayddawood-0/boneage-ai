# API

Part of the [BoneAge AI](../README.md) documentation set. See also: [architecture.md](architecture.md), [AGENTS.md](../AGENTS.md#the-growth-review-agent).

REST API, served by the FastAPI backend (stack confirmed, see [README.md](../README.md#tech-stack)), hosted on Render. Base path, versioning scheme, and auth token format are all `[TBD]`; the shapes below are illustrative, not final.

## Conventions

- All request/response bodies are JSON.
- Dates are ISO-8601 (`YYYY-MM-DD`); ages are expressed in months unless noted.
- All endpoints except `/auth/login` require an auth token (format `[TBD]` — e.g. bearer JWT).
- Error shape: `{ "error": { "code": "string", "message": "string" } }` (exact code list `[TBD]`).

## Auth

### `POST /auth/login`
Request:
```json
{ "email": "doctor@example.com", "password": "********" }
```
Response:
```json
{ "token": "jwt-or-session-token", "role": "doctor" }
```
`role` enum: `doctor` | `radiographer` | `admin`. Endpoint access per role is enforced server-side — see [requirements.md](requirements.md#user-roles) for the full permission matrix.

## Patients

### `GET /patients`
Response:
```json
{
  "patients": [
    { "id": "pat_123", "name_or_id": "J. Doe", "sex": "female", "date_of_birth": "2016-03-10" }
  ]
}
```

### `POST /patients`
Request:
```json
{ "name_or_id": "J. Doe", "sex": "female", "date_of_birth": "2016-03-10" }
```
Response: `{ "id": "pat_123" }`

### `GET /patients/{id}`
Response: patient record plus `cases: [...]` (summary list of that patient's cases).

## Cases

### `POST /cases`
Creates a new case for a patient, before image upload.
Request:
```json
{
  "patient_id": "pat_123",
  "xray_date": "2026-11-20",
  "height_cm": null,
  "weight_kg": null,
  "referral_reason": "Short stature concern"
}
```
Response:
```json
{ "id": "case_456", "chronological_age_months": 128 }
```

### `GET /cases/{id}`
Returns the full case report payload: patient info, chronological age, image reference, prediction, agent output, doctor decision (if any), prior scans for the patient.

### `GET /cases?status=flagged&sex=female&sort=date_desc&page=1`
Review queue listing with filters (status, sex), sort, and pagination.
Response:
```json
{
  "cases": [
    {
      "id": "case_456",
      "patient_name_or_id": "J. Doe",
      "sex": "female",
      "chronological_age_months": 128,
      "bone_age_months": 150,
      "gap_months": 22,
      "status": "flagged",
      "xray_date": "2026-11-20"
    }
  ],
  "page": 1,
  "total_pages": "[TBD]"
}
```

## Upload & prediction

### `POST /cases/{id}/upload`
Multipart upload of the X-ray (PNG/JPG/DICOM). Runs image quality checks server-side.
Response (quality check failed):
```json
{ "quality_ok": false, "issues": ["no_hand_detected"] }
```
Response (quality check passed):
```json
{ "quality_ok": true, "image_id": "img_789" }
```

### `POST /cases/{id}/predict`
Runs model inference on the uploaded image (the real model if a trained checkpoint exists, otherwise a clearly-labelled mock — see [model.md](model.md)). Generates three images, each the same size:
Response:
```json
{
  "bone_age_months": 150,
  "uncertainty_months": 4,
  "heatmap_url": "/cases/case_456/heatmap",
  "image_url": "/cases/case_456/image",
  "heatmap_layer_url": "/cases/case_456/heatmap-layer",
  "prediction_source": "real"
}
```

### `GET /cases/{id}/heatmap`
The X-ray and heatmap pre-blended into one flat PNG — used by the PDF report (`GET /cases/{id}/report.pdf`).

### `GET /cases/{id}/image`
The plain preprocessed X-ray alone (PNG, no heatmap) — the real uploaded image, resized/oriented the same way the model saw it, same size as `heatmap-layer` below so the frontend can line the two up. Always the real X-ray, even when `prediction_source` is `"mock"` — only the heatmap is fabricated in that case, never the image.

### `GET /cases/{id}/heatmap-layer`
The Grad-CAM heatmap alone, as a transparent PNG (inferno colours, alpha proportional to attention) the same size as `/image` — lets the frontend composite the two independently (adjustable opacity, side-by-side view) instead of only having the pre-blended version. When `prediction_source` is `"mock"`, this is a visibly-marked fake layer (flat amber tint + "MOCK HEATMAP" text), never dressed up to look like a real attention map.

## Growth review agent

### `POST /cases/{id}/agent-review`
Runs the growth review agent (OpenAI Agents SDK; see [AGENTS.md](../AGENTS.md#the-growth-review-agent)) on a case that already has a prediction. The note-writing step sends only structured numbers/labels (sex, ages, gap, threshold, flag) to the LLM — never the image or patient name/ID (see [safety-and-ethics.md](safety-and-ethics.md#privacy)).
Response:
```json
{
  "gap_direction": "advanced",
  "gap_magnitude_months": 22,
  "flag_status": "flagged",
  "doctor_note": "Predicted bone age is notably advanced relative to chronological age, outside the configured normal range. Possible causes the doctor may consider include early puberty. Please review alongside clinical history."
}
```

## Doctor decision

### `POST /cases/{id}/decision`
Request:
```json
{
  "decision": "confirm_flag",
  "manual_bone_age_months": null,
  "notes": "Agrees with agent flag; recommend endocrinology referral discussion."
}
```
`decision` enum: `confirm_flag` | `within_expected_range` | `model_looks_wrong`.
Response: `{ "ok": true, "decided_at": "2026-11-26T10:00:00Z", "decided_by": "doctor_user_id" }`

## Report export & follow-up

### `GET /cases/{id}/report.pdf`
Returns a generated PDF of the case report (X-ray, heatmap, measurements, agent note, doctor decision).

### `POST /cases/{id}/follow-up`
Request:
```json
{ "follow_up_date": "2027-05-20" }
```
Response: `{ "ok": true }`

## Settings

### `GET /settings`
Response:
```json
{
  "normal_range": { "reference_table": "Greulich & Pyle-based SD reference [TBD, to verify]", "threshold": "±2 SD (default)" },
  "auto_clear_enabled": true,
  "uncertainty_flag_threshold_months": "[TBD]",
  "retention_days": 30,
  "theme": "light",
  "age_unit": "months"
}
```

### `PUT /settings`
Request: same shape as above, partial updates allowed.
Response: `{ "ok": true }`

## Model performance

### `GET /model/performance`
Response:
```json
{
  "mae_overall_months": "[TBD]",
  "mae_by_sex": { "male": "[TBD]", "female": "[TBD]" },
  "mae_by_age_band": "[TBD]",
  "pct_within_12_months": "[TBD]",
  "model_card": { "version": "[TBD]" }
}
```
