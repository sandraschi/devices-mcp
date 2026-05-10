import { AlertCircle, Check, Edit3, Loader2, Save, Shield, User, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { type CapabilitiesResponse, getCapabilities } from '@/common/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface AuthStatus {
  authenticated: boolean;
  user?: string;
  auth_enabled: boolean;
}

interface ConfigData {
  success: boolean;
  path?: string;
  yaml?: string;
  json?: Record<string, unknown>;
  error?: string;
}

export function Settings() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [editYaml, setEditYaml] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/config');
      const data: ConfigData = await res.json();
      if (data.success) {
        setConfig(data);
        setEditYaml(data.yaml ?? '');
      } else {
        setError(data.error ?? 'Failed to load config');
      }
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      fetch('/api/auth/status').then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(String(r.status))),
      ),
      getCapabilities(),
      loadConfig(),
    ])
      .then(([authResult, capsResult]) => {
        if (cancelled) return;
        if (authResult.status === 'fulfilled') setAuth(authResult.value);
        else setError(String(authResult.reason));
        if (capsResult.status === 'fulfilled') setCapabilities(capsResult.value);
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
  }, [loadConfig]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const res = await fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yaml: editYaml }),
      });
      const data = await res.json();
      if (data.success) {
        setSaveMsg('Config saved. Restart backend to apply changes.');
        setEditing(false);
        setConfig((prev) => (prev ? { ...prev, yaml: editYaml } : prev));
      } else {
        setSaveMsg(data.error ?? 'Save failed');
      }
    } catch (e) {
      setSaveMsg(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setEditYaml(config?.yaml ?? '');
    setSaveMsg(null);
  };

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
            Auth enabled:{' '}
            <span className='font-medium'>{auth?.auth_enabled ? 'Yes' : 'No'}</span>
          </p>
          <p>
            Logged in:{' '}
            <span className='font-medium'>{auth?.authenticated ? 'Yes' : 'No'}</span>
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
        <CardHeader className='flex flex-row items-center justify-between pb-2'>
          <CardTitle className='text-base'>
            Configuration{config?.path ? ` — ${config.path}` : ''}
          </CardTitle>
          <div className='flex items-center gap-2'>
            {saveMsg && (
              <span
                className={`flex items-center gap-1 text-xs ${saveMsg.startsWith('Config saved') ? 'text-emerald-600' : 'text-red-600'}`}
              >
                {saveMsg.startsWith('Config saved') ? (
                  <Check className='h-3 w-3' />
                ) : (
                  <AlertCircle className='h-3 w-3' />
                )}
                {saveMsg}
              </span>
            )}
            {editing ? (
              <>
                <Button size='sm' variant='outline' onClick={handleCancelEdit} disabled={saving}>
                  <X className='mr-1 h-3 w-3' />
                  Cancel
                </Button>
                <Button size='sm' onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <Loader2 className='mr-1 h-3 w-3 animate-spin' />
                  ) : (
                    <Save className='mr-1 h-3 w-3' />
                  )}
                  Save
                </Button>
              </>
            ) : (
              <Button size='sm' variant='outline' onClick={() => setEditing(true)}>
                <Edit3 className='mr-1 h-3 w-3' />
                Edit
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {editing ? (
            <textarea
              className='h-[60vh] w-full resize-none rounded-md border border-slate-300 bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200'
              value={editYaml}
              onChange={(e) => setEditYaml(e.target.value)}
              spellCheck={false}
            />
          ) : (
            <pre className='max-h-[60vh] overflow-auto rounded-md border border-slate-200 bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'>
              {config?.yaml || 'No config loaded.'}
            </pre>
          )}
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
