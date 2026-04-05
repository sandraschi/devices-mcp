import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, Loader2 } from 'lucide-react'
import { getCapabilities, type CapabilitiesResponse } from '@/common/api'

export function McpCapabilities() {
  const [data, setData] = useState<CapabilitiesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getCapabilities()
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) setError(String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">MCP Capabilities</h1>
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertCircle className="h-5 w-5 shrink-0" />
          {error}
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Feature flags</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p>FastMCP: <span className="font-medium">{data?.server?.fastmcp ?? 'unknown'}</span></p>
          <p>Sampling: <span className="font-medium">{data?.features?.sampling ? 'available' : 'not detected'}</span></p>
          <p>Agentic workflows: <span className="font-medium">{data?.features?.agentic_workflows ? 'available' : 'not detected'}</span></p>
          <p>Prompts: <span className="font-medium">{data?.features?.prompts ? 'available' : 'not detected'}</span></p>
          <p>Resources: <span className="font-medium">{data?.features?.resources ? 'available' : 'not detected'}</span></p>
          <p>Skills: <span className="font-medium">{data?.features?.skills ? 'available' : 'not detected'}</span></p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tool surface</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p>Total tools: <span className="font-medium">{data?.tool_surface?.total ?? 0}</span></p>
          <p>Portmanteau: <span className="font-medium">{data?.tool_surface?.portmanteau_count ?? 0}</span></p>
          <p>Atomic: <span className="font-medium">{data?.tool_surface?.atomic_count ?? 0}</span></p>
          <p>Surface mode: <span className="font-medium">{data?.runtime?.surface_mode ?? 'unknown'}</span></p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Raw payload</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-[420px] overflow-auto rounded border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-900">
            {JSON.stringify(data, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}
