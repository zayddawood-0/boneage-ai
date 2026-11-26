// Mirrors backend/app/schemas.py exactly — see docs/api.md for the
// illustrative version (it says its own shapes are "not final"; these are
// the real ones).

export type Role = 'doctor' | 'radiographer' | 'admin'
export type Sex = 'male' | 'female'
export type Decision = 'confirm_flag' | 'within_expected_range' | 'model_looks_wrong'
export type FlagStatus = 'cleared' | 'flagged' | 'needs_review'
export type GapDirection = 'within_range' | 'delayed' | 'advanced' | 'uncertain'
export type RuleType = 'sd' | 'fixed_months'
export type PredictionSource = 'real' | 'mock'
export type NoteSource = 'llm' | 'template'

export interface OkResponse {
  ok: boolean
}

export interface TokenResponse {
  token: string
  role: Role
}

export interface PatientCreate {
  name_or_id: string
  sex: Sex
  date_of_birth: string
}

export interface PatientOut {
  id: number
  patient_code: string
  name_or_id: string
  sex: Sex
  date_of_birth: string
}

export interface PatientDetail extends PatientOut {
  cases: CaseListItem[]
}

export interface CaseCreate {
  patient_id: number
  xray_date: string
  height_cm?: number | null
  weight_kg?: number | null
  referral_reason?: string | null
}

export interface CaseCreateResponse {
  id: number
  case_code: string
  chronological_age_months: number
}

export interface CaseListItem {
  id: number
  case_code: string
  patient_name_or_id: string
  sex: Sex
  chronological_age_months: number | null
  bone_age_months: number | null
  gap_months: number | null
  flag_status: FlagStatus | null
  gap_direction: GapDirection | null
  decision: Decision | null
  xray_date: string
}

export interface CaseListResponse {
  cases: CaseListItem[]
  page: number
  total_pages: number
}

export interface UploadResponse {
  quality_ok: boolean
  issues: string[]
  image_id: string | null
}

export interface PredictResponse {
  bone_age_months: number
  uncertainty_months: number
  heatmap_url: string
  image_url: string
  heatmap_layer_url: string
  prediction_source: PredictionSource
}

export interface AgentReviewResponse {
  chronological_age_months: number
  gap_direction: GapDirection
  gap_magnitude_months: number
  flag_status: FlagStatus
  flag_reason: string | null
  doctor_note: string | null
  doctor_note_source: NoteSource | null
}

export interface DecisionRequest {
  decision: Decision
  manual_bone_age_months?: number | null
  notes?: string | null
}

export interface DecisionResponse {
  ok: boolean
  decided_at: string
  decided_by: number
}

export interface FollowUpRequest {
  follow_up_date: string
}

export interface CaseDetail {
  id: number
  case_code: string
  patient: PatientOut
  xray_date: string
  height_cm: number | null
  weight_kg: number | null
  referral_reason: string | null
  is_demo: boolean

  quality_ok: boolean | null
  quality_issues: string[] | null

  bone_age_months: number | null
  uncertainty_months: number | null
  heatmap_url: string | null
  image_url: string | null
  heatmap_layer_url: string | null
  prediction_source: PredictionSource | null

  chronological_age_months: number | null
  gap_months: number | null
  gap_direction: GapDirection | null
  flag_status: FlagStatus | null
  flag_reason: string | null
  doctor_note: string | null
  doctor_note_source: NoteSource | null

  decision: Decision | null
  manual_bone_age_months: number | null
  decision_notes: string | null
  decided_by_user_id: number | null
  decided_at: string | null

  follow_up_date: string | null
  prior_cases: CaseListItem[]
}

export interface SettingsOut {
  rule_type: RuleType
  threshold_sd: number
  threshold_months: number
  reference_table_name: string | null
  flag_advanced: boolean
  flag_uncertain_enabled: boolean
  uncertainty_threshold_months: number
  auto_clear_enabled: boolean
  write_note_enabled: boolean
  retention_days: number
  theme: string
  age_unit: string
}

export type SettingsUpdate = Partial<SettingsOut>

export interface ModelPerformanceResponse {
  mae_overall_months: number | string
  mae_by_sex: Record<string, number | string>
  mae_by_age_band: Record<string, number | string> | string
  pct_within_12_months: number | string
  model_card: Record<string, unknown>
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[]
}
