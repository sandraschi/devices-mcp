import { Inbox } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface StoreMessage {
  id: string;
  timestamp: string;
  severity: string;
  category: string;
  source: string;
  title: string;
  description: string;
  acknowledged: boolean;
}

interface Status {
  total: number;
  by_severity: { info: number; warning: number; alarm: number };
  unacked_total: number;
  unacked_alarms: number;
  oldest: string | null;
  newest: string | null;
}

const severityColor: Record<string, string> = {
  info: 'bg-sky-500/20 text-sky-300',
  warning: 'bg-amber-500/20 text-amber-300',
  alarm: 'bg-red-500/20 text-red-300',
};

export function Messaging() {
  const [status, setStatus] = useState<Status | null>(null);
  const [messages, setMessages] = useState<StoreMessage[]>([]);
  const [severity, setSeverity] = useState('');
  const [acked, setAcked] = useState('');
  const [source, setSource] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (severity) params.set('severity', severity);
      if (acked) params.set('unacknowledged_only', acked === 'unacked' ? 'true' : 'false');
      if (source) params.set('source', source);
      params.set('since_minutes', '100000');
      params.set('limit', '100');
      const [s, m] = await Promise.all([
        fetch('/api/messages/status').then((r) => r.json()),
        fetch(`/api/messages/?${params}`).then((r) => r.json()),
      ]);
      setStatus(s);
      setMessages(m.messages ?? []);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [severity, acked, source]);

  useEffect(() => {
    load();
  }, [load]);

  const ackOne = async (id: string) => {
    setLoading(true);
    setMsg(null);
    try {
      const r = await fetch('/api/messages/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_ids: [id] }),
      }).then((x) => x.json());
      setMsg(r.success ? 'Acknowledged' : (r.error ?? 'Failed'));
      load();
    } finally {
      setLoading(false);
    }
  };

  const ackAll = async () => {
    if (!window.confirm('Acknowledge all messages?')) return;
    setLoading(true);
    try {
      await fetch('/api/messages/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledge_all: true }),
      }).then((x) => x.json());
      setMsg('All acknowledged');
      load();
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    if (!window.confirm('DELETE ALL MESSAGES? This is not reversible.')) return;
    setLoading(true);
    try {
      const r = await fetch('/api/messages/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_all: true, confirm: true }),
      }).then((x) => x.json());
      setMsg(r.success ? `Cleared ${r.cleared_count}` : (r.error ?? 'Failed'));
      load();
    } finally {
      setLoading(false);
    }
  };

  const fmt = (iso: string) =>
    iso
      ? new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'medium' })
      : '-';

  return (
    <div className='space-y-6 py-4 max-w-5xl'>
      <div className='flex items-center justify-between gap-4'>
        <div className='flex items-center gap-4'>
          <Inbox className='text-amber-400 w-8 h-8' />
          <div>
            <h1 className='text-2xl font-bold text-white'>Messaging Store</h1>
            <p className='text-slate-400 text-sm'>
              Device alert history (SQLite-persisted, 30-day retention)
            </p>
          </div>
        </div>
        <div className='flex gap-2'>
          <button
            type='button'
            onClick={ackAll}
            disabled={loading}
            className='px-3 py-2 rounded-xl bg-emerald-700/80 hover:bg-emerald-600 text-white text-sm disabled:opacity-50'
          >
            Ack all
          </button>
          <button
            type='button'
            onClick={clearAll}
            disabled={loading}
            className='px-3 py-2 rounded-xl bg-red-700/80 hover:bg-red-600 text-white text-sm disabled:opacity-50'
          >
            Clear all
          </button>
        </div>
      </div>

      {err && <p className='text-red-300 text-sm'>{err}</p>}
      {msg && <p className='text-emerald-300 text-sm'>{msg}</p>}

      {status && (
        <div className='grid grid-cols-2 md:grid-cols-5 gap-3'>
          {[
            ['Total', status.total],
            ['Alarms', status.by_severity.alarm],
            ['Warnings', status.by_severity.warning],
            ['Unacked total', status.unacked_total],
            ['Unacked alarms', status.unacked_alarms],
          ].map(([label, value]) => (
            <div
              key={String(label)}
              className='rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4'
            >
              <p className='text-slate-500 text-xs'>{label}</p>
              <p className='text-2xl font-semibold text-white'>{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className='rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4'>
        <div className='flex flex-wrap gap-3 mb-4'>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className='rounded-xl bg-black/40 border border-white/10 px-3 py-2 text-slate-200 text-sm'
          >
            <option value=''>All severities</option>
            <option value='alarm'>Alarm</option>
            <option value='warning'>Warning</option>
            <option value='info'>Info</option>
          </select>
          <select
            value={acked}
            onChange={(e) => setAcked(e.target.value)}
            className='rounded-xl bg-black/40 border border-white/10 px-3 py-2 text-slate-200 text-sm'
          >
            <option value=''>Ack: both</option>
            <option value='unacked'>Unacknowledged only</option>
            <option value='acked'>Acknowledged only</option>
          </select>
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder='Source (device id)'
            className='rounded-xl bg-black/40 border border-white/10 px-3 py-2 text-slate-200 text-sm'
          />
        </div>

        <table className='w-full text-sm'>
          <thead>
            <tr className='text-left text-slate-500 text-xs'>
              <th className='pb-2'>Time</th>
              <th className='pb-2'>Severity</th>
              <th className='pb-2'>Source</th>
              <th className='pb-2'>Title</th>
              <th className='pb-2'>Description</th>
              <th className='pb-2'>Ack</th>
            </tr>
          </thead>
          <tbody>
            {messages.map((m) => (
              <tr key={m.id} className='border-t border-white/5 align-top'>
                <td className='py-2 pr-3 text-slate-500 text-xs whitespace-nowrap'>
                  {fmt(m.timestamp)}
                </td>
                <td className='py-2 pr-3'>
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                      severityColor[m.severity] ?? 'bg-slate-500/20 text-slate-300'
                    }`}
                  >
                    {m.severity}
                  </span>
                </td>
                <td className='py-2 pr-3 text-slate-400 text-xs'>{m.source}</td>
                <td className='py-2 pr-3 text-slate-200 font-medium'>{m.title}</td>
                <td className='py-2 pr-3 text-slate-400 text-xs'>{m.description}</td>
                <td className='py-2'>
                  {m.acknowledged ? (
                    <span className='text-emerald-400 text-xs'>acked</span>
                  ) : (
                    <button
                      type='button'
                      onClick={() => ackOne(m.id)}
                      disabled={loading}
                      className='px-2 py-1 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-xs disabled:opacity-50'
                    >
                      Ack
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {messages.length === 0 && (
              <tr>
                <td colSpan={6} className='py-6 text-center text-slate-500'>
                  No messages match the filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
