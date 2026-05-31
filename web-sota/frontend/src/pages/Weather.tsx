import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  AlertCircle,
  BatteryWarning,
  CheckCircle,
  CloudRain,
  CloudSun,
  Droplets,
  Loader2,
  RefreshCw,
  Thermometer,
  Wind,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface ModuleData {
  name: string;
  temperature?: number | null;
  humidity?: number | null;
  co2?: number | null;
  noise?: number | null;
  pressure?: number | null;
  battery?: number | null;
  temp_trend?: string | null;
  pressure_trend?: string | null;
  health_index?: string;
}

interface ModulesResponse {
  success: boolean;
  station_id?: string;
  modules: Record<string, ModuleData>;
  timestamp?: number;
}

interface HistoryPoint {
  date: string;
  temperature?: number | null;
  humidity?: number | null;
}

interface HistoryResponse {
  success: boolean;
  history: Record<string, HistoryPoint[]>;
  days: number;
}

interface ForecastDay {
  date: string;
  temp_max?: number | null;
  temp_min?: number | null;
  precipitation?: number | null;
  wind_max?: number | null;
}

interface HourlyPoint {
  time: string;
  temperature?: number | null;
  humidity?: number | null;
}

interface ForecastResponse {
  success: boolean;
  location?: string;
  forecast: ForecastDay[];
  today_hourly: HourlyPoint[];
  days: number;
}

interface NetatmoStatus {
  enabled: boolean;
  connected: boolean;
  initialized?: boolean;
  message: string;
  config_issue?: boolean;
  needs_config?: boolean;
  needs_oauth?: boolean;
  needs_init?: boolean;
  pyatmo_available?: boolean;
  last_error?: string | null;
}

function parseErrorBody(data: unknown): string {
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: string };
    if (typeof d.detail === 'string') return d.detail;
    if (Array.isArray(d.detail))
      return d.detail
        .map((x: { msg?: string }) => x.msg ?? '')
        .filter(Boolean)
        .join('; ');
    if (d.message) return d.message;
  }
  return 'Request failed';
}

const MODULE_COLORS: Record<string, string> = {
  indoor: '#06b6d4',
  outdoor: '#f59e0b',
  extra: '#8b5cf6',
};
const MODULE_COLORS_HUMIDITY: Record<string, string> = {
  indoor: '#3b82f6',
  outdoor: '#10b981',
  extra: '#ec4899',
};

export function Weather() {
  const [searchParams, setSearchParams] = useSearchParams();
  const oauthReturnHandled = useRef(false);
  const [modules, setModules] = useState<Record<string, ModuleData> | null>(null);
  const [history, setHistory] = useState<Record<string, HistoryPoint[]> | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [netatmoStatus, setNetatmoStatus] = useState<NetatmoStatus | null>(null);
  const [netatmoInitLoading, setNetatmoInitLoading] = useState(false);
  const [netatmoOauthLoading, setNetatmoOauthLoading] = useState(false);
  const [refreshLoading, setRefreshLoading] = useState(false);

  const loadWeather = useCallback(async () => {
    try {
      const [nm, mod, hist, fc] = await Promise.all([
        fetch('/api/netatmo/status').then((r) => (r.ok ? r.json() : null)),
        fetch('/api/weather/modules').then((r) =>
          r.ok ? (r.json() as Promise<ModulesResponse>) : null,
        ),
        fetch('/api/weather/history?days=7').then((r) =>
          r.ok ? (r.json() as Promise<HistoryResponse>) : null,
        ),
        fetch('/api/weather/forecast?days=7').then((r) =>
          r.ok ? (r.json() as Promise<ForecastResponse>) : null,
        ),
      ]);
      setNetatmoStatus(nm ?? null);
      if (mod?.success) setModules(mod.modules ?? {});
      else setModules(null);
      if (hist?.success) setHistory(hist.history ?? {});
      else setHistory(null);
      if (fc?.success) setForecast(fc);
      else setForecast(null);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWeather();
    const timer = window.setInterval(loadWeather, 30000);
    return () => window.clearInterval(timer);
  }, [loadWeather]);

  useEffect(() => {
    if (searchParams.get('netatmo_oauth') === 'ok' && !oauthReturnHandled.current) {
      oauthReturnHandled.current = true;
      loadWeather();
      const next = new URLSearchParams(searchParams);
      next.delete('netatmo_oauth');
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, loadWeather]);

  const refreshWeather = async () => {
    setRefreshLoading(true);
    await loadWeather();
    setRefreshLoading(false);
  };

  const doNetatmoInit = async () => {
    setNetatmoInitLoading(true);
    setError(null);
    try {
      const r = await fetch('/api/netatmo/init', { method: 'POST' });
      const data = (await r.json().catch(() => ({}))) as {
        success?: boolean;
        message?: string;
        detail?: string;
      };
      if (!r.ok) {
        setError(parseErrorBody(data) || `HTTP ${r.status}`);
        return;
      }
      if (data.success) await loadWeather();
      else setError(data.detail ?? data.message ?? 'Netatmo connection failed');
    } catch (e) {
      setError(String(e));
    } finally {
      setNetatmoInitLoading(false);
    }
  };

  const startNetatmoOAuth = async () => {
    setNetatmoOauthLoading(true);
    setError(null);
    try {
      const r = await fetch('/api/netatmo/oauth/start');
      const data = (await r.json().catch(() => ({}))) as {
        authorize_url?: unknown;
        detail?: string;
      };
      if (!r.ok) {
        setError(parseErrorBody(data) || `HTTP ${r.status}`);
        return;
      }
      if (typeof data.authorize_url !== 'string' || !data.authorize_url) {
        setError('Netatmo did not return an authorize URL');
        return;
      }
      window.location.href = data.authorize_url;
    } catch (e) {
      setError(String(e));
    } finally {
      setNetatmoOauthLoading(false);
    }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const moduleEntries = modules ? Object.entries(modules) : [];
  const moduleOrder = ['indoor', 'outdoor'];
  const sortedEntries = moduleEntries.sort((a, b) => {
    const ai = moduleOrder.indexOf(a[0]);
    const bi = moduleOrder.indexOf(b[0]);
    if (ai >= 0 && bi >= 0) return ai - bi;
    if (ai >= 0) return -1;
    if (bi >= 0) return 1;
    return a[0].localeCompare(b[0]);
  });

  const showNetatmoSignIn =
    netatmoStatus?.enabled === true &&
    netatmoStatus?.needs_oauth === true &&
    !netatmoStatus?.connected;
  const showNetatmoConnect =
    netatmoStatus?.enabled === true &&
    !netatmoStatus?.config_issue &&
    !netatmoStatus?.needs_config &&
    netatmoStatus?.needs_oauth !== true &&
    netatmoStatus?.pyatmo_available !== false &&
    !netatmoStatus?.connected &&
    netatmoStatus?.needs_init !== false;

  const indoorCO2 = modules?.indoor?.co2 ?? null;

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-2'>
        <h1 className='text-2xl font-bold tracking-tight'>Weather</h1>
        <Button size='sm' variant='outline' onClick={refreshWeather} disabled={refreshLoading}>
          {refreshLoading ? (
            <Loader2 className='h-4 w-4 animate-spin' />
          ) : (
            <RefreshCw className='h-4 w-4' />
          )}
          <span className='ml-1'>Refresh</span>
        </Button>
      </div>

      {netatmoStatus?.enabled && (
        <Card className={netatmoStatus.connected ? 'border-green-200 dark:border-green-900' : ''}>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-base font-medium'>Netatmo weather station</CardTitle>
            {netatmoStatus.connected ? (
              <CheckCircle className='h-5 w-5 text-green-600 dark:text-green-400' />
            ) : (
              <CloudSun className='h-5 w-5 text-slate-400' />
            )}
          </CardHeader>
          <CardContent className='space-y-2'>
            <p className='text-sm'>{netatmoStatus.message}</p>
            {netatmoStatus.needs_config && (
              <p className='text-xs text-slate-500 dark:text-slate-400'>
                Create an app at{' '}
                <a
                  href='https://dev.netatmo.com/'
                  className='underline underline-offset-2'
                  target='_blank'
                  rel='noreferrer'
                >
                  dev.netatmo.com
                </a>{' '}
                and paste <code className='text-[11px]'>client_id</code> and{' '}
                <code className='text-[11px]'>client_secret</code> into{' '}
                <code className='text-[11px]'>weather.integrations.netatmo</code> in config.yaml.
              </p>
            )}
            {netatmoStatus.last_error && !netatmoStatus.connected && (
              <p className='text-xs text-amber-700 dark:text-amber-300/90'>
                {netatmoStatus.last_error}
              </p>
            )}
            {showNetatmoSignIn && (
              <div className='space-y-2'>
                <Button type='button' onClick={startNetatmoOAuth} disabled={netatmoOauthLoading}>
                  {netatmoOauthLoading ? 'Opening Netatmo…' : 'Sign in with Netatmo'}
                </Button>
              </div>
            )}
            {showNetatmoConnect && (
              <Button type='button' onClick={doNetatmoInit} disabled={netatmoInitLoading}>
                {netatmoInitLoading ? 'Connecting…' : 'Connect Netatmo'}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {netatmoStatus && !netatmoStatus.enabled && (
        <Card>
          <CardHeader className='pb-2'>
            <CardTitle className='text-base font-medium'>Netatmo weather station</CardTitle>
          </CardHeader>
          <CardContent>
            <p className='text-sm text-slate-600 dark:text-slate-400'>{netatmoStatus.message}</p>
          </CardContent>
        </Card>
      )}

      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}

      {indoorCO2 != null && indoorCO2 >= 1000 && (
        <div className='rounded-lg border border-orange-300 bg-orange-50 p-4 text-sm text-orange-950 dark:border-orange-800 dark:bg-orange-950/30 dark:text-orange-100'>
          <p className='font-medium'>Indoor CO₂ {Math.round(indoorCO2)} ppm — check ventilation</p>
          <p className='mt-1 text-orange-900/90 dark:text-orange-200/90'>
            Sustained high CO₂ is a health issue. Open windows or increase airflow.{' '}
            <Link to='/alarms' className='font-medium underline underline-offset-2'>
              Alarms
            </Link>
          </p>
        </div>
      )}

      {sortedEntries.length > 0 && (
        <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
          {sortedEntries.map(([key, mod]) => (
            <Card key={key}>
              <CardHeader className='flex flex-row items-center justify-between pb-2'>
                <CardTitle className='text-base'>
                  {mod.name ?? key}
                  {mod.temp_trend && <span className='ml-1 text-sm'>↗</span>}
                </CardTitle>
                {mod.battery != null && mod.battery <= 20 && (
                  <BatteryWarning className='h-4 w-4 text-amber-500' />
                )}
              </CardHeader>
              <CardContent className='space-y-2 text-sm'>
                <div className='flex items-center gap-2'>
                  <Thermometer className='h-4 w-4 text-slate-500' />
                  <span className='text-2xl font-semibold'>
                    {mod.temperature?.toFixed(1) ?? '—'}°C
                  </span>
                </div>
                {mod.humidity != null && (
                  <p className='flex items-center gap-1 text-slate-600 dark:text-slate-400'>
                    <Droplets className='h-3.5 w-3.5' />
                    {mod.humidity}% humidity
                  </p>
                )}
                {mod.co2 != null && (
                  <p className='text-slate-600 dark:text-slate-400'>
                    CO₂ {Math.round(mod.co2)} ppm
                  </p>
                )}
                {mod.pressure != null && (
                  <p className='text-slate-600 dark:text-slate-400'>
                    {mod.pressure.toFixed(1)} hPa
                  </p>
                )}
                {mod.noise != null && (
                  <p className='text-slate-600 dark:text-slate-400'>{mod.noise} dB</p>
                )}
                {mod.battery != null && (
                  <p className='text-xs text-slate-500'>Battery {mod.battery}%</p>
                )}
                {mod.health_index && (
                  <p className='text-xs text-slate-500'>Air: {mod.health_index}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {history && Object.keys(history).length > 0 && (
        <Card>
          <CardHeader className='pb-2'>
            <CardTitle className='text-base'>Temperature history (7 days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='h-[280px] w-full'>
              <ResponsiveContainer width='100%' height='100%'>
                <LineChart margin={{ top: 8, right: 8, left: 0, bottom: 24 }}>
                  <CartesianGrid
                    strokeDasharray='3 3'
                    className='stroke-slate-200 dark:stroke-slate-700'
                  />
                  <XAxis
                    dataKey='date'
                    tick={{ fontSize: 11 }}
                    className='text-slate-500'
                    allowDuplicatedCategory={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    className='text-slate-500'
                    tickFormatter={(v) => `${v}°C`}
                  />
                  <Tooltip
                    formatter={(v: number, name: string) => [`${v}°C`, name]}
                    contentStyle={{ borderRadius: '8px' }}
                  />
                  <Legend />
                  {Object.entries(history).map(([key, points]) => {
                    const color = MODULE_COLORS[key] ?? '#8884d8';
                    const name = modules?.[key]?.name ?? key;
                    return (
                      <Line
                        key={`t_${key}`}
                        data={points}
                        dataKey='temperature'
                        name={`${name} °C`}
                        stroke={color}
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        connectNulls
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {history && Object.keys(history).length > 0 && (
        <Card>
          <CardHeader className='pb-2'>
            <CardTitle className='text-base'>Humidity history (7 days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='h-[280px] w-full'>
              <ResponsiveContainer width='100%' height='100%'>
                <LineChart margin={{ top: 8, right: 8, left: 0, bottom: 24 }}>
                  <CartesianGrid
                    strokeDasharray='3 3'
                    className='stroke-slate-200 dark:stroke-slate-700'
                  />
                  <XAxis
                    dataKey='date'
                    tick={{ fontSize: 11 }}
                    className='text-slate-500'
                    allowDuplicatedCategory={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    className='text-slate-500'
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    formatter={(v: number, name: string) => [`${v}%`, name]}
                    contentStyle={{ borderRadius: '8px' }}
                  />
                  <Legend />
                  {Object.entries(history).map(([key, points]) => {
                    const color = MODULE_COLORS_HUMIDITY[key] ?? '#82ca9d';
                    const name = modules?.[key]?.name ?? key;
                    return (
                      <Line
                        key={`h_${key}`}
                        data={points}
                        dataKey='humidity'
                        name={`${name} %`}
                        stroke={color}
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        connectNulls
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {forecast?.forecast && forecast.forecast.length > 0 && (
        <>
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-base'>
                <span className='flex items-center gap-2'>
                  <CloudSun className='h-4 w-4' />
                  Vienna forecast ({forecast.days} days)
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead>
                    <tr className='border-b border-slate-200 text-left text-xs uppercase text-slate-500 dark:border-slate-700'>
                      <th className='py-1 pr-3'>Day</th>
                      <th className='py-1 pr-3'>
                        <Thermometer className='inline h-3 w-3' /> Max
                      </th>
                      <th className='py-1 pr-3'>
                        <Thermometer className='inline h-3 w-3' /> Min
                      </th>
                      <th className='py-1 pr-3'>
                        <CloudRain className='inline h-3 w-3' /> Rain
                      </th>
                      <th className='py-1'>
                        <Wind className='inline h-3 w-3' /> Wind
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.forecast.map((d, i) => (
                      <tr
                        key={d.date}
                        className={`border-b border-slate-100 dark:border-slate-800 ${i === 0 ? 'font-medium' : ''}`}
                      >
                        <td className='py-1 pr-3'>
                          {i === 0
                            ? 'Today'
                            : new Date(`${d.date}T00:00:00`).toLocaleDateString('en', {
                                weekday: 'short',
                                month: 'short',
                                day: 'numeric',
                              })}
                        </td>
                        <td className='py-1 pr-3 text-emerald-600 dark:text-emerald-400'>
                          {d.temp_max?.toFixed(1) ?? '—'}°
                        </td>
                        <td className='py-1 pr-3 text-sky-600 dark:text-sky-400'>
                          {d.temp_min?.toFixed(1) ?? '—'}°
                        </td>
                        <td className='py-1 pr-3'>
                          {d.precipitation != null ? `${d.precipitation.toFixed(1)}mm` : '—'}
                        </td>
                        <td className='py-1'>
                          {d.wind_max != null ? `${d.wind_max.toFixed(0)} km/h` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {forecast.today_hourly.length > 0 && (
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-base'>Today hourly</CardTitle>
              </CardHeader>
              <CardContent>
                <div className='h-[220px] w-full'>
                  <ResponsiveContainer width='100%' height='100%'>
                    <LineChart margin={{ top: 8, right: 8, left: 0, bottom: 24 }}>
                      <CartesianGrid
                        strokeDasharray='3 3'
                        className='stroke-slate-200 dark:stroke-slate-700'
                      />
                      <XAxis
                        dataKey='time'
                        tick={{ fontSize: 10 }}
                        interval={3}
                        className='text-slate-500'
                      />
                      <YAxis
                        yAxisId='left'
                        tick={{ fontSize: 10 }}
                        className='text-slate-500'
                        tickFormatter={(v) => `${v}°C`}
                      />
                      <YAxis
                        yAxisId='right'
                        orientation='right'
                        tick={{ fontSize: 10 }}
                        className='text-slate-500'
                        tickFormatter={(v) => `${v}%`}
                      />
                      <Tooltip contentStyle={{ borderRadius: '8px' }} />
                      <Legend />
                      <Line
                        yAxisId='left'
                        data={forecast.today_hourly}
                        dataKey='temperature'
                        name='Temp °C'
                        stroke='#f59e0b'
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        yAxisId='right'
                        data={forecast.today_hourly}
                        dataKey='humidity'
                        name='Humidity %'
                        stroke='#3b82f6'
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {sortedEntries.length === 0 && !error && (
        <p className='text-slate-500'>No module data. Ensure Netatmo is connected and reporting.</p>
      )}
    </div>
  );
}
