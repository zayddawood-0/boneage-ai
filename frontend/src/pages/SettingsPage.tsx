import { useState } from 'react'
import * as api from '../api/client'
import type { RuleType, SettingsOut, SettingsUpdate } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { Card } from '../components/Card'
import { PrimaryButton, SecondaryButton } from '../components/Buttons'
import { PageHeader } from '../components/PageHeader'
import { SettingsToggleRow } from '../components/SettingsToggleRow'
import { ErrorState, LoadingState } from '../components/StateViews'
import { useTheme } from '../theme/ThemeContext'
import type { ThemePreference } from '../theme/ThemeContext'
import { useAsync } from '../lib/useAsync'

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
  width: '100%',
}
const textFieldStyle: React.CSSProperties = { ...selectStyle }

export function SettingsPage() {
  const { data, loading, error, reload } = useAsync(() => api.getSettings(), [])
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [local, setLocal] = useState<SettingsOut | null>(null)
  const [notAvailableNote, setNotAvailableNote] = useState<string | null>(null)
  const [emailNotifications, setEmailNotifications] = useState(false)
  const [dailySummary, setDailySummary] = useState(false)

  const settings = local ?? data

  async function patch(update: SettingsUpdate) {
    if (!settings) return
    setLocal({ ...settings, ...update })
    setSaveStatus('saving')
    try {
      await api.updateSettings(update)
      setSaveStatus('saved')
    } catch (err) {
      setSaveStatus('error')
      setSaveMessage(err instanceof Error ? err.message : 'Could not save this setting.')
      reload()
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Flagging rules, agent behaviour, appearance and privacy" />

      {saveStatus === 'saving' && <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>Saving…</p>}
      {saveStatus === 'saved' && <p style={{ margin: 0, fontSize: 13, color: 'var(--ok-text)' }}>Saved.</p>}
      {saveStatus === 'error' && (
        <p role="alert" style={{ margin: 0, fontSize: 13, color: 'var(--flag-text)' }}>
          {saveMessage}
        </p>
      )}
      {notAvailableNote && <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>{notAvailableNote}</p>}

      {loading && <LoadingState label="Loading settings…" />}
      {!loading && error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && settings && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <h2 style={{ margin: 0, fontSize: 18 }}>Flagging rules</h2>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
                The agent flags a case when the gap between bone age and real age is outside this range.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 14 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <label htmlFor="rule" style={{ fontSize: 13, fontWeight: 600 }}>
                    Rule type
                  </label>
                  <select
                    id="rule"
                    value={settings.rule_type}
                    onChange={(event) => patch({ rule_type: event.target.value as RuleType })}
                    style={selectStyle}
                  >
                    <option value="sd">Standard deviations for age and sex</option>
                    <option value="fixed_months">Fixed number of months</option>
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <label htmlFor="thr" style={{ fontSize: 13, fontWeight: 600 }}>
                    Threshold
                  </label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                      id="thr"
                      type="number"
                      min={0}
                      step={settings.rule_type === 'sd' ? 0.5 : 1}
                      value={settings.rule_type === 'sd' ? settings.threshold_sd : settings.threshold_months}
                      onChange={(event) =>
                        patch(
                          settings.rule_type === 'sd'
                            ? { threshold_sd: Number(event.target.value) }
                            : { threshold_months: Number(event.target.value) },
                        )
                      }
                      style={{ ...textFieldStyle, width: '100%' }}
                    />
                    <span style={{ fontSize: 13, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                      ± {settings.rule_type === 'sd' ? 'SD' : 'months'}
                    </span>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label htmlFor="ref" style={{ fontSize: 13, fontWeight: 600 }}>
                  Reference standard
                </label>
                <select
                  id="ref"
                  value={settings.reference_table_name ?? ''}
                  onChange={(event) => patch({ reference_table_name: event.target.value || null })}
                  style={selectStyle}
                  disabled={settings.rule_type !== 'sd'}
                >
                  <option value="">[Choose reference tables]</option>
                </select>
                {settings.rule_type === 'sd' && (
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                    The Greulich &amp; Pyle-based reference table is an empty <code>[TBD — to verify]</code> template —
                    every case will come back &quot;needs review&quot; until it&apos;s populated. See AGENTS.md.
                  </p>
                )}
              </div>
              <div>
                <SettingsToggleRow
                  title="Flag advanced bone age"
                  description="Also flag when bone age is ahead of real age."
                  checked={settings.flag_advanced}
                  onChange={(checked) => patch({ flag_advanced: checked })}
                />
                <SettingsToggleRow
                  title="Flag when model is unsure"
                  description="Send to a doctor if the uncertainty is wider than the threshold."
                  checked={settings.flag_uncertain_enabled}
                  onChange={(checked) => patch({ flag_uncertain_enabled: checked })}
                  noBorder
                />
              </div>
            </Card>

            <Card style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <h2 style={{ margin: '0 0 6px', fontSize: 18 }}>Agent behaviour</h2>
              <SettingsToggleRow
                title="Auto-clear normal cases"
                description="Cases inside the range skip the review queue."
                checked={settings.auto_clear_enabled}
                onChange={(checked) => patch({ auto_clear_enabled: checked })}
              />
              <SettingsToggleRow
                title="Write a note for the doctor"
                description="The agent explains the flag and suggests what to check."
                checked={settings.write_note_enabled}
                onChange={(checked) => patch({ write_note_enabled: checked })}
              />
              <SettingsToggleRow
                title="Email me about new flags"
                description="One email per flagged case."
                checked={emailNotifications}
                onChange={setEmailNotifications}
              />
              <SettingsToggleRow
                title="Daily summary"
                description="A short digest of the day's cases at 6 pm."
                checked={dailySummary}
                onChange={setDailySummary}
                noBorder
              />
            </Card>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
            <AppearanceCard settings={settings} onPatch={patch} />
            <Card style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <h2 style={{ margin: '0 0 6px', fontSize: 18 }}>Data and privacy</h2>
              <SettingsToggleRow
                title="Remove names from images on upload"
                description="Strip patient details burned into the X-ray. Always on in this build (server-side check)."
                checked
                onChange={() => setNotAvailableNote('De-identification is always on — it isn’t a configurable toggle in this build.')}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '14px 0' }}>
                <label htmlFor="ret" style={{ fontSize: 13, fontWeight: 600 }}>
                  Delete X-ray images after
                </label>
                <select
                  id="ret"
                  value={[30, 90].includes(settings.retention_days) ? String(settings.retention_days) : ''}
                  onChange={(event) => patch({ retention_days: Number(event.target.value) })}
                  style={selectStyle}
                >
                  <option value="" disabled>
                    [Retention period]
                  </option>
                  <option value="30">30 days</option>
                  <option value="90">90 days</option>
                  <option value="36500">Never</option>
                </select>
              </div>
              <SecondaryButton
                style={{ alignSelf: 'flex-start' }}
                onClick={() => setNotAvailableNote('Audit log export isn’t available in this build yet.')}
              >
                Download audit log
              </SecondaryButton>
            </Card>
          </div>

          <AccountCard onNotAvailable={setNotAvailableNote} />
        </>
      )}
    </>
  )
}

function AppearanceCard({ settings, onPatch }: { settings: SettingsOut; onPatch: (u: SettingsUpdate) => void }) {
  const { preference, setPreference } = useTheme()

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>Appearance and units</h2>
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Theme</legend>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 14 }}>
          {(['light', 'dark', 'system'] as ThemePreference[]).map((option) => (
            <label key={option} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="radio"
                name="th"
                checked={preference === option}
                onChange={() => setPreference(option)}
                style={{ width: 18, height: 18 }}
              />
              {option === 'light' ? 'Light' : option === 'dark' ? 'Dark' : 'Match my device'}
            </label>
          ))}
        </div>
      </fieldset>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <label htmlFor="units" style={{ fontSize: 13, fontWeight: 600 }}>
          Show ages as
        </label>
        <select id="units" value={settings.age_unit} onChange={(event) => onPatch({ age_unit: event.target.value })} style={selectStyle}>
          <option value="years_months">Years and months (9y 2m)</option>
          <option value="months">Months (110 mo)</option>
          <option value="decimal_years">Decimal years (9.2 y)</option>
        </select>
      </div>
    </Card>
  )
}

function AccountCard({ onNotAvailable }: { onNotAvailable: (msg: string) => void }) {
  const { user } = useAuth()
  const [name, setName] = useState('')

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>Account</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label htmlFor="an" style={{ fontSize: 13, fontWeight: 600 }}>
            Full name
          </label>
          <input id="an" type="text" placeholder="[Doctor name]" value={name} onChange={(event) => setName(event.target.value)} style={textFieldStyle} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label htmlFor="ae" style={{ fontSize: 13, fontWeight: 600 }}>
            Email
          </label>
          <input id="ae" type="email" value={user?.email ?? ''} readOnly style={textFieldStyle} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label htmlFor="ar" style={{ fontSize: 13, fontWeight: 600 }}>
            Role
          </label>
          <select id="ar" value={user?.role ?? 'admin'} disabled style={selectStyle}>
            <option value="doctor">Doctor</option>
            <option value="radiographer">Radiographer</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <PrimaryButton onClick={() => onNotAvailable('Profile editing isn’t available in this build yet.')}>
          Save changes
        </PrimaryButton>
        <SecondaryButton onClick={() => onNotAvailable('Password changes aren’t available in this build yet.')}>
          Change password
        </SecondaryButton>
      </div>
    </Card>
  )
}
