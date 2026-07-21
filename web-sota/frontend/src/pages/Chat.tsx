import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type LLMModelInfo, normalizeModelList } from "@/lib/llmModels";
import { LOCAL_LLM_CATALOG, mergeProviderTypes } from "@/lib/llmProviders";
import {
	AlertCircle,
	Download,
	Eraser,
	Loader2,
	MessageCircle,
	Send,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

const CHAT_KEY = "devices-mcp-chat-history";
const PERSONALITY_KEY = "devices-mcp-chat-personality";
const MAX_MESSAGES = 100;

const PERSONAS: { id: string; label: string; prompt: string }[] = [
	{
		id: "research",
		label: "Research Assistant",
		prompt:
			"You are a thorough home automation research assistant. Answer questions with detail, cite device data where relevant, and suggest improvements when appropriate.",
	},
	{
		id: "reviewer",
		label: "Expert Reviewer",
		prompt:
			"You are an expert smart home reviewer. Provide concise, critical analysis of device status and configurations. Be direct and technical.",
	},
	{
		id: "summarizer",
		label: "Quick Summarizer",
		prompt:
			"You are a quick summarizer. Give short, bullet-point responses. Focus on the most important information only. Be brief.",
	},
	{
		id: "operator",
		label: "Device Operator",
		prompt:
			"You are a smart home operator. When the user asks to control a device, confirm before acting. State device name, action, and expected result clearly.",
	},
	{
		id: "custom",
		label: "Custom",
		prompt: "",
	},
];

const EXAMPLE_PROMPTS = [
	{ text: "Show me the status of all cameras", group: "Status" },
	{ text: "What devices are online right now?", group: "Status" },
	{ text: "Turn on the living room lights", group: "Control" },
	{ text: "Is the Ring alarm armed?", group: "Security" },
	{ text: "Show me recent doorbell events", group: "Security" },
	{ text: "What's the weather outside?", group: "Info" },
	{ text: "Check my Nest Protect battery levels", group: "Security" },
	{ text: "List P115 plug energy usage", group: "Energy" },
];

interface ChatMessage {
	role: string;
	content: string;
	ts?: string;
}

function loadHistory(): ChatMessage[] {
	try {
		const raw = localStorage.getItem(CHAT_KEY);
		if (raw) return JSON.parse(raw) as ChatMessage[];
	} catch {
		/* ignore */
	}
	return [];
}

function saveHistory(msgs: ChatMessage[]) {
	try {
		localStorage.setItem(CHAT_KEY, JSON.stringify(msgs.slice(-MAX_MESSAGES)));
	} catch {
		/* ignore */
	}
}

export function Chat() {
	const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);
	const [input, setInput] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [providers, setProviders] = useState<string[]>([]);
	const [models, setModels] = useState<LLMModelInfo[]>([]);
	const [provider, setProvider] = useState("");
	const [model, setModel] = useState("");
	const [skillContent, setSkillContent] = useState("");
	const [personaId, setPersonaId] = useState(
		() => localStorage.getItem(PERSONALITY_KEY) || "operator",
	);
	const [customPrompt, setCustomPrompt] = useState("");
	const [streamingContent, setStreamingContent] = useState("");
	const bottomRef = useRef<HTMLDivElement>(null);
	const abortRef = useRef<AbortController | null>(null);

	const scrollBottom = () =>
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });

	useEffect(() => {
		scrollBottom();
	}, [messages, streamingContent]);

	// Persist messages on change
	useEffect(() => {
		saveHistory(messages);
	}, [messages]);

	// Persist personality
	useEffect(() => {
		localStorage.setItem(PERSONALITY_KEY, personaId);
	}, [personaId]);

	const currentPersona = PERSONAS.find((p) => p.id === personaId) ?? PERSONAS[0];

	const buildSystemPrompt = useCallback((): string => {
		const skill = skillContent
			? `## Home Inventory\n\n${skillContent}`
			: "";
		if (personaId === "custom") return customPrompt || skill;
		return `${skill}\n\n---\n\n## Role\n${currentPersona.prompt}`;
	}, [skillContent, personaId, customPrompt, currentPersona.prompt]);

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

	const loadSkill = useCallback(async () => {
		try {
			const r = await fetch("/api/skills");
			const data = await r.json();
			if (data.success && data.skills?.length) {
				const primary = data.skills[0].name;
				const sr = await fetch(`/api/skills/${encodeURIComponent(primary)}`);
				if (sr.ok) {
					const text = await sr.text();
					if (text !== "not found") setSkillContent(text);
				}
			}
		} catch {
			/* optional */
		}
	}, []);

	useEffect(() => {
		loadProviders();
		loadSkill();
		fetch("/api/llm/device-context")
			.then((r) => (r.ok ? r.json() : null))
			.then(() => {})
			.catch(() => {});
	}, [loadProviders, loadSkill]);

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
			if (!r.ok || !data.success) {
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
		const userMsg: ChatMessage = {
			role: "user",
			content: text,
			ts: new Date().toISOString(),
		};
		const updated = [...messages, userMsg];
		setMessages(updated);
		saveHistory(updated);
		setInput("");
		setLoading(true);
		setError(null);
		setStreamingContent("");

		const systemPrompt = buildSystemPrompt();
		const body = {
			messages: [
				...(systemPrompt
					? [{ role: "system" as const, content: systemPrompt }]
					: []),
				...updated.map((msg) => ({ role: msg.role, content: msg.content })),
			],
			provider: provider || undefined,
			model: model || undefined,
			stream: true,
			include_device_context: true,
		};

		abortRef.current = new AbortController();
		try {
			const r = await fetch("/api/llm/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
				signal: abortRef.current.signal,
			});
			if (!r.ok) {
				const data = await r.json().catch(() => ({}));
				setError(
					(data as { detail?: string }).detail ?? `HTTP ${r.status}`,
				);
				return;
			}
			// Streaming via NDJSON
			const reader = r.body?.getReader();
			if (!reader) {
				// Fallback: non-streaming response
				const data = await r.json();
				const content =
					typeof data.response === "string"
						? data.response
						: data.response ?? "";
				setMessages((prev) => [
					...prev,
					{
						role: "assistant",
						content: content || "(no response)",
						ts: new Date().toISOString(),
					},
				]);
				return;
			}
			const decoder = new TextDecoder();
			let buffer = "";
			let fullContent = "";
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split("\n");
				buffer = lines.pop() ?? "";
				for (const line of lines) {
					if (!line.trim()) continue;
					try {
						const chunk = JSON.parse(line);
						const delta =
							chunk.response ?? chunk.message?.content ?? chunk.text ?? "";
						if (delta) {
							fullContent += delta;
							setStreamingContent(fullContent);
						}
					} catch {
						// partial line — will be completed in next chunk
					}
				}
			}
			// Flush remaining buffer
			if (buffer.trim()) {
				try {
					const chunk = JSON.parse(buffer);
					const delta =
						chunk.response ?? chunk.message?.content ?? chunk.text ?? "";
					if (delta) fullContent += delta;
				} catch {
					/* ignore partial */
				}
			}
			if (fullContent) {
				setMessages((prev) => [
					...prev,
					{
						role: "assistant",
						content: fullContent,
						ts: new Date().toISOString(),
					},
				]);
				setStreamingContent("");
			}
		} catch (e: unknown) {
			if (e instanceof DOMException && e.name === "AbortError") return;
			setError(String(e));
		} finally {
			setLoading(false);
			abortRef.current = null;
		}
	};

	const handleExport = () => {
		if (!messages.length) return;
		const lines = messages.map(
			(m) =>
				`[${m.ts ?? "?"}] ${m.role === "user" ? "You" : "Assistant"}: ${m.content}`,
		);
		const blob = new Blob([lines.join("\n\n")], { type: "text/plain" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `devices-mcp-chat-${new Date().toISOString().slice(0, 10)}.txt`;
		a.click();
		URL.revokeObjectURL(url);
	};

	const handleClear = () => {
		setMessages([]);
		setStreamingContent("");
		setError(null);
		localStorage.removeItem(CHAT_KEY);
	};

	return (
		<div className="space-y-6" data-testid="chat-page">
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
						{skillContent && (
							<span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-normal text-slate-500 dark:bg-slate-800 dark:text-slate-400">
								skill:devices-mcp
							</span>
						)}
					</CardTitle>
					<div
						className="flex flex-wrap items-center gap-2"
						data-testid="chat-controls"
					>
						<select
							data-testid="personality-select"
							value={personaId}
							onChange={(e) => setPersonaId(e.target.value)}
							className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-zinc-800 dark:text-zinc-100"
						>
							{PERSONAS.map((p) => (
								<option key={p.id} value={p.id}>
									{p.label}
								</option>
							))}
						</select>
						{personaId === "custom" && (
							<input
								type="text"
								value={customPrompt}
								onChange={(e) => setCustomPrompt(e.target.value)}
								placeholder="Your custom system prompt..."
								className="w-40 rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-zinc-800 dark:text-zinc-100"
							/>
						)}
						<select
							value={provider}
							onChange={(e) => {
								setProvider(e.target.value);
								setModel("");
							}}
							className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-zinc-800 dark:text-zinc-100"
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
								}}
								className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-zinc-800 dark:text-zinc-100"
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
								variant="outline"
								onClick={loadModel}
								disabled={loading}
							>
								{loading ? (
									<Loader2 className="h-4 w-4 animate-spin" />
								) : (
									"Load"
								)}
							</Button>
						)}
						<Button
							size="sm"
							variant="ghost"
							onClick={handleExport}
							disabled={!messages.length}
							data-testid="chat-export"
							title="Export chat"
						>
							<Download className="h-4 w-4" />
						</Button>
						<Button
							size="sm"
							variant="ghost"
							onClick={handleClear}
							disabled={!messages.length}
							data-testid="chat-clear"
							title="Clear conversation"
						>
							<Eraser className="h-4 w-4" />
						</Button>
					</div>
				</CardHeader>
				<CardContent className="p-0">
					<div className="flex h-[480px] flex-col">
						<div
							className="flex-1 overflow-y-auto p-4 space-y-3"
							data-testid="chat-messages"
						>
							{!messages.length && !streamingContent && (
								<div data-testid="example-prompts">
									<p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
										{skillContent
											? "I know your home devices. Try one of these:"
											: "Load a model above, then ask about your home:"}
									</p>
									<div className="flex flex-wrap gap-2">
										{EXAMPLE_PROMPTS.map((ep) => (
											<button
												key={ep.text}
												type="button"
												onClick={() => setInput(ep.text)}
												className="rounded-md border border-slate-200 px-3 py-1.5 text-xs text-slate-600 transition hover:bg-amber-50 hover:border-amber-300 hover:text-amber-700 dark:border-slate-600 dark:text-slate-400 dark:hover:bg-amber-900/20 dark:hover:border-amber-500 dark:hover:text-amber-400"
											>
												{ep.text}
											</button>
										))}
									</div>
								</div>
							)}
							{messages.map((msg, i) => (
								<div
									key={`${msg.role}-${i}`}
									className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
										msg.role === "user"
											? "ml-auto bg-indigo-600 text-white dark:bg-indigo-700"
											: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
									}`}
								>
									{msg.content}
								</div>
							))}
							{streamingContent && (
								<div className="max-w-[85%] rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-800 dark:bg-slate-800 dark:text-slate-200 whitespace-pre-wrap">
									{streamingContent}
								</div>
							)}
							{loading && !streamingContent && (
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
								data-testid="chat-input"
								type="text"
								value={input}
								onChange={(e) => setInput(e.target.value)}
								placeholder="Type a message…"
								className="flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-zinc-800 dark:text-zinc-100"
								disabled={loading}
							/>
							<Button
								type="submit"
								size="sm"
								disabled={loading || !input.trim()}
								data-testid="chat-send"
							>
								{loading ? (
									<Loader2 className="h-4 w-4 animate-spin" />
								) : (
									<Send className="h-4 w-4" />
								)}
							</Button>
						</form>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
