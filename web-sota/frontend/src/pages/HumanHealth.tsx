import { useCallback, useEffect, useState } from 'react';
import { Activity, Droplet, Dumbbell, Heart, Scale } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type TrendInfo = {
  count: number;
  latest: number;
  min: number;
  max: number;
  avg: number;
};

type HealthPoint = {
  id: number;
  metric: string;
  timestamp: number;
  value: number;
  unit: string;
  source: string;
  notes: string;
};

const inputCls =
  'w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none';

const METRIC_LABELS: Record<string, string> = {
  weight_kg: 'Weight',
  sys_mmhg: 'Systolic',
  dia_mmhg: 'Diastolic',
  pulse_bpm: 'Pulse',
  glucose_mgdl: 'Glucose',
  workout_min: 'Workout',
};

function fmtTs(ts: number): string {
  return new Date(ts * 1000).toLocaleString('de-AT', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function HumanHealth() {
  const [trends, setTrends] = useState<Record<string, TrendInfo>>({});
  const [recent, setRecent] = useState<HealthPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [weight, setWeight] = useState('');
  const [sys, setSys] = useState('');
  const [dia, setDia] = useState('');
  const [pulse, setPulse] = useState('');
  const [glucose, setGlucose] = useState('');
  const [glucoseUnit, setGlucoseUnit] = useState('mgdl');
  const [workoutMin, setWorkoutMin] = useState('');
  const [workoutKind, setWorkoutKind] = useState('walk');
  const [workoutKm, setWorkoutKm] = useState('');

  const loadAll = useCallback(async () => {
    try {
      const [t, l] = await Promise.all([
        fetch('/api/wellness/trends?days=90').then((r) => r.json()),
        fetch('/api/wellness/list?days=30').then((r) => r.json()),
      ]);
      if (t.success) setTrends(t.metrics ?? {});
      if (l.success) setRecent((l.points ?? []).slice(-10).reverse());
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const post = async (url: string, body: unknown) => {
    setSaving(true);
    setError(null);
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `HTTP ${r.status}`);
      }
      await loadAll();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const logWeight = () =>
    post('/api/wellness/log', {
      metric: 'weight_kg',
      value: Number(weight),
      unit: 'kg',
    }).then(() => setWeight(''));

  const logBp = () =>
    post('/api/wellness/bp', {
      systolic: Number(sys),
      diastolic: Number(dia),
      ...(pulse ? { pulse: Number(pulse) } : {}),
    }).then(() => {
      setSys('');
      setDia('');
      setPulse('');
    });

  const logGlucose = () =>
    post('/api/wellness/log', {
      metric: 'glucose_mgdl',
      value: Number(glucose),
      unit: glucoseUnit === 'mmol' ? 'mmol/L' : 'mg/dL',
    }).then(() => setGlucose(''));

  const logWorkout = () =>
    post('/api/wellness/workout', {
      minutes: Number(workoutMin),
      kind: workoutKind,
      ...(workoutKm ? { km: Number(workoutKm) } : {}),
    }).then(() => {
      setWorkoutMin('');
      setWorkoutKm('');
    });

  const deletePoint = async (id: number) => {
    try {
      await fetch(`/api/wellness/${id}`, { method: 'DELETE' });
      await loadAll();
    } catch (e) {
      setError(String(e));
    }
  };

  const latest = (m: string) => trends[m]?.latest;

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Human Health</h1>
      {error && <p className='text-sm text-red-400'>{error}</p>}

      <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
        <Card>
          <CardContent className='flex items-center gap-3 pt-6'>
            <Scale className='h-8 w-8 text-indigo-400' />
            <div>
              <p className='text-xs text-slate-500'>Weight</p>
              <p className='text-xl font-semibold text-slate-100'>
                {latest('weight_kg') != null ? `${latest('weight_kg')} kg` : '—'}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className='flex items-center gap-3 pt-6'>
            <Heart className='h-8 w-8 text-rose-400' />
            <div>
              <p className='text-xs text-slate-500'>Blood pressure</p>
              <p className='text-xl font-semibold text-slate-100'>
                {latest('sys_mmhg') != null ? `${latest('sys_mmhg')}/${latest('dia_mmhg')}` : '—'}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className='flex items-center gap-3 pt-6'>
            <Droplet className='h-8 w-8 text-sky-400' />
            <div>
              <p className='text-xs text-slate-500'>Glucose mg/dL</p>
              <p className='text-xl font-semibold text-slate-100'>
                {latest('glucose_mgdl') != null
                  ? `${Math.round(latest('glucose_mgdl') ?? 0)}`
                  : '—'}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className='flex items-center gap-3 pt-6'>
            <Dumbbell className='h-8 w-8 text-emerald-400' />
            <div>
              <p className='text-xs text-slate-500'>Workout min (90d)</p>
              <p className='text-xl font-semibold text-slate-100'>
                {trends.workout_min
                  ? `${Math.round(
                      (trends.workout_min.avg ?? 0) * (trends.workout_min.count ?? 0),
                    )} total`
                  : '—'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className='grid gap-4 md:grid-cols-2'>
        <Card>
          <CardHeader>
            <CardTitle className='text-base'>Log weight (kg)</CardTitle>
          </CardHeader>
          <CardContent className='flex gap-2'>
            <input
              className={inputCls}
              type='number'
              step='0.1'
              placeholder='e.g. 72.5'
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              data-testid='weight-input'
            />
            <Button
              type='button'
              disabled={saving || !weight}
              onClick={logWeight}
              data-testid='weight-save'
            >
              Save
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className='text-base'>Log blood pressure (mmHg)</CardTitle>
          </CardHeader>
          <CardContent className='flex gap-2'>
            <input
              className={inputCls}
              type='number'
              placeholder='sys'
              value={sys}
              onChange={(e) => setSys(e.target.value)}
              data-testid='bp-sys'
            />
            <input
              className={inputCls}
              type='number'
              placeholder='dia'
              value={dia}
              onChange={(e) => setDia(e.target.value)}
              data-testid='bp-dia'
            />
            <input
              className={inputCls}
              type='number'
              placeholder='pulse?'
              value={pulse}
              onChange={(e) => setPulse(e.target.value)}
              data-testid='bp-pulse'
            />
            <Button
              type='button'
              disabled={saving || !sys || !dia}
              onClick={logBp}
              data-testid='bp-save'
            >
              Save
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className='text-base'>Log glucose</CardTitle>
          </CardHeader>
          <CardContent className='flex gap-2'>
            <input
              className={inputCls}
              type='number'
              placeholder='value'
              value={glucose}
              onChange={(e) => setGlucose(e.target.value)}
              data-testid='glucose-input'
            />
            <select
              className={inputCls}
              value={glucoseUnit}
              onChange={(e) => setGlucoseUnit(e.target.value)}
              data-testid='glucose-unit'
            >
              <option value='mgdl'>mg/dL</option>
              <option value='mmol'>mmol/L</option>
            </select>
            <Button
              type='button'
              disabled={saving || !glucose}
              onClick={logGlucose}
              data-testid='glucose-save'
            >
              Save
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className='text-base'>Log workout</CardTitle>
          </CardHeader>
          <CardContent className='flex gap-2'>
            <input
              className={inputCls}
              type='number'
              placeholder='min'
              value={workoutMin}
              onChange={(e) => setWorkoutMin(e.target.value)}
              data-testid='workout-min'
            />
            <select
              className={inputCls}
              value={workoutKind}
              onChange={(e) => setWorkoutKind(e.target.value)}
              data-testid='workout-kind'
            >
              <option value='walk'>walk</option>
              <option value='bike'>bike</option>
              <option value='run'>run</option>
              <option value='row'>row</option>
              <option value='other'>other</option>
            </select>
            <input
              className={inputCls}
              type='number'
              step='0.1'
              placeholder='km?'
              value={workoutKm}
              onChange={(e) => setWorkoutKm(e.target.value)}
              data-testid='workout-km'
            />
            <Button
              type='button'
              disabled={saving || !workoutMin}
              onClick={logWorkout}
              data-testid='workout-save'
            >
              Save
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className='text-base'>Recent entries</CardTitle>
        </CardHeader>
        <CardContent>
          {recent.length === 0 ? (
            <p className='text-sm text-slate-500'>
              Nothing logged yet — entries appear here with trends.
            </p>
          ) : (
            <ul className='space-y-1 text-sm'>
              {recent.map((p) => (
                <li
                  key={p.id}
                  className='flex items-center justify-between gap-2 rounded bg-slate-900 px-3 py-1.5'
                >
                  <span className='text-slate-300'>
                    {METRIC_LABELS[p.metric] ?? p.metric}: <strong>{p.value}</strong> {p.unit}
                    {p.notes ? ` · ${p.notes}` : ''}{' '}
                    <span className='text-slate-500'>
                      · {fmtTs(p.timestamp)} · {p.source}
                    </span>
                  </span>
                  <Button type='button' size='sm' variant='ghost' onClick={() => deletePoint(p.id)}>
                    Delete
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <p className='mt-3 flex items-center gap-2 text-xs text-slate-500'>
            <Activity className='h-3 w-3' />
            Vendor sync next: Withings OAuth (scale + BP), FTMS BLE (bike/belt live metrics).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
