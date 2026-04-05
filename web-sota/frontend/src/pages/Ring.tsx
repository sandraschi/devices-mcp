import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Bell, Loader2, AlertCircle, CheckCircle } from 'lucide-react'

interface RingStatus {
  connected: boolean
  initialized: boolean
  two_fa_pending?: boolean
  enabled: boolean
  message: string
  config_issue?: boolean
  needs_init?: boolean
  last_error?: string | null
}

function parseErrorBody(data: unknown): string {
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: string }
    if (typeof d.detail === 'string') return d.detail
    if (Array.isArray(d.detail))
      return d.detail
        .map((x: { msg?: string }) => x.msg ?? '')
        .filter(Boolean)
        .join('; ')
    if (d.message) return d.message
  }
  return 'Request failed'
}

export function Ring() {
  const [status, setStatus] = useState<RingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [initLoading, setInitLoading] = useState(false)
  const [twoFaCode, setTwoFaCode] = useState('')
  const [twoFaLoading, setTwoFaLoading] = useState(false)

  const load = async () => {
    try {
      const r = await fetch('/api/ring/status')
      if (!r.ok) throw new Error(parseErrorBody(await r.json().catch(() => ({}))))
      setStatus(await r.json())
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const doInit = async () => {
    setInitLoading(true)
    setError(null)
    try {
      const r = await fetch('/api/ring/init', { method: 'POST' })
      const data = (await r.json().catch(() => ({}))) as {
        success?: boolean
        two_fa_pending?: boolean
        message?: string
        detail?: string
      }
      if (!r.ok) {
        setError(parseErrorBody(data) || `HTTP ${r.status}`)
        return
      }
      if (data.success) await load()
      else if (data.two_fa_pending) await load()
      else setError(data.detail ?? data.message ?? 'Init failed')
    } catch (e) {
      setError(String(e))
    } finally {
      setInitLoading(false)
    }
  }

  const submit2fa = async () => {
    const code = twoFaCode.trim()
    if (!code) {
      setError('Enter the 2FA code from your email or SMS.')
      return
    }
    setTwoFaLoading(true)
    setError(null)
    try {
      const r = await fetch('/api/ring/auth/2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) {
        setError(parseErrorBody(data))
        return
      }
      setTwoFaCode('')
      await load()
    } catch (e) {
      setError(String(e))
    } finally {
      setTwoFaLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  const showInitButton =
    !status?.connected &&
    !status?.initialized &&
    status?.enabled &&
    !status?.config_issue &&
    !status?.two_fa_pending &&
    status?.needs_init !== false

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Ring Doorbell</h1>
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertCircle className="h-5 w-5 shrink-0" />
          {error}
        </div>
      )}
      <Card className={status?.connected ? 'border-green-200 dark:border-green-900' : ''}>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-base font-medium">Connection status</CardTitle>
          {status?.connected ? (
            <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
          ) : (
            <Bell className="h-5 w-5 text-slate-400" />
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm">{status?.message ?? '—'}</p>
          {status?.two_fa_pending && (
            <div className="space-y-2">
              <p className="text-sm text-amber-600 dark:text-amber-400">
                Enter the verification code Ring sent to your email or phone.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="6-digit code"
                  value={twoFaCode}
                  onChange={(e) => setTwoFaCode(e.target.value)}
                  className="min-w-[10rem] rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
                />
                <Button type="button" onClick={submit2fa} disabled={twoFaLoading}>
                  {twoFaLoading ? 'Verifying…' : 'Submit code'}
                </Button>
              </div>
            </div>
          )}
          {showInitButton && (
            <Button onClick={doInit} disabled={initLoading}>
              {initLoading ? 'Initializing…' : 'Initialize Ring'}
            </Button>
          )}
        </CardContent>
      </Card>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Monitor and control your Ring doorbell and alarm. Configure email/password in config.yaml
        and use Initialize to connect.
      </p>
    </div>
  )
}
