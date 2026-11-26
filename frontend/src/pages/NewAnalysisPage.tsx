import { useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import * as api from '../api/client'
import { ApiError } from '../api/client'
import type { Sex } from '../api/types'
import { Card } from '../components/Card'
import { PrimaryButton, SecondaryButton } from '../components/Buttons'
import { PageHeader } from '../components/PageHeader'
import { SexPicker } from '../components/SexPicker'
import { StatusChip } from '../components/StatusChip'
import { UploadIcon } from '../components/icons'
import { computeChronologicalAgeMonths, formatAgeMonths } from '../lib/age'

interface PrefillState {
  sex?: Sex
  dateOfBirth?: string
  xrayDate?: string
  file?: File
}

const textInputStyle: React.CSSProperties = {
  height: 44,
  border: '1px solid var(--input)',
  borderRadius: 8,
  padding: '0 12px',
  fontFamily: 'inherit',
  fontSize: 14,
  background: 'var(--surface)',
  color: 'var(--ink)',
  boxSizing: 'border-box',
  width: '100%',
}

const QUALITY_CHECKS: { code: string; label: string }[] = [
  { code: 'no_hand_detected', label: 'Hand detected and fully in frame' },
  { code: 'unexpected_orientation', label: 'Orientation corrected (fingers up)' },
  { code: 'low_resolution', label: 'Resolution high enough for the model' },
  { code: 'burned_in_details_detected', label: 'Patient details removed from the image' },
]

const stepDoneStyle: React.CSSProperties = {
  width: 28,
  height: 28,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 13,
  fontWeight: 700,
  background: '#24614B',
  color: '#fff',
}
const stepUpcomingStyle: React.CSSProperties = {
  ...stepDoneStyle,
  background: 'var(--seg)',
  color: 'var(--text2)',
}

export function NewAnalysisPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const prefill = (location.state as PrefillState | null) ?? null

  const [nameOrId, setNameOrId] = useState('')
  const [referringDoctor, setReferringDoctor] = useState('')
  const [sex, setSex] = useState<Sex | null>(prefill?.sex ?? null)
  const [dob, setDob] = useState(prefill?.dateOfBirth ?? '')
  const [xrayDate, setXrayDate] = useState(prefill?.xrayDate ?? '')
  const [heightCm, setHeightCm] = useState('')
  const [weightKg, setWeightKg] = useState('')
  const [reason, setReason] = useState('')
  const [file, setFile] = useState<File | null>(prefill?.file ?? null)

  const [qualityIssues, setQualityIssues] = useState<string[] | null>(null)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [draftNote, setDraftNote] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const chronologicalAgeMonths = computeChronologicalAgeMonths(dob, xrayDate)
  const canRun = nameOrId.trim() && sex && dob && xrayDate && file

  async function handleRun() {
    if (!sex || !file) return
    setRunning(true)
    setRunError(null)
    setQualityIssues(null)
    try {
      const patient = await api.createPatient({ name_or_id: nameOrId.trim(), sex, date_of_birth: dob })
      const created = await api.createCase({
        patient_id: patient.id,
        xray_date: xrayDate,
        height_cm: heightCm ? Number(heightCm) : null,
        weight_kg: weightKg ? Number(weightKg) : null,
        referral_reason: reason.trim() || null,
      })

      const uploadResult = await api.uploadXray(created.id, file)
      setQualityIssues(uploadResult.issues)
      if (!uploadResult.quality_ok) {
        setRunError('The image did not pass quality checks — see the list below. Upload a different X-ray to continue.')
        return
      }

      await api.predictCase(created.id)
      await api.agentReviewCase(created.id)
      navigate(`/cases/${created.id}`)
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : 'Something went wrong running the analysis.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <PageHeader title="New analysis" description="Add patient details and a hand X-ray to estimate bone age" />

      <Card style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'center', padding: '16px 22px' }}>
        <StepIndicator number={1} label="Patient details" done />
        <div style={{ flex: '0 0 32px', height: 1, background: 'var(--line)' }} />
        <StepIndicator number={2} label="Upload X-ray" done />
        <div style={{ flex: '0 0 32px', height: 1, background: 'var(--line)' }} />
        <StepIndicator number={3} label="Review and run" />
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 24 }}>
        <Card style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>1 · Patient details</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 14 }}>
            <Field label="Patient name or ID" htmlFor="pname">
              <input
                id="pname"
                type="text"
                placeholder="e.g. MRN 000000"
                value={nameOrId}
                onChange={(event) => setNameOrId(event.target.value)}
                style={textInputStyle}
              />
            </Field>
            <Field label="Referring doctor" htmlFor="ref">
              <input
                id="ref"
                type="text"
                placeholder="[Doctor name]"
                value={referringDoctor}
                onChange={(event) => setReferringDoctor(event.target.value)}
                style={textInputStyle}
              />
            </Field>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Sex (model input)</span>
            <SexPicker value={sex} onChange={setSex} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 14 }}>
            <Field label="Date of birth" htmlFor="dob">
              <input id="dob" type="date" value={dob} onChange={(event) => setDob(event.target.value)} style={textInputStyle} />
            </Field>
            <Field label="X-ray date" htmlFor="xd">
              <input
                id="xd"
                type="date"
                value={xrayDate}
                onChange={(event) => setXrayDate(event.target.value)}
                style={textInputStyle}
              />
            </Field>
          </div>
          <div
            style={{
              background: 'var(--soft)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              padding: '12px 14px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ fontSize: 13, color: 'var(--muted)' }}>Chronological age at X-ray</span>
            <span className="font-mono-ibm" style={{ fontSize: 18, fontWeight: 600 }}>
              {chronologicalAgeMonths != null ? formatAgeMonths(chronologicalAgeMonths) : '—'}
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 14 }}>
            <Field label="Height (cm, optional)" htmlFor="ht">
              <input id="ht" type="number" value={heightCm} onChange={(event) => setHeightCm(event.target.value)} style={textInputStyle} />
            </Field>
            <Field label="Weight (kg, optional)" htmlFor="wt">
              <input id="wt" type="number" value={weightKg} onChange={(event) => setWeightKg(event.target.value)} style={textInputStyle} />
            </Field>
          </div>
          <Field label="Reason for referral (optional)" htmlFor="reason">
            <textarea
              id="reason"
              rows={3}
              placeholder="e.g. short stature, early puberty signs"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              style={{ ...textInputStyle, height: 'auto', padding: 10, resize: 'vertical' }}
            />
          </Field>
        </Card>

        <Card style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>2 · Upload hand X-ray</h2>
          <label
            htmlFor="file"
            style={{
              border: '2px dashed var(--dash)',
              borderRadius: 12,
              background: 'var(--soft)',
              height: 360,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              textAlign: 'center',
              cursor: 'pointer',
              padding: 16,
              boxSizing: 'border-box',
            }}
          >
            <UploadIcon size={44} style={{ color: 'var(--accent-text)' }} />
            <span style={{ fontWeight: 600, fontSize: 16 }}>
              {file ? file.name : 'Drop the X-ray here, or browse'}
            </span>
            <span style={{ fontSize: 13, color: 'var(--muted)' }}>Left hand, palm down · PNG, JPG or DICOM</span>
            <input
              ref={fileInputRef}
              id="file"
              type="file"
              accept=".png,.jpg,.jpeg,.dcm"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null)
                setQualityIssues(null)
                setRunError(null)
              }}
              style={{ position: 'absolute', left: -9999 }}
            />
          </label>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Image quality checks</div>
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {QUALITY_CHECKS.map((check) => {
                const status = qualityIssues === null ? 'waiting' : qualityIssues.includes(check.code) ? 'fail' : 'pass'
                return (
                  <li key={check.code} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 14 }}>
                    <StatusChip variant={status === 'fail' ? 'flag' : status === 'pass' ? 'ok' : 'waiting'}>
                      {status === 'fail' ? 'Fail' : status === 'pass' ? 'Pass' : 'Waiting'}
                    </StatusChip>
                    <span>{check.label}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </Card>
      </div>

      <Card style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>3 · Review and run</div>
          <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }}>
            The model returns bone age in a few seconds. The agent then compares it with chronological age.
          </div>
          {runError && (
            <p role="alert" style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--flag-text)' }}>
              {runError}
            </p>
          )}
          {draftNote && (
            <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--muted)' }}>{draftNote}</p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <SecondaryButton onClick={() => setDraftNote('Drafts aren’t saved in this build yet.')}>
            Save as draft
          </SecondaryButton>
          <PrimaryButton onClick={handleRun} disabled={!canRun || running}>
            {running ? 'Running…' : 'Run bone age analysis'}
          </PrimaryButton>
        </div>
      </Card>
    </>
  )
}

function StepIndicator({ number, label, done = false }: { number: number; label: string; done?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, fontWeight: done ? 600 : 500, color: done ? 'var(--ink)' : 'var(--muted)' }}>
      <span style={done ? stepDoneStyle : stepUpcomingStyle}>{number}</span>
      {label}
    </div>
  )
}

function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label htmlFor={htmlFor} style={{ fontSize: 13, fontWeight: 600 }}>
        {label}
      </label>
      {children}
    </div>
  )
}
