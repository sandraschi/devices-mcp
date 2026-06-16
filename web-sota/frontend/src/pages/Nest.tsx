import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, CheckCircle, Flame, KeyRound, Loader2, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface NestDevice {
  device_id?: string;
  name?: string;
  location?: string;
  smoke_status?: string;
  co_status?: string;
  battery_health?: string;
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
  has_token?: boolean;
  oauth_url?: string;
  has_custom_creds?: boolean;
}

function parseErrorBody(data: unknown): string {
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: string };
    if (typeof d.detail === 'string') return d.detail;
    if (d.message) return d.message;
  }
  return 'Request failed';
}

export function Nest() {
  const [status, setStatus] = useState<NestStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [exchanging, setExchanging] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [savingToken, setSavingToken] = useState(false);

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

  const doExchange = async () => {
    if (!code.trim()) return;
    setExchanging(true);
    setError(null);
    try {
      const r = await fetch('/api/nest/oauth/exchange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code.trim() }),
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        throw new Error(parseErrorBody(data));
      }
      setCode('');
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setExchanging(false);
    }
  };

  const doSaveToken = async () => {
    if (!manualToken.trim()) return;
    setSavingToken(true);
    setError(null);
    try {
      const r = await fetch('/api/nest/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: manualToken.trim() }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? 'Failed to save token');
      setManualToken('');
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSavingToken(false);
    }
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
            Nest Protect
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
                {status?.total_devices ?? 0} device(s) &middot; smoke{' '}
                {status?.smoke_status ?? '&mdash;'} &middot; CO{' '}
                {status?.co_status ?? '&mdash;'}
              </p>
              {(status?.battery_warnings?.length ?? 0) > 0 && (
                <p className='text-amber-600'>
                  Low battery: {status!.battery_warnings!.join(', ')}
                </p>
              )}
            </>
          ) : (
            <>
              {status?.has_custom_creds && status?.oauth_url ? (
                <div className='space-y-2 pt-1'>
                  <p>Click below to sign in with Google:</p>
                  <a href={status.oauth_url} target='_blank' rel='noreferrer'>
                    <Button size='sm'>Sign in with Google</Button>
                  </a>
                  <div className='flex flex-wrap items-center gap-2 pt-1'>
                    <input
                      type='text'
                      placeholder='Paste authorization code...'
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      className='min-w-[20rem] rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900'
                    />
                    <Button size='sm' onClick={doExchange} disabled={!code.trim() || exchanging}>
                      {exchanging ? 'Exchanging...' : 'Exchange Code'}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className='space-y-3 pt-1'>
                  <div className='rounded-md border border-slate-200 p-3 dark:border-slate-700'>
                    <p className='mb-1 font-medium text-xs'>Paste Nest token directly</p>
                    <p className='text-xs text-slate-500 mb-2'>
                      From an existing Nest/Home Assistant setup, or from your Nest account.
                    </p>
                    <div className='flex flex-wrap items-center gap-2'>
                      <input
                        type='text'
                        placeholder='Paste refresh token...'
                        value={manualToken}
                        onChange={(e) => setManualToken(e.target.value)}
                        className='min-w-[16rem] flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900'
                      />
                      <Button size='sm' onClick={doSaveToken} disabled={!manualToken.trim() || savingToken}>
                        <KeyRound className='mr-1 h-3 w-3' />
                        {savingToken ? 'Saving...' : 'Save & Connect'}
                      </Button>
                    </div>
                  </div>
                </div>
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
                <li key={d.device_id ?? d.name} className='flex justify-between gap-2'>
                  <span>
                    {d.name ?? d.device_id}
                    {d.location ? ` (${d.location})` : ''}
                  </span>
                  <span className='text-slate-500'>
                    smoke {d.smoke_status ?? '—'} &middot; CO {d.co_status ?? '—'}
                    {d.battery_health === 'replace' ? ' · BATTERY' : ''}
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
