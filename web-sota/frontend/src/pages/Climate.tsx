import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AirVent, Droplets, Snowflake, Thermometer, Zap } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

type ClimateDevice = {
  device_id: string;
  name: string;
  host: string;
  power: boolean;
  mode: string;
  setpoint_c: number;
  room_temp_c: number | null;
  fan_speed: string;
  swing: boolean;
  power_w: number | null;
  mock: boolean;
  online: boolean;
  outdoor_temp_c: number | null;
  humidity_pct: number | null;
  eco: boolean;
  turbo: boolean;
  sleep: boolean;
  error_code: number;
  filter_alert: boolean;
  energy_kwh: number | null;
  scenario: string;
  last_error: string;
};

type ApiError = { error?: string; suggestions?: string[] } | string;

const MODES = ['off', 'cool', 'heat', 'dry', 'fan', 'auto'];
const FANS = ['auto', 'low', 'medium', 'high', 'turbo'];
const SCENARIO_LABELS: Record<string, string> = {
  heatwave: 'Heatwave',
  cold_snap: 'Cold snap',
  offline: 'Go offline',
  online: 'Back online',
  fault: 'Inject fault',
  clear_fault: 'Clear fault',
  filter_alert: 'Filter alert',
  reset: 'Reset',
};

const SELECT_CLASS =
  'rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100 disabled:opacity-50';

function describeError(detail: ApiError | undefined, status: number): string {
  if (!detail) return `HTTP ${status}`;
  if (typeof detail === 'string') return detail;
  const hint = detail.suggestions?.length ? ` (${detail.suggestions[0]})` : '';
  return `${detail.error ?? `HTTP ${status}`}${hint}`;
}

function Badge({
  tone,
  children,
  testId,
}: { tone: 'amber' | 'red' | 'sky' | 'slate'; children: string; testId?: string }) {
  const tones = {
    amber: 'bg-amber-900 text-amber-200',
    red: 'bg-red-900 text-red-200',
    sky: 'bg-sky-900 text-sky-200',
    slate: 'bg-slate-800 text-slate-300',
  };
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${tones[tone]}`}
      data-testid={testId}
    >
      {children}
    </span>
  );
}

export function Climate() {
  const [devices, setDevices] = useState<ClimateDevice[]>([]);
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [allMock, setAllMock] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      const r = await fetch('/api/climate');
      const j = await r.json();
      if (j.success) {
        setDevices(j.devices ?? []);
        setScenarios(j.scenarios ?? []);
        setAllMock(!!j.mock);
      } else {
        setError(j.error ?? 'Failed to load climate units');
      }
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    loadList();
    const t = setInterval(loadList, 5000);
    return () => clearInterval(t);
  }, [loadList]);

  const post = async (path: string, body: Record<string, unknown>, deviceId: string) => {
    setBusy(deviceId);
    setError(null);
    try {
      const r = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = (await r.json().catch(() => ({}))) as { detail?: ApiError };
        throw new Error(describeError(err.detail, r.status));
      }
      await loadList();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const control = (deviceId: string, body: Record<string, unknown>) =>
    post(`/api/climate/${deviceId}/control`, body, deviceId);
  const scenario = (deviceId: string, name: string) =>
    post(`/api/climate/${deviceId}/mock`, { scenario: name }, deviceId);

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Climate</h1>
      {allMock && (
        <p
          className='rounded-md border border-amber-700 bg-amber-950 px-3 py-2 text-sm text-amber-200'
          data-testid='mock-banner'
        >
          MOCK — simulated PortaSplit. Room temperature, power draw, energy and humidity follow a
          physics model; use the scenario buttons to exercise offline, fault and heatwave states.
          Real hardware needs the msmart-ng backend (see docs/MIDEA_PORTASPLIT.md).
        </p>
      )}
      {error && (
        <p className='text-sm text-red-400' data-testid='climate-error'>
          {error}
        </p>
      )}
      <div className='grid gap-4 md:grid-cols-2'>
        {devices.map((d) => {
          const disabled = busy === d.device_id || !d.online;
          return (
            <Card key={d.device_id} data-testid='climate-card'>
              <CardHeader>
                <CardTitle className='flex flex-wrap items-center gap-2 text-base'>
                  <AirVent className='h-5 w-5 text-sky-400' />
                  {d.name}
                  {d.mock && <Badge tone='amber'>MOCK</Badge>}
                  {!d.online && (
                    <Badge tone='red' testId='climate-offline'>
                      OFFLINE
                    </Badge>
                  )}
                  {d.error_code !== 0 && (
                    <Badge tone='red' testId='climate-fault'>
                      {`FAULT ${d.error_code}`}
                    </Badge>
                  )}
                  {d.filter_alert && (
                    <Badge tone='amber' testId='climate-filter'>
                      CLEAN FILTER
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className='space-y-3'>
                {!d.online && d.last_error && (
                  <p className='text-xs text-red-300'>{d.last_error}</p>
                )}
                <div className='flex items-center gap-2 text-2xl font-semibold text-slate-100'>
                  <Snowflake className='h-5 w-5 text-sky-300' />
                  <span data-testid='climate-room'>
                    {d.room_temp_c === null ? '--' : d.room_temp_c.toFixed(1)}&deg;C
                  </span>
                  <span className='text-sm font-normal text-slate-400'>
                    room &middot; set {d.setpoint_c.toFixed(1)}&deg;C
                  </span>
                </div>
                <div className='flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400'>
                  <span className='flex items-center gap-1'>
                    <Thermometer className='h-3 w-3' />
                    outdoor {d.outdoor_temp_c === null ? '--' : `${d.outdoor_temp_c.toFixed(1)}°C`}
                  </span>
                  <span className='flex items-center gap-1'>
                    <Droplets className='h-3 w-3' />
                    {d.humidity_pct === null ? '--' : `${Math.round(d.humidity_pct)}%`}
                  </span>
                  <span className='flex items-center gap-1' data-testid='climate-power-w'>
                    <Zap className='h-3 w-3' />
                    {d.power_w === null || !d.online
                      ? '--'
                      : d.power
                        ? `${Math.round(d.power_w)} W`
                        : 'standby'}
                  </span>
                  <span data-testid='climate-energy'>
                    {d.energy_kwh === null ? '-- kWh' : `${d.energy_kwh.toFixed(2)} kWh`}
                  </span>
                </div>
                <div className='flex flex-wrap gap-2'>
                  <Button
                    type='button'
                    size='sm'
                    variant={d.power ? 'default' : 'outline'}
                    disabled={disabled}
                    onClick={() => control(d.device_id, { power: !d.power })}
                    data-testid='climate-power'
                  >
                    {d.power ? 'Turn off' : 'Turn on'}
                  </Button>
                  <select
                    className={SELECT_CLASS}
                    value={d.mode}
                    disabled={disabled}
                    onChange={(e) => control(d.device_id, { mode: e.target.value })}
                    data-testid='climate-mode'
                  >
                    {MODES.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                  <select
                    className={SELECT_CLASS}
                    value={d.fan_speed}
                    disabled={disabled}
                    onChange={(e) => control(d.device_id, { fan_speed: e.target.value })}
                    data-testid='climate-fan'
                  >
                    {FANS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>
                <div className='flex flex-wrap items-center gap-2'>
                  <Button
                    type='button'
                    size='sm'
                    variant='outline'
                    disabled={disabled}
                    onClick={() =>
                      control(d.device_id, { setpoint: Math.min(30, d.setpoint_c + 1) })
                    }
                    data-testid='climate-plus'
                  >
                    +1&deg;
                  </Button>
                  <Button
                    type='button'
                    size='sm'
                    variant='outline'
                    disabled={disabled}
                    onClick={() =>
                      control(d.device_id, { setpoint: Math.max(16, d.setpoint_c - 1) })
                    }
                    data-testid='climate-minus'
                  >
                    &minus;1&deg;
                  </Button>
                  {(['swing', 'eco', 'turbo', 'sleep'] as const).map((flag) => (
                    <Button
                      key={flag}
                      type='button'
                      size='sm'
                      variant={d[flag] ? 'default' : 'ghost'}
                      disabled={disabled}
                      onClick={() => control(d.device_id, { [flag]: !d[flag] })}
                      data-testid={`climate-${flag}`}
                    >
                      {flag} {d[flag] ? 'on' : 'off'}
                    </Button>
                  ))}
                </div>
                {d.mock && (
                  <div
                    className='space-y-1 border-t border-slate-800 pt-3'
                    data-testid='mock-scenarios'
                  >
                    <p className='text-[11px] uppercase tracking-wide text-slate-500'>
                      Mock scenarios
                    </p>
                    <div className='flex flex-wrap gap-2'>
                      {scenarios.map((s) => (
                        <Button
                          key={s}
                          type='button'
                          size='sm'
                          variant={d.scenario === s ? 'default' : 'outline'}
                          disabled={busy === d.device_id}
                          onClick={() => scenario(d.device_id, s)}
                          data-testid={`scenario-${s}`}
                        >
                          {SCENARIO_LABELS[s] ?? s}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
      {devices.length === 0 && !error && (
        <p className='text-sm text-slate-500'>
          No climate units. Set climate.midea.mock: true for a demo unit, or add real units under
          climate.midea.devices.
        </p>
      )}
    </div>
  );
}
