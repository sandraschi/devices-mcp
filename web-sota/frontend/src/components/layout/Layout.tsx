import { Moon, Sun } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";

const ZOOM_LEVELS = [0.8, 1.0, 1.25, 1.5, 2.0, 3.0];

const THEME_KEY = "devices-mcp-light-mode";

// EXPERIMENTAL light mode (invert hack). Not fleet standard - see index.css.
// Toggling `.dark` off the root flips the invert filter; persisted so the
// choice survives reloads.
function useTheme() {
  const [light, setLight] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) === "1";
    } catch {
      return false;
    }
  });

  const toggle = useCallback(() => {
    setLight((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle("dark", !next);
      localStorage.setItem(THEME_KEY, next ? "1" : "0");
      return next;
    });
  }, []);

  return { light, toggle };
}

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
	const { light, toggle } = useTheme();

	return (
		<div className="min-h-screen bg-slate-950">
			<AppSidebar />
			<main className="min-h-screen pl-64">
				<header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950 px-6">
					<div className="text-sm font-medium text-slate-400">
						Devices MCP
					</div>
					<button
						type="button"
						onClick={toggle}
						className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-50"
						aria-label="Toggle dark mode"
						title={light ? "Switch to dark mode" : "Switch to light mode"}
					>
						{light ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
					</button>
				</header>
				<div className="min-h-screen overflow-y-auto overflow-x-hidden p-6">
					<Outlet />
				</div>
			</main>
		</div>
	);
}
