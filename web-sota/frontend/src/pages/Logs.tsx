import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, FileText, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface LogEntry {
	timestamp: string;
	level: string;
	logger: string;
	message: string;
}

interface LogsResponse {
	logs: LogEntry[];
	total: number;
	message?: string;
	error?: string;
	hint?: string;
	log_path?: string;
	path_exists?: boolean;
}

interface LogStats {
	enabled: boolean;
	total_files: number;
	total_size_mb: number;
	log_path?: string;
	path_exists?: boolean;
	error?: string;
}

const LEVELS = ["", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] as const;

export function Logs() {
	const [data, setData] = useState<LogsResponse | null>(null);
	const [stats, setStats] = useState<LogStats | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [lines, setLines] = useState(200);
	const [levelFilter, setLevelFilter] = useState<string>("");
	const [searchQuery, setSearchQuery] = useState("");

	const load = useCallback(async () => {
		setLoading(true);
		try {
			const params = new URLSearchParams();
			params.set("lines", String(lines));
			if (levelFilter) params.set("level", levelFilter);
			if (searchQuery.trim()) params.set("search", searchQuery.trim());

			const [logsRes, statsRes] = await Promise.all([
				fetch(`/api/logs?${params.toString()}`),
				fetch("/api/logs/stats"),
			]);
			if (logsRes.ok) {
				setData(await logsRes.json());
			} else {
				const errBody = await logsRes.json().catch(() => ({}));
				setData({
					logs: [],
					total: 0,
					error:
						(errBody as { detail?: string }).detail ?? `HTTP ${logsRes.status}`,
				});
			}
			if (statsRes.ok) setStats(await statsRes.json());
			setError(null);
		} catch (e) {
			setError(String(e));
		} finally {
			setLoading(false);
		}
	}, [lines, levelFilter, searchQuery]);

	useEffect(() => {
		void load();
	}, [load]);

	const levelColor = (level: string) => {
		const l = level.toUpperCase();
		if (l === "ERROR" || l === "CRITICAL")
			return "text-red-400";
		if (l === "WARNING") return "text-amber-400";
		if (l === "INFO") return "text-slate-400";
		if (l === "DEBUG") return "text-slate-500";
		return "text-slate-500";
	};

	return (
		<div className="space-y-6">
			<div className="flex flex-wrap items-center justify-between gap-4">
				<h1 className="text-2xl font-bold tracking-tight">Log management</h1>
				<div className="flex flex-wrap items-center gap-2">
					<label htmlFor="logs-lines" className="text-sm text-slate-500">
						Lines
					</label>
					<select
						id="logs-lines"
						className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm"
						value={lines}
						onChange={(e) => setLines(Number(e.target.value))}
					>
						{[50, 100, 200, 500, 1000].map((n) => (
							<option key={n} value={n}>
								{n}
							</option>
						))}
					</select>
					<label htmlFor="logs-level" className="text-sm text-slate-500">
						Level
					</label>
					<select
						id="logs-level"
						className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm"
						value={levelFilter}
						onChange={(e) => setLevelFilter(e.target.value)}
					>
						{LEVELS.map((lv) => (
							<option key={lv || "all"} value={lv}>
								{lv || "All"}
							</option>
						))}
					</select>
					<input
						type="search"
						placeholder="Search…"
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className="min-w-[8rem] rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm"
					/>
					<Button variant="outline" size="sm" onClick={load} disabled={loading}>
						<RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
						Refresh
					</Button>
				</div>
			</div>
			<p className="text-sm text-slate-400">
				Tails the default log under your user profile (
				<code className="text-xs">
					.local\share\devices-mcp\devices-mcp.log
				</code>
				). Change the path in Settings → Logging if needed.
			</p>
			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-900 bg-amber-950/30 p-4 text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}
			{data?.error && (
				<div className="flex items-center gap-2 rounded-lg border border-red-900 bg-red-950/30 p-4 text-red-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{data.error}
				</div>
			)}
			{stats != null && (
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm font-medium text-slate-400">
							Log file
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-1 text-sm">
						{stats.log_path && (
							<p className="break-all font-mono text-xs text-slate-300">
								{stats.log_path}
							</p>
						)}
						<p>
							Files (incl. rotations): {stats.total_files} · Total size:{" "}
							{stats.total_size_mb.toFixed(2)} MB
							{stats.path_exists === false && (
								<span className="text-amber-400">
									{" "}
									· path missing
								</span>
							)}
						</p>
						{stats.error && <p className="text-amber-600">{stats.error}</p>}
					</CardContent>
				</Card>
			)}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base">Recent logs</CardTitle>
					<FileText className="h-4 w-4 text-slate-400" />
				</CardHeader>
				<CardContent>
					{data?.log_path && (
						<p className="mb-2 break-all font-mono text-xs text-slate-400">
							Source: {data.log_path}
							{data.path_exists === false && " (not found)"}
						</p>
					)}
					{loading ? (
						<Loader2 className="h-6 w-6 animate-spin text-slate-400" />
					) : data?.message ? (
						<div className="space-y-2 text-slate-400">
							<p>{data.message}</p>
							{data.hint && <p className="text-sm">{data.hint}</p>}
						</div>
					) : (
						<div className="max-h-[60vh] overflow-y-auto font-mono text-xs">
							{(data?.logs ?? []).length === 0 ? (
								<p className="text-slate-500">
									No log entries match the current filters.
								</p>
							) : (
								(data?.logs ?? []).map((entry) => (
									<div
										key={entry.timestamp + entry.logger + entry.level}
										className="border-b border-slate-800 py-1"
									>
										{entry.timestamp && (
											<span className="text-slate-400">{entry.timestamp} </span>
										)}
										<span className={levelColor(entry.level)}>
											[{entry.level}]
										</span>{" "}
										<span className="text-slate-500">{entry.logger}</span>{" "}
										{entry.message}
									</div>
								))
							)}
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	);
}
