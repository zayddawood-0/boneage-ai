import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as api from '../api/client'
import type { CaseDetail, CaseListItem, Decision, Sex } from '../api/types'
import { Card } from '../components/Card'
import { PrimaryButton, SecondaryButton } from '../components/Buttons'
import { HeatmapViewer } from '../components/HeatmapViewer'
import { PageHeader } from '../components/PageHeader'
import { SegmentedTabs } from '../components/SegmentedTabs'
import { SexPicker } from '../components/SexPicker'
import { flagChipProps, StatusChip } from '../components/StatusChip'
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews'
import { UploadIcon } from '../components/icons'
import { formatAgeMonths, formatGapMonths } from '../lib/age'
import { useAsync } from '../lib/useAsync'

const textInputStyle: React.CSSProperties = {
  height: 44,
  border: '1px solid var(--input)',
  borderRadius: 8,
  padding: '0 10px',
  fontFamily: 'inherit',
  fontSize: 14,
  width: '100%',
  boxSizing: 'border-box',
}

function isAwaiting(c: CaseListItem): boolean {
  return (c.flag_status === 'flagged' || c.flag_status === 'needs_review') && c.decision === null
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

// x = years mapped to the mock's exact pixel ticks (0/6/12/18y at x=40/184/328/472).
function scatterX(years: number) {
  return 40 + Math.min(Math.max(years, 0), 18) * ((472 - 40) / 18)
}
// y = years mapped to the mock's exact pixel ticks (0/6/12/18y at y=270/190/106/22), inverted.
function scatterY(years: number) {
  return 270 - Math.min(Math.max(years, 0), 18) * ((270 - 22) / 18)
}

export function DashboardPage() {
  const { data: allCases, loading: casesLoading, error: casesError, reload: reloadCases } = useAsync(
    () => api.listCases({ sort: 'date_desc', page_size: 200 }).then((r) => r.cases),
    [],
  )
  const { data: modelPerf } = useAsync(() => api.getModelPerformance(), [])

  const mostRecent = allCases && allCases.length > 0 ? allCases[0] : null
  const { data: mostRecentDetail, reload: reloadMostRecent } = useAsync(
    () => (mostRecent ? api.getCase(mostRecent.id) : Promise.resolve(null)),
    [mostRecent?.id],
  )

  const analysesToday = allCases?.filter((c) => c.xray_date === todayIso()).length ?? 0
  const flaggedCount = allCases?.filter((c) => c.flag_status === 'flagged').length ?? 0
  const awaitingCount = allCases?.filter(isAwaiting).length ?? 0
  const mae = typeof modelPerf?.mae_overall_months === 'number' ? `${modelPerf.mae_overall_months.toFixed(1)} mo` : '[__] mo'

  const [queueTab, setQueueTab] = useState<'all' | 'flagged'>('all')
  const queueRows = (allCases ?? []).filter((c) => queueTab === 'all' || c.flag_status === 'flagged').slice(0, 5)

  function handleDecisionSaved() {
    reloadMostRecent()
    reloadCases()
  }

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Bone age estimation from hand X-rays, with agent flags for clinician review"
        extra={
          <>
            <label htmlFor="search" style={{ position: 'absolute', left: -9999 }}>
              Search cases
            </label>
            <input id="search" type="search" placeholder="Search case ID or patient" style={{ ...textInputStyle, height: 44, width: 260, padding: '0 14px' }} />
          </>
        }
      />

      <section aria-label="Summary" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Analyses today</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6 }}>
            {casesLoading ? '—' : analysesToday}
          </div>
        </Card>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Flagged by agent</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6, color: 'var(--flag)' }}>
            {casesLoading ? '—' : flaggedCount}
          </div>
        </Card>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Awaiting doctor review</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6 }}>
            {casesLoading ? '—' : awaitingCount}
          </div>
        </Card>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Model MAE (validation)</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6 }}>
            {mae}
          </div>
        </Card>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 24 }}>
        <NewAnalysisShortcutCard />
        <ResultCard loading={casesLoading} error={casesError} detail={mostRecentDetail} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 24 }}>
        <AgentPanelCard detail={mostRecentDetail} onSaved={handleDecisionSaved} />
        <ScatterChartCard cases={allCases ?? []} />
      </div>

      <Card style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Review queue</h2>
          <SegmentedTabs
            options={[
              { key: 'all' as const, label: 'All cases' },
              { key: 'flagged' as const, label: 'Flagged only' },
            ]}
            value={queueTab}
            onChange={setQueueTab}
            ariaLabel="Filter cases"
          />
        </div>
        {casesLoading && <LoadingState label="Loading cases…" />}
        {!casesLoading && casesError && <ErrorState message={casesError} onRetry={reloadCases} />}
        {!casesLoading && !casesError && queueRows.length === 0 && (
          <EmptyState title="No cases yet" description="Run a new analysis to see it here." />
        )}
        {!casesLoading && !casesError && queueRows.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', minWidth: 720, borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--muted)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Case</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Sex</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Chronological</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Bone age</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Gap</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Agent result</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>Status</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ position: 'absolute', left: -9999 }}>Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {queueRows.map((row) => {
                  const chip = flagChipProps(row.flag_status, row.gap_direction)
                  const flagged = row.flag_status === 'flagged' || row.flag_status === 'needs_review'
                  return (
                    <tr key={row.id}>
                      <td className="font-mono-ibm" style={{ padding: 12, borderBottom: '1px solid var(--row)', fontWeight: 600 }}>
                        {row.case_code}
                      </td>
                      <td style={{ padding: 12, borderBottom: '1px solid var(--row)' }}>{row.sex === 'male' ? 'M' : 'F'}</td>
                      <td className="font-mono-ibm" style={{ padding: 12, borderBottom: '1px solid var(--row)' }}>
                        {formatAgeMonths(row.chronological_age_months)}
                      </td>
                      <td className="font-mono-ibm" style={{ padding: 12, borderBottom: '1px solid var(--row)' }}>
                        {formatAgeMonths(row.bone_age_months)}
                      </td>
                      <td
                        className="font-mono-ibm"
                        style={{ padding: 12, borderBottom: '1px solid var(--row)', fontWeight: 600, color: flagged ? 'var(--flag)' : 'var(--text2)' }}
                      >
                        {formatGapMonths(row.gap_months)}
                      </td>
                      <td style={{ padding: 12, borderBottom: '1px solid var(--row)' }}>
                        <StatusChip variant={chip.variant}>{chip.label}</StatusChip>
                      </td>
                      <td style={{ padding: 12, borderBottom: '1px solid var(--row)', color: 'var(--text2)' }}>
                        {row.decision ? 'Reviewed' : flagged ? 'Awaiting review' : 'Auto-cleared'}
                      </td>
                      <td style={{ padding: 12, borderBottom: '1px solid var(--row)', textAlign: 'right' }}>
                        <Link to={`/cases/${row.id}`} style={{ fontWeight: 600, fontSize: 14, color: 'var(--accent-text)' }}>
                          Open
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}

// design/Main.html's "New analysis" card duplicates most of the full
// /analysis/new form but has no patient-name field — docs/design.md calls
// it an "entry point into the 3-step flow," so it collects what it visually
// shows and hands off to the full page to complete and submit, rather than
// creating a nameless patient.
function NewAnalysisShortcutCard() {
  const navigate = useNavigate()
  const [sex, setSex] = useState<Sex | null>(null)
  const [dob, setDob] = useState('')
  const [examDate, setExamDate] = useState('')
  const [file, setFile] = useState<File | null>(null)

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>New analysis</h2>
      <label
        htmlFor="xray"
        style={{
          border: '2px dashed var(--dash)',
          borderRadius: 12,
          background: 'var(--soft)',
          padding: '28px 16px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          textAlign: 'center',
          cursor: 'pointer',
        }}
      >
        <UploadIcon size={36} style={{ color: 'var(--accent-text)' }} />
        <span style={{ fontWeight: 600, fontSize: 15 }}>{file ? file.name : 'Upload left-hand X-ray'}</span>
        <span style={{ fontSize: 13, color: 'var(--muted)' }}>PNG, JPG or DICOM</span>
        <input
          id="xray"
          type="file"
          accept=".png,.jpg,.jpeg,.dcm"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          style={{ position: 'absolute', left: -9999 }}
        />
      </label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>Sex (model input)</span>
        <SexPicker value={sex} onChange={setSex} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label htmlFor="dash-dob" style={{ fontSize: 13, fontWeight: 600 }}>
            Date of birth
          </label>
          <input id="dash-dob" type="date" value={dob} onChange={(event) => setDob(event.target.value)} style={textInputStyle} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label htmlFor="dash-exam" style={{ fontSize: 13, fontWeight: 600 }}>
            X-ray date
          </label>
          <input id="dash-exam" type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} style={textInputStyle} />
        </div>
      </div>
      <div style={{ fontSize: 13, color: 'var(--muted)' }}>Chronological age is calculated from these two dates.</div>
      <PrimaryButton
        height={48}
        fontSize={15}
        onClick={() =>
          navigate('/analysis/new', {
            state: { sex: sex ?? undefined, dateOfBirth: dob || undefined, xrayDate: examDate || undefined, file: file ?? undefined },
          })
        }
      >
        Run bone age analysis
      </PrimaryButton>
    </Card>
  )
}

function ResultCard({
  loading,
  error,
  detail,
}: {
  loading: boolean
  error: string | null
  detail: CaseDetail | null | undefined
}) {
  const chip = detail ? flagChipProps(detail.flag_status, detail.gap_direction) : null
  // Illustrative marker position (see delivery notes: the real ±SD/±months
  // threshold bounds used by Settings aren't fetchable by the doctor role,
  // so only the category — delayed/within/advanced — is real).
  const markerLeft = detail?.gap_direction === 'delayed' ? '14%' : detail?.gap_direction === 'advanced' ? '86%' : '50%'

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Result{detail ? ` · Case ${detail.case_code}` : ''}</h2>
        {chip && <StatusChip variant={chip.variant}>{chip.label}</StatusChip>}
        {detail?.prediction_source === 'mock' && <StatusChip variant="demo">Demo model</StatusChip>}
      </div>
      {loading && <LoadingState label="Loading the latest case…" />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && !error && !detail && <EmptyState title="No analyses yet" description="Run one to see the result here." />}
      {!loading && !error && detail && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <HeatmapViewer
            heading={<span style={{ fontSize: 13, fontWeight: 600 }}>X-ray with attention heatmap</span>}
            imageUrl={detail.image_url}
            heatmapLayerUrl={detail.heatmap_layer_url}
            heightPx={400}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
              <div style={{ background: 'var(--soft-blue)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>Predicted bone age</div>
                <div className="font-mono-ibm" style={{ fontSize: 22, fontWeight: 600, color: 'var(--accent-text)' }}>
                  {formatAgeMonths(detail.bone_age_months)}
                </div>
              </div>
              <div style={{ background: 'var(--bg)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>Chronological age</div>
                <div className="font-mono-ibm" style={{ fontSize: 22, fontWeight: 600 }}>
                  {formatAgeMonths(detail.chronological_age_months)}
                </div>
              </div>
            </div>
            <div style={{ background: 'var(--gap-bg)', border: '1px solid var(--gap-border)', borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--gap-label)' }}>Gap (bone − chronological)</div>
              <div className="font-mono-ibm" style={{ fontSize: 22, fontWeight: 600, color: 'var(--flag)' }}>
                {formatGapMonths(detail.gap_months)}
                {detail.gap_direction && detail.gap_direction !== 'within_range' ? ` · ${detail.gap_direction}` : ''}
              </div>
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--muted)' }}>
                <span>Delayed</span>
                <span>Normal (±2 SD)</span>
                <span>Advanced</span>
              </div>
              <div style={{ position: 'relative', height: 12, borderRadius: 6, background: 'var(--track)', marginTop: 6 }}>
                <div style={{ position: 'absolute', left: '30%', width: '40%', top: 0, bottom: 0, background: 'var(--band)', borderRadius: 6 }} />
                <div style={{ position: 'absolute', left: markerLeft, top: -4, width: 4, height: 20, background: 'var(--flag)', borderRadius: 2 }} />
              </div>
            </div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>
            Model confidence interval: ±{formatAgeMonths(detail.uncertainty_months)} · Sex input:{' '}
            {detail.patient.sex === 'male' ? 'Male' : 'Female'}
          </div>
        </div>
      )}
    </Card>
  )
}

function AgentPanelCard({ detail, onSaved }: { detail: CaseDetail | null | undefined; onSaved: () => void }) {
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
  const lastDetailId = useRef<number | null>(null)

  useEffect(() => {
    if (detail && detail.id !== lastDetailId.current) {
      setNote(detail.decision_notes ?? '')
      lastDetailId.current = detail.id
    }
  }, [detail])

  async function saveDecision(decision: Decision) {
    if (!detail) return
    setSaving(true)
    setSaveError(null)
    try {
      await api.recordDecision(detail.id, { decision, manual_bone_age_months: null, notes: note.trim() || null })
      onSaved()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Could not save.')
    } finally {
      setSaving(false)
    }
  }

  async function exportPdf() {
    if (!detail) return
    setExporting(true)
    try {
      const blobUrl = await api.fetchAuthedBlobUrl(`/cases/${detail.id}/report.pdf`)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `${detail.case_code}_report.pdf`
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
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Growth review agent</h2>
      </div>
      {!detail && <EmptyState title="No case to review yet" />}
      {detail && (
        <>
          <ol style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10, fontSize: 14 }}>
            <li style={{ display: 'flex', gap: 10 }}>
              <span style={{ color: 'var(--accent-text)', fontWeight: 700 }}>1</span>
              <span>Bone age estimated from X-ray and sex input.</span>
            </li>
            <li style={{ display: 'flex', gap: 10 }}>
              <span style={{ color: 'var(--accent-text)', fontWeight: 700 }}>2</span>
              <span>Compared with chronological age against the sex-specific normal range.</span>
            </li>
            <li style={{ display: 'flex', gap: 10 }}>
              <span style={{ color: detail.flag_status === 'cleared' ? 'var(--ok-text)' : 'var(--flag)', fontWeight: 700 }}>3</span>
              <span>
                {detail.flag_status === 'flagged' && (
                  <>
                    <strong>Flag raised:</strong> bone age is {detail.gap_direction} beyond the normal range.
                  </>
                )}
                {detail.flag_status === 'needs_review' && (
                  <>
                    <strong>Flagged as uncertain:</strong> model confidence is too low to classify automatically.
                  </>
                )}
                {detail.flag_status === 'cleared' && <>No flag: bone age is within the normal range.</>}
                {!detail.flag_status && <>Waiting for the growth review agent.</>}
              </span>
            </li>
          </ol>
          {detail.doctor_note && (
            <div style={{ background: 'var(--soft)', border: '1px solid var(--border)', borderRadius: 10, padding: 14, fontSize: 14, lineHeight: 1.55 }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Note for the doctor</div>
              {detail.doctor_note}
            </div>
          )}
          <label htmlFor="note" style={{ fontSize: 13, fontWeight: 600 }}>
            Doctor&apos;s note
          </label>
          <textarea
            id="note"
            rows={2}
            placeholder="Add your assessment…"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            style={{ border: '1px solid var(--input)', borderRadius: 8, padding: 10, fontFamily: 'inherit', fontSize: 14, resize: 'vertical', background: 'var(--surface)', color: 'var(--ink)' }}
          />
          {saveError && (
            <p role="alert" style={{ margin: 0, fontSize: 13, color: 'var(--flag-text)' }}>
              {saveError}
            </p>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <PrimaryButton onClick={() => saveDecision('confirm_flag')} disabled={saving}>
              Confirm flag
            </PrimaryButton>
            <SecondaryButton onClick={() => saveDecision('within_expected_range')} disabled={saving}>
              Mark as normal
            </SecondaryButton>
            <SecondaryButton onClick={exportPdf} disabled={exporting}>
              {exporting ? 'Exporting…' : 'Export report (PDF)'}
            </SecondaryButton>
          </div>
        </>
      )}
      <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
        Decision support only. The final assessment is made by the clinician.
      </p>
    </Card>
  )
}

function ScatterChartCard({ cases }: { cases: CaseListItem[] }) {
  const points = cases
    .filter((c) => c.chronological_age_months != null && c.bone_age_months != null)
    .slice(0, 6)

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>Bone age vs chronological age</h2>
      {points.length === 0 ? (
        <EmptyState title="No predictions yet" description="Run an analysis to see cases plotted here." />
      ) : (
        <svg
          viewBox="0 0 500 310"
          role="img"
          aria-label={`Scatter of ${points.length} recent cases: bone age against chronological age, with a shaded illustrative normal band around the equal-age line.`}
          style={{ width: '100%', height: 'auto' }}
        >
          <polygon points="40,249 436,18 472,18 472,39 76,270 40,270" style={{ fill: 'var(--band2)' }} />
          <line x1={40} y1={270} x2={436} y2={18} stroke="#8DB8A4" strokeWidth={1.5} strokeDasharray="5 4" />
          <line x1={40} y1={270} x2={480} y2={270} stroke="#9AA6B2" />
          <line x1={40} y1={270} x2={40} y2={10} stroke="#9AA6B2" />
          <text x={40} y={288} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="middle">0</text>
          <text x={184} y={288} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="middle">6</text>
          <text x={328} y={288} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="middle">12</text>
          <text x={472} y={288} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="middle">18</text>
          <text x={256} y={306} fontSize={12} style={{ fill: 'var(--text2)' }} textAnchor="middle">Chronological age (years)</text>
          <text x={30} y={274} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="end">0</text>
          <text x={30} y={190} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="end">6</text>
          <text x={30} y={106} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="end">12</text>
          <text x={30} y={22} fontSize={11} style={{ fill: 'var(--muted)' }} textAnchor="end">18</text>
          <text x={14} y={150} fontSize={12} style={{ fill: 'var(--text2)' }} textAnchor="middle" transform="rotate(-90 14 150)">
            Bone age (years)
          </text>
          {points.map((point, index) => {
            const chronYears = (point.chronological_age_months ?? 0) / 12
            const boneYears = (point.bone_age_months ?? 0) / 12
            const x = scatterX(chronYears)
            const y = scatterY(boneYears)
            const flagged = point.flag_status === 'flagged' || point.flag_status === 'needs_review'
            if (index === 0 && flagged) {
              return (
                <g key={point.id}>
                  <circle cx={x} cy={y} r={8} style={{ fill: 'var(--flag)' }} />
                  <text x={x + 12} y={y + 4} fontSize={12} fontWeight={600} style={{ fill: 'var(--flag-text)' }}>
                    {point.case_code}
                  </text>
                </g>
              )
            }
            if (flagged) {
              return <circle key={point.id} cx={x} cy={y} r={6} style={{ fill: 'var(--surface)', stroke: 'var(--flag)' }} strokeWidth={2.5} />
            }
            return <circle key={point.id} cx={x} cy={y} r={5} fill="#3A8A6A" />
          })}
        </svg>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, fontSize: 12, color: 'var(--muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 14, height: 10, background: 'var(--band2)', borderRadius: 2 }} />
          Normal range (±2 SD, illustrative)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#3A8A6A' }} />
          Within range
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--flag)' }} />
          Flagged
        </span>
      </div>
    </Card>
  )
}
