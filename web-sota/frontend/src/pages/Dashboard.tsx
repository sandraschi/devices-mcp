import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Video, Zap, Bell, AlertCircle, Loader2, Puzzle } from 'lucide-react'
import { getCapabilities, type CapabilitiesResponse } from '@/common/api'

interface CameraStatus {
  total: number
  online: number
  offline: number
}

interface RingStatus {
  connected: boolean
  initialized: boolean
  message: string
  two_fa_pending?: boolean
  config_issue?: boolean
}

interface SensorsResponse {
  devices: Array<{ device_id: string; name?: string; power_state?: boolean; current_power?: number; daily_energy?: number }>
  count: number
}

export function Dashboard() {
  const [cameras, setCameras] = useState<CameraStatus | null>(null)
  const [ring, setRing] = useState<RingStatus | null>(null)
  const [sensors, setSensors] = useState<SensorsResponse | null>(null)
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [camRes, ringRes, sensorsRes, capabilitiesRes] = await Promise.allSettled([
          fetch('/api/cameras/status'),
          fetch('/api/ring/status'),
          fetch('/api/sensors/tapo-p115'),
          getCapabilities(),
        ])
        if (cancelled) return
        if (camRes.status === 'fulfilled' && camRes.value.ok) {
          const data = await camRes.value.json()
          setCameras({ total: data.total ?? 0, online: data.online ?? 0, offline: data.offline ?? 0 })
        }
        if (ringRes.status === 'fulfilled' && ringRes.value.ok) {
          setRing(await ringRes.value.json())
        }
        if (sensorsRes.status === 'fulfilled' && sensorsRes.value.ok) {
          setSensors(await sensorsRes.value.json())
        }
        if (capabilitiesRes.status === 'fulfilled') {
          setCapabilities(capabilitiesRes.value)
        }
      } catch (e) {
        if (!cancelled) setError(String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertCircle className="h-5 w-5 shrink-0" />
          {error}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Cameras
            </CardTitle>
            <Video className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {cameras ? `${cameras.online}/${cameras.total}` : '—'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">online</p>
            <Link to="/cameras">
              <Button variant="ghost" size="sm" className="mt-2 px-0">View cameras</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Energy (Tapo P115)
            </CardTitle>
            <Zap className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {sensors?.count != null ? sensors.count : '—'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">plugs</p>
            <Link to="/energy">
              <Button variant="ghost" size="sm" className="mt-2 px-0">View energy</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Ring
            </CardTitle>
            <Bell className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {ring?.connected ? 'Connected' : ring?.two_fa_pending ? '2FA' : ring?.config_issue ? 'Off' : 'Not connected'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{ring?.message ?? '—'}</p>
            <Link to="/ring">
              <Button variant="ghost" size="sm" className="mt-2 px-0">Ring doorbell</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              MCP Capabilities
            </CardTitle>
            <Puzzle className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {capabilities?.tool_surface?.total ?? '—'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              tools · sampling {capabilities?.features?.sampling ? 'on' : 'off'}
            </p>
            <Link to="/mcp-capabilities">
              <Button variant="ghost" size="sm" className="mt-2 px-0">View capabilities</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
