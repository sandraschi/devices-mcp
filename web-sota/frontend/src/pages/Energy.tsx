import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Loader2, Power, RefreshCw, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
	Area,
	AreaChart,
	CartesianGrid,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

interface P115Device {
	device_id: string;
	name?: string;
	power_state?: boolean;
	current_power?: number;
	daily_energy?: number;
	monthly_energy?: number;
	voltage?: number;
	current?: number;
	host?: string;
	readonly?: boolean;
}

interface HistoryPoint {
	timestamp: string;
	power_w: number;
	voltage_v?: number;
	current_a?: number;
}

function formatTime(ts: string): string {
	try {
		const d = new Date(ts);
		return Number.isNaN(d.getTime())
			? ts
			: d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
	} catch {
		return ts;
	}
}

export function Energy() {
	const [devices, setDevices] = useState<P115Device[]>([]);
	const [history, setHistory] = useState<Record<string, HistoryPoint[]>>({});
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [refreshing, setRefreshing] = useState(false);
	const [togglingId, setTogglingId] = useState<string | null>(null);

	const loadList = useCallback(async () => {
		const r = await fetch("/api/sensors/tapo-p115");
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		const data = await r.json();
		const list: P115Device[] = data.devices ?? [];
		setDevices(list);
		const hist: Record<string, HistoryPoint[]> = {};
		await Promise.all(
			list.slice(0, 10).map(async (d) => {
				const h = await fetch(
					`/api/sensors/tapo-p115/${encodeURIComponent(d.device_id)}/history?hours=24`,
				);
				if (h.ok) {
					const j = await h.json();
					hist[d.device_id] = j.data_points ?? [];
				}
			}),
		);
		setHistory(hist);
	}, []);

	useEffect(() => {
		let cancelled = false;
		const load = async () => {
			try {
				await loadList();
				if (cancelled) return;
			} catch (e) {
				if (!cancelled) setError(String(e));
			} finally {
				if (!cancelled) setLoading(false);
			}
		};
		load();
		return () => {
			cancelled = true;
		};
	}, [loadList]);

	const onRefresh = async () => {
		setRefreshing(true);
		setError(null);
		try {
			const r = await fetch("/api/sensors/tapo-p115/refresh", {
				method: "POST",
			});
			if (!r.ok) {
				const err = await r.json().catch(() => ({}));
				throw new Error(
					(err as { detail?: string }).detail ?? `HTTP ${r.status}`,
				);
			}
			const data = await r.json();
			const list: P115Device[] = data.devices ?? [];
			setDevices(list);
			const hist: Record<string, HistoryPoint[]> = {};
			await Promise.all(
				list.slice(0, 10).map(async (d) => {
					const h = await fetch(
						`/api/sensors/tapo-p115/${encodeURIComponent(d.device_id)}/history?hours=24`,
					);
					if (h.ok) {
						const j = await h.json();
						hist[d.device_id] = j.data_points ?? [];
					}
				}),
			);
			setHistory(hist);
		} catch (e) {
			setError(String(e));
		} finally {
			setRefreshing(false);
		}
	};

	const onToggle = async (deviceId: string, turnOn: boolean) => {
		setTogglingId(deviceId);
		setError(null);
		try {
			const r = await fetch(
				`/api/sensors/tapo-p115/${encodeURIComponent(deviceId)}/toggle`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ turn_on: turnOn }),
				},
			);
			if (!r.ok) {
				const err = await r.json().catch(() => ({}));
				throw new Error(
					(err as { detail?: string }).detail ?? `HTTP ${r.status}`,
				);
			}
			await loadList();
		} catch (e) {
			setError(String(e));
		} finally {
			setTogglingId(null);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-slate-400" />
			</div>
		);
	}

	return (
		<div className="space-y-6">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<h1 className="text-2xl font-bold tracking-tight">Energy</h1>
				<Button
					type="button"
					variant="outline"
					size="sm"
					onClick={onRefresh}
					disabled={refreshing}
				>
					{refreshing ? (
						<Loader2 className="mr-2 h-4 w-4 animate-spin" />
					) : (
						<RefreshCw className="mr-2 h-4 w-4" />
					)}
					Rediscover plugs
				</Button>
			</div>
			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-900 bg-amber-950/30 p-4 text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}
			<p className="text-sm text-slate-400">
				Tapo P115 smart plugs · power and usage. Use <strong>On</strong>/
				<strong>Off</strong> to switch load; <strong>Rediscover</strong> re-runs
				LAN discovery if plugs show 0 W. History uses{" "}
				<code className="rounded bg-slate-800 px-1">
					data/timeseries.db
				</code>
				.
			</p>

			{devices.length > 0 && (
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-base">Power over time (24h)</CardTitle>
						<p className="text-xs font-normal text-slate-400">
							Charts use samples stored on the server. New points appear after
							discovery or the health poll.
						</p>
					</CardHeader>
					<CardContent>
						<div className="space-y-6">
							{devices.map((d) => {
								const points = history[d.device_id] ?? [];
								const chartData = points.map((p) => ({
									time: formatTime(String(p.timestamp)),
									power: p.power_w ?? 0,
									full: String(p.timestamp),
								}));
								const name = d.name ?? d.device_id;
								return (
									<div key={d.device_id} className="space-y-1">
										<p className="text-sm font-medium text-slate-300">
											{name}
										</p>
										{chartData.length === 0 ? (
											<p className="text-xs text-slate-500">
												No history yet. Try <strong>Rediscover plugs</strong> or
												wait for the next poll.
											</p>
										) : (
											<div className="h-[200px] w-full">
												<ResponsiveContainer width="100%" height="100%">
													<AreaChart
														data={chartData}
														margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
													>
														<CartesianGrid
															strokeDasharray="3"
															className="stroke-slate-200 stroke-slate-700"
														/>
														<XAxis
															dataKey="time"
															tick={{ fontSize: 11 }}
															className="text-slate-500"
														/>
														<YAxis
															tick={{ fontSize: 11 }}
															className="text-slate-500"
															tickFormatter={(v) => `${v} W`}
														/>
														<Tooltip
															formatter={(v: number) => [
																`${v.toFixed(1)} W`,
																"Power",
															]}
															labelFormatter={(_, payload) =>
																payload?.[0]?.payload?.full
																	? formatTime(payload[0].payload.full)
																	: ""
															}
														/>
														<Area
															type="monotone"
															dataKey="power"
															stroke="#6366f1"
															fill="#6366f1"
															fillOpacity={0.2}
															strokeWidth={2}
														/>
													</AreaChart>
												</ResponsiveContainer>
											</div>
										)}
									</div>
								);
							})}
						</div>
					</CardContent>
				</Card>
			)}

			<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
				{devices.length === 0 ? (
					<p className="text-slate-500">
						No Tapo P115 devices found. Configure{" "}
						<code className="rounded bg-slate-800 px-1">
							energy.tapo_p115
						</code>{" "}
						in config.yaml and tap <strong>Rediscover plugs</strong>.
					</p>
				) : (
					devices.map((d) => {
						const busy = togglingId === d.device_id;
						const ro = d.readonly === true;
						return (
							<Card key={d.device_id}>
								<CardHeader className="flex flex-row items-center justify-between pb-2">
									<CardTitle className="text-base">
										{d.name ?? d.device_id}
									</CardTitle>
									<Zap className="h-4 w-4 text-slate-400" />
								</CardHeader>
								<CardContent className="space-y-3 text-sm">
									<div className="flex flex-wrap items-center gap-2">
										<span className="text-slate-400">
											Power:{" "}
											<span className="font-medium">
												{d.power_state ? "On" : "Off"}
											</span>
										</span>
										{ro && (
											<span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
												Read-only
											</span>
										)}
									</div>
									{!ro && (
										<div className="flex flex-wrap gap-2">
											<Button
												type="button"
												size="sm"
												variant={d.power_state ? "outline" : "default"}
												disabled={busy}
												onClick={() => onToggle(d.device_id, true)}
											>
												{busy ? (
													<Loader2 className="h-4 w-4 animate-spin" />
												) : (
													<Power className="mr-1 h-4 w-4" />
												)}
												On
											</Button>
											<Button
												type="button"
												size="sm"
												variant={d.power_state ? "default" : "outline"}
												disabled={busy}
												onClick={() => onToggle(d.device_id, false)}
											>
												Off
											</Button>
										</div>
									)}
									{d.host && (
										<p className="text-xs text-slate-500">
											Host:{" "}
											<code className="rounded bg-slate-800 px-1">
												{d.host}
											</code>
										</p>
									)}
									{d.current_power != null && (
										<p>
											Current:{" "}
											<span className="font-medium">
												{d.current_power.toFixed(1)} W
											</span>
										</p>
									)}
									{d.daily_energy != null && (
										<p>
											Today:{" "}
											<span className="font-medium">
												{d.daily_energy.toFixed(2)} kWh
											</span>
										</p>
									)}
									{d.monthly_energy != null && (
										<p>
											Month:{" "}
											<span className="font-medium">
												{d.monthly_energy.toFixed(2)} kWh
											</span>
										</p>
									)}
								</CardContent>
							</Card>
						);
					})
				)}
			</div>
		</div>
	);
}
