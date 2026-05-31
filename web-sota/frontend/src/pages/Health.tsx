import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Activity,
  AlertCircle,
  Cpu,
  Database,
  HardDrive,
  Loader2,
  MemoryStick,
  Video,
} from 'lucide-react';
import { useEffect, useState } from 'react';

interface HealthData {
  success?: boolean;
  error?: string;
  uptime_seconds?: number;
  uptime_human?: string;
  system?: {
    cpu_percent?: number;
    memory?: { total: number; available: number; percent: number } | null;
    disk?: { total: number; used: number; free: number; percent: number } | null;
  };
  process?: { memory_rss?: number; cpu_percent?: number };
  cameras?: { total: number; online: number; offline: number; error?: string };
  databases?: Record<string, { status: string; size_mb?: number; error?: string }>;
}

function formatBytes(n: number): string {
  if (n >= 1024 * 1024 * 1024) return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return String(n);
}

function formatUptime(sec?: number): string {
  if (sec == null) return '—';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return `${h}h ${m}m`;
}

interface ConnectionHealth {
  total_devices?: number;
  online?: number;
  offline?: number;
  devices?: Array<{
    name?: string;
    type?: string;
    connected?: boolean;
    error?: string | null;
  }>;
  error?: string;
}

export function Health() {
  const [data, setData] = useState<HealthData | null>(null);
  const [connection, setConnection] = useState<ConnectionHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const ctrl = new AbortController();
        const timeout = setTimeout(() => ctrl.abort(), 15000);
        const [healthRes, connRes] = await Promise.allSettled([
          fetch('/api/health', { signal: ctrl.signal }),
          fetch('/api/system/connection-health', { signal: ctrl.signal }),
        ]);
        clearTimeout(timeout);

        if (cancelled) return;
        if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
          setData(await healthRes.value.json());
          setError(null);
        } else if (healthRes.status === 'fulfilled') {
          const json = await healthRes.value.json().catch(() => ({}));
          setError((json as { error?: string }).error ?? 'Health check failed');
        } else {
          setError('Health API request failed');
        }
        if (connRes.status === 'fulfilled' && connRes.value.ok) {
          setConnection(await connRes.value.json());
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const sys = data?.system;
  const mem = sys?.memory;
  const disk = sys?.disk;
  const cameras = data?.cameras;
  const dbs = data?.databases;

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>PC Health</h1>
      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      {!data?.success && !error && <p className='text-slate-500'>No health data available.</p>}
      <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
        {sys?.cpu_percent != null && (
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2'>
                <Cpu className='h-4 w-4' /> CPU
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-2xl font-semibold'>{sys.cpu_percent.toFixed(1)}%</p>
            </CardContent>
          </Card>
        )}
        {mem && (
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2'>
                <MemoryStick className='h-4 w-4' /> Memory
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-2xl font-semibold'>{mem.percent.toFixed(1)}%</p>
              <p className='text-xs text-slate-500'>
                {formatBytes(mem.available)} free of {formatBytes(mem.total)}
              </p>
            </CardContent>
          </Card>
        )}
        {disk && (
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2'>
                <HardDrive className='h-4 w-4' /> Disk
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-2xl font-semibold'>{disk.percent.toFixed(1)}%</p>
              <p className='text-xs text-slate-500'>
                {formatBytes(disk.used)} used, {formatBytes(disk.free)} free
              </p>
            </CardContent>
          </Card>
        )}
        {(data?.uptime_seconds != null || data?.uptime_human) && (
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2'>
                <Activity className='h-4 w-4' /> Uptime
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-2xl font-semibold'>
                {data.uptime_human ?? formatUptime(data.uptime_seconds)}
              </p>
            </CardContent>
          </Card>
        )}
        {cameras && (
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2'>
                <Video className='h-4 w-4' /> Cameras
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-2xl font-semibold'>
                {cameras.online}/{cameras.total}
              </p>
              <p className='text-xs text-slate-500'>
                {cameras.offline} offline{cameras.error ? ` · ${cameras.error}` : ''}
              </p>
            </CardContent>
          </Card>
        )}
        {dbs && Object.keys(dbs).length > 0 && (
          <Card>
            <CardHeader className='flex flex-row items-center justify-between pb-2'>
              <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2'>
                <Database className='h-4 w-4' /> Databases
              </CardTitle>
            </CardHeader>
            <CardContent className='space-y-1'>
              {Object.entries(dbs).map(([name, info]) => (
                <p key={name} className='text-sm'>
                  <span className='font-medium'>{name}</span>: {info.status}
                  {info.size_mb != null && ` (${info.size_mb} MB)`}
                </p>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      {connection && (connection.total_devices ?? 0) > 0 && (
        <Card>
          <CardHeader className='pb-2'>
            <CardTitle className='text-base'>Device connectivity</CardTitle>
          </CardHeader>
          <CardContent className='space-y-2'>
            <p className='text-sm text-slate-600 dark:text-slate-400'>
              {connection.online ?? 0} online · {connection.offline ?? 0} offline ·{' '}
              {connection.total_devices ?? 0} total
            </p>
            <ul className='space-y-1 text-sm'>
              {(connection.devices ?? []).map((d) => (
                <li key={`${d.type}-${d.name}`} className='flex justify-between gap-2'>
                  <span>
                    {d.name} ({d.type})
                  </span>
                  <span className={d.connected ? 'text-green-600' : 'text-amber-600'}>
                    {d.connected ? 'online' : (d.error ?? 'offline')}
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
