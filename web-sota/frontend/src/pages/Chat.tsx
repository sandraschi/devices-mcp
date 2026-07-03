import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type LLMModelInfo, normalizeModelList } from "@/lib/llmModels";
import { LOCAL_LLM_CATALOG, mergeProviderTypes } from "@/lib/llmProviders";
import { AlertCircle, Loader2, MessageCircle, Send } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface ChatMessage {
	role: string;
	content: string;
}

export function Chat() {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [input, setInput] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [providers, setProviders] = useState<string[]>([]);
	const [models, setModels] = useState<LLMModelInfo[]>([]);
	const [provider, setProvider] = useState("");
	const [model, setModel] = useState("");
	const [modelLoaded, setModelLoaded] = useState(false);
	const [deviceContextReady, setDeviceContextReady] = useState(false);
	const bottomRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, []);

	const loadProviders = useCallback(async () => {
		try {
			const r = await fetch("/api/llm/providers");
			const data = await r.json();
			if (data.success) {
				const fromApi = (data.providers ?? []).map(
					(p: { type?: string; name?: string }) => p.type ?? p.name ?? "",
				);
				const names = mergeProviderTypes(fromApi);
				setProviders(names);
				const preferred =
					(data as { preferred_provider?: string }).preferred_provider ??
					LOCAL_LLM_CATALOG[0].type;
				setProvider((current) => current || preferred || names[0] || "");
			} else {
				setProviders(mergeProviderTypes([]));
				setProvider(LOCAL_LLM_CATALOG[0].type);
			}
		} catch {
			setProviders(mergeProviderTypes([]));
			setProvider(LOCAL_LLM_CATALOG[0].type);
			setError(
				"Could not reach LLM API — using Ollama / LM Studio defaults. Configure in Settings.",
			);
		}
	}, []);

	const loadModels = useCallback(async () => {
		if (!provider) return;
		try {
			const r = await fetch(
				`/api/llm/models?provider=${encodeURIComponent(provider)}`,
			);
			const data = await r.json();
			if (data.success && data.models?.length) {
				const normalized = normalizeModelList(data.models);
				setModels(normalized);
				setModel((current) => current || normalized[0]?.name || "");
			} else {
				setModels([]);
			}
		} catch {
			setModels([]);
		}
	}, [provider]);

	useEffect(() => {
		loadProviders();
		fetch("/api/llm/device-context")
			.then((r) => (r.ok ? r.json() : null))
			.then((data) => setDeviceContextReady(Boolean(data?.success)))
			.catch(() => setDeviceContextReady(false));
	}, [loadProviders]);

	useEffect(() => {
		loadModels();
	}, [loadModels]);

	const loadModel = async () => {
		if (!model) return;
		setLoading(true);
		setError(null);
		try {
			const r = await fetch("/api/llm/models/load", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					model_name: model,
					provider: provider || undefined,
				}),
			});
			const data = await r.json();
			if (r.ok && data.success) {
				setModelLoaded(true);
			} else {
				setError((data as { detail?: string }).detail ?? "Load failed");
			}
		} catch (e) {
			setError(String(e));
		} finally {
			setLoading(false);
		}
	};

	const send = async (e: React.FormEvent) => {
		e.preventDefault();
		const text = input.trim();
		if (!text || loading) return;
		const userMsg: ChatMessage = { role: "user", content: text };
		setMessages((m) => [...m, userMsg]);
		setInput("");
		setLoading(true);
		setError(null);
		try {
			const r = await fetch("/api/llm/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					messages: [...messages, userMsg].map((msg) => ({
						role: msg.role,
						content: msg.content,
					})),
					provider: provider || undefined,
					model: model || undefined,
					stream: false,
					include_device_context: true,
				}),
			});
			const data = await r.json();
			if (r.ok && data.success) {
				const content =
					typeof data.response === "string"
						? data.response
						: (data.response ?? "");
				setMessages((m) => [
					...m,
					{ role: "assistant", content: content || "(no response)" },
				]);
			} else {
				setError((data as { detail?: string }).detail ?? "Chat failed");
			}
		} catch (e) {
			setError(String(e));
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold tracking-tight">Chat</h1>
			{error && (
				<div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
					<AlertCircle className="h-5 w-5 shrink-0" />
					{error}
				</div>
			)}
			<Card>
				<CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-2">
					<CardTitle className="text-base font-medium flex items-center gap-2">
						<MessageCircle className="h-5 w-5" /> Local LLM
					</CardTitle>
					<div className="flex flex-wrap items-center gap-2">
						<select
							value={provider}
							onChange={(e) => {
								setProvider(e.target.value);
								setModel("");
								setModelLoaded(false);
							}}
							className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
						>
							{(providers.length
								? providers
								: LOCAL_LLM_CATALOG.map((c) => c.type)
							).map((p) => (
								<option key={p} value={p}>
									{LOCAL_LLM_CATALOG.find((c) => c.type === p)?.label ?? p}
								</option>
							))}
						</select>
						{models.length > 0 && (
							<select
								value={model}
								onChange={(e) => {
									setModel(e.target.value);
									setModelLoaded(false);
								}}
								className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
							>
								{models.map((m) => (
									<option key={m.name} value={m.name}>
										{m.name}
									</option>
								))}
							</select>
						)}
						{model && (
							<Button
								size="sm"
								variant={modelLoaded ? "outline" : "default"}
								onClick={loadModel}
								disabled={loading}
							>
								{loading ? (
									<Loader2 className="h-4 w-4 animate-spin" />
								) : modelLoaded ? (
									"Loaded"
								) : (
									"Load model"
								)}
							</Button>
						)}
					</div>
				</CardHeader>
				<CardContent className="p-0">
					<div className="flex h-[420px] flex-col">
						<div className="flex-1 overflow-y-auto p-4 space-y-3">
							{messages.length === 0 && (
								<p className="text-sm text-slate-500 dark:text-slate-400">
									Load a model above, then ask about your home — e.g.{" "}
									<strong>What cameras do we have?</strong>
									{deviceContextReady
										? " Live device inventory is prepended to each request."
										: " Device inventory loads when the backend is ready."}
								</p>
							)}
							{messages.map((msg) => (
								<div
									key={msg.role + msg.content.slice(0, 40)}
									className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
										msg.role === "user"
											? "ml-auto bg-indigo-600 text-white dark:bg-indigo-700"
											: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
									}`}
								>
									{msg.content}
								</div>
							))}
							{loading && messages[messages.length - 1]?.role === "user" && (
								<div className="flex items-center gap-2 text-slate-500">
									<Loader2 className="h-4 w-4 animate-spin" />
									<span className="text-sm">Thinking…</span>
								</div>
							)}
							<div ref={bottomRef} />
						</div>
						<form
							onSubmit={send}
							className="flex gap-2 border-t border-slate-200 p-3 dark:border-slate-800"
						>
							<input
								type="text"
								value={input}
								onChange={(e) => setInput(e.target.value)}
								placeholder="Type a message…"
								className="flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
								disabled={loading}
							/>
							<Button
								type="submit"
								size="sm"
								disabled={loading || !input.trim()}
							>
								<Send className="h-4 w-4" />
							</Button>
						</form>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
