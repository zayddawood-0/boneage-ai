import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { AuthProvider } from '../auth/AuthContext'
import { ThemeProvider } from '../theme/ThemeContext'
import type { CaseDetail, CaseListResponse, ModelPerformanceResponse } from '../api/types'

const NEW_CASE_ID = 42

const caseDetail: CaseDetail = {
  id: NEW_CASE_ID,
  case_code: 'BA-1099',
  patient: { id: 7, patient_code: 'P-0099', name_or_id: 'Test Patient', sex: 'male', date_of_birth: '2014-01-15' },
  xray_date: '2026-11-26',
  height_cm: null,
  weight_kg: null,
  referral_reason: null,
  is_demo: false,
  quality_ok: true,
  quality_issues: [],
  bone_age_months: 110,
  uncertainty_months: 6,
  heatmap_url: '/cases/42/heatmap',
  image_url: null,
  heatmap_layer_url: null,
  prediction_source: 'mock',
  chronological_age_months: 120,
  gap_months: -10,
  gap_direction: 'delayed',
  flag_status: 'flagged',
  flag_reason: 'Bone age is delayed beyond the normal range.',
  doctor_note: 'Predicted bone age is delayed relative to chronological age.',
  doctor_note_source: 'template',
  decision: null,
  manual_bone_age_months: null,
  decision_notes: null,
  decided_by_user_id: null,
  decided_at: null,
  follow_up_date: null,
  prior_cases: [],
}

const emptyCaseList: CaseListResponse = { cases: [], page: 1, total_pages: 1 }
const modelPerformance: ModelPerformanceResponse = {
  mae_overall_months: '[TBD]',
  mae_by_sex: {},
  mae_by_age_band: '[TBD]',
  pct_within_12_months: '[TBD]',
  model_card: {},
}

const api = vi.hoisted(() => ({
  login: vi.fn(),
  listCases: vi.fn(),
  getModelPerformance: vi.fn(),
  getCase: vi.fn(),
  createPatient: vi.fn(),
  createCase: vi.fn(),
  uploadXray: vi.fn(),
  predictCase: vi.fn(),
  agentReviewCase: vi.fn(),
  recordDecision: vi.fn(),
  scheduleFollowUp: vi.fn(),
  fetchAuthedBlobUrl: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
}))

vi.mock('../api/client', () => api)

function renderApp() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  vi.clearAllMocks()

  api.login.mockResolvedValue({ token: 'test-token', role: 'doctor' })
  api.listCases.mockResolvedValue(emptyCaseList)
  api.getModelPerformance.mockResolvedValue(modelPerformance)
  api.getCase.mockResolvedValue(caseDetail)
  api.createPatient.mockResolvedValue({
    id: 7,
    patient_code: 'P-0099',
    name_or_id: 'Test Patient',
    sex: 'male',
    date_of_birth: '2014-01-15',
  })
  api.createCase.mockResolvedValue({ id: NEW_CASE_ID, case_code: 'BA-1099', chronological_age_months: 120 })
  api.uploadXray.mockResolvedValue({ quality_ok: true, issues: [], image_id: 'img-1' })
  api.predictCase.mockResolvedValue({
    bone_age_months: 110,
    uncertainty_months: 6,
    heatmap_url: '/cases/42/heatmap',
    image_url: '/cases/42/image',
    heatmap_layer_url: '/cases/42/heatmap-layer',
    prediction_source: 'mock',
  })
  api.agentReviewCase.mockResolvedValue({
    chronological_age_months: 120,
    gap_direction: 'delayed',
    gap_magnitude_months: 10,
    flag_status: 'flagged',
    flag_reason: 'test',
    doctor_note: 'test note',
    doctor_note_source: 'template',
  })
})

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

describe('login -> new analysis -> case report', () => {
  it('signs in, runs a new analysis, and lands on the resulting case report', async () => {
    const user = userEvent.setup()
    renderApp()

    await user.type(screen.getByLabelText('Email'), 'doctor@boneage.ai')
    await user.type(screen.getByLabelText('Password'), 'demo-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(api.login).toHaveBeenCalledWith('doctor@boneage.ai', 'demo-password')

    await user.click(screen.getByRole('link', { name: 'New analysis' }))
    expect(await screen.findByRole('heading', { name: 'New analysis' })).toBeInTheDocument()

    await user.type(screen.getByLabelText('Patient name or ID'), 'Test Patient')
    await user.click(screen.getByRole('button', { name: 'Male' }))
    await user.type(screen.getByLabelText('Date of birth'), '2014-01-15')
    await user.type(screen.getByLabelText('X-ray date'), '2026-11-26')

    const file = new File(['fake-xray-bytes'], 'xray.png', { type: 'image/png' })
    const fileInput = document.getElementById('file') as HTMLInputElement
    await user.upload(fileInput, file)

    const runButton = screen.getByRole('button', { name: 'Run bone age analysis' })
    expect(runButton).toBeEnabled()
    await user.click(runButton)

    expect(await screen.findByRole('heading', { name: 'Case report' })).toBeInTheDocument()

    expect(api.createPatient).toHaveBeenCalledWith({ name_or_id: 'Test Patient', sex: 'male', date_of_birth: '2014-01-15' })
    expect(api.createCase).toHaveBeenCalledWith(
      expect.objectContaining({ patient_id: 7, xray_date: '2026-11-26' }),
    )
    expect(api.uploadXray).toHaveBeenCalledWith(NEW_CASE_ID, file)
    expect(api.predictCase).toHaveBeenCalledWith(NEW_CASE_ID)
    expect(api.agentReviewCase).toHaveBeenCalledWith(NEW_CASE_ID)
    expect(api.getCase).toHaveBeenCalledWith(NEW_CASE_ID)

    expect(await screen.findByText('BA-1099')).toBeInTheDocument()
    expect(screen.getByText('Demo model')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('No X-ray uploaded yet')).toBeInTheDocument())
  })

  it('stops short and shows the quality-check failure instead of navigating when the image fails checks', async () => {
    api.uploadXray.mockResolvedValue({ quality_ok: false, issues: ['low_resolution'], image_id: null })
    const user = userEvent.setup()
    renderApp()

    await user.type(screen.getByLabelText('Email'), 'doctor@boneage.ai')
    await user.type(screen.getByLabelText('Password'), 'demo-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByRole('heading', { name: 'Dashboard' })

    await user.click(screen.getByRole('link', { name: 'New analysis' }))
    await screen.findByRole('heading', { name: 'New analysis' })

    await user.type(screen.getByLabelText('Patient name or ID'), 'Test Patient')
    await user.click(screen.getByRole('button', { name: 'Female' }))
    await user.type(screen.getByLabelText('Date of birth'), '2014-01-15')
    await user.type(screen.getByLabelText('X-ray date'), '2026-11-26')
    const file = new File(['fake-xray-bytes'], 'xray.png', { type: 'image/png' })
    await user.upload(document.getElementById('file') as HTMLInputElement, file)

    await user.click(screen.getByRole('button', { name: 'Run bone age analysis' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/did not pass quality checks/i)
    expect(api.predictCase).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'New analysis' })).toBeInTheDocument()
  })
})
