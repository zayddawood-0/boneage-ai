// Typed client for the BoneAge AI backend (backend/app/, see docs/api.md).
// In dev, requests go to /api and Vite proxies them to the backend
// (vite.config.ts) — no CORS setup needed locally. For a real deployment
// with the frontend and backend on separate origins (docs/architecture.md:
// Vercel + Render), set VITE_API_BASE_URL and add CORS on the backend.
import type {
  AgentReviewResponse,
  CaseCreate,
  CaseCreateResponse,
  CaseDetail,
  CaseListResponse,
  DecisionRequest,
  DecisionResponse,
  FollowUpRequest,
  ModelPerformanceResponse,
  OkResponse,
  PatientCreate,
  PatientDetail,
  PatientOut,
  PredictResponse,
  SettingsOut,
  SettingsUpdate,
  TokenResponse,
  UploadResponse,
} from './types'
import { clearSession, loadSession } from './token'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

/** Called by the app shell when a 401 comes back, so the session is cleared
 * and the user is sent back to /login — never silently kept "signed in". */
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg).join('; ')
    }
  } catch {
    // body wasn't JSON — fall through to the generic message
  }
  return `Request failed (${response.status})`
}

interface RequestOptions {
  method?: string
  body?: unknown
  isFormData?: boolean
  query?: Record<string, string | number | undefined>
}

async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = loadSession()
  const headers: Record<string, string> = {}
  if (session) headers.Authorization = `Bearer ${session.token}`

  let url = `${BASE_URL}${path}`
  if (options.query) {
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined) params.set(key, String(value))
    }
    const qs = params.toString()
    if (qs) url += `?${qs}`
  }

  let body: BodyInit | undefined
  if (options.isFormData) {
    body = options.body as FormData
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  const response = await fetch(url, { method: options.method ?? 'GET', headers, body })

  if (response.status === 401) {
    clearSession()
    onUnauthorized?.()
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }
  return undefined as T
}

// ---- Auth ----
export function login(email: string, password: string): Promise<TokenResponse> {
  return apiFetch('/auth/login', { method: 'POST', body: { email, password } })
}

// ---- Patients ----
export function listPatients(): Promise<PatientOut[]> {
  return apiFetch('/patients')
}

export function createPatient(payload: PatientCreate): Promise<PatientOut> {
  return apiFetch('/patients', { method: 'POST', body: payload })
}

export function getPatient(id: number): Promise<PatientDetail> {
  return apiFetch(`/patients/${id}`)
}

// ---- Cases ----
export function createCase(payload: CaseCreate): Promise<CaseCreateResponse> {
  return apiFetch('/cases', { method: 'POST', body: payload })
}

export interface ListCasesParams {
  status?: string
  sex?: string
  sort?: string
  page?: number
  page_size?: number
  [key: string]: string | number | undefined
}

export function listCases(params: ListCasesParams = {}): Promise<CaseListResponse> {
  return apiFetch('/cases', { query: params })
}

export function getCase(id: number): Promise<CaseDetail> {
  return apiFetch(`/cases/${id}`)
}

export function uploadXray(caseId: number, file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch(`/cases/${caseId}/upload`, { method: 'POST', body: form, isFormData: true })
}

export function predictCase(caseId: number): Promise<PredictResponse> {
  return apiFetch(`/cases/${caseId}/predict`, { method: 'POST' })
}

export function agentReviewCase(caseId: number): Promise<AgentReviewResponse> {
  return apiFetch(`/cases/${caseId}/agent-review`, { method: 'POST' })
}

export function recordDecision(caseId: number, payload: DecisionRequest): Promise<DecisionResponse> {
  return apiFetch(`/cases/${caseId}/decision`, { method: 'POST', body: payload })
}

export function scheduleFollowUp(caseId: number, payload: FollowUpRequest): Promise<OkResponse> {
  return apiFetch(`/cases/${caseId}/follow-up`, { method: 'POST', body: payload })
}

/** Fetches an authenticated binary resource (heatmap PNG, PDF) as a blob URL —
 * the backend requires a Bearer token, so these can't be used as plain <img src>. */
export async function fetchAuthedBlobUrl(path: string): Promise<string> {
  const session = loadSession()
  const headers: Record<string, string> = {}
  if (session) headers.Authorization = `Bearer ${session.token}`
  const response = await fetch(`${BASE_URL}${path}`, { headers })
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

// ---- Settings ----
export function getSettings(): Promise<SettingsOut> {
  return apiFetch('/settings')
}

export function updateSettings(payload: SettingsUpdate): Promise<OkResponse> {
  return apiFetch('/settings', { method: 'PUT', body: payload })
}

// ---- Model performance ----
export function getModelPerformance(): Promise<ModelPerformanceResponse> {
  return apiFetch('/model/performance')
}
