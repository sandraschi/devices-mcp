import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Loader2, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface PlexStatus {
	status?: string;
	last_event?: string;
	active_stream?: boolean;
}

interface NowPlaying {
	active?: boolean;
	event?: string;
	user?: string;
	player?: string;
	media?: string;
	metadata?: Record<string, unknown>;
	timestamp?: string;
}

export function Plex() {
	const [status, setStatus] = useState<PlexStatus | null>(null);
	const [nowPlaying, setNowPlaying] = useState<NowPlaying | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const load = useCallback(async () => {
		try {
			const [sRes, npRes] = await Promise.all([
				fetch("/api/plex/status"),
				fetch("/api/plex/now-playing"),
			]);
			if (sRes.ok) setStatus(await sRes.json());
			if (npRes.ok) setNowPlaying(await npRes.json());
			setError(null);
		} catch (e) {
			setError(String(e));
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		void load();
	}, [load]);

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-slate-400" />
			</div>
		);
	}

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold tracking-tight">Plex Media</h1>
			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base">Integration status</CardTitle>
					<Play className="h-4 w-4 text-slate-400" />
				</CardHeader>
				<CardContent className="space-y-1 text-sm">
					<p>{status?.status ?? "—"}</p>
					{status?.last_event && (
						<p className="text-slate-500">Last event: {status.last_event}</p>
					)}
				</CardContent>
			</Card>
			<Card>
				<CardHeader className="pb-2">
					<CardTitle className="text-base">Now playing</CardTitle>
				</CardHeader>
				<CardContent className="space-y-1 text-sm">
					{nowPlaying?.active ? (
						<>
							{nowPlaying.media && <p>Media: {nowPlaying.media}</p>}
							{nowPlaying.user && <p>User: {nowPlaying.user}</p>}
							{nowPlaying.player && <p>Player: {nowPlaying.player}</p>}
							{nowPlaying.event && <p>Event: {nowPlaying.event}</p>}
							{nowPlaying.metadata &&
								Object.keys(nowPlaying.metadata).length > 0 && (
									<pre className="mt-2 overflow-auto rounded bg-slate-100 p-2 text-xs dark:bg-slate-800">
										{JSON.stringify(nowPlaying.metadata, null, 2)}
									</pre>
								)}
						</>
					) : (
						<p className="text-slate-500">
							No active stream. Plex webhook updates this when playback starts.
						</p>
					)}
				</CardContent>
			</Card>
		</div>
	);
}
