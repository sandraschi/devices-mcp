import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Loader2, RefreshCw, Thermometer } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface ShellyStatus {
  connected: boolean;
  initialized: boolean;
  enabled?: boolean;
  message: string;
  device_count?: number;
  needs_init?: boolean;
}

interface ShellySensor {
  device_name?: string;
  sensor_id?: string;
  temperature_c?: number;
  alert_active?: boolean;
  is_online?: boolean;
}

interface ShellySummary {
  sensor_count?: number;
  alert_count?: number;
  online_count?: number;
  sensors?: ShellySensor[];
  alerts?: ShellySensor[];
}

export function Shelly() {
  const [status, setStatus] = useState<ShellyStatus | null>(null);
  const [summary, setSummary] = useState<ShellySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    try {
      const r = await fetch('/api/shelly/summary');
      if (r.ok) setSummary(await r.json());
      else setSummary(null);
    } catch {
      setSummary(null);
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/shelly/status');
      const st = await r.json();
      setStatus(st);
      setError(null);
      if (st.connected) await loadSummary();
      else setSummary(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [loadSummary]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 30000);
    return () => window.clearInterval(timer);
  }, [load]);

  const refresh = async () => {
    setRefreshLoading(true);
    try {
      const r = await fetch('/api/shelly/temperatures');
      if (r.ok) {
        const data = await r.json();
        setSummary({
          sensor_count: data.count,
          alert_count: data.alerts?.length ?? 0,
          sensors: data.sensors,
          alerts: data.alerts,
        });
      }
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshLoading(false);
    }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const sensors = summary?.sensors ?? [];

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-2'>
        <h1 className='text-2xl font-bold tracking-tight'>Shelly Temperature</h1>
        {status?.connected && (
          <Button size='sm' variant='outline' onClick={refresh} disabled={refreshLoading}>
            {refreshLoading ? (
              <Loader2 className='h-4 w-4 animate-spin' />
            ) : (
              <RefreshCw className='h-4 w-4' />
            )}
            <span className='ml-1'>Refresh</span>
          </Button>
        )}
      </div>

      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}

      <Card className={status?.connected ? 'border-green-200 dark:border-green-900' : ''}>
        <CardHeader className='flex flex-row items-center gap-2 pb-2'>
          <Thermometer className='h-5 w-5' />
          <CardTitle className='text-base'>Connection</CardTitle>
        </CardHeader>
        <CardContent>
          <p className='text-sm'>{status?.message ?? '—'}</p>
          {status?.enabled === false && (
            <p className='mt-2 text-sm text-slate-500'>
              Enable shelly in config.yaml and restart the webapp.
            </p>
          )}
          {status?.needs_init && (
            <p className='mt-2 text-sm text-slate-500'>
              Add devices under shelly.devices in config.yaml (IP, name, thresholds).
            </p>
          )}
        </CardContent>
      </Card>

      {status?.connected && summary && (
        <>
          <div className='grid gap-4 md:grid-cols-3'>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm text-slate-500'>Sensors</CardTitle>
              </CardHeader>
              <CardContent className='text-2xl font-semibold'>
                {summary.sensor_count ?? sensors.length}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm text-slate-500'>Alerts</CardTitle>
              </CardHeader>
              <CardContent className='text-2xl font-semibold text-amber-600'>
                {summary.alert_count ?? 0}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm text-slate-500'>Online</CardTitle>
              </CardHeader>
              <CardContent className='text-2xl font-semibold'>
                {summary.online_count ?? '—'}
              </CardContent>
            </Card>
          </div>

          {sensors.length > 0 && (
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-base'>Temperature readings</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className='space-y-2 text-sm'>
                  {sensors.map((s) => (
                    <li
                      key={`${s.device_name}-${s.sensor_id}`}
                      className='flex justify-between gap-2'
                    >
                      <span>{s.device_name ?? s.sensor_id}</span>
                      <span
                        className={s.alert_active ? 'text-amber-600 font-medium' : 'text-slate-500'}
                      >
                        {s.temperature_c != null ? `${s.temperature_c.toFixed(1)} °C` : '—'}
                        {s.alert_active ? ' · alert' : ''}
                        {s.is_online === false ? ' · offline' : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
