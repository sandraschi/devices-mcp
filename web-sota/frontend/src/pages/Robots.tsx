import { AlertCircle, Bot, Home, Loader2, Play, Square } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface RobotItem {
  id: string;
  name: string;
  type: string;
  status: string;
  is_online: boolean;
  battery_percentage?: number;
  is_virtual?: boolean;
}

interface RobotsResponse {
  success: boolean;
  robots: RobotItem[];
  total: number;
  online: number;
}

const COMMANDS = [
  { value: 'start_patrol', label: 'Start patrol', icon: Play },
  { value: 'stop_patrol', label: 'Stop patrol', icon: Square },
  { value: 'return_home', label: 'Return home', icon: Home },
  { value: 'dock', label: 'Dock' },
  { value: 'start_cleaning', label: 'Start cleaning' },
  { value: 'stop_cleaning', label: 'Stop cleaning' },
] as const;

export function Robots() {
  const [data, setData] = useState<RobotsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState<string | null>(null);

  const load = async () => {
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
  };

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
        const err = await r.json();
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
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
        {robots.length === 0 ? (
          <p className='text-slate-500'>No robots registered. Use discover or add via config.</p>
        ) : (
          robots.map((robot) => (
            <Card key={robot.id}>
              <CardHeader className='flex flex-row items-center justify-between pb-2'>
                <CardTitle className='text-base'>{robot.name}</CardTitle>
                <Bot
                  className={`h-4 w-4 ${robot.is_online ? 'text-green-500' : 'text-slate-400'}`}
                />
              </CardHeader>
              <CardContent className='space-y-2 text-sm'>
                <p className='text-slate-500'>
                  {robot.type} · {robot.status}
                  {robot.battery_percentage != null && ` · ${robot.battery_percentage}%`}
                </p>
                <div className='flex flex-wrap gap-1'>
                  {COMMANDS.map(({ value, label }) => (
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
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
