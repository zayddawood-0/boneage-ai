import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import * as api from '../api/client'
import type { CaseListItem, Sex } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { SegmentedTabs } from '../components/SegmentedTabs'
import { flagChipProps, StatusChip } from '../components/StatusChip'
import { SecondaryButton } from '../components/Buttons'
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews'
import { formatAgeMonths, formatDateDisplay, formatGapMonths } from '../lib/age'
import { useAsync } from '../lib/useAsync'
import { useAuth } from '../auth/AuthContext'

type Tab = 'all' | 'await' | 'flagged' | 'done'
type SortKey = 'gap' | 'newest' | 'oldest'

const TAB_OPTIONS: { key: Tab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'await', label: 'Awaiting review' },
  { key: 'flagged', label: 'Flagged' },
  { key: 'done', label: 'Reviewed' },
]

const selectStyle: React.CSSProperties = {
  height: 44,
  border: '1px solid var(--input)',
  borderRadius: 8,
  padding: '0 12px',
  fontFamily: 'inherit',
  fontSize: 14,
  background: 'var(--surface)',
  color: 'var(--ink)',
  boxSizing: 'border-box',
  width: 170,
}

const thStyle: React.CSSProperties = { padding: '10px 12px', borderBottom: '1px solid var(--border)', textAlign: 'left' }
const tdStyle: React.CSSProperties = { padding: 12, borderBottom: '1px solid var(--row)' }

const PAGE_SIZE = 10

function isAwaiting(c: CaseListItem): boolean {
  return (c.flag_status === 'flagged' || c.flag_status === 'needs_review') && c.decision === null
}
function isAutoCleared(c: CaseListItem): boolean {
  return c.flag_status === 'cleared' && c.decision === null
}

function statusLabel(c: CaseListItem): string {
  if (isAutoCleared(c)) return 'Auto-cleared'
  if (isAwaiting(c)) return 'Awaiting review'
  if (c.decision === 'confirm_flag') return 'Reviewed · confirmed'
  if (c.decision) return 'Reviewed'
  return 'Within expected range'
}

// The backend has no endpoint to resolve "who decided this case" to a name
// (decided_by_user_id has no lookup) — see the frontend delivery notes.
// Shown honestly as "whether" a doctor has acted, not "which" doctor.
function assignedToLabel(c: CaseListItem): string {
  if (isAutoCleared(c)) return '—'
  return c.decision ? 'Doctor' : 'Not yet assigned'
}

export function QueuePage() {
  const { user } = useAuth()
  const readOnly = user?.role === 'radiographer'

  const { data, loading, error, reload } = useAsync(() => api.listCases({ page_size: 200 }), [])
  const [tab, setTab] = useState<Tab>('all')
  const [search, setSearch] = useState('')
  const [sex, setSex] = useState<'' | Sex>('')
  const [sort, setSort] = useState<SortKey>('gap')
  const [page, setPage] = useState(1)

  const allCases = data?.cases ?? []

  const filtered = useMemo(() => {
    let rows = allCases
    if (tab === 'await') rows = rows.filter(isAwaiting)
    else if (tab === 'flagged') rows = rows.filter((c) => c.flag_status === 'flagged' || c.flag_status === 'needs_review')
    else if (tab === 'done') rows = rows.filter((c) => c.decision !== null)

    if (sex) rows = rows.filter((c) => c.sex === sex)

    const query = search.trim().toLowerCase()
    if (query) {
      rows = rows.filter(
        (c) => c.case_code.toLowerCase().includes(query) || c.patient_name_or_id.toLowerCase().includes(query),
      )
    }

    const sorted = [...rows]
    if (sort === 'gap') sorted.sort((a, b) => Math.abs(b.gap_months ?? 0) - Math.abs(a.gap_months ?? 0))
    else if (sort === 'newest') sorted.sort((a, b) => b.xray_date.localeCompare(a.xray_date))
    else sorted.sort((a, b) => a.xray_date.localeCompare(b.xray_date))
    return sorted
  }, [allCases, tab, sex, search, sort])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const awaitingCount = allCases.filter(isAwaiting).length
  const reviewedCount = allCases.filter((c) => c.decision !== null).length // see delivery notes: "this week" not computable from the list endpoint
  const autoClearedCount = allCases.filter(isAutoCleared).length

  return (
    <>
      <PageHeader
        title="Review queue"
        description="Cases the agent has checked, with flagged ones waiting for a doctor"
      />

      <section aria-label="Queue summary" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Awaiting review</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6, color: 'var(--flag)' }}>
            {loading ? '—' : awaitingCount}
          </div>
        </Card>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Reviewed this week</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6 }}>
            {loading ? '—' : reviewedCount}
          </div>
        </Card>
        <Card style={{ padding: 18 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Auto-cleared as normal</div>
          <div className="font-mono-ibm" style={{ fontSize: 30, fontWeight: 600, marginTop: 6 }}>
            {loading ? '—' : autoClearedCount}
          </div>
        </Card>
      </section>

      <Card style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h2 style={{ position: 'absolute', left: -9999 }}>Cases</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <SegmentedTabs
            options={TAB_OPTIONS}
            value={tab}
            onChange={(key) => {
              setTab(key)
              setPage(1)
            }}
            ariaLabel="Filter by status"
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <label htmlFor="qs" style={{ position: 'absolute', left: -9999 }}>
              Search
            </label>
            <input
              id="qs"
              type="search"
              placeholder="Search case or patient"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
              style={{ ...selectStyle, width: 240 }}
            />
            <label htmlFor="qsex" style={{ position: 'absolute', left: -9999 }}>
              Sex
            </label>
            <select
              id="qsex"
              value={sex}
              onChange={(event) => {
                setSex(event.target.value as '' | Sex)
                setPage(1)
              }}
              style={{ ...selectStyle, width: 140 }}
            >
              <option value="">Any sex</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
            <label htmlFor="qsort" style={{ position: 'absolute', left: -9999 }}>
              Sort
            </label>
            <select id="qsort" value={sort} onChange={(event) => setSort(event.target.value as SortKey)} style={selectStyle}>
              <option value="gap">Largest gap first</option>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </div>
        </div>

        {loading && <LoadingState label="Loading review queue…" />}
        {!loading && error && <ErrorState message={error} onRetry={reload} />}
        {!loading && !error && filtered.length === 0 && (
          <EmptyState title="No cases match this view" description="Try a different tab or clear the filters." />
        )}
        {!loading && !error && filtered.length > 0 && (
          <>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', minWidth: 960, borderCollapse: 'collapse', fontSize: 14 }}>
                <thead>
                  <tr style={{ color: 'var(--muted)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    <th style={thStyle}>Case</th>
                    <th style={thStyle}>X-ray date</th>
                    <th style={thStyle}>Sex</th>
                    <th style={thStyle}>Chronological</th>
                    <th style={thStyle}>Bone age</th>
                    <th style={thStyle}>Gap</th>
                    <th style={thStyle}>Agent result</th>
                    <th style={thStyle}>Assigned to</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>
                      <span style={{ position: 'absolute', left: -9999 }}>Action</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((row) => {
                    const chip = flagChipProps(row.flag_status, row.gap_direction)
                    const flagged = row.flag_status === 'flagged' || row.flag_status === 'needs_review'
                    return (
                      <tr key={row.id}>
                        <td className="font-mono-ibm" style={{ ...tdStyle, fontWeight: 600 }}>
                          {row.case_code}
                        </td>
                        <td style={{ ...tdStyle, color: 'var(--text2)' }}>{formatDateDisplay(row.xray_date)}</td>
                        <td style={tdStyle}>{row.sex === 'male' ? 'M' : 'F'}</td>
                        <td className="font-mono-ibm" style={tdStyle}>
                          {formatAgeMonths(row.chronological_age_months)}
                        </td>
                        <td className="font-mono-ibm" style={tdStyle}>
                          {formatAgeMonths(row.bone_age_months)}
                        </td>
                        <td className="font-mono-ibm" style={{ ...tdStyle, fontWeight: 600, color: flagged ? 'var(--flag)' : 'var(--text2)' }}>
                          {formatGapMonths(row.gap_months)}
                        </td>
                        <td style={tdStyle}>
                          <StatusChip variant={chip.variant}>{chip.label}</StatusChip>
                        </td>
                        <td style={{ ...tdStyle, color: 'var(--text2)' }}>{assignedToLabel(row)}</td>
                        <td style={{ ...tdStyle, color: 'var(--text2)' }}>{statusLabel(row)}</td>
                        <td style={{ ...tdStyle, textAlign: 'right' }}>
                          <Link to={`/cases/${row.id}`} style={{ fontWeight: 600, color: 'var(--accent-text)' }}>
                            {readOnly ? 'View' : 'Open'}
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--muted)' }}>
              <span>
                Showing {pageRows.length} of {filtered.length} cases
              </span>
              <div style={{ display: 'flex', gap: 6 }}>
                <SecondaryButton height={36} onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  Previous
                </SecondaryButton>
                <SecondaryButton height={36} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                  Next
                </SecondaryButton>
              </div>
            </div>
          </>
        )}
      </Card>
    </>
  )
}
