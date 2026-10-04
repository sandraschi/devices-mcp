import { useCallback, useEffect, useState } from 'react';
import { AirVent, Snowflake } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type ClimateDevice = {
  device_id: string;
  name: string;
  host: string;
  power: boolean;
  mode: string;
  setpoint_c: number;
  room_temp_c: number;
  fan_speed: string;
  swing: boolean;
  power_w: number;
  mock: boolean;
};

const MODES = ['off', 'cool', 'heat', 'dry', 'fan', 'auto'];
const FANS = ['auto', 'low', 'medium', 'high', 'turbo'];

export function Climate() {
  const [devices, setDevices] = useState<ClimateDevice[]>([]);
  const [allMock, setAllMock] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      const r = await fetch('/api/climate');
      const j = await r.json();
      if (j.success) {
        setDevices(j.devices ?? []);
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
    const t = setInterval(loadList, 15000);
    return () => clearInterval(t);
  }, [loadList]);

  const control = async (deviceId: string, body: Record<string, unknown>) => {
    setBusy(deviceId);
    setError(null);
    try {
      const r = await fetch(`/api/climate/${deviceId}/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `HTTP ${r.status}`);
      }
      await loadList();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Climate</h1>
      {allMock && (
        <p
          className='rounded-md border border-amber-700 bg-amber-950 px-3 py-2 text-sm text-amber-200'
          data-testid='mock-banner'
        >
          MOCK — demo unit until the winter PortaSplit arrives. The whole surface (power, mode,
          setpoint, fan, swing) is live against simulation.
        </p>
      )}
      {error && <p className='text-sm text-red-400'>{error}</p>}
      <div className='grid gap-4 md:grid-cols-2'>
        {devices.map((d) => (
          <Card key={d.device_id}>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <AirVent className='h-5 w-5 text-sky-400' />
                {d.name}
                {d.mock && (
                  <span className='rounded bg-amber-900 px-1.5 py-0.5 text-[10px] font-semibold text-amber-200'>
                    MOCK
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className='space-y-3'>
              <div className='flex items-center gap-2 text-2xl font-semibold text-slate-100'>
                <Snowflake className='h-5 w-5 text-sky-300' />
                {d.room_temp_c.toFixed(1)}&deg;C
                <span className='text-sm font-normal text-slate-400'>
                  room &middot; set {d.setpoint_c.toFixed(0)}&deg;C &middot;{' '}
                  {d.power ? `${Math.round(d.power_w)} W` : 'standby'}
                </span>
              </div>
              <div className='flex flex-wrap gap-2'>
                <Button
                  type='button'
                  size='sm'
                  variant={d.power ? 'default' : 'outline'}
                  disabled={busy === d.device_id}
                  onClick={() => control(d.device_id, { power: !d.power })}
                  data-testid='climate-power'
                >
                  {d.power ? 'Turn off' : 'Turn on'}
                </Button>
                <select
                  className='rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100'
                  value={d.mode}
                  disabled={busy === d.device_id}
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
                  className='rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100'
                  value={d.fan_speed}
                  disabled={busy === d.device_id}
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
              <div className='flex items-center gap-2'>
                <Button
                  type='button'
                  size='sm'
                  variant='outline'
                  disabled={busy === d.device_id}
                  onClick={() =>
                    control(d.device_id, {
                      setpoint: Math.min(30, d.setpoint_c + 1),
                    })
                  }
                  data-testid='climate-plus'
                >
                  +1&deg;
                </Button>
                <Button
                  type='button'
                  size='sm'
                  variant='outline'
                  disabled={busy === d.device_id}
                  onClick={() =>
                    control(d.device_id, {
                      setpoint: Math.max(16, d.setpoint_c - 1),
                    })
                  }
                  data-testid='climate-minus'
                >
                  &minus;1&deg;
                </Button>
                <Button
                  type='button'
                  size='sm'
                  variant={d.swing ? 'default' : 'ghost'}
                  disabled={busy === d.device_id}
                  onClick={() => control(d.device_id, { swing: !d.swing })}
                  data-testid='climate-swing'
                >
                  Swing {d.swing ? 'on' : 'off'}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {devices.length === 0 && !error && (
        <p className='text-sm text-slate-500'>No climate units found.</p>
      )}
    </div>
  );
}
