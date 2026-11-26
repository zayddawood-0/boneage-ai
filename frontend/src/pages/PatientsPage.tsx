import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import * as api from '../api/client'
import type { CaseListItem, PatientDetail } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { primaryButtonStyle } from '../components/Buttons'
import { StatusChip } from '../components/StatusChip'
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews'
import { formatAgeMonths, formatDateDisplay, formatGapMonths } from '../lib/age'
import { useAsync } from '../lib/useAsync'

const inputStyle: React.CSSProperties = {
  height: 44,
  border: '1px solid var(--input)',
  borderRadius: 8,
  padding: '0 12px',
  fontFamily: 'inherit',
  fontSize: 14,
  background: 'var(--surface)',
  color: 'var(--ink)',
  boxSizing: 'border-box',
  width: 240,
}

const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderBottom: '1px solid var(--border)',
  textAlign: 'left',
}
const tdStyle: React.CSSProperties = { padding: 12, borderBottom: '1px solid var(--row)' }

interface PatientRow {
  patient: PatientDetail
  sortedCases: CaseListItem[]
  latest: CaseListItem | null
  trend: string
}

function trendFor(sortedCases: CaseListItem[]): string {
  if (sortedCases.length < 2) return 'First scan'
  const latestGap = sortedCases[sortedCases.length - 1].gap_months
  const previousGap = sortedCases[sortedCases.length - 2].gap_months
  if (latestGap == null || previousGap == null) return 'Gap steady'
  const latestAbs = Math.abs(latestGap)
  const previousAbs = Math.abs(previousGap)
  if (latestAbs < previousAbs) return 'Gap narrowing'
  if (latestAbs > previousAbs) return 'Gap widening'
  return 'Gap steady'
}

async function loadPatientRows(): Promise<PatientRow[]> {
  const patients = await api.listPatients()
  const details = await Promise.all(patients.map((p) => api.getPatient(p.id)))
  return details.map((patient) => {
    const sortedCases = [...patient.cases].sort((a, b) => a.xray_date.localeCompare(b.xray_date))
    const latest = sortedCases.length > 0 ? sortedCases[sortedCases.length - 1] : null
    return { patient, sortedCases, latest, trend: trendFor(sortedCases) }
  })
}

export function PatientsPage() {
  const { data: rows, loading, error, reload } = useAsync(loadPatientRows, [])
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!rows) return []
    const query = search.trim().toLowerCase()
    if (!query) return rows
    return rows.filter(
      (row) =>
        row.patient.name_or_id.toLowerCase().includes(query) ||
        row.patient.patient_code.toLowerCase().includes(query),
    )
  }, [rows, search])

  return (
    <>
      <PageHeader title="Patients" description="Every child with a bone age scan, and how their gap is changing" />

      <Card style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>All patients</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <label htmlFor="ps" style={{ position: 'absolute', left: -9999 }}>
              Search patients
            </label>
            <input
              id="ps"
              type="search"
              placeholder="Search name or ID"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={inputStyle}
            />
            <Link to="/analysis/new" style={primaryButtonStyle()}>
              Add patient
            </Link>
          </div>
        </div>

        {loading && <LoadingState label="Loading patients…" />}
        {!loading && error && <ErrorState message={error} onRetry={reload} />}
        {!loading && !error && filtered.length === 0 && (
          <EmptyState
            title={search ? 'No patients match your search' : 'No patients yet'}
            description={search ? undefined : 'Start a new analysis to add the first patient.'}
          />
        )}
        {!loading && !error && filtered.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ color: 'var(--muted)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  <th style={thStyle}>Patient</th>
                  <th style={thStyle}>Sex</th>
                  <th style={thStyle}>Age</th>
                  <th style={thStyle}>Scans</th>
                  <th style={thStyle}>Latest bone age</th>
                  <th style={thStyle}>Latest gap</th>
                  <th style={thStyle}>Trend</th>
                  <th style={thStyle}>Last scan</th>
                  <th style={thStyle}>
                    <span style={{ position: 'absolute', left: -9999 }}>Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(({ patient, sortedCases, latest, trend }) => (
                  <tr key={patient.id}>
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600 }}>{patient.name_or_id}</div>
                      <div className="font-mono-ibm" style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {patient.patient_code}
                      </div>
                    </td>
                    <td style={tdStyle}>{patient.sex === 'male' ? 'M' : 'F'}</td>
                    <td className="font-mono-ibm" style={tdStyle}>
                      {formatAgeMonths(latest?.chronological_age_months)}
                    </td>
                    <td className="font-mono-ibm" style={tdStyle}>
                      {sortedCases.length}
                    </td>
                    <td className="font-mono-ibm" style={tdStyle}>
                      {formatAgeMonths(latest?.bone_age_months)}
                    </td>
                    <td style={tdStyle}>
                      {latest?.gap_months != null ? (
                        <StatusChip variant={latest.flag_status === 'flagged' ? 'flag' : 'ok'}>
                          {formatGapMonths(latest.gap_months)}
                        </StatusChip>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td style={{ ...tdStyle, color: 'var(--text2)' }}>{trend}</td>
                    <td style={{ ...tdStyle, color: 'var(--text2)' }}>{formatDateDisplay(latest?.xray_date)}</td>
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      {latest ? (
                        <Link to={`/cases/${latest.id}`} style={{ fontWeight: 600, color: 'var(--accent-text)' }}>
                          View
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
