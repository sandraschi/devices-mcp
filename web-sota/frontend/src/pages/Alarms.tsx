import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Shield, Loader2, AlertCircle, CheckCircle, Bell, AlertTriangle } from 'lucide-react'

interface RingStatus {
  connected: boolean
  initialized: boolean
  enabled: boolean
  message: string
}

interface PublicAlert {
  id: string
  source: string
  alert_type: string
  severity: string
  severity_color?: string
  severity_icon?: string
  title: string
  description: string
  region?: string
  is_active?: boolean
}

interface AlarmStatus {
  alarm: {
    mode?: string
    mode_name?: string
    is_armed?: boolean
    sensors?: { name?: string; sensor_type?: string; faulted?: boolean }[]
    base_station?: { name?: string; battery_level?: string }
    keypads?: unknown[]
  } | null
  message?: string
}

export function Alarms() {
  const [ringStatus, setRingStatus] = useState<RingStatus | null>(null)
  const [alarm, setAlarm] = useState<AlarmStatus | null>(null)
  const [airAlerts, setAirAlerts] = useState<PublicAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [settingMode, setSettingMode] = useState<string | null>(null)

  const load = async () => {
    try {
      const [statusRes, alarmRes, alertsRes] = await Promise.allSettled([
        fetch('/api/ring/status'),
        fetch('/api/ring/alarm').catch(() => ({ ok: false, json: () => ({ alarm: null }) })),
        fetch('/alerts/all?use_cache=false'),
      ])
      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        setRingStatus(await statusRes.value.json())
      } else if (statusRes.status === 'fulfilled') {
        setRingStatus(await statusRes.value.json())
      }
      if (alarmRes.status === 'fulfilled' && alarmRes.value.ok) {
        setAlarm(await alarmRes.value.json())
      } else if (alarmRes.status === 'fulfilled' && !alarmRes.value.ok) {
        const raw = alarmRes.value as { json: () => unknown }
        const err = (await Promise.resolve(raw.json()).catch(() => ({}))) as { detail?: string }
        setAlarm({ alarm: null, message: err?.detail ?? 'Unavailable' })
      }
      if (alertsRes.status === 'fulfilled' && alertsRes.value.ok) {
        const data = (await alertsRes.value.json()) as { alerts?: PublicAlert[] }
        const all = data.alerts ?? []
        setAirAlerts(
          all.filter(
            (a) =>
              a.source === 'netatmo' ||
              (typeof a.id === 'string' && a.id.startsWith('netatmo_co2')),
          ),
        )
      } else {
        setAirAlerts([])
      }
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const setAlarmMode = async (mode: string) => {
    setSettingMode(mode)
    try {
      const r = await fetch('/api/ring/alarm/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      })
      if (r.ok) await load()
      else setError((await r.json()).detail ?? 'Failed to set mode')
    } catch (e) {
      setError(String(e))
    } finally {
      setSettingMode(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  const alarmData = alarm?.alarm
  const mode = alarmData?.mode ?? 'disarmed'
  const modes = [
    { id: 'disarmed', label: 'Disarm', variant: 'outline' as const },
    { id: 'home', label: 'Home', variant: 'outline' as const },
    { id: 'away', label: 'Away', variant: 'default' as const },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Alarms</h1>
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertCircle className="h-5 w-5 shrink-0" />
          {error}
        </div>
      )}

      {airAlerts.length > 0 && (
        <Card className="border-orange-300 dark:border-orange-800">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base font-medium">
              <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              Indoor air (Netatmo CO₂)
            </CardTitle>
            <p className="text-xs font-normal text-slate-500 dark:text-slate-400">
              High CO₂ means poor ventilation — not only headaches, but real risk if it stays high for
              hours or days, especially with several people in a small flat.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {airAlerts.map((a) => (
              <div
                key={a.id}
                className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                style={
                  a.severity_color
                    ? { borderLeftWidth: 4, borderLeftColor: a.severity_color }
                    : undefined
                }
              >
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{a.title}</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{a.description}</p>
                {a.region && (
                  <p className="mt-1 text-xs text-slate-500">{a.region}</p>
                )}
              </div>
            ))}
            <p className="text-xs text-slate-500">
              Same entries appear in{' '}
              <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">/alerts/summary</code> with
              weather alerts. Ventilate and recheck the Weather page for live ppm.
            </p>
          </CardContent>
        </Card>
      )}

      {!ringStatus?.enabled && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Ring integration is disabled. Enable it in config to use alarm controls.
            </p>
          </CardContent>
        </Card>
      )}
      {ringStatus?.enabled && !ringStatus?.connected && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-slate-600 dark:text-slate-400">{ringStatus.message}</p>
            <p className="mt-2 text-xs text-slate-500">Initialize Ring from the Ring Doorbell page.</p>
          </CardContent>
        </Card>
      )}
      {ringStatus?.connected && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Shield className="h-5 w-5" /> Ring Alarm
            </CardTitle>
            {alarmData && (
              <span className="flex items-center gap-1 text-sm text-slate-500">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                Connected
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {!alarmData && (
              <p className="text-sm text-slate-500">
                No alarm system found for this account. {alarm?.message ?? ''}
              </p>
            )}
            {alarmData && (
              <>
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Mode</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {modes.map(({ id, label, variant }) => (
                      <Button
                        key={id}
                        size="sm"
                        variant={mode === id ? 'default' : variant}
                        disabled={settingMode !== null}
                        onClick={() => setAlarmMode(id)}
                      >
                        {settingMode === id ? '…' : label}
                      </Button>
                    ))}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Current: {alarmData.mode_name ?? alarmData.mode ?? 'disarmed'}
                  </p>
                </div>
                {alarmData.sensors && alarmData.sensors.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Sensors</p>
                    <ul className="mt-1 list-inside list-disc text-sm text-slate-600 dark:text-slate-400">
                      {alarmData.sensors.slice(0, 10).map((s, i) => (
                        <li key={i}>
                          {s.name ?? s.sensor_type ?? 'Sensor'} {s.faulted ? '(faulted)' : ''}
                        </li>
                      ))}
                      {alarmData.sensors.length > 10 && (
                        <li className="text-slate-500">+{alarmData.sensors.length - 10} more</li>
                      )}
                    </ul>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
      <Card>
        <CardContent className="flex items-start gap-3 pt-6">
          <Bell className="h-5 w-5 shrink-0 text-slate-500" />
          <div className="text-sm text-slate-600 dark:text-slate-400">
            <p className="font-medium text-slate-800 dark:text-slate-200">Security alarms</p>
            <p>
              Ring Alarm mode (disarm / home / away) and sensors are shown above when Ring is connected.
              For doorbell and motion events, see the Ring Doorbell page. Netatmo CO₂ warnings (when
              configured) appear above as indoor-air alerts and share the public alerts feed.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
