import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  CloudRain,
  Loader2,
  AlertCircle,
  Thermometer,
  Wind,
  Droplets,
  CheckCircle,
  CloudSun,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'

interface CurrentWeather {
  weather?: {
    temperature?: number
    feels_like?: number
    humidity?: number
    pressure?: number
    wind_speed?: number
    wind_direction?: number
    condition?: string
    location?: string
    timestamp?: string
    sunrise?: string
    sunset?: string
    co2_ppm?: number | null
    noise_db?: number | null
  }
  success?: boolean
}

interface WeatherStations {
  stations?: Array<{ name?: string; id?: string; station_id?: string; [key: string]: unknown }>
  success?: boolean
}

interface ForecastDay {
  date?: string
  day?: string
  temp?: number
  temp_min?: number
  temp_max?: number
  temperature?: number
}

interface HistoryDay {
  date?: string
  day?: string
  temp?: number
  temperature?: number
}

interface NetatmoStatus {
  enabled: boolean
  connected: boolean
  initialized?: boolean
  message: string
  config_issue?: boolean
  needs_config?: boolean
  needs_oauth?: boolean
  needs_init?: boolean
  pyatmo_available?: boolean
  last_error?: string | null
}

function parseErrorBody(data: unknown): string {
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: string }
    if (typeof d.detail === 'string') return d.detail
    if (Array.isArray(d.detail))
      return d.detail
        .map((x: { msg?: string }) => x.msg ?? '')
        .filter(Boolean)
        .join('; ')
    if (d.message) return d.message
  }
  return 'Request failed'
}

export function Weather() {
  const [searchParams, setSearchParams] = useSearchParams()
  const oauthReturnHandled = useRef(false)
  const [current, setCurrent] = useState<CurrentWeather | null>(null)
  const [stations, setStations] = useState<WeatherStations | null>(null)
  const [forecast, setForecast] = useState<ForecastDay[]>([])
  const [history, setHistory] = useState<HistoryDay[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [netatmoStatus, setNetatmoStatus] = useState<NetatmoStatus | null>(null)
  const [netatmoInitLoading, setNetatmoInitLoading] = useState(false)
  const [netatmoOauthLoading, setNetatmoOauthLoading] = useState(false)
  const [dataRefreshKey, setDataRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch('/api/netatmo/status').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/weather/current').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/weather/stations').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/weather/forecast?days=5').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/weather/history?days=7').then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([nm, cur, st, fc, hist]) => {
        if (!cancelled) {
          setNetatmoStatus(nm ?? null)
          setCurrent(cur ?? null)
          setStations(st ?? null)
          setForecast(Array.isArray(fc?.forecast) ? fc.forecast : [])
          setHistory(Array.isArray(hist?.history) ? hist.history : [])
        }
      })
      .catch((e) => {
        if (!cancelled) setError(String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [dataRefreshKey])

  const refreshWeatherData = () => setDataRefreshKey((k) => k + 1)

  useEffect(() => {
    // After Netatmo OAuth callback, backend redirects to /app/weather?netatmo_oauth=ok.
    // When this query flag appears, refresh dashboard data once.
    if (searchParams.get('netatmo_oauth') === 'ok' && !oauthReturnHandled.current) {
      oauthReturnHandled.current = true
      refreshWeatherData()
      const next = new URLSearchParams(searchParams)
      next.delete('netatmo_oauth')
      setSearchParams(next, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const doNetatmoInit = async () => {
    setNetatmoInitLoading(true)
    setError(null)
    try {
      const r = await fetch('/api/netatmo/init', { method: 'POST' })
      const data = (await r.json().catch(() => ({}))) as {
        success?: boolean
        message?: string
        detail?: string
      }
      if (!r.ok) {
        setError(parseErrorBody(data) || `HTTP ${r.status}`)
        return
      }
      if (data.success) refreshWeatherData()
      else setError(data.detail ?? data.message ?? 'Netatmo connection failed')
    } catch (e) {
      setError(String(e))
    } finally {
      setNetatmoInitLoading(false)
    }
  }

  const startNetatmoOAuth = async () => {
    setNetatmoOauthLoading(true)
    setError(null)
    try {
      const r = await fetch('/api/netatmo/oauth/start')
      const data = (await r.json().catch(() => ({}))) as {
        authorize_url?: unknown
        redirect_uri_used?: unknown
        hint?: unknown
        detail?: string
      }
      if (!r.ok) {
        setError(parseErrorBody(data) || `HTTP ${r.status}`)
        return
      }

      if (typeof data.authorize_url !== 'string' || !data.authorize_url) {
        setError('Netatmo did not return an authorize URL')
        return
      }

      window.location.href = data.authorize_url
    } catch (e) {
      setError(String(e))
    } finally {
      setNetatmoOauthLoading(false)
    }
  }

  const runNetatmoInit = async () => {
    await doNetatmoInit()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  const w = current?.weather

  const forecastChartData = forecast.map((d) => ({
    label: d.date ?? d.day ?? '',
    temp: d.temp ?? d.temperature ?? d.temp_max ?? d.temp_min ?? 0,
  })).filter((d) => d.label)

  const historyChartData = history.map((d) => ({
    label: d.date ?? d.day ?? '',
    temp: d.temp ?? d.temperature ?? 0,
  })).filter((d) => d.label)

  const showNetatmoSignIn =
    netatmoStatus?.enabled === true &&
    netatmoStatus?.needs_oauth === true &&
    !netatmoStatus?.connected

  const showNetatmoConnect =
    netatmoStatus?.enabled === true &&
    !netatmoStatus?.config_issue &&
    !netatmoStatus?.needs_config &&
    netatmoStatus?.needs_oauth !== true &&
    netatmoStatus?.pyatmo_available !== false &&
    !netatmoStatus?.connected &&
    netatmoStatus?.needs_init !== false

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Weather</h1>
      {netatmoStatus && netatmoStatus.enabled && (
        <Card
          className={
            netatmoStatus.connected ? 'border-green-200 dark:border-green-900' : ''
          }
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base font-medium">Netatmo weather station</CardTitle>
            {netatmoStatus.connected ? (
              <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
            ) : (
              <CloudSun className="h-5 w-5 text-slate-400" />
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">{netatmoStatus.message}</p>
            {netatmoStatus.needs_config && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Create an app at{' '}
                <a
                  href="https://dev.netatmo.com/"
                  className="underline underline-offset-2"
                  target="_blank"
                  rel="noreferrer"
                >
                  dev.netatmo.com
                </a>{' '}
                and paste <code className="text-[11px]">client_id</code> and{' '}
                <code className="text-[11px]">client_secret</code> into{' '}
                <code className="text-[11px]">weather.integrations.netatmo</code> in config.yaml.
              </p>
            )}
            {netatmoStatus.last_error && !netatmoStatus.connected && (
              <p className="text-xs text-amber-700 dark:text-amber-300/90">
                {netatmoStatus.last_error}
              </p>
            )}
            {showNetatmoSignIn && (
              <div className="space-y-2">
                <Button
                  type="button"
                  onClick={startNetatmoOAuth}
                  disabled={netatmoOauthLoading}
                >
                  {netatmoOauthLoading ? 'Opening Netatmo…' : 'Sign in with Netatmo'}
                </Button>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  You will log in on Netatmo’s site. The app must list the exact callback URL the API
                  uses — if sign-in fails, set <code className="text-[11px]">oauth_callback_url</code> in
                  config to match your Netatmo application (see{' '}
                  <a
                    href="https://dev.netatmo.com/"
                    className="underline underline-offset-2"
                    target="_blank"
                    rel="noreferrer"
                  >
                    dev.netatmo.com
                  </a>
                  ).
                </p>
              </div>
            )}
            {showNetatmoConnect && (
              <Button type="button" onClick={runNetatmoInit} disabled={netatmoInitLoading}>
                {netatmoInitLoading ? 'Connecting…' : 'Connect Netatmo'}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
      {netatmoStatus && !netatmoStatus.enabled && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Netatmo weather station</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600 dark:text-slate-400">{netatmoStatus.message}</p>
          </CardContent>
        </Card>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertCircle className="h-5 w-5 shrink-0" />
          {error}
        </div>
      )}
      {w && w.co2_ppm != null && w.co2_ppm >= 1000 && (
        <div className="rounded-lg border border-orange-300 bg-orange-50 p-4 text-sm text-orange-950 dark:border-orange-800 dark:bg-orange-950/30 dark:text-orange-100">
          <p className="font-medium">Indoor CO₂ {Math.round(w.co2_ppm)} ppm — check ventilation</p>
          <p className="mt-1 text-orange-900/90 dark:text-orange-200/90">
            Sustained high CO₂ is a health issue in small spaces with several people, not only a comfort
            problem. Open windows or increase airflow; details and severity bands are on{' '}
            <Link to="/alarms" className="font-medium underline underline-offset-2">
              Alarms
            </Link>
            .
          </p>
        </div>
      )}
      {w && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base">{w.location ?? 'Current weather'}</CardTitle>
            <CloudRain className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <Thermometer className="h-4 w-4 text-slate-500" />
              <span className="text-2xl font-semibold">{w.temperature ?? '—'}°C</span>
              {w.feels_like != null && (
                <span className="text-slate-500">Feels like {w.feels_like}°C</span>
              )}
            </div>
            <p className="capitalize text-slate-600 dark:text-slate-400">
              {w.condition?.replace(/-/g, ' ') ?? '—'}
            </p>
            <div className="flex flex-wrap gap-4">
              {w.humidity != null && (
                <span className="flex items-center gap-1">
                  <Droplets className="h-4 w-4" />
                  {w.humidity}% humidity
                </span>
              )}
              {w.pressure != null && <span>{w.pressure} hPa</span>}
              {w.co2_ppm != null && (
                <span className="text-slate-600 dark:text-slate-400">CO₂ {Math.round(w.co2_ppm)} ppm</span>
              )}
              {w.wind_speed != null && (
                <span className="flex items-center gap-1">
                  <Wind className="h-4 w-4" />
                  {w.wind_speed} km/h
                </span>
              )}
            </div>
            {w.sunrise && w.sunset && (
              <p className="text-slate-500">Sunrise {w.sunrise} · Sunset {w.sunset}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Forecast timeline */}
      {forecastChartData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Forecast (next {forecastChartData.length} days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={forecastChartData} margin={{ top: 8, right: 8, left: 0, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} className="text-slate-500" />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    className="text-slate-500"
                    tickFormatter={(v) => `${v}°C`}
                  />
                  <Tooltip
                    formatter={(v: number) => [`${v}°C`, 'Temp']}
                    contentStyle={{ borderRadius: '8px' }}
                  />
                  <Bar dataKey="temp" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Temp" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* History timeline */}
      {historyChartData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Temperature history (past {historyChartData.length} days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyChartData} margin={{ top: 8, right: 8, left: 0, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} className="text-slate-500" />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    className="text-slate-500"
                    tickFormatter={(v) => `${v}°C`}
                  />
                  <Tooltip
                    formatter={(v: number) => [`${v}°C`, 'Temp']}
                    contentStyle={{ borderRadius: '8px' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="temp"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Temp"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {stations?.stations && stations.stations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Stations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-inside list-disc text-sm text-slate-600 dark:text-slate-400">
              {stations.stations.map((s, i) => (
                <li key={String(s.station_id ?? s.id ?? s.name ?? i)}>
                  <span>{s.name ?? s.station_id ?? s.id ?? 'Station'}</span>
                  {Array.isArray((s as any).modules) && (s as any).modules.length > 0 && (
                    <ul className="mt-2 list-inside list-disc pl-4 text-xs text-slate-500">
                      {(s as any).modules.map((m: any, j: number) => (
                        <li key={String(m.module_id ?? m.name ?? j)}>
                          {m.name ?? m.module_id ?? 'Module'} {m.type ? `(${m.type})` : ''}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
      {!w && !error && forecastChartData.length === 0 && historyChartData.length === 0 && (
        <p className="text-slate-500">No weather data. Configure Netatmo or weather tools in config.</p>
      )}
    </div>
  )
}
