import {
  AlertCircle,
  Bot,
  Home,
  Lightbulb,
  Loader2,
  Play,
  RotateCw,
  Square,
  Volume2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface RobotItem {
  id: string;
  name: string;
  type: string;
  status: string;
  is_online: boolean;
  battery_percentage?: number;
  error?: string;
}

interface RobotsResponse {
  success: boolean;
  robots: RobotItem[];
  total: number;
  online: number;
}

const DREAME_COMMANDS = [
  { value: 'start_cleaning', label: 'Start clean', icon: Play },
  { value: 'stop_cleaning', label: 'Stop', icon: Square },
  { value: 'pause', label: 'Pause' },
  { value: 'return_home', label: 'Return home', icon: Home },
  { value: 'find_robot', label: 'Find robot', icon: Volume2 },
] as const;

const YAHBOOM_COMMANDS = [
  { value: 'start_patrol', label: 'Move forward', icon: Play },
  { value: 'stop', label: 'Stop all', icon: Square },
  { value: 'return_home', label: 'Move backward', icon: RotateCw },
] as const;

export function Robots() {
  const [data, setData] = useState<RobotsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/robots/');
      if (!r.ok) throw new Error(String(r.status));
      setData(await r.json());
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const sendCommand = async (robotId: string, command: string) => {
    setSending(`${robotId}:${command}`);
    try {
      const r = await fetch(`/api/robots/${encodeURIComponent(robotId)}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, parameters: {} }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: 'Command failed' }));
        setError(err.detail ?? 'Command failed');
      } else {
        setError(null);
        await load();
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setSending(null);
    }
  };

  const sendYahboomMove = async (robotId: string, linear: number, angular: number) => {
    setSending(`${robotId}:move`);
    try {
      const r = await fetch(`/api/robots/${encodeURIComponent(robotId)}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'start_patrol', parameters: { linear, angular } }),
      });
      if (!r.ok) setError((await r.json().catch(() => ({ detail: 'Move failed' }))).detail ?? 'Move failed');
      else { setError(null); await load(); }
    } catch (e) { setError(String(e)); }
    finally { setSending(null); }
  };

  const sendYahboomLight = async (robotId: string, r: number, g: number, b: number) => {
    setSending(`${robotId}:light`);
    try {
      const resp = await fetch(`/api/robots/${encodeURIComponent(robotId)}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'flash_lights', parameters: { r, g, b } }),
      });
      if (!resp.ok) setError('Light command failed');
      else setError(null);
    } catch (e) { setError(String(e)); }
    finally { setSending(null); }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <Loader2 className='h-8 w-8 animate-spin text-slate-400' />
      </div>
    );
  }

  const robots = data?.robots ?? [];

  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>Robots</h1>
      {error && (
        <div className='flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'>
          <AlertCircle className='h-5 w-5 shrink-0' />
          {error}
        </div>
      )}
      <Card>
        <CardHeader className='pb-2'>
          <CardTitle className='text-sm font-medium text-slate-500 dark:text-slate-400'>
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className='text-sm'>
          {data?.total ?? 0} robots · {data?.online ?? 0} online
        </CardContent>
      </Card>

      {robots.length === 0 && (
        <p className='text-slate-500'>No robots registered. Configure them in config.yaml.</p>
      )}

      {robots.length > 0 && (
        <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
          {robots.map((robot) => (
            <Card key={robot.id}>
              <CardHeader className='flex flex-row items-center justify-between pb-2'>
                <CardTitle className='text-base'>{robot.name}</CardTitle>
                <Bot
                  className={`h-4 w-4 ${robot.is_online ? 'text-green-500' : 'text-red-400'}`}
                />
              </CardHeader>
              <CardContent className='space-y-3 text-sm'>
                <p className='text-slate-500'>
                  {robot.type}
                  {robot.status && ` · ${robot.status}`}
                  {robot.battery_percentage != null && ` · ${robot.battery_percentage}%`}
                </p>

                {/* Dreame vacuum controls */}
                {robot.type === 'dreame' && (
                  <div className='flex flex-wrap gap-1'>
                    {DREAME_COMMANDS.map(({ value, label }) => (
                      <Button
                        key={value}
                        size='sm'
                        variant='outline'
                        disabled={sending !== null}
                        onClick={() => sendCommand(robot.id, value)}
                      >
                        {sending === `${robot.id}:${value}` ? '…' : label}
                      </Button>
                    ))}
                  </div>
                )}

                {/* Yahboom robot car controls */}
                {robot.type === 'yahboom' && (
                  <div className='space-y-3'>
                    <div className='flex flex-wrap gap-1'>
                      {YAHBOOM_COMMANDS.map(({ value, label }) => (
                        <Button
                          key={value}
                          size='sm'
                          variant='outline'
                          disabled={sending !== null}
                          onClick={() => sendCommand(robot.id, value)}
                        >
                          {sending === `${robot.id}:${value}` ? '…' : label}
                        </Button>
                      ))}
                    </div>

                    {/* Directional drive controls */}
                    <div>
                      <p className='mb-1 text-xs text-slate-500'>Drive</p>
                      <div className='grid grid-cols-3 gap-1 max-w-[160px]'>
                        <div />
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomMove(robot.id, 0.2, 0)}>↑</Button>
                        <div />
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomMove(robot.id, 0, 0.3)}>←</Button>
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomMove(robot.id, 0, 0)}>■</Button>
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomMove(robot.id, 0, -0.3)}>→</Button>
                        <div />
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomMove(robot.id, -0.2, 0)}>↓</Button>
                        <div />
                      </div>
                    </div>

                    {/* Light effects */}
                    <div>
                      <p className='mb-1 text-xs text-slate-500'>Lights</p>
                      <div className='flex flex-wrap gap-1'>
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomLight(robot.id, 255, 0, 0)}>
                          <Lightbulb className='mr-1 h-3 w-3 text-red-500' />
                          Red
                        </Button>
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomLight(robot.id, 0, 255, 0)}>
                          <Lightbulb className='mr-1 h-3 w-3 text-green-500' />
                          Green
                        </Button>
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomLight(robot.id, 0, 0, 255)}>
                          <Lightbulb className='mr-1 h-3 w-3 text-blue-500' />
                          Blue
                        </Button>
                        <Button size='sm' variant='outline' disabled={sending !== null} onClick={() => sendYahboomLight(robot.id, 255, 255, 255)}>
                          White
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {robot.type !== 'dreame' && robot.type !== 'yahboom' && (
                  <p className='text-xs text-amber-600'>Unknown robot type: {robot.type}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
