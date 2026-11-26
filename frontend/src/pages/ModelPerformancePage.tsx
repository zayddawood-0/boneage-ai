import * as api from '../api/client'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { ErrorState, LoadingState } from '../components/StateViews'
import { useAsync } from '../lib/useAsync'

function formatMae(value: number | string | undefined): string {
  if (typeof value === 'number') return `${value.toFixed(1)} mo`
  return value ?? '[TBD]'
}

function formatPct(value: number | string | undefined): string {
  if (typeof value === 'number') return `${value.toFixed(0)}%`
  return value ?? '[TBD]'
}

const kpiCardStyle = { padding: 18 } as const

export function ModelPerformancePage() {
  const { data, loading, error, reload } = useAsync(() => api.getModelPerformance(), [])

  return (
    <>
      <PageHeader
        title="Model performance"
        description="How accurate the bone age model is, and where it may fall short"
      />

      {loading && <LoadingState label="Loading model performance…" />}
      {!loading && error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && data && (
        <>
          <section
            aria-label="Key metrics"
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}
          >
            <Card style={kpiCardStyle}>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>Mean absolute error</div>
              <div className="font-mono-ibm" style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>
                {formatMae(data.mae_overall_months)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>RSNA validation set</div>
            </Card>
            <Card style={kpiCardStyle}>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>MAE · male</div>
              <div className="font-mono-ibm" style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>
                {formatMae(data.mae_by_sex?.male)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>Validation set</div>
            </Card>
            <Card style={kpiCardStyle}>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>MAE · female</div>
              <div className="font-mono-ibm" style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>
                {formatMae(data.mae_by_sex?.female)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>Validation set</div>
            </Card>
            <Card style={kpiCardStyle}>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>Within ±12 months</div>
              <div className="font-mono-ibm" style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>
                {formatPct(data.pct_within_12_months)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>Share of validation cases</div>
            </Card>
          </section>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <h2 style={{ margin: 0, fontSize: 18 }}>Predicted vs true bone age</h2>
              <div
                role="img"
                aria-label="Scatter of predicted vs radiologist bone age, from your validation run"
                style={placeholderPanelStyle}
              >
                [Scatter of predicted vs radiologist bone age, from your validation run]
              </div>
            </Card>
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <h2 style={{ margin: 0, fontSize: 18 }}>Error by age group</h2>
              {typeof data.mae_by_age_band === 'object' && data.mae_by_age_band !== null ? (
                <AgeBandBarChart maeByAgeBand={data.mae_by_age_band} />
              ) : (
                <div
                  role="img"
                  aria-label="Bar chart of MAE per age band (0–5, 5–10, 10–15, 15–19 years)"
                  style={placeholderPanelStyle}
                >
                  [Bar chart of MAE per age band (0–5, 5–10, 10–15, 15–19 years)]
                </div>
              )}
            </Card>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
            <Card>
              <h2 style={{ margin: '0 0 8px', fontSize: 18 }}>Model card</h2>
              <ModelCardRow label="Task" value="Bone age regression from left-hand X-ray" />
              <ModelCardRow label="Inputs" value="X-ray image + sex" />
              <ModelCardRow label="Architecture" value="[Backbone, e.g. CNN name]" />
              <ModelCardRow label="Training data" value="RSNA Pediatric Bone Age Challenge 2017" />
              <ModelCardRow label="Dataset split" value="12,611 train · 1,425 validation · 200 test" />
              <ModelCardRow
                label="Version"
                value={
                  <span className="font-mono-ibm">{String(data.model_card?.version ?? '[v_._]')}</span>
                }
                last
              />
              <ModelCardRow label="Last trained" value="[date]" last />
            </Card>
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <h2 style={{ margin: 0, fontSize: 18 }}>Limitations</h2>
              <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 10, fontSize: 14, lineHeight: 1.5 }}>
                <li>Trained on X-rays from a small number of US hospitals; accuracy may differ for other populations.</li>
                <li>Labels follow radiologist bone age readings, so the model inherits their variation.</li>
                <li>The normal-range threshold used by the agent is a setting, not something the model learns.</li>
                <li>Not for children outside the age range of the training data.</li>
              </ul>
              <div style={{ background: 'var(--soft)', border: '1px solid var(--border)', borderRadius: 10, padding: 14, fontSize: 13, color: 'var(--text2)' }}>
                External check: evaluate on the Digital Hand Atlas or RHPE datasets to see how the model does on other
                populations.
              </div>
            </Card>
          </div>
        </>
      )}
    </>
  )
}

const placeholderPanelStyle = {
  height: 320,
  borderRadius: 10,
  border: '1px dashed var(--dash)',
  background: 'var(--soft)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center' as const,
  color: 'var(--muted)',
  fontSize: 14,
  padding: 16,
  boxSizing: 'border-box' as const,
}

function ModelCardRow({ label, value, last = false }: { label: string; value: React.ReactNode; last?: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: 16,
        padding: '10px 0',
        borderBottom: last ? undefined : '1px solid var(--row)',
        fontSize: 14,
      }}
    >
      <span style={{ color: 'var(--muted)' }}>{label}</span>
      <span style={{ fontWeight: 600, textAlign: 'right' }}>{value}</span>
    </div>
  )
}

function AgeBandBarChart({ maeByAgeBand }: { maeByAgeBand: Record<string, number | string> }) {
  const entries = Object.entries(maeByAgeBand)
  const numeric = entries.filter(([, v]) => typeof v === 'number') as [string, number][]
  const max = Math.max(1, ...numeric.map(([, v]) => v))

  return (
    <div
      role="img"
      aria-label="Bar chart of mean absolute error per age band"
      style={{ ...placeholderPanelStyle, border: '1px solid var(--border)', background: 'var(--surface)', flexDirection: 'column', gap: 10, padding: 16 }}
    >
      {entries.map(([band, value]) => (
        <div key={band} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 70, fontSize: 12, color: 'var(--muted)', textAlign: 'right' }}>{band}</span>
          <div style={{ flex: 1, height: 14, background: 'var(--track)', borderRadius: 7 }}>
            {typeof value === 'number' && (
              <div
                style={{
                  height: '100%',
                  width: `${(value / max) * 100}%`,
                  background: 'var(--accent-text)',
                  borderRadius: 7,
                }}
              />
            )}
          </div>
          <span className="font-mono-ibm" style={{ width: 60, fontSize: 12 }}>
            {typeof value === 'number' ? `${value.toFixed(1)} mo` : value}
          </span>
        </div>
      ))}
    </div>
  )
}
