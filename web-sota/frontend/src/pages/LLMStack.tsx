import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type LLMModelInfo, normalizeModelList } from '@/lib/llmModels';
import { AlertCircle, Box, Cpu, Loader2, Play, Square } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface ProviderInfo {
  type?: string;
  name?: string;
  base_url?: string;
  [key: string]: unknown;
}

export function LLMStack() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [models, setModels] = useState<LLMModelInfo[]>([]);
  const [provider, setProvider] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<string | null>(null);

  const loadProviders = useCallback(async () => {
    try {
      const r = await fetch('/api/llm/providers');
      const data = await r.json();
      if (data.success && data.providers?.length) {
        setProviders(data.providers);
        setProvider((current) => {
          if (current) return current;
          const p = data.providers[0];
          return p.type ?? p.name ?? '';
        });
      }
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const loadModels = useCallback(async () => {
    if (!provider) return;
    try {
      const r = await fetch(`/api/llm/models?provider=${encodeURIComponent(provider)}`);
      const data = await r.json();
      if (data.success && data.models?.length) {
        setModels(normalizeModelList(data.models));
      } else {
        setModels([]);
      }
    } catch {
      setModels([]);
    }
  }, [provider]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      await loadProviders();
      if (!cancelled) setLoading(false);
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [loadProviders]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const loadModel = async (modelName: string) => {
    setAction(`load-${modelName}`);
    setError(null);
    try {
      const r = await fetch('/api/llm/models/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelName, provider: provider || undefined }),
      });
      const data = await r.json();
      if (!r.ok) setError((data as { detail?: string }).detail ?? 'Load failed');
      else await loadModels();
    } catch (e) {
      setError(String(e));
    } finally {
      setAction(null);
    }
  };

  const unloadModel = async () => {
    setAction('unload');
    setError(null);
    try {
      const r = await fetch('/api/llm/models/unload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: provider || undefined }),
      });
      const data = await r.json();
      if (!r.ok) setError((data as { detail?: string }).detail ?? 'Unload failed');
      else await loadModels();
    } catch (e) {
      setError(String(e));
    } finally {
      setAction(null);
    }
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
      <h1 className='text-2xl font-bold tracking-tight'>Local LLM Stack</h1>
      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      <Card>
        <CardHeader className='flex flex-row items-center justify-between pb-2'>
          <CardTitle className='text-base font-medium flex items-center gap-2'>
            <Cpu className='h-5 w-5' /> Providers
          </CardTitle>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className='rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800'
          >
            {providers.length === 0 && <option value=''>No providers</option>}
            {providers.map((p) => {
              const id = p.type ?? p.name ?? '';
              return (
                <option key={id} value={id}>
                  {id}
                </option>
              );
            })}
          </select>
        </CardHeader>
        <CardContent className='text-sm text-slate-600 dark:text-slate-400'>
          {providers.length === 0 && (
            <p>
              No LLM providers registered. Register Ollama or LM Studio via API: POST
              /api/llm/providers/register.
            </p>
          )}
          {providers.length > 0 && (
            <ul className='list-inside list-disc space-y-1'>
              {providers.map((p) => {
                const id = p.type ?? p.name ?? '';
                return (
                  <li key={id}>
                    <span className='font-medium text-slate-800 dark:text-slate-200'>{id}</span>
                    {p.base_url != null && (
                      <span className='ml-2 text-slate-500'>({String(p.base_url)})</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className='flex flex-row items-center justify-between pb-2'>
          <CardTitle className='text-base font-medium flex items-center gap-2'>
            <Box className='h-5 w-5' /> Models
          </CardTitle>
          {provider && (
            <Button
              size='sm'
              variant='outline'
              onClick={unloadModel}
              disabled={action === 'unload'}
            >
              {action === 'unload' ? (
                <Loader2 className='h-4 w-4 animate-spin' />
              ) : (
                <Square className='h-4 w-4' />
              )}
              <span className='ml-1'>Unload model</span>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {!provider && <p className='text-sm text-slate-500'>Select a provider above.</p>}
          {provider && models.length === 0 && (
            <p className='text-sm text-slate-500'>
              No models listed for this provider. Start Ollama/LM Studio and pull a model.
            </p>
          )}
          {provider && models.length > 0 && (
            <ul className='space-y-2'>
              {models.map((m) => (
                <li
                  key={m.name}
                  className='flex items-center justify-between rounded-lg border border-slate-200 py-2 px-3 dark:border-slate-700'
                >
                  <span className='font-medium'>{m.name}</span>
                  <Button
                    size='sm'
                    variant='outline'
                    onClick={() => loadModel(m.name)}
                    disabled={action !== null}
                  >
                    {action === `load-${m.name}` ? (
                      <Loader2 className='h-4 w-4 animate-spin' />
                    ) : (
                      <Play className='h-4 w-4' />
                    )}
                    <span className='ml-1'>Load</span>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
