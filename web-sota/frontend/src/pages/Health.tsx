import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Activity,
	AlertCircle,
	Cpu,
	Database,
	HardDrive,
	Loader2,
	MemoryStick,
	Radar,
	RefreshCw,
	Video,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface HealthData {
	success?: boolean;
	error?: string;
	uptime_seconds?: number;
	uptime_human?: string;
	system?: {
		cpu_percent?: number;
		memory?: { total: number; available: number; percent: number } | null;
		disk?: {
			total: number;
			used: number;
			free: number;
			percent: number;
		} | null;
	};
	process?: { memory_rss?: number; cpu_percent?: number };
	cameras?: { total: number; online: number; offline: number; error?: string };
	databases?: Record<
		string,
		{ status: string; size_mb?: number; error?: string }
	>;
}

interface DeviceRow {
	id: string;
	name: string;
	type: string;
	integration: string;
	address: string;
	source: string;
	enabled: boolean;
	connected: boolean | null;
	status: string;
	last_error?: string | null;
	last_check?: string | null;
}

interface DeviceInventory {
	home_preset?: string;
	discovery?: Record<string, boolean>;
	total_devices?: number;
	online?: number;
	offline?: number;
	unknown?: number;
	by_type?: Record<string, number>;
	devices?: DeviceRow[];
	error?: string;
	newly_discovered?: number;
}

function formatBytes(n: number): string {
	if (n >= 1024 * 1024 * 1024)
		return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
	if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
	if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
	return String(n);
}

function formatUptime(sec?: number): string {
	if (sec == null) return "—";
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	if (h > 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
	return `${h}h ${m}m`;
}

function statusBadgeClass(status: string): string {
	switch (status) {
		case "online":
			return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300";
		case "offline":
			return "bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200";
		case "disabled":
			return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
		case "error":
			return "bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300";
		default:
			return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
	}
}

function typeLabel(type: string): string {
	const labels: Record<string, string> = {
		camera: "Camera",
		plug: "Energy plug",
		lighting: "Lighting",
		light: "Light",
		security: "Security",
		sensor: "Sensor",
		nest: "Nest",
		weather: "Weather",
		webcam: "Webcam",
		robot: "Robot",
	};
	return labels[type] ?? type;
}

export function Health() {
	const [data, setData] = useState<HealthData | null>(null);
	const [inventory, setInventory] = useState<DeviceInventory | null>(null);
	const [loading, setLoading] = useState(true);
	const [discovering, setDiscovering] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [filter, setFilter] = useState<string>("all");

	const load = useCallback(async (runDiscovery = false) => {
		setLoading(true);
		try {
			const ctrl = new AbortController();
			const timeout = setTimeout(() => ctrl.abort(), 20000);
			const q = runDiscovery ? "?run_discovery=true" : "";
			const [healthRes, devicesRes] = await Promise.allSettled([
				fetch("/api/health", { signal: ctrl.signal }),
				fetch(`/api/devices${q}`, { signal: ctrl.signal }),
			]);
			clearTimeout(timeout);

			if (healthRes.status === "fulfilled" && healthRes.value.ok) {
				setData(await healthRes.value.json());
				setError(null);
			} else if (healthRes.status === "fulfilled") {
				const json = await healthRes.value.json().catch(() => ({}));
				setError((json as { error?: string }).error ?? "Health check failed");
			}

			if (devicesRes.status === "fulfilled" && devicesRes.value.ok) {
				setInventory(await devicesRes.value.json());
			}
		} catch (e) {
			setError(String(e));
		} finally {
			setLoading(false);
			setDiscovering(false);
		}
	}, []);

	useEffect(() => {
		load(false);
	}, [load]);

	const runDiscover = async () => {
		setDiscovering(true);
		try {
			const res = await fetch("/api/devices/discover", { method: "POST" });
			if (res.ok) {
				setInventory(await res.json());
			}
		} finally {
			setDiscovering(false);
		}
	};

	if (loading && !inventory) {
		return (
			<div className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-slate-400" />
			</div>
		);
	}

	const sys = data?.system;
	const mem = sys?.memory;
	const disk = sys?.disk;
	const cameras = data?.cameras;
	const dbs = data?.databases;
	const rows = inventory?.devices ?? [];
	const filtered =
		filter === "all"
			? rows
			: rows.filter((r) => r.type === filter || r.status === filter);

	return (
		<div className="space-y-6">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div>
					<h1 className="text-2xl font-bold tracking-tight">Status & health</h1>
					<p className="text-sm text-slate-500 dark:text-slate-400">
						Preset:{" "}
						<span className="font-medium text-slate-700 dark:text-slate-200">
							{inventory?.home_preset ?? "—"}
						</span>
						{inventory?.discovery?.tapo_p115 && (
							<span className="ml-2 text-xs text-slate-400">
								· LAN autodiscover on
							</span>
						)}
					</p>
				</div>
				<div className="flex gap-2">
					<Button
						variant="outline"
						size="sm"
						onClick={() => load(false)}
						disabled={loading}
					>
						<RefreshCw
							className={`mr-1 h-4 w-4 ${loading ? "animate-spin" : ""}`}
						/>
						Refresh
					</Button>
					<Button
						variant="default"
						size="sm"
						onClick={runDiscover}
						disabled={discovering}
					>
						<Radar
							className={`mr-1 h-4 w-4 ${discovering ? "animate-pulse" : ""}`}
						/>
						Autodiscover
					</Button>
				</div>
			</div>

			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}

			{inventory && (inventory.total_devices ?? 0) > 0 && (
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-base">All devices</CardTitle>
						<p className="text-sm font-normal text-slate-500">
							{inventory.online ?? 0} online · {inventory.offline ?? 0} offline
							· {inventory.unknown ?? 0} unknown · {inventory.total_devices}{" "}
							total
							{inventory.newly_discovered != null &&
								inventory.newly_discovered > 0 && (
									<span className="ml-1 text-emerald-600">
										{" "}
										(+{inventory.newly_discovered} discovered)
									</span>
								)}
						</p>
					</CardHeader>
					<CardContent className="p-0">
						<div className="flex flex-wrap gap-2 border-b border-slate-200 px-4 py-2 dark:border-slate-800">
							{[
								"all",
								"online",
								"offline",
								"camera",
								"plug",
								"lighting",
								"weather",
								"nest",
							].map((f) => (
								<button
									key={f}
									type="button"
									onClick={() => setFilter(f)}
									className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
										filter === f
											? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
											: "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
									}`}
								>
									{f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
								</button>
							))}
						</div>
						<div className="overflow-x-auto">
							<table className="w-full min-w-[720px] text-left text-sm">
								<thead>
									<tr className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-900/50">
										<th className="px-4 py-3 font-semibold">Name</th>
										<th className="px-4 py-3 font-semibold">Type</th>
										<th className="px-4 py-3 font-semibold">Address</th>
										<th className="px-4 py-3 font-semibold">Integration</th>
										<th className="px-4 py-3 font-semibold">Source</th>
										<th className="px-4 py-3 font-semibold">Status</th>
										<th className="px-4 py-3 font-semibold">Detail</th>
									</tr>
								</thead>
								<tbody>
									{filtered.length === 0 ? (
										<tr>
											<td
												colSpan={7}
												className="px-4 py-8 text-center text-slate-500"
											>
												No devices match this filter.
											</td>
										</tr>
									) : (
										filtered.map((d, i) => (
											<tr
												key={d.id}
												className={`border-b border-slate-100 dark:border-slate-800/80 ${
													i % 2 === 0
														? "bg-white dark:bg-transparent"
														: "bg-slate-50/40 dark:bg-slate-900/20"
												}`}
											>
												<td className="px-4 py-2.5 font-medium text-slate-900 dark:text-slate-100">
													{d.name}
												</td>
												<td className="px-4 py-2.5 text-slate-600 dark:text-slate-400">
													{typeLabel(d.type)}
												</td>
												<td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-400">
													{d.address}
												</td>
												<td className="px-4 py-2.5 text-slate-600 dark:text-slate-400">
													{d.integration}
												</td>
												<td className="px-4 py-2.5 text-xs text-slate-500">
													{d.source}
												</td>
												<td className="px-4 py-2.5">
													<span
														className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadgeClass(d.status)}`}
													>
														{d.status}
													</span>
												</td>
												<td
													className="max-w-[200px] truncate px-4 py-2.5 text-xs text-slate-500"
													title={d.last_error ?? ""}
												>
													{d.last_error ??
														(d.enabled ? "—" : "disabled in config")}
												</td>
											</tr>
										))
									)}
								</tbody>
							</table>
						</div>
					</CardContent>
				</Card>
			)}

			<h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300">
				Host metrics
			</h2>
			<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{sys?.cpu_percent != null && (
					<Card>
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
								<Cpu className="h-4 w-4" /> CPU
							</CardTitle>
						</CardHeader>
						<CardContent>
							<p className="text-2xl font-semibold">
								{sys.cpu_percent.toFixed(1)}%
							</p>
						</CardContent>
					</Card>
				)}
				{mem && (
					<Card>
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
								<MemoryStick className="h-4 w-4" /> Memory
							</CardTitle>
						</CardHeader>
						<CardContent>
							<p className="text-2xl font-semibold">
								{mem.percent.toFixed(1)}%
							</p>
							<p className="text-xs text-slate-500">
								{formatBytes(mem.available)} free of {formatBytes(mem.total)}
							</p>
						</CardContent>
					</Card>
				)}
				{disk && (
					<Card>
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
								<HardDrive className="h-4 w-4" /> Disk
							</CardTitle>
						</CardHeader>
						<CardContent>
							<p className="text-2xl font-semibold">
								{disk.percent.toFixed(1)}%
							</p>
							<p className="text-xs text-slate-500">
								{formatBytes(disk.used)} used, {formatBytes(disk.free)} free
							</p>
						</CardContent>
					</Card>
				)}
				{(data?.uptime_seconds != null || data?.uptime_human) && (
					<Card>
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
								<Activity className="h-4 w-4" /> Uptime
							</CardTitle>
						</CardHeader>
						<CardContent>
							<p className="text-2xl font-semibold">
								{data.uptime_human ?? formatUptime(data.uptime_seconds)}
							</p>
						</CardContent>
					</Card>
				)}
				{cameras && (
					<Card>
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
								<Video className="h-4 w-4" /> Cameras
							</CardTitle>
						</CardHeader>
						<CardContent>
							<p className="text-2xl font-semibold">
								{cameras.online}/{cameras.total}
							</p>
							<p className="text-xs text-slate-500">
								{cameras.offline} offline
								{cameras.error ? ` · ${cameras.error}` : ""}
							</p>
						</CardContent>
					</Card>
				)}
				{dbs && Object.keys(dbs).length > 0 && (
					<Card>
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
								<Database className="h-4 w-4" /> Databases
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-1">
							{Object.entries(dbs).map(([name, info]) => (
								<p key={name} className="text-sm">
									<span className="font-medium">{name}</span>: {info.status}
									{info.size_mb != null && ` (${info.size_mb} MB)`}
								</p>
							))}
						</CardContent>
					</Card>
				)}
			</div>
		</div>
	);
}
