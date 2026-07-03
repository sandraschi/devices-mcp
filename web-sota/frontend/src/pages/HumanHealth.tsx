import { Card, CardContent } from "@/components/ui/card";
import { Activity, Heart, Info } from "lucide-react";

export function HumanHealth() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold tracking-tight">Human Health</h1>
			<Card>
				<CardContent className="flex items-start gap-3 pt-6">
					<Info className="h-5 w-5 shrink-0 text-slate-500 dark:text-slate-400" />
					<div className="text-sm text-slate-600 dark:text-slate-400">
						<p className="font-medium text-slate-800 dark:text-slate-200">
							Device integration
						</p>
						<p>
							Human health devices (e.g. blood pressure monitors, glucose
							meters, fitness trackers, scales) can be connected and shown here
							once configured. No devices are configured yet.
						</p>
					</div>
				</CardContent>
			</Card>
			<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<Card className="border-slate-200 dark:border-slate-800 opacity-75">
					<CardContent className="flex items-center gap-3 pt-6">
						<Heart className="h-8 w-8 text-slate-400" />
						<div>
							<p className="font-medium text-slate-700 dark:text-slate-300">
								Blood pressure / Glucose
							</p>
							<p className="text-xs text-slate-500">
								Configure in settings when supported.
							</p>
						</div>
					</CardContent>
				</Card>
				<Card className="border-slate-200 dark:border-slate-800 opacity-75">
					<CardContent className="flex items-center gap-3 pt-6">
						<Activity className="h-8 w-8 text-slate-400" />
						<div>
							<p className="font-medium text-slate-700 dark:text-slate-300">
								Fitness & scales
							</p>
							<p className="text-xs text-slate-500">
								Wearables and smart scales.
							</p>
						</div>
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
