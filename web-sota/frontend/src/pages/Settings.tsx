import { AlertCircle, Loader2, Shield, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import { type CapabilitiesResponse, getCapabilities } from '@/common/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface AuthStatus {
  authenticated: boolean;
  user?: string;
  auth_enabled: boolean;
}

export function Settings() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      fetch('/api/auth/status').then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(String(r.status))),
      ),
      getCapabilities(),
    ])
      .then(([authResult, capsResult]) => {
        if (cancelled) return;
        if (authResult.status === 'fulfilled') {
          setAuth(authResult.value);
        } else {
          setError(String(authResult.reason));
        }
        if (capsResult.status === 'fulfilled') {
          setCapabilities(capsResult.value);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
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

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Settings</h1>
      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      <Card>
        <CardHeader className='flex flex-row items-center justify-between pb-2'>
          <CardTitle className='text-base'>Authentication</CardTitle>
          <Shield className='h-4 w-4 text-slate-400' />
        </CardHeader>
        <CardContent className='space-y-2 text-sm'>
          <p>
            Auth enabled: <span className='font-medium'>{auth?.auth_enabled ? 'Yes' : 'No'}</span>
          </p>
          <p>
            Logged in: <span className='font-medium'>{auth?.authenticated ? 'Yes' : 'No'}</span>
          </p>
          {auth?.user && (
            <p className='flex items-center gap-1'>
              <User className='h-4 w-4' />
              {auth.user}
            </p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className='pb-2'>
          <CardTitle className='text-base'>Configuration</CardTitle>
        </CardHeader>
        <CardContent className='space-y-2 text-sm text-slate-600 dark:text-slate-400'>
          <p>
            Devices MCP is configured via{' '}
            <code className='rounded bg-slate-100 px-1 dark:bg-slate-800'>config.yaml</code> in the
            project root. Edit cameras, Ring, Tapo P115, Hue, Netatmo, and other integrations there.
          </p>
          <p>Restart the backend after changing config.</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className='pb-2'>
          <CardTitle className='text-base'>Runtime capabilities</CardTitle>
        </CardHeader>
        <CardContent className='space-y-2 text-sm text-slate-600 dark:text-slate-400'>
          <p>
            Tool surface mode:{' '}
            <span className='font-medium'>{capabilities?.runtime?.surface_mode ?? 'unknown'}</span>
          </p>
          <p>
            Total tools:{' '}
            <span className='font-medium'>{capabilities?.tool_surface?.total ?? 0}</span>
          </p>
          <p>
            Sampling:{' '}
            <span className='font-medium'>
              {capabilities?.features?.sampling ? 'available' : 'not detected'}
            </span>
          </p>
          <p>
            Prompts / Skills:{' '}
            <span className='font-medium'>
              {capabilities?.inventory?.prompt_names?.length ?? 0} /{' '}
              {capabilities?.inventory?.skill_uris?.length ?? 0}
            </span>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
