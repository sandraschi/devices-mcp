import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	AlertCircle,
	Bot,
	Home,
	Lightbulb,
	Loader2,
	Play,
	PlugZap,
	RotateCw,
	Square,
	Volume2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface YahboomConnection {
	mcp_reachable?: boolean;
	mcp_online?: boolean;
	ros_connected?: boolean;
	cmd_vel_ready?: boolean;
	robot_ip?: string;
	hint?: string | null;
}

interface RobotItem {
	id: string;
	name: string;
	type: string;
	status: string;
	is_online: boolean;
	battery_percentage?: number;
	ip_address?: string;
	yahboom_mcp_url?: string;
	connection?: YahboomConnection;
	telemetry_live?: boolean;
	telemetry_message?: string;
	error?: string;
}

interface RobotsResponse {
	success: boolean;
	robots: RobotItem[];
	total: number;
	online: number;
}

const DREAME_COMMANDS = [
	{ value: "start_cleaning", label: "Start clean", icon: Play },
	{ value: "stop_cleaning", label: "Stop", icon: Square },
	{ value: "pause", label: "Pause" },
	{ value: "return_home", label: "Return home", icon: Home },
	{ value: "find_robot", label: "Find robot", icon: Volume2 },
] as const;

const YAHBOOM_COMMANDS = [
	{ value: "start_patrol", label: "Move forward", icon: Play },
	{ value: "stop", label: "Stop all", icon: Square },
	{ value: "return_home", label: "Move backward", icon: RotateCw },
] as const;

function yahboomStatusLabel(robot: RobotItem): string {
	const conn = robot.connection;
	if (!conn?.mcp_reachable) return "yahboom-mcp unreachable";
	if (!conn.mcp_online) return "MCP offline";
	if (!conn.ros_connected) return "ROS disconnected";
	if (!conn.cmd_vel_ready) return "cmd_vel not ready";
	if (robot.telemetry_live) return "Live telemetry";
	return "MCP up, waiting for robot telemetry";
}

export function Robots() {
	const [data, setData] = useState<RobotsResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [sending, setSending] = useState<string | null>(null);

	const load = useCallback(async () => {
		try {
			const r = await fetch("/api/robots/");
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
		const timer = window.setInterval(load, 5000);
		return () => window.clearInterval(timer);
	}, [load]);

	const sendCommand = async (
		robotId: string,
		command: string,
		parameters: Record<string, unknown> = {},
	) => {
		setSending(`${robotId}:${command}`);
		try {
			const r = await fetch(
				`/api/robots/${encodeURIComponent(robotId)}/command`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ command, parameters }),
				},
			);
			const payload = await r.json().catch(() => ({}));
			if (!r.ok || payload.success === false) {
				setError(
					payload.error ??
						payload.detail ??
						payload.message ??
						"Command failed",
				);
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

	const sendYahboomMove = async (
		robotId: string,
		linear: number,
		angular: number,
	) => {
		await sendCommand(robotId, "start_patrol", { linear, angular });
	};

	const sendYahboomStop = async (robotId: string) => {
		await sendCommand(robotId, "stop");
	};

	const sendYahboomLight = async (
		robotId: string,
		r: number,
		g: number,
		b: number,
	) => {
		await sendCommand(robotId, "flash_lights", { r, g, b });
	};

	const reconnectYahboom = async () => {
		setSending("yahboom:reconnect");
		try {
			const r = await fetch("/api/robots/yahboom/reconnect", {
				method: "POST",
			});
			const payload = await r.json().catch(() => ({}));
			if (!r.ok || payload.success === false) {
				setError(payload.error ?? payload.detail ?? "Reconnect failed");
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
			<div className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-slate-400" />
			</div>
		);
	}

	const robots = data?.robots ?? [];
	const yahboomRobot = robots.find((robot) => robot.type === "yahboom");

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold tracking-tight">Robots</h1>
			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}
			<Card>
				<CardHeader className="pb-2">
					<CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
						Summary
					</CardTitle>
				</CardHeader>
				<CardContent className="text-sm">
					{data?.total ?? 0} robots · {data?.online ?? 0} online
				</CardContent>
			</Card>

			{yahboomRobot && (
				<Card>
					<CardHeader className="flex flex-row items-center justify-between pb-2">
						<CardTitle className="text-base">Yahboom MCP</CardTitle>
						<Button
							size="sm"
							variant="outline"
							disabled={sending !== null}
							onClick={reconnectYahboom}
						>
							{sending === "yahboom:reconnect" ? (
								<Loader2 className="h-4 w-4 animate-spin" />
							) : (
								<PlugZap className="h-4 w-4" />
							)}
							<span className="ml-1">Reconnect</span>
						</Button>
					</CardHeader>
					<CardContent className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
						<p>
							Gateway:{" "}
							<span className="font-mono text-slate-800 dark:text-slate-200">
								{yahboomRobot.yahboom_mcp_url ?? "http://127.0.0.1:10892"}
							</span>
						</p>
						<p>Status: {yahboomStatusLabel(yahboomRobot)}</p>
						{yahboomRobot.connection?.robot_ip && (
							<p>Robot IP: {yahboomRobot.connection.robot_ip}</p>
						)}
						{yahboomRobot.connection?.hint && (
							<p className="text-amber-700 dark:text-amber-300">
								{yahboomRobot.connection.hint}
							</p>
						)}
						{yahboomRobot.telemetry_message && (
							<p className="text-slate-500">{yahboomRobot.telemetry_message}</p>
						)}
					</CardContent>
				</Card>
			)}

			{robots.length === 0 && (
				<p className="text-slate-500">
					No robots registered. Enable robotics in config.yaml and start
					yahboom-mcp on port 10892.
				</p>
			)}

			{robots.length > 0 && (
				<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
					{robots.map((robot) => (
						<Card key={robot.id}>
							<CardHeader className="flex flex-row items-center justify-between pb-2">
								<CardTitle className="text-base">{robot.name}</CardTitle>
								<Bot
									className={`h-4 w-4 ${robot.is_online ? "text-green-500" : "text-red-400"}`}
								/>
							</CardHeader>
							<CardContent className="space-y-3 text-sm">
								<p className="text-slate-500">
									{robot.type}
									{robot.status && ` · ${robot.status}`}
									{robot.battery_percentage != null &&
										` · ${robot.battery_percentage}%`}
								</p>

								{robot.type === "yahboom" && (
									<p className="text-xs text-slate-500">
										{yahboomStatusLabel(robot)}
									</p>
								)}

								{robot.type === "dreame" && (
									<div className="flex flex-wrap gap-1">
										{DREAME_COMMANDS.map(({ value, label }) => (
											<Button
												key={value}
												size="sm"
												variant="outline"
												disabled={sending !== null}
												onClick={() => sendCommand(robot.id, value)}
											>
												{sending === `${robot.id}:${value}` ? "…" : label}
											</Button>
										))}
									</div>
								)}

								{robot.type === "yahboom" && (
									<div className="space-y-3">
										<div className="flex flex-wrap gap-1">
											{YAHBOOM_COMMANDS.map(({ value, label }) => (
												<Button
													key={value}
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendCommand(robot.id, value)}
												>
													{sending === `${robot.id}:${value}` ? "…" : label}
												</Button>
											))}
										</div>

										<div>
											<p className="mb-1 text-xs text-slate-500">Drive</p>
											<div className="grid max-w-[160px] grid-cols-3 gap-1">
												<div />
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomMove(robot.id, 0.2, 0)}
												>
													↑
												</Button>
												<div />
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomMove(robot.id, 0, 0.3)}
												>
													←
												</Button>
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomStop(robot.id)}
												>
													■
												</Button>
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomMove(robot.id, 0, -0.3)}
												>
													→
												</Button>
												<div />
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomMove(robot.id, -0.2, 0)}
												>
													↓
												</Button>
												<div />
											</div>
										</div>

										<div>
											<p className="mb-1 text-xs text-slate-500">Lights</p>
											<div className="flex flex-wrap gap-1">
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomLight(robot.id, 255, 0, 0)}
												>
													<Lightbulb className="mr-1 h-3 w-3 text-red-500" />
													Red
												</Button>
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomLight(robot.id, 0, 255, 0)}
												>
													<Lightbulb className="mr-1 h-3 w-3 text-green-500" />
													Green
												</Button>
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() => sendYahboomLight(robot.id, 0, 0, 255)}
												>
													<Lightbulb className="mr-1 h-3 w-3 text-blue-500" />
													Blue
												</Button>
												<Button
													size="sm"
													variant="outline"
													disabled={sending !== null}
													onClick={() =>
														sendYahboomLight(robot.id, 255, 255, 255)
													}
												>
													White
												</Button>
											</div>
										</div>
									</div>
								)}

								{robot.type !== "dreame" && robot.type !== "yahboom" && (
									<p className="text-xs text-amber-600">
										Unknown robot type: {robot.type}
									</p>
								)}
							</CardContent>
						</Card>
					))}
				</div>
			)}
		</div>
	);
}
