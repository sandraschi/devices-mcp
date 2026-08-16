import { type CapabilitiesResponse, getCapabilities } from '@/common/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Activity,
  AlertCircle,
  Bell,
  Bot,
  CloudRain,
  Flame,
  Lightbulb,
  Loader2,
  Puzzle,
  RefreshCcw,
  Video,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface CameraStatus {
  total: number;
  online: number;
  offline: number;
}

interface RingStatus {
  connected: boolean;
  initialized: boolean;
  message: string;
  two_fa_pending?: boolean;
  config_issue?: boolean;
}

interface SensorsResponse {
  devices: Array<{
    device_id: string;
    name?: string;
    power_state?: boolean;
    current_power?: number;
    daily_energy?: number;
  }>;
  count: number;
}

interface AlertSummary {
  total_alerts: number;
  highest_severity: string;
  highest_severity_color: string;
  status: string;
  alerts: Array<{
    id: string;
    title: string;
    severity: string;
    severity_color: string;
    source: string;
    alert_type: string;
    description: string;
  }>;
}

interface NestStatus {
  initialized?: boolean;
  total_devices?: number;
  all_ok?: boolean;
  error?: string;
}

interface NetatmoStatus {
  enabled?: boolean;
  connected?: boolean;
  initialized?: boolean;
  message?: string;
  needs_reconnect?: boolean;
  reconnect_url?: string;
}

interface HueStatus {
  connected?: boolean;
  bridge_name?: string;
  lights_count?: number;
  requires_https?: boolean;
  message?: string;
}

interface ReconnectResult {
  status?: string;
  hue?: { ok?: boolean; connected?: boolean; lights_count?: number; message?: string };
  netatmo?: { ok?: boolean; connected?: boolean; message?: string; reconnect_url?: string };
}

function kpiValue(value: string | number | undefined, fallback = '—') {
  return value === undefined || value === null || value === '' ? fallback : value;
}

export function Dashboard() {
  const [cameras, setCameras] = useState<CameraStatus | null>(null);
  const [ring, setRing] = useState<RingStatus | null>(null);
  const [nest, setNest] = useState<NestStatus | null>(null);
  const [weather, setWeather] = useState<NetatmoStatus | null>(null);
  const [hue, setHue] = useState<HueStatus | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  const [sensors, setSensors] = useState<SensorsResponse | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectNote, setReconnectNote] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [camRes, ringRes, nestRes, sensorsRes, capabilitiesRes, alertsRes, weatherRes, hueRes] =
        await Promise.allSettled([
          fetch('/api/cameras/status'),
          fetch('/api/ring/status'),
          fetch('/api/nest/status'),
          fetch('/api/sensors/tapo-p115'),
          getCapabilities(),
          fetch('/alerts/summary'),
          fetch('/api/netatmo/status'),
          fetch('/api/lighting/hue/status'),
        ]);
      if (camRes.status === 'fulfilled' && camRes.value.ok) {
        const data = await camRes.value.json();
        setCameras({
          total: data.total ?? 0,
          online: data.online ?? 0,
          offline: data.offline ?? 0,
        });
      }
      if (ringRes.status === 'fulfilled' && ringRes.value.ok) {
        setRing(await ringRes.value.json());
      }
      if (nestRes.status === 'fulfilled' && nestRes.value.ok) {
        setNest(await nestRes.value.json());
      }
      if (sensorsRes.status === 'fulfilled' && sensorsRes.value.ok) {
        setSensors(await sensorsRes.value.json());
      }
      if (capabilitiesRes.status === 'fulfilled') {
        setCapabilities(capabilitiesRes.value);
      }
      if (alertsRes.status === 'fulfilled' && alertsRes.value.ok) {
        setAlerts(await alertsRes.value.json());
      }
      if (weatherRes.status === 'fulfilled' && weatherRes.value.ok) {
        setWeather(await weatherRes.value.json());
      }
      if (hueRes.status === 'fulfilled' && hueRes.value.ok) {
        setHue(await hueRes.value.json());
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const checkBackend = useCallback(async () => {
    try {
      const r = await fetch('/api/health', { signal: AbortSignal.timeout(5000) });
      setBackendOk(r.ok);
    } catch {
      setBackendOk(false);
    }
  }, []);

  const reconnectServices = useCallback(async () => {
    setReconnecting(true);
    setReconnectNote(null);
    try {
      const r = await fetch('/api/system/reconnect', {
        method: 'POST',
        signal: AbortSignal.timeout(60000),
      });
      const data = (await r.json()) as ReconnectResult;
      const notes: string[] = [];
      if (data.hue) notes.push(`Hue: ${data.hue.message ?? '—'}`);
      if (data.netatmo) notes.push(`Netatmo: ${data.netatmo.message ?? '—'}`);
      setReconnectNote(notes.join(' · '));
    } catch (e) {
      setReconnectNote(`Reconnect failed: ${String(e)}`);
    } finally {
      setReconnecting(false);
      await Promise.all([loadAll(), checkBackend()]);
    }
  }, [loadAll, checkBackend]);

  useEffect(() => {
    loadAll();
    checkBackend();
    const interval = setInterval(checkBackend, 15000);
    return () => clearInterval(interval);
  }, [loadAll, checkBackend]);

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const weatherConnected = weather?.connected === true;
  const hueConnected = hue?.connected === true;
  const alertActive =
    alerts?.total_alerts != null && alerts.total_alerts > 0 && alerts.status !== 'ok';
  const onlinePlugs = sensors?.devices?.filter((d) => d.power_state === true).length ?? 0;
  const totalPower = sensors?.devices?.reduce((acc, d) => acc + (d.current_power ?? 0), 0) ?? 0;
  const totalDailyEnergy =
    sensors?.devices?.reduce((acc, d) => acc + (d.daily_energy ?? 0), 0) ?? 0;

  return (
    <div data-testid='dashboard' className='space-y-6'>
      {/* Hero */}
      <section className='relative overflow-hidden rounded-xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-6 md:p-8'>
        <div className='pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl' />
        <div className='pointer-events-none absolute -bottom-20 -left-10 h-64 w-64 rounded-full bg-amber-500/10 blur-3xl' />
        <div className='relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between'>
          <div className='max-w-xl'>
            <p className='mb-2 flex items-center gap-2 text-xs font-medium tracking-widest text-amber-400 uppercase'>
              <Activity className='h-3.5 w-3.5' />
              Devices MCP
            </p>
            <h1 className='text-3xl font-bold tracking-tight text-white md:text-4xl'>
              Your home, supervised
            </h1>
            <p className='mt-3 text-sm leading-relaxed text-slate-400'>
              Cameras, energy, lighting, weather and safety — one live control plane for the whole
              house.
            </p>
          </div>
          <div className='flex shrink-0 flex-wrap items-center gap-2'>
            <span
              data-testid='backend-dot'
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
                backendOk === null
                  ? 'border-slate-700 text-slate-400'
                  : backendOk
                    ? 'border-green-800 bg-green-950/30 text-green-300'
                    : 'border-red-800 bg-red-950/30 text-red-300'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  backendOk === null ? 'bg-slate-500' : backendOk ? 'bg-green-500' : 'bg-red-500'
                } animate-pulse`}
              />
              {backendOk === null
                ? 'Connecting…'
                : backendOk
                  ? 'Backend online'
                  : 'Backend offline'}
            </span>
            <Button
              variant='outline'
              size='sm'
              className='border-slate-700 text-slate-200 hover:bg-slate-800'
              onClick={reconnectServices}
              disabled={reconnecting}
              data-testid='reconnect-services'
            >
              <RefreshCcw className={`mr-1.5 h-3.5 w-3.5 ${reconnecting ? 'animate-spin' : ''}`} />
              {reconnecting ? 'Reconnecting…' : 'Reconnect services'}
            </Button>
            <Link to='/cameras'>
              <Button variant='default' className='bg-amber-500 text-slate-950 hover:bg-amber-400'>
                <Video className='mr-2 h-4 w-4' />
                View cameras
              </Button>
            </Link>
          </div>
        </div>
        {reconnectNote && (
          <div className='relative mt-4 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs text-slate-300'>
            {reconnectNote}
          </div>
        )}
      </section>

      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-900 bg-amber-950/30 p-4 text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      {alertActive && (
        <div
          className={`rounded-lg border p-4 text-sm ${
            alerts.highest_severity === 'extreme' || alerts.highest_severity === 'severe'
              ? 'border-red-800 bg-red-950/30 text-red-200'
              : 'border-amber-800 bg-amber-950/30 text-amber-200'
          }`}
        >
          <div className='flex items-center gap-2 font-medium'>
            <CloudRain className='h-4 w-4' />
            {alerts.total_alerts} active alert
            {alerts.total_alerts !== 1 ? 's' : ''}
            {alerts.alerts.slice(0, 3).map((a) => (
              <span key={a.id} className='font-normal text-xs ml-2'>
                {a.title}
              </span>
            ))}
          </div>
          <Link
            to='/alarms'
            className='mt-1 block text-xs underline underline-offset-2 opacity-70 hover:opacity-100'
          >
            View all
          </Link>
        </div>
      )}

      {/* KPI grid */}
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4' data-testid='kpi-grid'>
        <Card data-testid='kpi-cameras'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Cameras</CardTitle>
            <Video className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>
              {kpiValue(cameras ? `${cameras.online}/${cameras.total}` : undefined)}
            </p>
            <p className='text-xs text-slate-400'>online / total</p>
            <Link to='/cameras'>
              <Button variant='ghost' size='sm' className='mt-2 px-0'>
                View cameras
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card data-testid='kpi-energy'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Energy (Tapo P115)</CardTitle>
            <Zap className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>
              {kpiValue(onlinePlugs ? `${onlinePlugs}/${sensors?.count}` : sensors?.count)}
            </p>
            <p className='text-xs text-slate-400'>on / plugs · {totalPower.toFixed(1)} W now</p>
            <div className='mt-2 space-y-1'>
              {(sensors?.devices ?? []).slice(0, 4).map((d) => (
                <div key={d.device_id} className='flex items-center justify-between text-xs'>
                  <span className='flex items-center gap-1.5 text-slate-300'>
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        d.power_state ? 'bg-green-500' : 'bg-slate-600'
                      }`}
                    />
                    {d.name ?? d.device_id}
                  </span>
                  <span className='text-slate-400'>
                    {d.current_power != null ? `${d.current_power.toFixed(1)} W` : '—'}
                    {d.daily_energy != null ? ` · ${d.daily_energy.toFixed(2)} kWh` : ''}
                  </span>
                </div>
              ))}
              {(sensors?.devices?.length ?? 0) > 4 && (
                <p className='text-xs text-slate-500'>
                  +{(sensors?.devices?.length ?? 0) - 4} more · {totalDailyEnergy.toFixed(2)} kWh
                  today
                </p>
              )}
            </div>
            <Link to='/energy'>
              <Button variant='ghost' size='sm' className='mt-2 px-0'>
                View energy
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card data-testid='kpi-lighting'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Lighting</CardTitle>
            <Lightbulb className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>
              {hueConnected ? kpiValue(hue?.lights_count) : 'Offline'}
            </p>
            <p className='text-xs text-slate-400'>
              {hueConnected
                ? `lights · ${hue?.bridge_name ?? 'Hue Bridge'}`
                : (hue?.message ?? 'Hue bridge not connected')}
            </p>
            <div className='mt-2 flex gap-2'>
              <Link to='/lighting'>
                <Button variant='ghost' size='sm' className='px-0'>
                  Lighting controls
                </Button>
              </Link>
              <Button
                variant='ghost'
                size='sm'
                className='px-0 text-amber-400 hover:text-amber-300'
                onClick={() => {
                  void fetch('/api/lighting/hue/reconnect', { method: 'POST' })
                    .then(() => loadAll())
                    .catch(() => undefined);
                }}
                data-testid='hue-reconnect'
              >
                <RefreshCcw className='mr-1 h-3.5 w-3.5' />
                Reconnect
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card data-testid='kpi-weather'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Weather</CardTitle>
            <CloudRain className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>{weatherConnected ? 'Connected' : 'Offline'}</p>
            <p className='text-xs text-slate-400'>
              {weather?.message && weather.message.length > 60
                ? `${weather.message.slice(0, 60)}…`
                : (weather?.message ?? 'Netatmo station')}
            </p>
            <div className='mt-2 flex gap-2'>
              <Link to='/weather'>
                <Button variant='ghost' size='sm' className='px-0'>
                  Weather station
                </Button>
              </Link>
              {weather?.needs_reconnect && weather.reconnect_url && (
                <a href={weather.reconnect_url} target='_blank' rel='noreferrer'>
                  <Button
                    variant='ghost'
                    size='sm'
                    className='px-0 text-amber-400 hover:text-amber-300'
                    data-testid='netatmo-reconnect'
                  >
                    <RefreshCcw className='mr-1 h-3.5 w-3.5' />
                    Reconnect
                  </Button>
                </a>
              )}
            </div>
          </CardContent>
        </Card>

        <Card data-testid='kpi-ring'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Ring</CardTitle>
            <Bell className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>
              {ring?.connected
                ? 'Connected'
                : ring?.two_fa_pending
                  ? '2FA'
                  : ring?.config_issue
                    ? 'Off'
                    : 'Not connected'}
            </p>
            <p className='text-xs text-slate-400'>{ring?.message ?? '—'}</p>
            <Link to='/ring'>
              <Button variant='ghost' size='sm' className='mt-2 px-0'>
                Ring doorbell
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card data-testid='kpi-nest'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Nest Protect</CardTitle>
            <Flame className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>
              {nest?.initialized ? (nest.all_ok ? 'OK' : 'Alert') : 'Off'}
            </p>
            <p className='text-xs text-slate-400'>
              {nest?.initialized
                ? `${nest.total_devices ?? 0} device(s)`
                : (nest?.error ?? 'Via Home Assistant')}
            </p>
            <Link to='/nest'>
              <Button variant='ghost' size='sm' className='mt-2 px-0'>
                Nest Protect
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card data-testid='kpi-alerts'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>Alarms</CardTitle>
            <Bot className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>{kpiValue(alerts?.total_alerts)}</p>
            <p className='text-xs text-slate-400'>
              {alertActive ? 'attention needed' : 'all clear'}
            </p>
            <Link to='/alarms'>
              <Button variant='ghost' size='sm' className='mt-2 px-0'>
                View alarms
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card data-testid='kpi-capabilities'>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-sm font-medium text-slate-400'>MCP Capabilities</CardTitle>
            <Puzzle className='h-4 w-4 text-slate-400' />
          </CardHeader>
          <CardContent>
            <p className='text-2xl font-bold'>{kpiValue(capabilities?.tool_surface?.total)}</p>
            <p className='text-xs text-slate-400'>
              tools · sampling {capabilities?.features?.sampling ? 'on' : 'off'}
            </p>
            <Link to='/mcp-capabilities'>
              <Button variant='ghost' size='sm' className='mt-2 px-0'>
                View capabilities
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
