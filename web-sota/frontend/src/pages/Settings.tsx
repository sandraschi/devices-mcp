import { type CapabilitiesResponse, getCapabilities } from "@/common/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LOCAL_LLM_CATALOG } from "@/lib/llmProviders";
import {
	AlertCircle,
	Check,
	Cpu,
	Edit3,
	FileText,
	Loader2,
	Save,
	Shield,
	User,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface AuthStatus {
	authenticated: boolean;
	user?: string;
	auth_enabled: boolean;
}

interface ConfigData {
	success: boolean;
	path?: string;
	yaml?: string;
	json?: Record<string, unknown>;
	error?: string;
}

interface LoggingSettings {
	success: boolean;
	file?: string;
	default_file?: string;
	path_exists?: boolean;
	error?: string;
}

interface LlmProviderRow {
	type?: string;
	label?: string;
	base_url?: string;
	available?: boolean;
	model_count?: number;
}

interface LlmSettings {
	success: boolean;
	ollama_url?: string;
	lm_studio_url?: string;
	preferred_provider?: string;
	preferred_model?: string;
	providers?: LlmProviderRow[];
	error?: string;
}

export function Settings() {
	const [auth, setAuth] = useState<AuthStatus | null>(null);
	const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(
		null,
	);
	const [config, setConfig] = useState<ConfigData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const [editing, setEditing] = useState(false);
	const [editYaml, setEditYaml] = useState("");
	const [saving, setSaving] = useState(false);
	const [saveMsg, setSaveMsg] = useState<string | null>(null);

	const [logSettings, setLogSettings] = useState<LoggingSettings | null>(null);
	const [logPathEdit, setLogPathEdit] = useState("");
	const [logSaving, setLogSaving] = useState(false);
	const [logMsg, setLogMsg] = useState<string | null>(null);

	const [llmSettings, setLlmSettings] = useState<LlmSettings | null>(null);
	const [ollamaUrl, setOllamaUrl] = useState("http://127.0.0.1:11434");
	const [lmStudioUrl, setLmStudioUrl] = useState("http://127.0.0.1:1234");
	const [preferredProvider, setPreferredProvider] = useState("ollama");
	const [preferredModel, setPreferredModel] = useState("");
	const [availableModels, setAvailableModels] = useState<string[]>([]);
	const [modelsLoading, setModelsLoading] = useState(false);
	const [llmSaving, setLlmSaving] = useState(false);
	const [llmMsg, setLlmMsg] = useState<string | null>(null);

	const loadLogging = useCallback(async () => {
		try {
			const res = await fetch("/api/settings/logging");
			const data: LoggingSettings = await res.json();
			if (data.success) {
				setLogSettings(data);
				setLogPathEdit(data.file ?? data.default_file ?? "");
			}
		} catch {
			/* optional */
		}
	}, []);

	const loadLlm = useCallback(async () => {
		try {
			const res = await fetch("/api/settings/llm");
			const data: LlmSettings = await res.json();
			if (data.success) {
				setLlmSettings(data);
				setOllamaUrl(data.ollama_url ?? LOCAL_LLM_CATALOG[0].defaultUrl);
				setLmStudioUrl(data.lm_studio_url ?? LOCAL_LLM_CATALOG[1].defaultUrl);
				setPreferredProvider(data.preferred_provider ?? "ollama");
				setPreferredModel(data.preferred_model ?? "");
			}
		} catch {
			/* optional */
		}
	}, []);

	const loadConfig = useCallback(async () => {
		try {
			const res = await fetch("/api/config");
			const data: ConfigData = await res.json();
			if (data.success) {
				setConfig(data);
				setEditYaml(data.yaml ?? "");
			} else {
				setError(data.error ?? "Failed to load config");
			}
		} catch (e) {
			setError(String(e));
		}
	}, []);

	useEffect(() => {
		const hash = window.location.hash.replace("#", "");
		if (hash) {
			document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" });
		}
	}, []);

	// Fetch available models when preferred provider changes
	useEffect(() => {
		if (!preferredProvider) return;
		let cancelled = false;
		setModelsLoading(true);
		fetch(`/api/llm/models?provider=${encodeURIComponent(preferredProvider)}`)
			.then((r) => (r.ok ? r.json() : []))
			.then((data) => {
				if (cancelled) return;
				const models: string[] = (data.models ?? data.data ?? []).map(
					(m: { name?: string; id?: string; model?: string }) =>
						m.name ?? m.id ?? m.model ?? String(m),
				);
				setAvailableModels(models);
			})
			.catch(() => {
				if (!cancelled) setAvailableModels([]);
			})
			.finally(() => {
				if (!cancelled) setModelsLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, [preferredProvider]);

	useEffect(() => {
		let cancelled = false;
		Promise.allSettled([
			fetch("/api/auth/status").then((r) =>
				r.ok ? r.json() : Promise.reject(new Error(String(r.status))),
			),
			getCapabilities(),
			loadConfig(),
			loadLogging(),
			loadLlm(),
		])
			.then(([authResult, capsResult]) => {
				if (cancelled) return;
				if (authResult.status === "fulfilled") setAuth(authResult.value);
				else setError(String(authResult.reason));
				if (capsResult.status === "fulfilled")
					setCapabilities(capsResult.value);
			})
			.catch((e) => {
				if (!cancelled) setError(String(e));
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, [loadConfig, loadLogging, loadLlm]);

	const handleSaveLogging = async () => {
		setLogSaving(true);
		setLogMsg(null);
		try {
			const res = await fetch("/api/settings/logging", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ file: logPathEdit.trim() || null }),
			});
			const data = await res.json();
			if (data.success) {
				setLogMsg("Log path saved.");
				await loadLogging();
			} else {
				setLogMsg(data.error ?? "Save failed");
			}
		} catch (e) {
			setLogMsg(String(e));
		} finally {
			setLogSaving(false);
		}
	};

	const handleResetLogPath = () => {
		setLogPathEdit(logSettings?.default_file ?? "");
	};

	const handleSaveLlm = async () => {
		setLlmSaving(true);
		setLlmMsg(null);
		try {
			const res = await fetch("/api/settings/llm", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					ollama_url: ollamaUrl.trim(),
					lm_studio_url: lmStudioUrl.trim(),
					preferred_provider: preferredProvider,
					preferred_model: preferredModel,
					reconnect: true,
				}),
			});
			const data = await res.json();
			if (data.success) {
				setLlmMsg("Local LLM settings saved.");
				setLlmSettings((prev) => ({
					...prev,
					success: true,
					providers: data.providers,
				}));
			} else {
				setLlmMsg(data.error ?? "Save failed");
			}
		} catch (e) {
			setLlmMsg(String(e));
		} finally {
			setLlmSaving(false);
		}
	};

	const handleSave = async () => {
		setSaving(true);
		setSaveMsg(null);
		try {
			const res = await fetch("/api/config", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ yaml: editYaml }),
			});
			const data = await res.json();
			if (data.success) {
				setSaveMsg("Config saved. Restart backend to apply changes.");
				setEditing(false);
				setConfig((prev) => (prev ? { ...prev, yaml: editYaml } : prev));
			} else {
				setSaveMsg(data.error ?? "Save failed");
			}
		} catch (e) {
			setSaveMsg(String(e));
		} finally {
			setSaving(false);
		}
	};

	const handleCancelEdit = () => {
		setEditing(false);
		setEditYaml(config?.yaml ?? "");
		setSaveMsg(null);
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
			<h1 className="text-2xl font-bold tracking-tight">Settings</h1>
			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-900 bg-amber-950/30 p-4 text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}

			<Card>
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base">Authentication</CardTitle>
					<Shield className="h-4 w-4 text-slate-400" />
				</CardHeader>
				<CardContent className="space-y-2 text-sm">
					<p>
						Auth enabled:{" "}
						<span className="font-medium">
							{auth?.auth_enabled ? "Yes" : "No"}
						</span>
					</p>
					<p>
						Logged in:{" "}
						<span className="font-medium">
							{auth?.authenticated ? "Yes" : "No"}
						</span>
					</p>
					{auth?.user && (
						<p className="flex items-center gap-1">
							<User className="h-4 w-4" />
							{auth.user}
						</p>
					)}
				</CardContent>
			</Card>

			<Card id="logging">
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base flex items-center gap-2">
						<FileText className="h-4 w-4 text-slate-400" />
						Logging
					</CardTitle>
				</CardHeader>
				<CardContent className="space-y-3 text-sm">
					<p className="text-slate-400">
						New installs write logs here by default. You only need to change
						this if you want a different folder.
					</p>
					{logSettings?.default_file && (
						<p className="text-xs text-slate-500">
							Default:{" "}
							<code className="break-all">{logSettings.default_file}</code>
						</p>
					)}
					<label className="block">
						<span className="mb-1 block font-medium text-slate-300">
							Log file path
						</span>
						<input
							type="text"
							value={logPathEdit}
							onChange={(e) => setLogPathEdit(e.target.value)}
							className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-xs"
							spellCheck={false}
						/>
					</label>
					{logSettings?.path_exists === false && (
						<p className="text-amber-600 text-xs">
							File will be created on next log write.
						</p>
					)}
					<div className="flex flex-wrap items-center gap-2">
						<Button size="sm" onClick={handleSaveLogging} disabled={logSaving}>
							{logSaving ? (
								<Loader2 className="mr-1 h-3 w-3 animate-spin" />
							) : (
								<Save className="mr-1 h-3 w-3" />
							)}
							Save log path
						</Button>
						<Button size="sm" variant="outline" onClick={handleResetLogPath}>
							Use default
						</Button>
						{logMsg && <span className="text-xs text-slate-500">{logMsg}</span>}
					</div>
				</CardContent>
			</Card>

			<Card id="local-llm">
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base flex items-center gap-2">
						<Cpu className="h-4 w-4 text-slate-400" />
						Local LLM
					</CardTitle>
				</CardHeader>
				<CardContent className="space-y-4 text-sm">
					<p className="text-slate-400">
						Ollama and LM Studio are always available in Chat. Start the app on
						your PC, then save URLs below and pick a default provider.
					</p>
					<label className="block">
						<span className="mb-1 block font-medium">Ollama URL</span>
						<input
							type="url"
							value={ollamaUrl}
							onChange={(e) => setOllamaUrl(e.target.value)}
							className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-xs"
						/>
					</label>
					<label className="block">
						<span className="mb-1 block font-medium">LM Studio URL</span>
						<input
							type="url"
							value={lmStudioUrl}
							onChange={(e) => setLmStudioUrl(e.target.value)}
							className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-xs"
						/>
					</label>
					<label className="block">
						<span className="mb-1 block font-medium">
							Default provider (Chat)
						</span>
						<select
							value={preferredProvider}
							onChange={(e) => setPreferredProvider(e.target.value)}
							className="rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm"
						>
							{LOCAL_LLM_CATALOG.map((c) => (
								<option key={c.type} value={c.type}>
									{c.label}
								</option>
							))}
						</select>
					</label>
					<label className="block">
						<span className="mb-1 block font-medium">
							Model ({preferredProvider})
						</span>
						<select
							value={preferredModel}
							onChange={(e) => setPreferredModel(e.target.value)}
							className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm"
							disabled={modelsLoading}
						>
							{!preferredModel && (
								<option value="">-- auto (first available) --</option>
							)}
							{availableModels.map((m) => (
								<option key={m} value={m}>
									{m}
								</option>
							))}
						</select>
						{modelsLoading && (
							<span className="mt-1 flex items-center gap-1 text-xs text-slate-500">
								<Loader2 className="h-3 w-3 animate-spin" />
								Loading models...
							</span>
						)}
					</label>
					{llmSettings?.providers && llmSettings.providers.length > 0 && (
						<ul className="space-y-1 rounded-md border border-slate-700 p-3 text-xs">
							{llmSettings.providers.map((p) => (
								<li key={p.type} className="flex justify-between gap-2">
									<span className="font-medium">{p.label ?? p.type}</span>
									<span
										className={
											p.available ? "text-emerald-600" : "text-slate-500"
										}
									>
										{p.available
											? `up · ${p.model_count ?? 0} models`
											: "not reachable"}
									</span>
								</li>
							))}
						</ul>
					)}
					<div className="flex items-center gap-2">
						<Button size="sm" onClick={handleSaveLlm} disabled={llmSaving}>
							{llmSaving ? (
								<Loader2 className="mr-1 h-3 w-3 animate-spin" />
							) : (
								<Save className="mr-1 h-3 w-3" />
							)}
							Save & connect
						</Button>
						{llmMsg && <span className="text-xs text-slate-500">{llmMsg}</span>}
					</div>
				</CardContent>
			</Card>

			<Card>
				<CardHeader className="flex flex-row items-center justify-between pb-2">
					<CardTitle className="text-base">
						Configuration{config?.path ? ` — ${config.path}` : ""}
					</CardTitle>
					<div className="flex items-center gap-2">
						{saveMsg && (
							<span
								className={`flex items-center gap-1 text-xs ${saveMsg.startsWith("Config saved") ? "text-emerald-600" : "text-red-600"}`}
							>
								{saveMsg.startsWith("Config saved") ? (
									<Check className="h-3 w-3" />
								) : (
									<AlertCircle className="h-3 w-3" />
								)}
								{saveMsg}
							</span>
						)}
						{editing ? (
							<>
								<Button
									size="sm"
									variant="outline"
									onClick={handleCancelEdit}
									disabled={saving}
								>
									<X className="mr-1 h-3 w-3" />
									Cancel
								</Button>
								<Button size="sm" onClick={handleSave} disabled={saving}>
									{saving ? (
										<Loader2 className="mr-1 h-3 w-3 animate-spin" />
									) : (
										<Save className="mr-1 h-3 w-3" />
									)}
									Save
								</Button>
							</>
						) : (
							<Button
								size="sm"
								variant="outline"
								onClick={() => setEditing(true)}
							>
								<Edit3 className="mr-1 h-3 w-3" />
								Edit
							</Button>
						)}
					</div>
				</CardHeader>
				<CardContent>
					{editing ? (
						<textarea
							className="h-[60vh] w-full resize-none rounded-md border border-slate-600 bg-slate-900 p-4 font-mono text-xs leading-relaxed text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
							value={editYaml}
							onChange={(e) => setEditYaml(e.target.value)}
							spellCheck={false}
						/>
					) : (
						<pre className="max-h-[60vh] overflow-auto rounded-md border border-slate-700 bg-slate-900 p-4 font-mono text-xs leading-relaxed text-slate-300">
							{config?.yaml || "No config loaded."}
						</pre>
					)}
				</CardContent>
			</Card>

			<Card>
				<CardHeader className="pb-2">
					<CardTitle className="text-base">Runtime capabilities</CardTitle>
				</CardHeader>
				<CardContent className="space-y-2 text-sm text-slate-400">
					<p>
						Tool surface mode:{" "}
						<span className="font-medium">
							{capabilities?.runtime?.surface_mode ?? "unknown"}
						</span>
					</p>
					<p>
						Total tools:{" "}
						<span className="font-medium">
							{capabilities?.tool_surface?.total ?? 0}
						</span>
					</p>
					<p>
						Sampling:{" "}
						<span className="font-medium">
							{capabilities?.features?.sampling ? "available" : "not detected"}
						</span>
					</p>
					<p>
						Prompts / Skills:{" "}
						<span className="font-medium">
							{capabilities?.inventory?.prompt_names?.length ?? 0} /{" "}
							{capabilities?.inventory?.skill_uris?.length ?? 0}
						</span>
					</p>
				</CardContent>
			</Card>
		</div>
	);
}
