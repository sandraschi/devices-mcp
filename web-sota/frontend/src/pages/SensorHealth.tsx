import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Thermometer,
  XCircle,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface ModuleData {
  name: string;
  temperature?: number | null;
  humidity?: number | null;
  co2?: number | null;
  battery?: number | null;
  power?: number | null;
}

interface ModulesResponse {
  success: boolean;
  modules: Record<string, ModuleData>;
}

const CO2_WARN = 1000;
const CO2_DANGER = 2000;
const TEMP_WARN = 35;
const TEMP_DANGER = 40;
const TEMP_LOW_WARN = 10;
const TEMP_LOW_DANGER = 5;
const HUMID_WARN = 70;
const BATTERY_WARN = 20;
const POWER_WARN = 1000;
const POWER_DANGER = 2000;

type Status = 'ok' | 'warning' | 'danger' | 'unknown';

function tempStatus(value: number | null | undefined): Status {
  if (value == null) return 'unknown';
  if (value >= TEMP_DANGER || value <= TEMP_LOW_DANGER) return 'danger';
  if (value >= TEMP_WARN || value <= TEMP_LOW_WARN) return 'warning';
  return 'ok';
}

function co2Status(value: number | null | undefined): Status {
  if (value == null) return 'unknown';
  if (value >= CO2_DANGER) return 'danger';
  if (value >= CO2_WARN) return 'warning';
  return 'ok';
}

function humidityStatus(value: number | null | undefined): Status {
  if (value == null) return 'unknown';
  if (value >= HUMID_WARN) return 'warning';
  return 'ok';
}

function batteryStatus(value: number | null | undefined): Status {
  if (value == null) return 'unknown';
  if (value <= BATTERY_WARN) return 'warning';
  return 'ok';
}

function powerStatus(value: number | null | undefined): Status {
  if (value == null) return 'unknown';
  if (value >= POWER_DANGER) return 'danger';
  if (value >= POWER_WARN) return 'warning';
  return 'ok';
}

function zoneStatus(module: ModuleData): Status {
  const statuses = [
    tempStatus(module.temperature),
    co2Status(module.co2),
    humidityStatus(module.humidity),
    powerStatus(module.power),
  ];
  if (module.battery != null) statuses.push(batteryStatus(module.battery));
  if (statuses.includes('danger')) return 'danger';
  if (statuses.includes('warning')) return 'warning';
  if (statuses.includes('unknown')) return 'unknown';
  return 'ok';
}

const STATUS_CFG: Record<
  Status,
  { label: string; border: string; bg: string; icon: typeof CheckCircle2 }
> = {
  ok: {
    label: 'OK',
    border: 'border-emerald-200 dark:border-emerald-900',
    bg: 'bg-emerald-50 dark:bg-emerald-950/20',
    icon: CheckCircle2,
  },
  warning: {
    label: 'Warning',
    border: 'border-amber-200 dark:border-amber-900',
    bg: 'bg-amber-50 dark:bg-amber-950/20',
    icon: AlertTriangle,
  },
  danger: {
    label: 'Danger',
    border: 'border-red-200 dark:border-red-900',
    bg: 'bg-red-50 dark:bg-red-950/20',
    icon: XCircle,
  },
  unknown: {
    label: 'Unknown',
    border: 'border-slate-200 dark:border-slate-800',
    bg: 'bg-slate-50 dark:bg-slate-950',
    icon: Activity,
  },
};

function SensorRow({
  label,
  value,
  unit,
  status,
}: {
  label: React.ReactNode;
  value: number | null | undefined;
  unit: string;
  status: Status;
}) {
  const cfg = STATUS_CFG[status];
  const valueStr = value != null ? `${value}${unit}` : '—';
  return (
    <div className='flex items-center justify-between py-1'>
      <span className='text-sm text-slate-600 dark:text-slate-400'>{label}</span>
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.border} border`}
      >
        <cfg.icon className='h-3 w-3' />
        {valueStr}
      </span>
    </div>
  );
}

export function SensorHealth() {
  const [modules, setModules] = useState<Record<string, ModuleData> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [weatherR, energyR] = await Promise.all([
        fetch('/api/weather/modules'),
        fetch('/api/sensors/tapo-p115'),
      ]);
      const weatherData = (await weatherR.json()) as ModulesResponse;
      const merged: Record<string, ModuleData> = {};
      if (weatherData.success) {
        for (const [k, v] of Object.entries(weatherData.modules ?? {})) {
          merged[k] = { ...v };
        }
      }
      if (energyR.ok) {
        const energyData = await energyR.json();
        const plugs: { device_id: string; name?: string; current_power?: number }[] =
          energyData.devices ?? [];
        for (const p of plugs) {
          if (p.current_power != null) {
            merged[`plug_${p.device_id}`] = {
              name: p.name ?? p.device_id,
              power: p.current_power,
            };
          }
        }
      }
      setModules(Object.keys(merged).length > 0 ? merged : null);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 30000);
    return () => window.clearInterval(timer);
  }, [load]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const entries = modules ? Object.entries(modules) : [];
  const zoneCounts = { ok: 0, warning: 0, danger: 0, unknown: 0 };
  for (const [, mod] of entries) {
    zoneCounts[zoneStatus(mod)]++;
  }

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-2'>
        <h1 className='text-2xl font-bold tracking-tight'>Sensor Health</h1>
        <Button size='sm' variant='outline' onClick={handleRefresh} disabled={refreshing}>
          {refreshing ? (
            <Loader2 className='h-4 w-4 animate-spin' />
          ) : (
            <RefreshCw className='h-4 w-4' />
          )}
          <span className='ml-1'>Refresh</span>
        </Button>
      </div>

      {zoneCounts.ok + zoneCounts.warning + zoneCounts.danger > 0 && (
        <div className='flex flex-wrap gap-3'>
          {zoneCounts.ok > 0 && (
            <Card className={`flex-1 ${STATUS_CFG.ok.border}`}>
              <CardContent className='flex items-center gap-3 p-4'>
                <div className={`rounded-full p-2 ${STATUS_CFG.ok.bg}`}>
                  <CheckCircle2 className='h-5 w-5 text-emerald-600 dark:text-emerald-400' />
                </div>
                <div>
                  <p className='text-2xl font-bold'>{zoneCounts.ok}</p>
                  <p className='text-sm text-slate-500'>OK</p>
                </div>
              </CardContent>
            </Card>
          )}
          {zoneCounts.warning > 0 && (
            <Card className={`flex-1 ${STATUS_CFG.warning.border}`}>
              <CardContent className='flex items-center gap-3 p-4'>
                <div className={`rounded-full p-2 ${STATUS_CFG.warning.bg}`}>
                  <AlertTriangle className='h-5 w-5 text-amber-600 dark:text-amber-400' />
                </div>
                <div>
                  <p className='text-2xl font-bold'>{zoneCounts.warning}</p>
                  <p className='text-sm text-slate-500'>Warning</p>
                </div>
              </CardContent>
            </Card>
          )}
          {zoneCounts.danger > 0 && (
            <Card className={`flex-1 ${STATUS_CFG.danger.border}`}>
              <CardContent className='flex items-center gap-3 p-4'>
                <div className={`rounded-full p-2 ${STATUS_CFG.danger.bg}`}>
                  <XCircle className='h-5 w-5 text-red-600 dark:text-red-400' />
                </div>
                <div>
                  <p className='text-2xl font-bold'>{zoneCounts.danger}</p>
                  <p className='text-sm text-slate-500'>Danger</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertTriangle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}

      {entries.length > 0 && (
        <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
          {entries.map(([key, mod]) => {
            const zs = zoneStatus(mod);
            const cfg = STATUS_CFG[zs];
            const Icon = cfg.icon;
            return (
              <Card key={key} className={cfg.border}>
                <CardHeader className='flex flex-row items-center justify-between pb-2'>
                  <CardTitle className='text-base flex items-center gap-2'>
                    {mod.name ?? key}
                    <Icon
                      className={`h-4 w-4 ${zs === 'ok' ? 'text-emerald-500' : zs === 'warning' ? 'text-amber-500' : zs === 'danger' ? 'text-red-500' : 'text-slate-400'}`}
                    />
                  </CardTitle>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${cfg.bg} ${cfg.border} border`}
                  >
                    {cfg.label}
                  </span>
                </CardHeader>
                <CardContent className='space-y-1'>
                  {mod.temperature != null && (
                    <SensorRow
                      label={
                        <span>
                          <Thermometer className='mr-1 inline h-3.5 w-3.5' />
                          Temperature
                        </span>
                      }
                      value={mod.temperature}
                      unit='°C'
                      status={tempStatus(mod.temperature)}
                    />
                  )}
                  {mod.co2 != null && (
                    <SensorRow
                      label='CO₂'
                      value={mod.co2}
                      unit=' ppm'
                      status={co2Status(mod.co2)}
                    />
                  )}
                  {mod.humidity != null && (
                    <SensorRow
                      label='Humidity'
                      value={mod.humidity}
                      unit='%'
                      status={humidityStatus(mod.humidity)}
                    />
                  )}
                  {mod.power != null && (
                    <SensorRow
                      label={
                        <span>
                          <Zap className='mr-1 inline h-3.5 w-3.5' />
                          Power
                        </span>
                      }
                      value={mod.power}
                      unit=' W'
                      status={powerStatus(mod.power)}
                    />
                  )}
                  {mod.battery != null && (
                    <SensorRow
                      label='Battery'
                      value={mod.battery}
                      unit='%'
                      status={batteryStatus(mod.battery)}
                    />
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {entries.length === 0 && !error && (
        <p className='text-slate-500'>No sensor data. Ensure Netatmo is connected and reporting.</p>
      )}
    </div>
  );
}
