import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'

interface Camera {
  id?: string
  name?: string
  type?: string
  status?: string | { connected?: boolean; error?: string }
  /** Populated only if the API adds it; list_cameras usually omits this. */
  stream_url?: string
}

/** Backend exposes browser-safe video at GET /api/cameras/{id}/mjpeg for these types. */
function supportsMjpegPreview(t: string | undefined): boolean {
  const x = (t ?? '').toLowerCase()
  return (
    x === 'tapo' ||
    x === 'onvif' ||
    x === 'webcam' ||
    x === 'microscope'
  )
}

function supportsPtz(t: string | undefined): boolean {
  const x = (t ?? '').toLowerCase()
  return x === 'tapo' || x === 'onvif'
}

function TapoPtzPanel({ cameraName }: { cameraName: string }) {
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const enc = encodeURIComponent(cameraName)

  const run = async (path: string) => {
    setBusy(true)
    setNote(null)
    try {
      const r = await fetch(path, { method: 'POST' })
      const j = (await r.json().catch(() => ({}))) as { detail?: string; message?: string }
      if (!r.ok) throw new Error(j.detail ?? `HTTP ${r.status}`)
      setNote(j.message ?? null)
    } catch (e) {
      setNote(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-600 dark:bg-slate-900/40">
      <p className="mb-2 text-xs font-medium text-slate-600 dark:text-slate-400">PTZ</p>
      <div className="flex max-w-[220px] flex-col items-center gap-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 w-14"
          disabled={busy}
          onClick={() => run(`/api/ptz/up/${enc}`)}
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : '↑'}
        </Button>
        <div className="flex gap-1">
          <Button type="button" variant="outline" size="sm" className="h-8 w-14" disabled={busy} onClick={() => run(`/api/ptz/left/${enc}`)}>
            ←
          </Button>
          <Button type="button" variant="outline" size="sm" className="h-8 w-14" disabled={busy} onClick={() => run(`/api/ptz/stop/${enc}`)}>
            ■
          </Button>
          <Button type="button" variant="outline" size="sm" className="h-8 w-14" disabled={busy} onClick={() => run(`/api/ptz/right/${enc}`)}>
            →
          </Button>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 w-14"
          disabled={busy}
          onClick={() => run(`/api/ptz/down/${enc}`)}
        >
          ↓
        </Button>
        <div className="mt-2 flex gap-1">
          <Button type="button" variant="outline" size="sm" className="text-xs" disabled={busy} onClick={() => run(`/api/ptz/zoom-in/${enc}`)}>
            Zoom +
          </Button>
          <Button type="button" variant="outline" size="sm" className="text-xs" disabled={busy} onClick={() => run(`/api/ptz/zoom-out/${enc}`)}>
            Zoom −
          </Button>
        </div>
      </div>
      {note && <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">{note}</p>}
    </div>
  )
}

function statusLabel(cam: Camera): string {
  const s = cam.status
  if (typeof s === 'string') return s.toLowerCase()
  if (s && typeof s === 'object') return s.connected ? 'online' : (s.error ?? 'offline')
  return 'unknown'
}

export function Cameras() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const ac = new AbortController()
    fetch('/api/cameras', { signal: ac.signal })
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return
        const list = Array.isArray(data) ? data : (data?.cameras ?? [])
        setCameras(Array.isArray(list) ? list : [])
        if (!data?.success && data?.error) setError(data.error)
      })
      .catch((e) => {
        if (!cancelled && e.name !== 'AbortError') setError(e.message || 'Failed to load cameras')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      ac.abort()
    }
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Cameras</h1>
      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          {error}
        </div>
      )}
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cameras.length === 0 ? (
            <p className="text-slate-500">No cameras configured.</p>
          ) : (
            cameras.map((cam, i) => {
              const key = cam.id ?? cam.name ?? `camera-${i}`
              const name = cam.name ?? cam.id ?? key
              const cameraId = (cam.name ?? cam.id ?? '').trim()
              const mjpegUrl =
                cameraId && supportsMjpegPreview(cam.type)
                  ? `/api/cameras/${encodeURIComponent(cameraId)}/mjpeg`
                  : null
              return (
                <Card key={key}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{name}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-slate-500">
                      {cam.type ?? 'camera'} · {statusLabel(cam)}
                    </p>
                    {mjpegUrl && (
                      <div className="overflow-hidden rounded-lg border border-slate-200 bg-black dark:border-slate-700">
                        <img
                          src={mjpegUrl}
                          alt={`Live preview: ${name}`}
                          className="aspect-video w-full object-contain"
                          loading="lazy"
                        />
                      </div>
                    )}
                    {(cam.type ?? '').toLowerCase() === 'webcam' && (
                      <p className="text-xs text-slate-500">
                        USB: if the preview stays black, close Teams/Zoom/OBS using the camera, or stop the
                        duplicate USB server on port 10715 so only one app captures the device.
                      </p>
                    )}
                    {supportsPtz(cam.type) && cameraId && (
                      <TapoPtzPanel cameraName={cameraId} />
                    )}
                    <div className="flex flex-wrap gap-2">
                      {mjpegUrl && (
                        <a href={mjpegUrl} target="_blank" rel="noreferrer">
                          <Button variant="outline" size="sm">Open stream (new tab)</Button>
                        </a>
                      )}
                      {cam.stream_url && (
                        <a href={cam.stream_url} target="_blank" rel="noreferrer">
                          <Button variant="outline" size="sm">RTSP / external</Button>
                        </a>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
