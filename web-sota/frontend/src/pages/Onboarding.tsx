import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  AlertCircle,
  Camera,
  CheckCircle,
  Cloud,
  Loader2,
  RefreshCw,
  Shield,
  Thermometer,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface DiscoveredDevice {
  device_id: string;
  device_type: string;
  display_name: string;
  location?: string;
  status: string;
  requires_auth?: boolean;
  [key: string]: unknown;
}

interface Progress {
  status: string;
  total_devices_discovered: number;
  devices_configured: number;
  onboarding_complete: boolean;
  completion_percentage: number;
  discovered_devices: DiscoveredDevice[];
  configured_devices: Record<
    string,
    { display_name: string; location: string; [key: string]: unknown }
  >;
  next_recommended_steps: string[];
}

const typeIcons: Record<string, React.ReactNode> = {
  tapo_p115: <Zap className='h-5 w-5' />,
  webcam: <Camera className='h-5 w-5' />,
  nest_protect: <Thermometer className='h-5 w-5' />,
  ring: <Shield className='h-5 w-5' />,
};
const defaultIcon = <Cloud className='h-5 w-5' />;

export function Onboarding() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [configuring, setConfiguring] = useState<string | null>(null);
  const [configForm, setConfigForm] = useState<{
    device_id: string;
    display_name: string;
    location: string;
  } | null>(null);
  const [resetting, setResetting] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/onboarding/progress');
      if (r.ok) {
        const data = await r.json();
        setProgress(data);
      } else {
        const err = await r.json().catch(() => ({}));
        setError((err as { detail?: string }).detail ?? 'Failed to load progress');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const startDiscovery = async () => {
    setDiscovering(true);
    setError(null);
    try {
      const r = await fetch('/api/onboarding/discover', { method: 'POST' });
      const data = await r.json();
      if (r.ok) {
        setTimeout(load, 2000);
      } else {
        setError((data as { detail?: string }).detail ?? 'Discovery failed');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setDiscovering(false);
    }
  };

  const configure = async (e: React.FormEvent) => {
    if (!configForm) return;
    e.preventDefault();
    setConfiguring(configForm.device_id);
    try {
      const r = await fetch('/api/onboarding/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: configForm.device_id,
          display_name: configForm.display_name,
          location: configForm.location,
          settings: {},
        }),
      });
      if (r.ok) await load();
      else setError((await r.json()).detail ?? 'Configure failed');
      setConfigForm(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setConfiguring(null);
    }
  };

  const complete = async () => {
    setCompleting(true);
    setError(null);
    try {
      const r = await fetch('/api/onboarding/complete', { method: 'POST' });
      const data = await r.json();
      if (r.ok) await load();
      else setError((data as { detail?: string }).detail ?? 'Complete failed');
    } catch (e) {
      setError(String(e));
    } finally {
      setCompleting(false);
    }
  };

  const resetOnboarding = async () => {
    if (!confirm('Reset onboarding? Discovered devices and configuration will be cleared.')) return;
    setResetting(true);
    setError(null);
    try {
      const r = await fetch('/api/onboarding/reset', { method: 'DELETE' });
      if (r.ok) await load();
      else
        setError(
          ((await r.json().catch(() => ({}))) as { detail?: string }).detail ?? 'Reset failed',
        );
    } catch (e) {
      setError(String(e));
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const devices = progress?.discovered_devices ?? [];
  const unconfigured = devices.filter((d) => d.status !== 'configured');
  const canComplete = unconfigured.length === 0 && devices.length > 0;

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Device Onboarding</h1>
      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      {progress?.onboarding_complete && (
        <Card className='border-green-200 dark:border-green-900'>
          <CardContent className='flex items-center gap-3 pt-6'>
            <CheckCircle className='h-8 w-8 text-green-600 dark:text-green-400' />
            <div>
              <p className='font-medium text-green-800 dark:text-green-200'>Onboarding complete</p>
              <p className='text-sm text-slate-600 dark:text-slate-400'>
                {progress.devices_configured} devices configured. Use the dashboard to manage them.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader className='flex flex-row items-center justify-between pb-2'>
          <CardTitle className='text-base font-medium'>Progress</CardTitle>
          <div className='flex gap-2'>
            <Button variant='outline' size='sm' onClick={startDiscovery} disabled={discovering}>
              {discovering ? (
                <Loader2 className='h-4 w-4 animate-spin' />
              ) : (
                <RefreshCw className='h-4 w-4' />
              )}
              <span className='ml-2'>{discovering ? 'Discovering…' : 'Start discovery'}</span>
            </Button>
            <Button variant='ghost' size='sm' onClick={resetOnboarding} disabled={resetting}>
              {resetting ? '…' : 'Reset'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className='mb-4 h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700'>
            <div
              className='h-full rounded-full bg-indigo-500 transition-all'
              style={{ width: `${progress?.completion_percentage ?? 0}%` }}
            />
          </div>
          <p className='text-sm text-slate-600 dark:text-slate-400'>
            {progress?.devices_configured ?? 0} / {progress?.total_devices_discovered ?? 0} devices
            configured
            {progress?.next_recommended_steps?.length
              ? ` · ${progress.next_recommended_steps[0]}`
              : ''}
          </p>
        </CardContent>
      </Card>
      {devices.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className='text-base'>Discovered devices</CardTitle>
          </CardHeader>
          <CardContent className='space-y-3'>
            {devices.map((d) => {
              const isConfigured = d.status === 'configured';
              const cfg = progress?.configured_devices[d.device_id];
              const isEditing = configForm?.device_id === d.device_id;
              return (
                <div
                  key={d.device_id}
                  className='flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700'
                >
                  <div className='flex items-center gap-3'>
                    <span className='flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'>
                      {typeIcons[d.device_type] ?? defaultIcon}
                    </span>
                    <div>
                      <p className='font-medium'>{cfg?.display_name ?? d.display_name}</p>
                      <p className='text-xs text-slate-500'>
                        {d.device_type} · {d.device_id}
                      </p>
                    </div>
                    {isConfigured && <CheckCircle className='h-4 w-4 text-green-600' />}
                  </div>
                  {!isConfigured && (
                    <div className='flex items-center gap-2'>
                      {isEditing ? (
                        <form onSubmit={configure} className='flex flex-wrap items-end gap-2'>
                          <input
                            type='text'
                            placeholder='Display name'
                            value={configForm?.display_name ?? ''}
                            onChange={(e) =>
                              setConfigForm((f) =>
                                f ? { ...f, display_name: e.target.value } : null,
                              )
                            }
                            className='rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800'
                          />
                          <input
                            type='text'
                            placeholder='Location'
                            value={configForm?.location ?? ''}
                            onChange={(e) =>
                              setConfigForm((f) => (f ? { ...f, location: e.target.value } : null))
                            }
                            className='w-28 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800'
                          />
                          <Button type='submit' size='sm' disabled={configuring === d.device_id}>
                            {configuring === d.device_id ? '…' : 'Save'}
                          </Button>
                          <Button
                            type='button'
                            size='sm'
                            variant='ghost'
                            onClick={() => setConfigForm(null)}
                          >
                            Cancel
                          </Button>
                        </form>
                      ) : (
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() =>
                            setConfigForm({
                              device_id: d.device_id,
                              display_name: d.display_name,
                              location: d.location ?? '',
                            })
                          }
                        >
                          Configure
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
      {canComplete && (
        <Button onClick={complete} disabled={completing}>
          {completing ? '…' : 'Complete onboarding'}
        </Button>
      )}
    </div>
  );
}
