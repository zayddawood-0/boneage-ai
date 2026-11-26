import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as api from '../api/client'
import type { CaseDetail, Decision } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { Card } from '../components/Card'
import { PrimaryButton, SecondaryButton } from '../components/Buttons'
import { HeatmapViewer } from '../components/HeatmapViewer'
import { PageHeader } from '../components/PageHeader'
import { StatusChip } from '../components/StatusChip'
import { ErrorState, LoadingState } from '../components/StateViews'
import { formatAgeMonths, formatDateDisplay, formatGapMonths, parseAgeInputToMonths } from '../lib/age'
import { plotScans } from '../lib/scanChart'
import { useAsync } from '../lib/useAsync'

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

const measurementRowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  padding: '10px 0',
  borderBottom: '1px solid var(--row)',
  fontSize: 14,
}

function flagHeadlineChip(flagStatus: string | null, gapDirection: string | null) {
  if (!flagStatus) return { variant: 'waiting' as const, label: 'Pending analysis' }
  if (flagStatus === 'flagged' && gapDirection === 'delayed') {
    return { variant: 'flag' as const, label: 'Flagged · delayed bone age' }
  }
  if (flagStatus === 'flagged' && gapDirection === 'advanced') {
    return { variant: 'flag' as const, label: 'Flagged · advanced bone age' }
  }
  if (flagStatus === 'needs_review') return { variant: 'flag' as const, label: 'Uncertain · needs review' }
  return { variant: 'ok' as const, label: 'Normal' }
}

export function CaseReportPage() {
  const { id } = useParams<{ id: string }>()
  const caseId = Number(id)
  const { user } = useAuth()
  const canDecide = user?.role === 'doctor'

  const { data: caseDetail, loading, error, reload } = useAsync(() => api.getCase(caseId), [caseId])

  const [decision, setDecision] = useState<Decision>('confirm_flag')
  const [manualReading, setManualReading] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [followUpDate, setFollowUpDate] = useState('')
  const [schedulingFollowUp, setSchedulingFollowUp] = useState(false)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (!caseDetail) return
    if (caseDetail.decision) setDecision(caseDetail.decision)
    setManualReading(
      caseDetail.manual_bone_age_months != null ? formatAgeMonths(caseDetail.manual_bone_age_months) : '',
    )
    setNotes(caseDetail.decision_notes ?? '')
    setFollowUpDate(caseDetail.follow_up_date ?? '')
  }, [caseDetail])

  async function handleSaveDecision() {
    setSaving(true)
    setSaveError(null)
    try {
      await api.recordDecision(caseId, {
        decision,
        manual_bone_age_months: manualReading.trim() ? parseAgeInputToMonths(manualReading) : null,
        notes: notes.trim() || null,
      })
      reload()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Could not save the decision.')
    } finally {
      setSaving(false)
    }
  }

  async function handleScheduleFollowUp() {
    if (!followUpDate) return
    setSchedulingFollowUp(true)
    try {
      await api.scheduleFollowUp(caseId, { follow_up_date: followUpDate })
      reload()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Could not schedule the follow-up.')
    } finally {
      setSchedulingFollowUp(false)
    }
  }

  async function handleExportPdf() {
    setExporting(true)
    try {
      const blobUrl = await api.fetchAuthedBlobUrl(`/cases/${caseId}/report.pdf`)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `${caseDetail?.case_code ?? caseId}_report.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Could not export the PDF.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <PageHeader title="Case report" description="Model result, agent reasoning and the doctor's decision for one X-ray" />
      <Link to="/queue" style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent-text)', textDecoration: 'none' }}>
        ← Back to review queue
      </Link>

      {loading && <LoadingState label="Loading case…" />}
      {!loading && error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && caseDetail && (
        <>
          <Card style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: '50%',
                  background: 'var(--avatar)',
                  color: 'var(--accent-text)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                }}
              >
                {caseDetail.patient.name_or_id.charAt(0).toUpperCase()}
              </div>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {caseDetail.patient.name_or_id} ·{' '}
                  <span className="font-mono-ibm">{caseDetail.case_code}</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                  {caseDetail.patient.sex === 'male' ? 'Male' : 'Female'} · DOB{' '}
                  {formatDateDisplay(caseDetail.patient.date_of_birth)} · X-ray{' '}
                  {formatDateDisplay(caseDetail.xray_date)} · Referred by [Doctor name]
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              {(() => {
                const chip = flagHeadlineChip(caseDetail.flag_status, caseDetail.gap_direction)
                return (
                  <StatusChip variant={chip.variant} size="md">
                    {chip.label}
                  </StatusChip>
                )
              })()}
              {caseDetail.prediction_source === 'mock' && (
                <StatusChip variant="demo">Demo model</StatusChip>
              )}
              {canDecide && (
                <SecondaryButton onClick={handleExportPdf} disabled={exporting}>
                  {exporting ? 'Exporting…' : 'Export report (PDF)'}
                </SecondaryButton>
              )}
            </div>
          </Card>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <HeatmapViewer
                heading={<h2 style={{ margin: 0, fontSize: 18 }}>X-ray and attention heatmap</h2>}
                imageUrl={caseDetail.image_url}
                heatmapLayerUrl={caseDetail.heatmap_layer_url}
                heightPx={560}
              />
            </Card>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <Card>
                <h2 style={{ margin: '0 0 8px', fontSize: 18 }}>Measurements</h2>
                <div style={measurementRowStyle}>
                  <span style={{ color: 'var(--muted)' }}>Predicted bone age</span>
                  <span className="font-mono-ibm" style={{ fontWeight: 600, color: 'var(--accent-text)' }}>
                    {formatAgeMonths(caseDetail.bone_age_months)}
                  </span>
                </div>
                <div style={measurementRowStyle}>
                  <span style={{ color: 'var(--muted)' }}>Chronological age</span>
                  <span className="font-mono-ibm" style={{ fontWeight: 600 }}>
                    {formatAgeMonths(caseDetail.chronological_age_months)}
                  </span>
                </div>
                <div style={measurementRowStyle}>
                  <span style={{ color: 'var(--muted)' }}>Gap (bone − chronological)</span>
                  <span className="font-mono-ibm" style={{ fontWeight: 600, color: 'var(--flag)' }}>
                    {formatGapMonths(caseDetail.gap_months)}
                  </span>
                </div>
                <div style={measurementRowStyle}>
                  <span style={{ color: 'var(--muted)' }}>Gap in SD for age and sex</span>
                  <span className="font-mono-ibm" style={{ fontWeight: 600 }}>
                    [__] SD
                  </span>
                </div>
                <div style={measurementRowStyle}>
                  <span style={{ color: 'var(--muted)' }}>Model uncertainty</span>
                  <span className="font-mono-ibm" style={{ fontWeight: 600 }}>
                    ±{formatAgeMonths(caseDetail.uncertainty_months)}
                  </span>
                </div>
                <div style={{ ...measurementRowStyle, borderBottom: 0 }}>
                  <span style={{ color: 'var(--muted)' }}>Model version</span>
                  <span className="font-mono-ibm" style={{ fontWeight: 600 }}>
                    [v_._]
                  </span>
                </div>
              </Card>
              <AgentReasoningCard caseDetail={caseDetail} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
            <PreviousScansCard caseDetail={caseDetail} />
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <h2 style={{ margin: 0, fontSize: 18 }}>Doctor&apos;s decision</h2>
              {!canDecide && (
                <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
                  Read-only for your role — decisions are recorded by a doctor.
                </p>
              )}
              <fieldset disabled={!canDecide} style={{ border: 0, padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Assessment</legend>
                <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 14 }}>
                  <input
                    type="radio"
                    name="dec"
                    checked={decision === 'confirm_flag'}
                    onChange={() => setDecision('confirm_flag')}
                    style={{ width: 18, height: 18 }}
                  />
                  Confirm flag: refer for further evaluation
                </label>
                <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 14 }}>
                  <input
                    type="radio"
                    name="dec"
                    checked={decision === 'within_expected_range'}
                    onChange={() => setDecision('within_expected_range')}
                    style={{ width: 18, height: 18 }}
                  />
                  Within expected range for this child
                </label>
                <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 14 }}>
                  <input
                    type="radio"
                    name="dec"
                    checked={decision === 'model_looks_wrong'}
                    onChange={() => setDecision('model_looks_wrong')}
                    style={{ width: 18, height: 18 }}
                  />
                  Model estimate looks wrong: re-read manually
                </label>
              </fieldset>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label htmlFor="mba" style={{ fontSize: 13, fontWeight: 600 }}>
                  Your bone age reading (optional)
                </label>
                <input
                  id="mba"
                  type="text"
                  placeholder="e.g. 9y 0m"
                  value={manualReading}
                  onChange={(event) => setManualReading(event.target.value)}
                  disabled={!canDecide}
                  style={textInputStyle}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label htmlFor="dn" style={{ fontSize: 13, fontWeight: 600 }}>
                  Notes
                </label>
                <textarea
                  id="dn"
                  rows={3}
                  placeholder="Next steps, tests ordered, follow-up date…"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  disabled={!canDecide}
                  style={{ ...textInputStyle, height: 'auto', padding: 10, resize: 'vertical' }}
                />
              </div>
              {saveError && (
                <p role="alert" style={{ margin: 0, fontSize: 13, color: 'var(--flag-text)' }}>
                  {saveError}
                </p>
              )}
              {canDecide && (
                <>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                    <PrimaryButton onClick={handleSaveDecision} disabled={saving}>
                      {saving ? 'Saving…' : 'Save decision'}
                    </PrimaryButton>
                    <input
                      type="date"
                      aria-label="Follow-up date"
                      value={followUpDate}
                      onChange={(event) => setFollowUpDate(event.target.value)}
                      style={{ ...textInputStyle, width: 160 }}
                    />
                    <SecondaryButton onClick={handleScheduleFollowUp} disabled={!followUpDate || schedulingFollowUp}>
                      {schedulingFollowUp ? 'Scheduling…' : 'Schedule follow-up scan'}
                    </SecondaryButton>
                  </div>
                  {caseDetail.decided_at && (
                    <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                      Last saved {new Date(caseDetail.decided_at).toLocaleString()}
                    </p>
                  )}
                  {caseDetail.follow_up_date && (
                    <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                      Follow-up scheduled for {formatDateDisplay(caseDetail.follow_up_date)}
                    </p>
                  )}
                </>
              )}
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                Decision support only. The final assessment is made by the clinician.
              </p>
            </Card>
          </div>
        </>
      )}
    </>
  )
}

function AgentReasoningCard({ caseDetail }: { caseDetail: CaseDetail }) {
  const sexLabel = caseDetail.patient.sex === 'male' ? 'male' : 'female'
  const ageYears = caseDetail.chronological_age_months != null ? Math.round(caseDetail.chronological_age_months / 12) : null
  const childLabel = ageYears != null ? `${ageYears}-year-old ${caseDetail.patient.sex === 'male' ? 'boy' : 'girl'}` : 'child'

  const hasPrediction = caseDetail.bone_age_months != null
  const hasReview = caseDetail.flag_status != null

  const stepFour = (() => {
    if (!hasReview) return null
    if (caseDetail.flag_status === 'flagged') {
      return { title: 'Flagged for doctor review', color: 'var(--flag)', body: caseDetail.doctor_note }
    }
    if (caseDetail.flag_status === 'needs_review') {
      return { title: 'Flagged as uncertain', color: 'var(--flag)', body: caseDetail.doctor_note }
    }
    return { title: 'Within expected range', color: 'var(--ok-text)', body: caseDetail.doctor_note }
  })()

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>Agent reasoning</h2>
      <ol
        style={{
          margin: 0,
          padding: '0 0 0 4px',
          listStyle: 'none',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          fontSize: 14,
          borderLeft: '2px solid var(--border)',
        }}
      >
        <li style={{ paddingLeft: 14 }}>
          <div style={{ fontWeight: 600 }}>Image checked</div>
          <div style={{ color: 'var(--muted)' }}>
            {caseDetail.quality_ok ? 'Left hand in frame, orientation corrected.' : 'Quality check pending or failed.'}
          </div>
        </li>
        <li style={{ paddingLeft: 14 }}>
          <div style={{ fontWeight: 600 }}>Bone age estimated</div>
          <div style={{ color: 'var(--muted)' }}>
            {hasPrediction
              ? `${formatAgeMonths(caseDetail.bone_age_months)} from the X-ray with sex = ${sexLabel}.`
              : 'Waiting for a prediction.'}
          </div>
        </li>
        <li style={{ paddingLeft: 14 }}>
          <div style={{ fontWeight: 600 }}>Compared with normal range</div>
          <div style={{ color: 'var(--muted)' }}>
            {hasReview
              ? `Gap of ${formatGapMonths(caseDetail.gap_months)} is ${
                  caseDetail.gap_direction === 'within_range' ? 'within' : 'outside'
                } the configured range for a ${childLabel}.`
              : 'Waiting for the growth review agent.'}
          </div>
        </li>
        {stepFour && (
          <li style={{ paddingLeft: 14 }}>
            <div style={{ fontWeight: 600, color: stepFour.color }}>{stepFour.title}</div>
            <div style={{ color: 'var(--muted)' }}>{stepFour.body}</div>
          </li>
        )}
      </ol>
    </Card>
  )
}

function PreviousScansCard({ caseDetail }: { caseDetail: CaseDetail }) {
  const scans = [...caseDetail.prior_cases, {
    id: caseDetail.id,
    case_code: caseDetail.case_code,
    xray_date: caseDetail.xray_date,
    chronological_age_months: caseDetail.chronological_age_months,
    bone_age_months: caseDetail.bone_age_months,
  }]
    .filter((c) => c.chronological_age_months != null && c.bone_age_months != null)
    .sort((a, b) => a.xray_date.localeCompare(b.xray_date))

  if (scans.length < 2) {
    return (
      <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Previous scans</h2>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
          Only one scan on record for this patient so far — a trend will appear once there&apos;s a second.
        </p>
      </Card>
    )
  }

  const plotted = plotScans(
    scans.map((s) => ({
      dateLabel: formatDateDisplay(s.xray_date),
      chronMonths: s.chronological_age_months as number,
      boneMonths: s.bone_age_months as number,
    })),
  )
  const flagColor = caseDetail.flag_status === 'flagged' || caseDetail.flag_status === 'needs_review' ? 'var(--flag)' : 'var(--ok-text)'
  const chronPoints = plotted.map((p) => `${p.x},${p.chronY}`).join(' ')
  const bonePoints = plotted.map((p) => `${p.x},${p.boneY}`).join(' ')
  const last = plotted[plotted.length - 1]

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>Previous scans</h2>
      <svg
        viewBox="0 0 460 220"
        role="img"
        aria-label={`Bone age and chronological age across ${plotted.length} scans for this patient.`}
        style={{ width: '100%', height: 'auto' }}
      >
        <line x1={40} y1={190} x2={450} y2={190} stroke="#9AA6B2" />
        <line x1={40} y1={190} x2={40} y2={10} stroke="#9AA6B2" />
        <polyline points={chronPoints} fill="none" stroke="#9AA6B2" strokeWidth={2} strokeDasharray="5 4" />
        <polyline points={bonePoints} fill="none" style={{ stroke: flagColor }} strokeWidth={3} />
        {plotted.map((p) => (
          <circle key={p.dateLabel} cx={p.x} cy={p.boneY} r={5} style={{ fill: flagColor }} />
        ))}
        {plotted.map((p) => (
          <text key={`${p.dateLabel}-label`} x={p.x} y={208} fontSize={11} textAnchor="middle" style={{ fill: 'var(--muted)' }}>
            {p.dateLabel}
          </text>
        ))}
        <text x={last.x - 42} y={last.chronY - 8} fontSize={11} style={{ fill: 'var(--muted)' }}>
          Real age
        </text>
        <text x={last.x - 42} y={last.boneY + 16} fontSize={11} style={{ fill: 'var(--flag-text)' }}>
          Bone age
        </text>
      </svg>
      <div style={{ fontSize: 13, color: 'var(--muted)' }}>
        {plotted.length} scans on record for this patient.
      </div>
    </Card>
  )
}
