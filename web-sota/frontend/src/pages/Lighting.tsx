import { AlertCircle, CheckCircle, Hand, Lightbulb, Loader2, Radio } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface LightDevice {
  device_id?: string;
  id?: string;
  name?: string;
  is_on?: boolean;
  on?: boolean;
  brightness?: number;
  brightness_percent?: number;
  rgb?: [number, number, number];
  hue?: number;
  saturation?: number;
  light_type?: string;
  [key: string]: unknown;
}

interface LightingStatus {
  devices: LightDevice[];
  total_lights: number;
  active_lights: number;
  success?: boolean;
}

interface ScenesResponse {
  scenes?: string[];
  success?: boolean;
}

interface HueBridgeInfo {
  bridge_id?: string;
  internalipaddress?: string;
  macaddress?: string;
  name?: string;
}

interface HueStatus {
  enabled?: boolean;
  config_issue?: boolean;
  phue_available?: boolean;
  bridge_ip?: string | null;
  has_username?: boolean;
  connected?: boolean;
  needs_bridge_ip?: boolean;
  needs_pairing?: boolean;
  needs_reconnect?: boolean;
  lights_count?: number;
  clip_v2_available?: boolean;
  clip_v2_error?: string | null;
  message?: string;
  last_error?: string | null;
  error?: string;
  hint?: string;
}

interface MotionAwareAreaRow {
  id?: string;
  name?: string;
  enabled?: boolean;
  motion?: boolean;
}

interface MotionAwareDetail {
  enabled?: boolean;
  feature?: string;
  api?: string;
  clip_v2_available?: boolean;
  clip_v2_error?: string | null;
  reason?: string;
  convenience_area_motions?: MotionAwareAreaRow[];
  security_area_motions?: MotionAwareAreaRow[];
  areas_reporting_motion?: number;
  fetch_hint?: string | null;
}

function parseErrorBody(data: unknown): string {
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: string };
    if (typeof d.detail === 'string') return d.detail;
    if (Array.isArray(d.detail))
      return d.detail
        .map((x: { msg?: string }) => x.msg ?? '')
        .filter(Boolean)
        .join('; ');
    if (d.message) return d.message;
  }
  return 'Request failed';
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('')}`;
}

function hexToRgb(hex: string): [number, number, number] {
  const m = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  if (!m) return [255, 255, 255];
  return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
}

export function Lighting() {
  const [status, setStatus] = useState<LightingStatus | null>(null);
  const [scenes, setScenes] = useState<ScenesResponse | null>(null);
  const [hueStatus, setHueStatus] = useState<HueStatus | null>(null);
  const [discovered, setDiscovered] = useState<HueBridgeInfo[]>([]);
  const [bridgeIpInput, setBridgeIpInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [hueBusy, setHueBusy] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [motionAware, setMotionAware] = useState<MotionAwareDetail | null>(null);

  const load = async () => {
    try {
      const [statusRes, scenesRes, hueRes, maRes] = await Promise.allSettled([
        fetch('/api/lighting/status'),
        fetch('/api/lighting/scenes'),
        fetch('/api/lighting/hue/status'),
        fetch('/api/lighting/hue/motionaware/status'),
      ]);
      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        setStatus(await statusRes.value.json());
      } else if (statusRes.status === 'fulfilled' && !statusRes.value.ok) {
        setStatus({ devices: [], total_lights: 0, active_lights: 0 });
      }
      if (scenesRes.status === 'fulfilled' && scenesRes.value.ok) {
        setScenes(await scenesRes.value.json());
      }
      if (hueRes.status === 'fulfilled' && hueRes.value.ok) {
        const h = await hueRes.value.json();
        setHueStatus(h);
        if (h.bridge_ip && !bridgeIpInput) setBridgeIpInput(String(h.bridge_ip));
      } else {
        setHueStatus(null);
      }
      if (maRes.status === 'fulfilled' && maRes.value.ok) {
        const ma = await maRes.value.json();
        const detail = ma.motionaware as MotionAwareDetail | undefined;
        setMotionAware(detail ?? null);
      } else {
        setMotionAware(null);
      }
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [load]);

  const discoverBridges = async () => {
    setDiscoverLoading(true);
    setError(null);
    try {
      const r = await fetch('/api/lighting/hue/discover');
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(parseErrorBody(data));
        return;
      }
      setDiscovered(Array.isArray(data.bridges) ? data.bridges : []);
    } catch (e) {
      setError(String(e));
    } finally {
      setDiscoverLoading(false);
    }
  };

  const saveBridgeIp = async (ip: string) => {
    const trimmed = ip.trim();
    if (!trimmed) return;
    setHueBusy(true);
    setError(null);
    try {
      const r = await fetch('/api/lighting/hue/bridge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bridge_ip: trimmed }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(parseErrorBody(data));
        return;
      }
      setBridgeIpInput(trimmed);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setHueBusy(false);
    }
  };

  const pairBridge = async () => {
    const ip = bridgeIpInput.trim();
    if (!ip) {
      setError('Enter the bridge IP first (discover above or from the Hue app).');
      return;
    }
    setHueBusy(true);
    setError(null);
    try {
      const r = await fetch('/api/lighting/hue/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bridge_ip: ip }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(parseErrorBody(data));
        return;
      }
      if (data.success !== true) {
        const msg =
          (data.needs_button && data.hint) || data.error || data.message || 'Pairing failed';
        setError(String(msg));
        return;
      }
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setHueBusy(false);
    }
  };

  const reconnectHue = async () => {
    setHueBusy(true);
    setError(null);
    try {
      const r = await fetch('/api/lighting/hue/reconnect', { method: 'POST' });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(parseErrorBody(data));
        return;
      }
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setHueBusy(false);
    }
  };

  const control = async (deviceId: string, action: string, body?: Record<string, unknown>) => {
    setBusy(deviceId);
    try {
      const url = `/api/lighting/control?device_id=${encodeURIComponent(deviceId)}&action=${encodeURIComponent(action)}`;
      const r = await fetch(url, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      if (r.ok) await load();
      else setError(parseErrorBody(await r.json().catch(() => ({}))) || 'Control failed');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const setBrightness = (deviceId: string, value: number) => {
    control(deviceId, 'brightness', { brightness_percent: value });
  };

  const setColor = (deviceId: string, hex: string) => {
    control(deviceId, 'color', { rgb: hexToRgb(hex) });
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const devices = status?.devices ?? [];
  const showHueCard = hueStatus && hueStatus.enabled !== false && !hueStatus.config_issue;

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Lighting</h1>

      {showHueCard && (
        <Card className={hueStatus?.connected ? 'border-green-200 dark:border-green-900' : ''}>
          <CardHeader className='flex flex-row items-center justify-between pb-2'>
            <CardTitle className='text-base font-medium'>Philips Hue Bridge</CardTitle>
            {hueStatus?.connected ? (
              <CheckCircle className='h-5 w-5 text-green-600 dark:text-green-400' />
            ) : (
              <Radio className='h-5 w-5 text-slate-400' />
            )}
          </CardHeader>
          <CardContent className='space-y-3 text-sm'>
            <p>{hueStatus?.message}</p>
            {hueStatus?.phue_available === false && (
              <p className='text-amber-700 dark:text-amber-300'>
                Install the Python package: <code className='text-xs'>pip install phue</code>, then
                restart the server.
              </p>
            )}
            {hueStatus?.last_error && !hueStatus?.connected && (
              <p className='text-xs text-amber-700 dark:text-amber-300/90'>
                {hueStatus.last_error}
              </p>
            )}

            {hueStatus?.phue_available !== false && (
              <>
                <div className='flex flex-wrap items-end gap-2'>
                  <div className='flex flex-col gap-1'>
                    <label className='text-xs text-slate-500'>Bridge IP (LAN)</label>
                    <input
                      type='text'
                      placeholder='e.g. 192.168.0.236'
                      value={bridgeIpInput}
                      onChange={(e) => setBridgeIpInput(e.target.value)}
                      className='min-w-[10rem] rounded-md border border-slate-300 bg-white px-2 py-1.5 font-mono text-sm dark:border-slate-600 dark:bg-slate-900'
                    />
                  </div>
                  <Button
                    type='button'
                    variant='outline'
                    size='sm'
                    disabled={hueBusy || !bridgeIpInput.trim()}
                    onClick={() => saveBridgeIp(bridgeIpInput)}
                  >
                    Save IP
                  </Button>
                  <Button
                    type='button'
                    variant='outline'
                    size='sm'
                    disabled={discoverLoading}
                    onClick={discoverBridges}
                  >
                    {discoverLoading ? 'Searching…' : 'Find bridges'}
                  </Button>
                </div>
                {discovered.length > 0 && (
                  <div className='flex flex-wrap gap-2'>
                    {discovered.map((b) => (
                      <Button
                        key={b.internalipaddress ?? b.bridge_id}
                        type='button'
                        variant='outline'
                        size='sm'
                        disabled={hueBusy}
                        onClick={() => {
                          const ip = b.internalipaddress ?? '';
                          setBridgeIpInput(ip);
                          void saveBridgeIp(ip);
                        }}
                      >
                        Use {b.internalipaddress}
                        {b.name ? ` (${b.name})` : ''}
                      </Button>
                    ))}
                  </div>
                )}
                <p className='text-xs text-slate-500 dark:text-slate-400'>
                  If discovery is empty, open the Hue app → Settings → Hue bridges and copy the IP
                  (same Wi‑Fi as this PC). To let <em>this server</em> control lights, you will
                  later press the{' '}
                  <strong className='font-semibold text-slate-700 dark:text-slate-200'>
                    physical link button
                  </strong>{' '}
                  on the Hue Bridge — not something you toggle only in the phone app. Credentials
                  are stored in <code className='text-[11px]'>hue_bridge.cache</code> in the repo
                  (gitignored).
                </p>

                {hueStatus?.needs_pairing && (
                  <div
                    role='alert'
                    className='rounded-lg border-2 border-amber-400 bg-amber-50 p-4 shadow-sm dark:border-amber-600 dark:bg-amber-950/50'
                  >
                    <div className='flex flex-col gap-3 sm:flex-row sm:gap-4'>
                      <div className='flex shrink-0 justify-center sm:block'>
                        <div className='flex h-14 w-14 items-center justify-center rounded-full border-2 border-amber-500 bg-amber-100 dark:border-amber-500 dark:bg-amber-900/60'>
                          <Hand
                            className='h-8 w-8 text-amber-800 dark:text-amber-200'
                            aria-hidden
                          />
                        </div>
                      </div>
                      <div className='min-w-0 flex-1 space-y-3'>
                        <div>
                          <p className='text-base font-semibold tracking-tight text-amber-950 dark:text-amber-50'>
                            Press the button on the Hue Bridge before you pair
                          </p>
                          <p className='mt-1.5 text-sm leading-relaxed text-amber-950/90 dark:text-amber-100/90'>
                            The Hue app on your phone does{' '}
                            <strong className='font-semibold'>not</strong> grant access to this
                            webapp. You must use the{' '}
                            <strong className='font-semibold'>hardware link button</strong> on the
                            bridge (Hue Bridge v2: large round button on the front of the white
                            box).
                          </p>
                        </div>
                        <ol className='list-decimal space-y-2 pl-5 text-sm text-amber-950 dark:text-amber-50'>
                          <li>
                            Walk to your Hue Bridge (usually near your router) and find the{' '}
                            <strong className='font-semibold'>large round button</strong> on the
                            front.
                          </li>
                          <li>
                            <strong className='font-semibold'>Press it once</strong> (you may see
                            LEDs blink). You have roughly{' '}
                            <strong className='font-semibold'>30 seconds</strong>.
                          </li>
                          <li>
                            While that window is open, click{' '}
                            <strong className='font-semibold'>Pair now</strong> below.
                          </li>
                        </ol>
                        <Button
                          type='button'
                          className='w-full sm:w-auto'
                          disabled={hueBusy || !bridgeIpInput.trim()}
                          onClick={pairBridge}
                        >
                          {hueBusy ? 'Pairing…' : 'Pair now'}
                        </Button>
                        <p className='text-xs leading-relaxed text-amber-900/85 dark:text-amber-200/85'>
                          If you see “link button” or pairing fails: press the round bridge button
                          again, then click Pair now right away.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {(hueStatus?.needs_reconnect ||
                  (hueStatus?.has_username && !hueStatus?.connected)) && (
                  <Button type='button' variant='outline' disabled={hueBusy} onClick={reconnectHue}>
                    {hueBusy ? 'Connecting…' : 'Reconnect to Hue Bridge'}
                  </Button>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {showHueCard && hueStatus?.connected && (
        <Card>
          <CardHeader className='pb-2'>
            <CardTitle className='text-base font-medium'>MotionAware</CardTitle>
            <p className='text-xs font-normal text-slate-500 dark:text-slate-400'>
              Signify Hue API v2 — Zigbee mesh motion areas you set up in the Hue app (
              <code className='text-[11px]'>convenience_area_motion</code> /{' '}
              <code className='text-[11px]'>security_area_motion</code>).
            </p>
          </CardHeader>
          <CardContent className='space-y-3 text-sm'>
            {!motionAware && (
              <p className='text-slate-500 dark:text-slate-400'>Loading motion area status…</p>
            )}
            {motionAware && !motionAware.enabled && (
              <p className='text-slate-600 dark:text-slate-400'>
                {motionAware.reason ??
                  hueStatus?.clip_v2_error ??
                  'Hue CLIP v2 not available (needs Bridge Pro with HTTPS reachable from this server).'}
              </p>
            )}
            {motionAware?.enabled && (
              <>
                {motionAware.fetch_hint ? (
                  <p className='text-xs text-amber-800 dark:text-amber-200'>
                    {motionAware.fetch_hint}
                  </p>
                ) : null}
                <p className='text-xs text-slate-500'>
                  Areas reporting motion now:{' '}
                  <strong>{motionAware.areas_reporting_motion ?? 0}</strong>
                </p>
                {(motionAware.convenience_area_motions?.length ?? 0) > 0 && (
                  <div>
                    <p className='mb-1 text-xs font-medium text-slate-600 dark:text-slate-300'>
                      Convenience / lighting
                    </p>
                    <ul className='space-y-1 text-xs'>
                      {motionAware.convenience_area_motions!.map((a) => (
                        <li
                          key={`c-${a.id}`}
                          className='flex justify-between gap-2 rounded border border-slate-200 px-2 py-1 dark:border-slate-600'
                        >
                          <span className='truncate'>{a.name ?? a.id}</span>
                          <span
                            className={
                              a.motion
                                ? 'font-medium text-amber-700 dark:text-amber-300'
                                : 'text-slate-400'
                            }
                          >
                            {a.motion ? 'motion' : 'clear'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(motionAware.security_area_motions?.length ?? 0) > 0 && (
                  <div>
                    <p className='mb-1 text-xs font-medium text-slate-600 dark:text-slate-300'>
                      Security areas
                    </p>
                    <ul className='space-y-1 text-xs'>
                      {motionAware.security_area_motions!.map((a) => (
                        <li
                          key={`s-${a.id}`}
                          className='flex justify-between gap-2 rounded border border-slate-200 px-2 py-1 dark:border-slate-600'
                        >
                          <span className='truncate'>{a.name ?? a.id}</span>
                          <span
                            className={
                              a.motion
                                ? 'font-medium text-amber-700 dark:text-amber-300'
                                : 'text-slate-400'
                            }
                          >
                            {a.motion ? 'motion' : 'clear'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(motionAware.convenience_area_motions?.length ?? 0) === 0 &&
                  (motionAware.security_area_motions?.length ?? 0) === 0 && (
                    <p className='text-xs text-slate-500'>
                      No motion areas returned yet. Create a Motion area in the Hue app (Hue Bridge
                      Pro), then refresh this page.
                    </p>
                  )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {hueStatus?.enabled === false && hueStatus.config_issue && (
        <Card>
          <CardContent className='pt-6'>
            <p className='text-sm text-slate-600 dark:text-slate-400'>{hueStatus.message}</p>
          </CardContent>
        </Card>
      )}

      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      <p className='text-sm text-slate-500 dark:text-slate-400'>
        {status?.total_lights ?? 0} lights · {status?.active_lights ?? 0} on
      </p>
      <div className='grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'>
        {devices.length === 0 ? (
          <p className='text-slate-500'>
            No lights in the list yet. Finish Hue setup above and/or configure Tapo lighting in
            config.yaml.
          </p>
        ) : (
          devices.map((d) => {
            const id = (d.device_id ?? d.id ?? '') as string;
            const name = (d.name ?? (id || 'Light')) as string;
            const isOn = (d.is_on ?? d.on ?? false) as boolean;
            const brightness = (d.brightness ?? d.brightness_percent ?? 100) as number;
            const rgb = d.rgb as [number, number, number] | undefined;
            const hasColor = Array.isArray(rgb) && rgb.length >= 3;
            const colorHex = hasColor ? rgbToHex(rgb[0], rgb[1], rgb[2]) : '#ffffff';
            const isDisabled = busy === id;

            return (
              <Card key={id} className='overflow-hidden'>
                <CardContent className='p-3'>
                  <div className='flex items-center gap-2'>
                    <button
                      type='button'
                      onClick={() => control(id, 'toggle')}
                      disabled={isDisabled}
                      className='shrink-0 rounded-full p-1.5 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50'
                      title={isOn ? 'Turn off' : 'Turn on'}
                    >
                      <Lightbulb
                        className={`h-6 w-6 ${isOn ? 'text-amber-500' : 'text-slate-400'}`}
                      />
                    </button>
                    <span className='min-w-0 flex-1 truncate text-sm font-medium' title={name}>
                      {name}
                    </span>
                  </div>
                  <div className='mt-2 space-y-2'>
                    <div className='flex items-center gap-2'>
                      <span className='text-xs text-slate-500'>Brightness</span>
                      <input
                        type='range'
                        min='0'
                        max='100'
                        value={brightness}
                        disabled={!isOn || isDisabled}
                        onChange={(e) => setBrightness(id, Number(e.target.value))}
                        className='h-2 flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 dark:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-indigo-500'
                      />
                      <span className='w-7 text-right text-xs text-slate-500'>{brightness}%</span>
                    </div>
                    {hasColor && (
                      <div className='flex items-center gap-2'>
                        <span className='text-xs text-slate-500'>Color</span>
                        <input
                          type='color'
                          value={colorHex}
                          disabled={!isOn || isDisabled}
                          onChange={(e) => setColor(id, e.target.value)}
                          className='h-8 w-14 cursor-pointer rounded border border-slate-200 bg-transparent p-0 dark:border-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                        />
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
      {scenes?.scenes && scenes.scenes.length > 0 && (
        <Card>
          <CardContent className='p-4'>
            <p className='mb-2 text-sm font-medium'>Scenes</p>
            <ul className='flex flex-wrap gap-2 text-sm text-slate-600 dark:text-slate-400'>
              {scenes.scenes.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
