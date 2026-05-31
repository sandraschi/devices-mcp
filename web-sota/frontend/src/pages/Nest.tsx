import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, CheckCircle, Flame, Loader2, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface NestDevice {
  friendly_name?: string;
  entity_id?: string;
  smoke_status?: string;
  co_status?: string;
  battery_level?: number;
  is_online?: boolean;
}

interface NestStatus {
  initialized?: boolean;
  error?: string;
  total_devices?: number;
  online_count?: number;
  smoke_status?: string;
  co_status?: string;
  all_ok?: boolean;
  battery_warnings?: string[];
  devices?: NestDevice[];
  setup_instructions?: string[];
}

export function Nest() {
  const [status, setStatus] = useState<NestStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/nest/status');
      const data = await r.json();
      setStatus(data);
      setError(data.error && !data.initialized ? data.error : null);
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

  const refresh = async () => {
    setRefreshLoading(true);
    await load();
    setRefreshLoading(false);
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const devices = status?.devices ?? [];
  const connected = status?.initialized === true;

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-2'>
        <h1 className='text-2xl font-bold tracking-tight'>Nest Protect</h1>
        <Button size='sm' variant='outline' onClick={refresh} disabled={refreshLoading}>
          {refreshLoading ? (
            <Loader2 className='h-4 w-4 animate-spin' />
          ) : (
            <RefreshCw className='h-4 w-4' />
          )}
          <span className='ml-1'>Refresh</span>
        </Button>
      </div>

      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}

      <Card className={connected ? 'border-green-200 dark:border-green-900' : ''}>
        <CardHeader className='flex flex-row items-center justify-between pb-2'>
          <CardTitle className='text-base flex items-center gap-2'>
            <Flame className='h-5 w-5' />
            Home Assistant / Nest
          </CardTitle>
          {connected && status?.all_ok ? (
            <CheckCircle className='h-5 w-5 text-green-600' />
          ) : (
            <Flame className='h-5 w-5 text-slate-400' />
          )}
        </CardHeader>
        <CardContent className='space-y-2 text-sm'>
          {connected ? (
            <>
              <p>
                {status?.total_devices ?? 0} device(s) · smoke {status?.smoke_status ?? '—'} · CO{' '}
                {status?.co_status ?? '—'}
              </p>
              {(status?.battery_warnings?.length ?? 0) > 0 && (
                <p className='text-amber-600'>
                  Low battery: {status!.battery_warnings!.join(', ')}
                </p>
              )}
            </>
          ) : (
            <>
              <p>Nest Protect requires Home Assistant with the Nest integration.</p>
              {status?.setup_instructions && (
                <ol className='mt-2 list-decimal space-y-1 pl-5 text-slate-600 dark:text-slate-400'>
                  {status.setup_instructions.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {devices.length > 0 && (
        <Card>
          <CardHeader className='pb-2'>
            <CardTitle className='text-base'>Devices</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className='space-y-2 text-sm'>
              {devices.map((d) => (
                <li key={d.entity_id ?? d.friendly_name} className='flex justify-between gap-2'>
                  <span>{d.friendly_name ?? d.entity_id}</span>
                  <span className='text-slate-500'>
                    smoke {d.smoke_status ?? '—'} · CO {d.co_status ?? '—'}
                    {d.battery_level != null ? ` · ${d.battery_level}%` : ''}
                    {d.is_online === false ? ' · offline' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
