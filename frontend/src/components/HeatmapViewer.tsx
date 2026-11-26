import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchAuthedBlobUrl } from '../api/client'
import { SegmentedTabs } from './SegmentedTabs'
import { ErrorState, LoadingState } from './StateViews'

type ViewMode = 'xray' | 'overlay' | 'sideBySide'

const VIEW_OPTIONS = [
  { key: 'xray' as ViewMode, label: 'X-ray' },
  { key: 'overlay' as ViewMode, label: 'Heatmap overlay' },
  { key: 'sideBySide' as ViewMode, label: 'Side by side' },
]

function useAuthedImage(url: string | null): { blobUrl: string | null; loading: boolean; error: string | null } {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(url))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!url) {
      setBlobUrl(null)
      setLoading(false)
      return
    }
    let cancelled = false
    let created: string | null = null
    setLoading(true)
    setError(null)
    fetchAuthedBlobUrl(url)
      .then((objectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(objectUrl)
          return
        }
        created = objectUrl
        setBlobUrl(objectUrl)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      if (created) URL.revokeObjectURL(created)
    }
  }, [url])

  return { blobUrl, loading, error }
}

/**
 * The X-ray/Heatmap-overlay/Side-by-side viewer in design/Main.html and
 * design/Case.html. The backend serves the plain X-ray and the heatmap as
 * two separate same-sized layers (GET /cases/{id}/image,
 * GET /cases/{id}/heatmap-layer — see docs/api.md) so this composites them
 * itself: the opacity slider controls the heatmap LAYER's CSS opacity in
 * real time, true independent-layer blending rather than a pre-flattened image.
 */
export function HeatmapViewer({
  heading,
  imageUrl,
  heatmapLayerUrl,
  heightPx,
}: {
  heading: ReactNode
  imageUrl: string | null
  heatmapLayerUrl: string | null
  heightPx: number
}) {
  const [view, setView] = useState<ViewMode>('overlay')
  const [opacityPercent, setOpacityPercent] = useState(60)

  const image = useAuthedImage(imageUrl)
  const layer = useAuthedImage(heatmapLayerUrl)

  const panelStyle = {
    height: heightPx,
    borderRadius: 12,
    background: '#0E0D0C',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#A8A097',
    fontSize: 14,
    textAlign: 'center' as const,
    padding: 16,
    boxSizing: 'border-box' as const,
    position: 'relative' as const,
    overflow: 'hidden' as const,
  }

  function renderLayers(showHeatmap: boolean) {
    if (!image.blobUrl) return null
    return (
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        <img
          src={image.blobUrl}
          alt=""
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain' }}
        />
        {showHeatmap && layer.blobUrl && (
          <img
            src={layer.blobUrl}
            alt=""
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              opacity: opacityPercent / 100,
            }}
          />
        )}
      </div>
    )
  }

  const loading = image.loading || layer.loading
  const error = image.error ?? layer.error

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        {heading}
        <SegmentedTabs options={VIEW_OPTIONS} value={view} onChange={setView} size="imageView" ariaLabel="Image view" />
      </div>

      <div
        role="img"
        aria-label={
          view === 'xray'
            ? 'Hand X-ray, no heatmap overlay'
            : 'Hand X-ray with attention heatmap overlay — brighter regions received more of the model’s attention'
        }
        style={panelStyle}
      >
        {loading && <LoadingState label="Loading X-ray…" />}
        {!loading && error && <ErrorState message={error} />}
        {!loading && !error && !image.blobUrl && 'No X-ray uploaded yet'}
        {!loading && !error && image.blobUrl && view !== 'sideBySide' && renderLayers(view === 'overlay')}
        {!loading && !error && image.blobUrl && view === 'sideBySide' && (
          <div style={{ display: 'flex', width: '100%', height: '100%', gap: 8 }}>
            <div style={{ flex: 1, minWidth: 0 }}>{renderLayers(false)}</div>
            <div style={{ flex: 1, minWidth: 0 }}>{renderLayers(true)}</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, fontSize: 12, color: 'var(--muted)' }}>
        <span>Model attention</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          Low
          <span
            style={{
              width: 140,
              height: 10,
              borderRadius: 5,
              background: 'linear-gradient(90deg, #3B0F70, #B73779, #FC8961, #FCFDBF)',
            }}
          />
          High
        </span>
        <label htmlFor="heatmap-opacity" style={{ marginLeft: 'auto' }}>
          Overlay opacity
        </label>
        <input
          id="heatmap-opacity"
          type="range"
          min={0}
          max={100}
          value={opacityPercent}
          onChange={(event) => setOpacityPercent(Number(event.target.value))}
          disabled={view === 'xray'}
          style={{ width: 120 }}
        />
      </div>
    </div>
  )
}
