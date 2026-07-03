import { useCallback, useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";

const ZOOM_LEVELS = [0.8, 1.0, 1.25, 1.5, 2.0, 3.0];

function useZoom() {
	const [zoomIndex, setZoomIndex] = useState(() => {
		try {
			const saved = localStorage.getItem("tauri-zoom");
			return saved ? ZOOM_LEVELS.indexOf(Number.parseFloat(saved)) : 0;
		} catch {
			return 0;
		}
	});
	void zoomIndex;

	const applyZoom = useCallback(async (level: number) => {
		localStorage.setItem("tauri-zoom", String(level));
		try {
			const { getCurrentWindow } = await import("@tauri-apps/api/window");
			await (
				getCurrentWindow() as unknown as {
					setZoom: (z: number) => Promise<void>;
				}
			).setZoom(level);
		} catch {
			/* dev browser -- no-op */
		}
	}, []);

	useEffect(() => {
		const handler = (e: WheelEvent) => {
			if (!e.ctrlKey) return;
			e.preventDefault();
			setZoomIndex((prev) => {
				const next =
					e.deltaY < 0
						? Math.min(prev + 1, ZOOM_LEVELS.length - 1)
						: Math.max(prev - 1, 0);
				if (next !== prev) applyZoom(ZOOM_LEVELS[next]);
				return next;
			});
		};
		window.addEventListener("wheel", handler, { passive: false });
		const saved = localStorage.getItem("tauri-zoom");
		if (saved) applyZoom(Number.parseFloat(saved));
		return () => window.removeEventListener("wheel", handler);
	}, [applyZoom]);
}

export function Layout() {
	useZoom();

	return (
		<div className="min-h-screen bg-slate-50 dark:bg-slate-950">
			<AppSidebar />
			<main className="min-h-screen pl-64">
				<div className="min-h-screen overflow-y-auto overflow-x-hidden p-6">
					<Outlet />
				</div>
			</main>
		</div>
	);
}
