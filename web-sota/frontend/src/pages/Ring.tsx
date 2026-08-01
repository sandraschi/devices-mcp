import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRingWebRTC } from "@/lib/useRingWebRTC";
import {
	AlertCircle,
	Bell,
	CheckCircle,
	Loader2,
	Mic,
	MicOff,
	PhoneOff,
	RefreshCw,
	Shield,
	Video,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

function DoorbellSnapshot({ deviceId }: { deviceId: string }) {
	const [ts, setTs] = useState(Date.now());
	const [failed, setFailed] = useState(false);
	const [showLive, setShowLive] = useState(false);
	const {
		videoRef,
		streamState,
		error: webrtcError,
		startStream,
		stopStream,
		toggleTalk,
		talkEnabled,
	} = useRingWebRTC();

	useEffect(() => {
		if (!showLive) stopStream();
	}, [showLive, stopStream]);

	const handleStartLive = async () => {
		setShowLive(true);
		await startStream(deviceId);
	};

	const handleStopLive = () => {
		stopStream();
		setShowLive(false);
	};

	return (
		<div className="space-y-2">
			{showLive ? (
				<div className="space-y-2">
					<div className="relative overflow-hidden rounded-lg border border-slate-700 bg-black">
						<video
							ref={videoRef}
							autoPlay
							playsInline
							className="aspect-video w-full object-contain"
						/>
						{streamState === "connecting" && (
							<div className="absolute inset-0 flex items-center justify-center bg-black/50">
								<Loader2 className="h-8 w-8 animate-spin text-white" />
							</div>
						)}
					</div>
					{webrtcError && (
						<p className="text-xs text-red-400">
							{webrtcError}
						</p>
					)}
					<div className="flex flex-wrap gap-2">
						<Button
							size="sm"
							variant={talkEnabled ? "default" : "outline"}
							onClick={toggleTalk}
							disabled={streamState !== "streaming"}
						>
							{talkEnabled ? (
								<MicOff className="mr-1 h-3 w-3" />
							) : (
								<Mic className="mr-1 h-3 w-3" />
							)}
							{talkEnabled ? "Mute" : "Talk"}
						</Button>
						<Button
							size="sm"
							variant="outline"
							className="border-red-800 text-red-400 hover:bg-red-950/30"
							onClick={handleStopLive}
						>
							<PhoneOff className="mr-1 h-3 w-3" />
							Close
						</Button>
					</div>
				</div>
			) : (
				<>
					<div className="overflow-hidden rounded-lg border border-slate-700 bg-slate-800">
						{failed ? (
							<div className="flex aspect-video items-center justify-center text-sm text-slate-500">
								Snapshot unavailable
							</div>
						) : (
							<img
								src={`/api/ring/snapshot/${deviceId}?t=${ts}`}
								alt="Doorbell snapshot"
								className="aspect-video w-full object-contain"
								onError={() => setFailed(true)}
							/>
						)}
					</div>
					<div className="flex flex-wrap gap-2">
						<Button
							size="sm"
							variant="outline"
							onClick={() => {
								setTs(Date.now());
								setFailed(false);
							}}
						>
							<RefreshCw className="mr-1 h-3 w-3" />
							Refresh
						</Button>
						<Button
							size="sm"
							variant="default"
							onClick={handleStartLive}
						>
							<Video className="mr-1 h-3 w-3" />
							Live view
						</Button>
					</div>
				</>
			)}
		</div>
	);
}

interface RingStatus {
	connected: boolean;
	initialized: boolean;
	two_fa_pending?: boolean;
	enabled: boolean;
	message: string;
	config_issue?: boolean;
	needs_init?: boolean;
	last_error?: string | null;
}

interface RingDeviceRow {
	id?: string;
	name?: string;
	device_type?: string;
	battery_level?: number | null;
	is_online?: boolean;
}

interface RingSensorRow {
	id?: string;
	name?: string;
	sensor_type?: string;
	is_open?: boolean | null;
	motion_detected?: boolean;
	battery_level?: number | null;
	is_online?: boolean;
}

interface RingSummary {
	initialized?: boolean;
	two_fa_pending?: boolean;
	doorbells?: RingDeviceRow[];
	doorbell_count?: number;
	alarm?: {
		mode?: string;
		sensors?: RingSensorRow[];
		base_station?: { name?: string; mode?: string; is_online?: boolean };
	} | null;
	alarm_devices?: {
		total?: number;
		contact_sensors?: number;
		motion_sensors?: number;
	};
	recent_events?: Array<{
		device_name?: string;
		event_type?: string;
		timestamp?: string;
	}>;
}

function parseErrorBody(data: unknown): string {
	if (data && typeof data === "object") {
		const d = data as { detail?: unknown; message?: string };
		if (typeof d.detail === "string") return d.detail;
		if (Array.isArray(d.detail))
			return d.detail
				.map((x: { msg?: string }) => x.msg ?? "")
				.filter(Boolean)
				.join("; ");
		if (d.message) return d.message;
	}
	return "Request failed";
}

export function Ring() {
	const [status, setStatus] = useState<RingStatus | null>(null);
	const [summary, setSummary] = useState<RingSummary | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [initLoading, setInitLoading] = useState(false);
	const [refreshLoading, setRefreshLoading] = useState(false);
	const [modeLoading, setModeLoading] = useState<string | null>(null);
	const [twoFaCode, setTwoFaCode] = useState("");
	const [twoFaLoading, setTwoFaLoading] = useState(false);
	const [ringEvents, setRingEvents] = useState<
		Array<{ event_type?: string; device_name?: string; timestamp?: string }>
	>([]);

	const loadSummary = useCallback(async () => {
		try {
			const r = await fetch("/api/ring/summary");
			if (r.ok) setSummary(await r.json());
			else setSummary(null);
		} catch {
			setSummary(null);
		}
	}, []);

	const load = useCallback(async () => {
		try {
			const r = await fetch("/api/ring/status");
			if (!r.ok)
				throw new Error(parseErrorBody(await r.json().catch(() => ({}))));
			const st = await r.json();
			setStatus(st);
			setError(null);
			if (st.connected) await loadSummary();
			else setSummary(null);
		} catch (e) {
			setError(String(e));
		} finally {
			setLoading(false);
		}
	}, [loadSummary]);

	useEffect(() => {
		load();
		const timer = window.setInterval(load, 30000);
		return () => window.clearInterval(timer);
	}, [load]);

	useEffect(() => {
		if (!status?.connected) return;
		let cancelled = false;
		const poll = async () => {
			try {
				const r = await fetch("/api/ring/events?limit=10");
				if (r.ok && !cancelled) {
					const data = await r.json();
					setRingEvents(data.events ?? []);
				}
			} catch {}
		};
		poll();
		const timer = setInterval(poll, 15000);
		return () => {
			cancelled = true;
			clearInterval(timer);
		};
	}, [status?.connected]);

	const doInit = async () => {
		setInitLoading(true);
		setError(null);
		try {
			const r = await fetch("/api/ring/init", { method: "POST" });
			const data = (await r.json().catch(() => ({}))) as {
				success?: boolean;
				two_fa_pending?: boolean;
				message?: string;
				detail?: string;
			};
			if (!r.ok) {
				setError(parseErrorBody(data) || `HTTP ${r.status}`);
				return;
			}
			if (data.success) await load();
			else if (data.two_fa_pending) await load();
			else setError(data.detail ?? data.message ?? "Init failed");
		} catch (e) {
			setError(String(e));
		} finally {
			setInitLoading(false);
		}
	};

	const refresh = async () => {
		setRefreshLoading(true);
		setError(null);
		try {
			const r = await fetch("/api/ring/refresh", { method: "POST" });
			const data = await r.json().catch(() => ({}));
			if (!r.ok) {
				setError(parseErrorBody(data));
				return;
			}
			if (data.summary) setSummary(data.summary);
			else await loadSummary();
		} catch (e) {
			setError(String(e));
		} finally {
			setRefreshLoading(false);
		}
	};

	const setAlarmMode = async (mode: string) => {
		setModeLoading(mode);
		setError(null);
		try {
			const r = await fetch("/api/ring/alarm/mode", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ mode }),
			});
			const data = await r.json().catch(() => ({}));
			if (!r.ok) setError(parseErrorBody(data));
			else await load();
		} catch (e) {
			setError(String(e));
		} finally {
			setModeLoading(null);
		}
	};

	const submit2fa = async () => {
		const code = twoFaCode.trim();
		if (!code) {
			setError("Enter the 2FA code from your email or SMS.");
			return;
		}
		setTwoFaLoading(true);
		setError(null);
		try {
			const r = await fetch("/api/ring/auth/2fa", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ code }),
			});
			const data = await r.json().catch(() => ({}));
			if (!r.ok) {
				setError(parseErrorBody(data));
				return;
			}
			setTwoFaCode("");
			await load();
		} catch (e) {
			setError(String(e));
		} finally {
			setTwoFaLoading(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-slate-400" />
			</div>
		);
	}

	const showInitButton =
		!status?.connected &&
		!status?.initialized &&
		status?.enabled &&
		!status?.config_issue &&
		!status?.two_fa_pending &&
		status?.needs_init !== false;

	const sensors = summary?.alarm?.sensors ?? [];
	const doorbells = summary?.doorbells ?? [];

	return (
		<div className="space-y-6">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<h1 className="text-2xl font-bold tracking-tight">Ring Doorbell</h1>
				{status?.connected && (
					<Button
						size="sm"
						variant="outline"
						onClick={refresh}
						disabled={refreshLoading}
					>
						{refreshLoading ? (
							<Loader2 className="h-4 w-4 animate-spin" />
						) : (
							<RefreshCw className="h-4 w-4" />
						)}
						<span className="ml-1">Refresh</span>
					</Button>
				)}
			</div>

			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-900 bg-amber-950/30 p-4 text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}

			<Card
				className={
					status?.connected ? "border-green-900" : ""
				}
			>
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base font-medium">
						Connection status
					</CardTitle>
					{status?.connected ? (
						<CheckCircle className="h-5 w-5 text-green-400" />
					) : (
						<Bell className="h-5 w-5 text-slate-400" />
					)}
				</CardHeader>
				<CardContent className="space-y-3">
					<p className="text-sm">{status?.message ?? "—"}</p>
					{status?.last_error && !status.connected && (
						<p className="text-xs text-amber-300">
							{status.last_error}
						</p>
					)}
					{status?.two_fa_pending && (
						<div className="space-y-2">
							<p className="text-sm text-amber-400">
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
									className="min-w-[10rem] rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm"
								/>
								<Button
									type="button"
									onClick={submit2fa}
									disabled={twoFaLoading}
								>
									{twoFaLoading ? "Verifying…" : "Submit code"}
								</Button>
							</div>
						</div>
					)}
					{showInitButton && (
						<Button onClick={doInit} disabled={initLoading}>
							{initLoading ? "Initializing…" : "Initialize Ring"}
						</Button>
					)}
				</CardContent>
			</Card>

			{status?.connected && summary && (
				<>
					<div className="grid gap-4 md:grid-cols-3">
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-sm text-slate-500">
									Doorbells
								</CardTitle>
							</CardHeader>
							<CardContent className="text-2xl font-semibold">
								{summary.doorbell_count ?? doorbells.length}
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-sm text-slate-500">
									Alarm sensors
								</CardTitle>
							</CardHeader>
							<CardContent className="text-2xl font-semibold">
								{summary.alarm_devices?.total ?? sensors.length}
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-sm text-slate-500">
									Alarm mode
								</CardTitle>
							</CardHeader>
							<CardContent className="text-lg font-medium capitalize">
								{summary.alarm?.mode ??
									summary.alarm?.base_station?.mode ??
									"unknown"}
							</CardContent>
						</Card>
					</div>

					{summary.alarm?.base_station && (
						<Card>
							<CardHeader className="flex flex-row items-center gap-2 pb-2">
								<Shield className="h-5 w-5" />
								<CardTitle className="text-base">Alarm</CardTitle>
							</CardHeader>
							<CardContent className="space-y-3">
								<p className="text-sm text-slate-400">
									{summary.alarm.base_station.name ?? "Base station"}
									{summary.alarm.base_station.is_online === false
										? " · offline"
										: ""}
								</p>
								<div className="flex flex-wrap gap-2">
									{(["disarmed", "home", "away"] as const).map((mode) => (
										<Button
											key={mode}
											size="sm"
											variant="outline"
											disabled={modeLoading !== null}
											onClick={() => setAlarmMode(mode)}
										>
											{modeLoading === mode ? "…" : mode}
										</Button>
									))}
								</div>
							</CardContent>
						</Card>
					)}

					{doorbells.length > 0 && (
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-base">Doorbells</CardTitle>
							</CardHeader>
							<CardContent className="space-y-4">
								{doorbells.map((d) => (
									<div key={d.id} className="space-y-2">
										<div className="flex items-center justify-between text-sm">
											<span className="font-medium">{d.name ?? d.id}</span>
											<span className="text-slate-500">
												{d.is_online === false ? "offline" : "online"}
												{d.battery_level != null
													? ` · ${d.battery_level}%`
													: ""}
											</span>
										</div>
										{d.id && <DoorbellSnapshot deviceId={d.id} />}
									</div>
								))}
							</CardContent>
						</Card>
					)}

					{ringEvents.length > 0 && (
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-base">Recent events</CardTitle>
							</CardHeader>
							<CardContent>
								<ul className="space-y-1 text-sm text-slate-400">
									{ringEvents.slice(0, 10).map((ev, i) => (
										<li
											key={`${ev.timestamp}-${i}`}
											className={
												ev.event_type === "ding"
													? "font-medium text-amber-400"
													: ""
											}
										>
											{ev.event_type === "ding" ? "🔔" : "👁️"}{" "}
											{ev.device_name ?? "Doorbell"} ·{" "}
											{ev.event_type ?? "event"}
											{ev.timestamp
												? ` · ${new Date(ev.timestamp).toLocaleTimeString()}`
												: ""}
										</li>
									))}
								</ul>
							</CardContent>
						</Card>
					)}

					{sensors.length > 0 && (
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-base">Sensors</CardTitle>
							</CardHeader>
							<CardContent>
								<ul className="space-y-2 text-sm">
									{sensors.map((s) => (
										<li key={s.id} className="flex justify-between gap-2">
											<span>
												{s.name ?? s.id}
												{s.sensor_type ? ` (${s.sensor_type})` : ""}
											</span>
											<span className="text-slate-500">
												{s.sensor_type === "contact" && s.is_open != null
													? s.is_open
														? "open"
														: "closed"
													: null}
												{s.sensor_type === "motion" && s.motion_detected
													? "motion"
													: null}
												{s.battery_level != null
													? ` · ${s.battery_level}%`
													: ""}
											</span>
										</li>
									))}
								</ul>
							</CardContent>
						</Card>
					)}
				</>
			)}

			{!status?.connected && (
				<p className="text-sm text-slate-400">
					Enable Ring in config.yaml, then Initialize. Token is cached in
					ring_token.cache after first successful login.
				</p>
			)}
		</div>
	);
}
