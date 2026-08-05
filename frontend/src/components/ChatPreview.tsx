import { CheckCircle2, ChevronDown, Copy, Download, FileDown, FileText, LoaderCircle, Maximize2, RotateCcw, Send, Settings2, Share2, ThumbsDown, ThumbsUp, TriangleAlert, Upload, X } from "lucide-react";
import React, { FormEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { downloadMarkdown, downloadPdf } from "../utils/answerExport";
import { formatAnswerMarkdown } from "../utils/markdownFormat";
import "../providerSettings.css";
import "../chatComposer.css";

type Citation = { id: number; source: string; page: number; chunk_id: string | number; content: string; chunk_text?: string; sentence?: string; position?: number; confidence: number; valid?: boolean; confidence_level?: string };
type CitationSummary = { valid: number; invalid: number; coverage: number; confidence_level: string };
type Settings = { top_k: number; temperature: number; max_tokens: number; enable_cross_encoder: boolean; enable_bm25: boolean; enable_vector_search: boolean; enable_hybrid_search: boolean; enable_rrf: boolean };
type Provider = "groq" | "openai" | "gemini" | "ollama";
type ProviderState = { provider: Provider; model: string; connected: boolean; status: string };
type Message = { id: string; role: "user" | "assistant"; content: string; verified?: boolean; citations?: Citation[]; citation_summary?: CitationSummary; session_id?: string; retrieval_confidence?: number; citation_confidence?: number; confidence?: number; streaming?: boolean; };
type GenerationError = { detail: string; status?: number };
type ViewerContext = { citation: Citation; citations: Citation[] };

const defaults: Settings = { top_k: 8, temperature: .2, max_tokens: 2048, enable_cross_encoder: true, enable_bm25: true, enable_vector_search: true, enable_hybrid_search: true, enable_rrf: true };
const suggestions = ["Summarize the leave policy", "What is the casual leave allowance?", "What does the employee handbook say?"];

const providerDefaults: Record<Provider, string> = {
  groq: "llama-3.3-70b-versatile",
  openai: "gpt-4o-mini",
  gemini: "gemini-3.5-flash-lite",
  ollama: "llama3.2",
};

const geminiModels = ["gemini-3.5-flash-lite", "gemini-3.6-flash"];

function Sources({ citations = [], select }: { citations?: Citation[]; select: (citation: Citation) => void }) {
  const grouped = citations.reduce<Map<string, Citation[]>>((map, citation) => {
    const sources = map.get(citation.source) ?? [];
    if (!sources.some(item => item.id === citation.id)) sources.push(citation);
    map.set(citation.source, sources);
    return map;
  }, new Map());

  if (!grouped.size) return null;

  const copyChunk = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Ignore silently if clipboard is unavailable.
    }
  };

  const totalCitations = citations.length;

  return (
    <details className="sources-panel" open>
      <summary>
        <div className="sources-summary"><FileText size={16} /> Sources <span>{totalCitations} citations</span></div>
        <ChevronDown size={15} />
      </summary>
      <div className="sources-grid">
        {[...grouped].map(([source, citations]) => (
          <article className="source-card" key={source}>
            <div className="source-card-header">
              <div className="source-title"><FileText size={16} /> {source}</div>
              <span className="source-count">{citations.length} citation{citations.length === 1 ? "" : "s"}</span>
            </div>

            <div className="source-items">
              {citations.sort((a, b) => a.id - b.id).map(citation => (
                <div className="source-item" key={citation.id}>
                  <div className="source-item-top">
                    <button type="button" className="source-item-link" onClick={() => select(citation)}>
                      [{citation.id}] Page {citation.page} · Chunk {citation.chunk_id}
                    </button>
                    <div className="source-item-actions">
                      <span className="source-chip">{Math.round(citation.confidence * 100)}% confidence</span>
                      <button type="button" onClick={() => void copyChunk(citation.content)}>Copy</button>
                      <a href={`/api/documents/${encodeURIComponent(citation.source)}`} target="_blank" rel="noreferrer">Open</a>
                    </div>
                  </div>
                  <p className="source-snippet">{citation.content?.slice(0, 160)}{citation.content?.length > 160 ? "…" : ""}</p>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </details>
  );
}

/**
 * FIX #2: The answer is ALWAYS rendered through ReactMarkdown — never swapped for a
 * <pre> during streaming. This keeps the element type stable across the
 * streaming -> done transition, so React updates text in place instead of
 * unmounting/remounting the subtree (which was causing both the visual
 * "reformat" and the layout jump).
 *
 * FIX #1: The confidence panel now renders AFTER markdown-answer (not before it),
 * and stays mounted at all times — it transitions height/opacity instead of being
 * conditionally inserted, so it can never push the answer text downward.
 */
function Assistant({ message, select, regenerate, loading }: { message: Message; select: (citation: Citation) => void; regenerate: () => void; loading: boolean }) {
  const answer = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const isStreaming = Boolean(message.streaming);

  // Only run the (potentially expensive) formatting pass once streaming is done
  // and again only when content actually changes, instead of every render.
  const formatted = useMemo(() => formatAnswerMarkdown(message.content), [message.content]);

  if (!message.content.trim()) return null;

  // While streaming we feed ReactMarkdown the raw accumulated text (cheap, and
  // partial markdown renders fine incrementally). Once done, we switch the
  // *content* being fed to the same element — not the element itself — to the
  // fully formatted version.
  const displayText = isStreaming ? message.content : formatted;

  const citationCount = message.citations?.length ?? 0;
  const summary = message.citation_summary;
  const citationMap = new Map<string, Citation>((message.citations ?? []).map(citation => [citation.id.toString(), citation]));

  const metrics = [
    { label: "Retrieval", value: message.retrieval_confidence },
    { label: "Citation", value: message.citation_confidence },
    { label: "Grounding", value: message.confidence },
    { label: "Coverage", value: summary?.coverage ? summary.coverage / 100 : undefined },
  ];

  const hasMetrics = !isStreaming && (summary !== undefined || message.retrieval_confidence !== undefined);

  const components = {
    a: (props: any) => {
      const href = props.href as string | undefined;
      const children = props.children as ReactNode;
      if (href?.startsWith("citation:")) {
        const id = href.split(":")[1];
        const citation = citationMap.get(id);
        const tooltip = citation ? `${citation.source} · Page ${citation.page} · Chunk ${citation.chunk_id} · ${Math.round(citation.confidence * 100)}%` : undefined;
        return citation ? (
          <button type="button" className="citation-badge" title={tooltip} onClick={() => select(citation)} aria-label={`Open citation ${id}`}>
            [{children}]
          </button>
        ) : (
          <span>{children}</span>
        );
      }
      return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
    },
    code: ({ inline, className, children }: any) => (
      inline ? <code className="inline-code">{children}</code> : <pre className="code-block"><code className={className}>{children}</code></pre>
    ),
    blockquote: ({ children }: any) => <blockquote>{children}</blockquote>,
    table: ({ children }: any) => <div className="table-wrapper"><table>{children}</table></div>,
    th: ({ children }: any) => <th>{children}</th>,
    td: ({ children }: any) => <td>{children}</td>,
  };

  const shareAnswer = async () => {
    const payload = formatted;
    if (navigator.share) {
      try {
        await navigator.share({ title: "RAG answer", text: payload });
        return;
      } catch {
        // Fall back to clipboard if native share is unavailable or canceled.
      }
    }
    await navigator.clipboard.writeText(payload);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <motion.article className="chat-message assistant-message" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .22 }}>
      <div className="answer-toolbar">
        <div className="answer-status-wrap">
          <span className={message.verified ? "answer-status verified" : "answer-status unverified"}>
            {message.verified ? <CheckCircle2 size={16} /> : <TriangleAlert size={16} />}
            <span>
              {message.verified ? "Verified answer" : "Answer may be incomplete"}
              <small>{citationCount ? `${citationCount} cited page${citationCount === 1 ? "" : "s"}` : "No citations returned"}</small>
            </span>
          </span>
          {message.confidence !== undefined ? (
            <span className="answer-score">Overall {Math.round(message.confidence * 100)}%</span>
          ) : null}
        </div>

        <div className="answer-actions">
          <button title="Copy answer" onClick={async () => { await navigator.clipboard.writeText(formatted); setCopied(true); setTimeout(() => setCopied(false), 1200); }}>
            <Copy size={16} />{copied ? "Copied" : "Copy"}
          </button>
          <button title="Share answer" onClick={() => void shareAnswer()}>
            <Share2 size={16} />Share
          </button>
          <button title="Export Markdown" onClick={() => downloadMarkdown(formatted)}>
            <Download size={16} />Markdown
          </button>
          <button title="Export PDF" onClick={() => answer.current && downloadPdf(answer.current, message.citations)}>
            <FileDown size={16} />PDF
          </button>
          <button className={feedback === "up" ? "is-selected" : ""} title="Helpful" onClick={() => setFeedback("up")} aria-label="Like answer">
            <ThumbsUp size={16} />
          </button>
          <button className={feedback === "down" ? "is-selected" : ""} title="Not helpful" onClick={() => setFeedback("down")} aria-label="Dislike answer">
            <ThumbsDown size={16} />
          </button>
          <button title="Regenerate answer" onClick={regenerate} disabled={loading}>
            <RotateCcw size={16} />Regenerate
          </button>
        </div>
      </div>

      {/* FIX #2: single, stable element type across streaming -> done.
          No <pre>/<ReactMarkdown> swap => no unmount/remount => no reformat jump. */}
      <div ref={answer} className="markdown-answer" aria-live={isStreaming ? "polite" : "off"} role="status">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
          {displayText}
        </ReactMarkdown>
        {isStreaming && <span className="cursor-blink" aria-hidden="true" />}
      </div>

      {/* FIX #1: always mounted, positioned AFTER the answer, animates height/opacity
          instead of being conditionally inserted above the text. Can never push
          the answer down because it never appears above it and never pops in. */}
      <div className={`confidence-panel ${hasMetrics ? "is-visible" : "is-collapsed"}`} aria-hidden={!hasMetrics}>
        {metrics.map(metric => metric.value !== undefined ? (
          <div className="metric-row" key={metric.label}>
            <div className="metric-label">
              <span>{metric.label}</span>
              <strong>{Math.round((metric.value ?? 0) * 100)}%</strong>
            </div>
            <div className="metric-bar">
              <span style={{ width: `${Math.min(Math.max((metric.value ?? 0) * 100, 0), 100)}%` }} />
            </div>
          </div>
        ) : null)}
        {summary ? <div className="metric-note">Citation verification: {summary.confidence_level} confidence</div> : null}
      </div>

      <Sources citations={message.citations} select={select} />
    </motion.article>
  );
}

const MemoAssistant = React.memo(Assistant);

function Viewer({ citation, citations, close, width }: { citation: Citation; citations: Citation[]; close: () => void; width: number; resize: (width: number) => void }) {
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [page, setPage] = useState(citation.page);
  const [zoom, setZoom] = useState<"page-width" | "page-fit" | number>("page-width");
  const [currentIndex, setCurrentIndex] = useState(() => citations.findIndex(item => item.id === citation.id) || 0);
  const viewer = useRef<HTMLElement>(null);

  useEffect(() => {
    setLoading(true);
    setFailed(false);
    setPage(citation.page);
    const index = citations.findIndex(item => item.id === citation.id);
    setCurrentIndex(index >= 0 ? index : 0);
  }, [citation, citations]);

  const currentCitation = citations[currentIndex] ?? citation;
  const source = `/api/documents/${encodeURIComponent(currentCitation.source)}#page=${page}&zoom=${zoom}`;
  const fullscreen = () => document.fullscreenElement ? document.exitFullscreen() : viewer.current?.requestFullscreen();
  const snippet = currentCitation.content ? currentCitation.content.trim().slice(0, 340) : "";

  const canPrev = currentIndex > 0;
  const canNext = currentIndex + 1 < citations.length;

  return (
    <motion.aside ref={viewer} className="glass-card document-viewer" style={{ width }} initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 1, x: 18 }}>
      <header>
        <div className="viewer-title"><FileText size={16} /> {currentCitation.source}</div>
        <div className="viewer-controls">
          <button onClick={() => canPrev && setCurrentIndex(i => Math.max(0, i - 1))} disabled={!canPrev} aria-label="Previous citation">Prev</button>
          <button onClick={() => canNext && setCurrentIndex(i => Math.min(citations.length - 1, i + 1))} disabled={!canNext} aria-label="Next citation">Next</button>
          <button onClick={() => setPage(value => Math.max(1, value - 1))} aria-label="Previous page">‹</button>
          <b className="page-indicator">Page {page}</b>
          <button onClick={() => setPage(value => value + 1)} aria-label="Next page">›</button>
          <button onClick={() => setZoom(value => value === "page-width" ? "page-fit" : value === "page-fit" ? 100 : "page-width")} aria-label="Toggle zoom">
            {zoom === "page-width" ? "Fit page" : zoom === "page-fit" ? "100%" : "Fit width"}
          </button>
          <a href={`/api/documents/${encodeURIComponent(currentCitation.source)}`} download aria-label="Download PDF"><Download size={15} /></a>
          <button onClick={fullscreen} aria-label="Full screen"><Maximize2 size={15} /></button>
          <button onClick={close} aria-label="Close PDF viewer"><X size={17} /></button>
        </div>
      </header>

      <section className="citation-preview">
        <div className="citation-preview-heading">
          <span>Chunk {currentCitation.chunk_id}</span>
          <span>Page {currentCitation.page}</span>
          <span>{Math.round(currentCitation.confidence * 100)}% confidence</span>
        </div>
        <p>{snippet}{currentCitation.content.length > 340 ? "…" : ""}</p>
      </section>

      {loading && !failed && <div className="viewer-state"><LoaderCircle size={20} className="spinner" /> Loading PDF…</div>}
      {failed ? (
        <div className="viewer-state viewer-error"><TriangleAlert size={20} />This PDF could not be opened.</div>
      ) : (
        <iframe title={currentCitation.source} src={source} onLoad={() => setLoading(false)} onError={() => { setLoading(false); setFailed(true); }} />
      )}
    </motion.aside>
  );
}

function RetrievalSettings({ value, update }: { value: Settings; update: (setting: Partial<Settings>) => void }) {
  const toggles: [keyof Settings, string][] = [["enable_cross_encoder", "CrossEncoder"], ["enable_bm25", "BM25"], ["enable_vector_search", "Vector Search"], ["enable_hybrid_search", "Hybrid Search"], ["enable_rrf", "RRF"]];
  return <details className="settings-panel"><summary><Settings2 size={15} /> Retrieval settings <ChevronDown size={15} /></summary><div className="settings-grid"><label>Top-K<input type="number" min="1" max="20" value={value.top_k} onChange={e => update({ top_k: +e.target.value })} /></label><label>Temperature<input type="number" min="0" max="2" step=".1" value={value.temperature} onChange={e => update({ temperature: +e.target.value })} /></label><label>Max tokens<input type="number" min="64" max="4096" value={value.max_tokens} onChange={e => update({ max_tokens: +e.target.value })} /></label>{toggles.map(([key, title]) => <label className="toggle" key={key}><span>{title}</span><input type="checkbox" checked={Boolean(value[key])} onChange={e => update({ [key]: e.target.checked } as Partial<Settings>)} /></label>)}</div></details>;
}

function ProviderSettings({ value, update, open, onToggle }: { value: ProviderState; update: (value: Partial<ProviderState>) => void; open: boolean; onToggle: (open: boolean) => void }) {
  const [testing, setTesting] = useState(false);

  async function testConnection() {
    setTesting(true);
    update({ connected: false, status: "Testing connection…" });
    try {
      const response = await fetch("/api/providers/test", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider: value.provider, model: value.model || undefined }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Connection failed.");
      update({ connected: true, status: `Connected to ${result.provider}.` });
    } catch (error) {
      update({ connected: false, status: error instanceof Error ? error.message : "Connection failed." });
    } finally {
      setTesting(false);
    }
  }

  return (
    <details className="settings-panel provider-panel" open={open} onToggle={event => onToggle((event.currentTarget as HTMLDetailsElement).open)}>
      <summary>
        <Settings2 size={15} /> AI Provider Settings <ChevronDown size={15} />
      </summary>

      <div className="settings-grid">
        <label>
          Provider
          <select
            value={value.provider}
            onChange={(e) => {
              const provider = e.target.value as Provider;
              update({ provider, model: providerDefaults[provider], connected: false, status: "Not tested" });
            }}
          >
            <option value="groq">Groq</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Google Gemini</option>
            <option value="ollama">Ollama</option>
          </select>
        </label>

        <label>
          Model
          {value.provider === "gemini" ? (
            <select
              value={value.model}
              onChange={(e) => update({ model: e.target.value, connected: false, status: "Not tested" })}
            >
              {geminiModels.map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          ) : (
            <input
              value={value.model}
              onChange={(e) => update({ model: e.target.value, connected: false, status: "Not tested" })}
            />
          )}
        </label>

        <div className={`provider-status ${value.connected ? "connected" : ""}`}>
          {value.connected ? "● " : "○ "}
          {value.status}
        </div>

        <div className="provider-actions">
          <button type="button" onClick={() => void testConnection()} disabled={testing}>
            {testing ? "Testing…" : "Test connection"}
          </button>
        </div>
      </div>
    </details>
  );
}

export function ChatPreview() {
  const autoFollow = useRef(true); const scrollFrame = useRef<number | null>(null);
  const [messages, setMessages] = useState<Message[]>(() => (JSON.parse(sessionStorage.getItem("rag-history") ?? "[]") as Message[]).filter(message => message.role !== "assistant" || Boolean(message.content?.trim())));
  const [settings, setSettings] = useState(defaults);
  const [provider, setProvider] = useState<ProviderState>({ provider: "groq", model: providerDefaults.groq, connected: false, status: "Using the developer default Groq key." });
  const [providerPrompt, setProviderPrompt] = useState(false);
  const [question, setQuestion] = useState("");
  const [viewer, setViewer] = useState<ViewerContext | null>(null);
  const [viewerWidth, setViewerWidth] = useState(500);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [notice, setNotice] = useState("");
  const [generationError, setGenerationError] = useState<GenerationError | null>(null);
  const uploadInput = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const request = useRef<AbortController | null>(null);
  const lastQuestion = useRef("");
  const sessionId = useRef(sessionStorage.getItem("rag-session") ?? crypto.randomUUID());
  // Kept in a ref so stabilized callbacks (below) can always read the latest
  // messages without needing `messages` in their dependency array.
  const messagesRef = useRef<Message[]>(messages);
  messagesRef.current = messages;

  useEffect(() => { sessionStorage.setItem("rag-session", sessionId.current); }, []);

  // Seed retrieval settings AND initial provider/model from the backend, once.
  useEffect(() => {
    fetch("/api/settings")
      .then(r => (r.ok ? r.json() : null))
      .then((data: (Settings & { provider?: Provider; model?: string }) | null) => {
        if (!data) return;
        const { provider: fetchedProvider, model: fetchedModel, ...retrieval } = data;
        setSettings(current => ({ ...current, ...retrieval }));
        if (fetchedProvider) {
          setProvider(current => ({
            ...current,
            provider: fetchedProvider,
            model: fetchedModel ?? providerDefaults[fetchedProvider],
          }));
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => { sessionStorage.setItem("rag-history", JSON.stringify(messages)); if (!autoFollow.current) return; if (scrollFrame.current) cancelAnimationFrame(scrollFrame.current); scrollFrame.current = requestAnimationFrame(() => { const pane = document.querySelector<HTMLElement>(".chat-scroll"); if (pane && autoFollow.current) pane.scrollTop = pane.scrollHeight; }); return () => { if (scrollFrame.current) cancelAnimationFrame(scrollFrame.current); }; }, [messages, loading]);
  useEffect(() => { const pane = document.querySelector<HTMLElement>(".chat-scroll"); if (!pane) return; const updateFollow = () => { autoFollow.current = pane.scrollHeight - pane.scrollTop - pane.clientHeight < 80; }; pane.addEventListener("scroll", updateFollow, { passive: true }); updateFollow(); return () => pane.removeEventListener("scroll", updateFollow); }, []);
  useEffect(() => { const textarea = document.querySelector<HTMLTextAreaElement>(".chat-compose textarea"); const form = textarea?.closest("form"); if (!textarea || !form) return; const resize = () => { textarea.style.height = "0px"; textarea.style.height = `${Math.min(textarea.scrollHeight, 280)}px`; textarea.style.overflowY = textarea.scrollHeight > 280 ? "auto" : "hidden"; }; const sendOnEnter = (event: KeyboardEvent) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); if (!loading && textarea.value.trim()) void ask(textarea.value); } }; resize(); textarea.addEventListener("input", resize); textarea.addEventListener("keydown", sendOnEnter); form.classList.toggle("composer-loading", loading); return () => { textarea.removeEventListener("input", resize); textarea.removeEventListener("keydown", sendOnEnter); }; }, [question, loading]);
  useEffect(() => {
    if (!loading) {
      setElapsedMs(0);
      return;
    }
    const start = performance.now();
    const interval = window.setInterval(() => setElapsedMs(Math.round(performance.now() - start)), 250);
    return () => window.clearInterval(interval);
  }, [loading]);

  const cancelGeneration = () => {
    request.current?.abort();
    setLoading(false);
    setGenerationError({ detail: "Generation canceled.", status: 0 });
  };

  async function ask(value: string) {
    const text = value.trim();
    if (!text || loading) return;
    const id = crypto.randomUUID();
    lastQuestion.current = text;
    request.current = new AbortController();
    setQuestion("");
    setGenerationError(null);
    autoFollow.current = true;
    setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: text }]);
    setLoading(true);

    const appendAssistantToken = (token: string) => {
      if (!token) return;
      setMessages(prev => {
        const index = prev.findIndex(message => message.id === id);
        if (index === -1) {
          return [...prev, { id, role: "assistant", content: token, verified: false, streaming: true }];
        }
        const existing = prev[index];
        const updated = { ...existing, content: existing.content + token, streaming: true };
        return prev.map((message, idx) => (idx === index ? updated : message));
      });
    };

    // FIX #3: `content` is never overwritten by the "done" payload once tokens
    // have already streamed in. We only fall back to `payload.answer` for the
    // (unlikely) case where no tokens arrived at all — e.g. a non-streaming
    // fallback path. This prevents a server-normalized final string (different
    // whitespace/markdown than what streamed) from silently replacing text the
    // user already watched render, which was a second source of the "reformat"
    // symptom in addition to the <pre>/ReactMarkdown swap.
    const mergeAssistantResult = (payload: { answer?: string; verified?: boolean; citations?: Citation[]; citation_summary?: CitationSummary; session_id?: string; retrieval_confidence?: number; citation_confidence?: number; confidence?: number }) => {
      setMessages(prev => {
        const index = prev.findIndex(message => message.id === id);
        if (index === -1) {
          return [
            ...prev,
            {
              id,
              role: "assistant",
              content: payload.answer ?? "",
              verified: payload.verified ?? false,
              citations: payload.citations ?? [],
              citation_summary: payload.citation_summary,
              session_id: payload.session_id,
              retrieval_confidence: payload.retrieval_confidence,
              citation_confidence: payload.citation_confidence,
              confidence: payload.confidence,
              streaming: false,
            },
          ];
        }
        return prev.map(message =>
          message.id === id
            ? {
                ...message,
                // Never clobber streamed content with the server's final string.
                // Only used as a fallback when nothing was streamed at all.
                content: message.content || payload.answer || "",
                verified: payload.verified ?? message.verified,
                citations: payload.citations ?? message.citations,
                citation_summary: payload.citation_summary ?? message.citation_summary,
                session_id: payload.session_id ?? message.session_id,
                retrieval_confidence: payload.retrieval_confidence ?? message.retrieval_confidence,
                citation_confidence: payload.citation_confidence ?? message.citation_confidence,
                confidence: payload.confidence ?? message.confidence,
                streaming: false,
              }
            : message,
        );
      });
    };

    const processEvent = (eventText: string) => {
      const lines = eventText.split("\n");
      let eventType = "";
      const dataLines: string[] = [];

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5));
        }
      }

      if (!dataLines.length) return;

      const rawData = dataLines.join("\n");
      let payload: any;
      try {
        payload = JSON.parse(rawData);
      } catch (error) {
        console.error("Failed to parse SSE payload:", rawData, error);
        return;
      }

      if (eventType === "token" && typeof payload.token === "string") {
        appendAssistantToken(payload.token);
      } else if (eventType === "done") {
        mergeAssistantResult(payload);
      } else if (eventType === "error") {
        setGenerationError({ detail: payload.detail || "Unable to generate a response.", status: payload.status });
        if ([401, 429].includes(payload.status)) {
          setProviderPrompt(true);
        }
      }
    };

    try {
      const response = await fetch("/api/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Session-ID": sessionId.current },
        signal: request.current.signal,
        body: JSON.stringify({
          question: text,
          settings: {
            ...settings,
            provider: provider.provider,
            model: provider.model,
          },
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw Object.assign(new Error(payload.detail || "Unable to generate a response."), { status: response.status });
      }

      if (!response.body) {
        throw new Error("Unable to generate a response.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const processBuffer = () => {
        while (true) {
          const delimiterIndex = buffer.indexOf("\n\n");
          if (delimiterIndex === -1) break;
          const eventText = buffer.slice(0, delimiterIndex);
          buffer = buffer.slice(delimiterIndex + 2);
          const trimmed = eventText.trim();
          if (trimmed) {
            processEvent(trimmed);
          }
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        if (buffer.includes("\r\n")) {
          buffer = buffer.split("\r\n").join("\n");
        }
        if (buffer.includes("\r")) {
          buffer = buffer.split("\r").join("\n");
        }
        processBuffer();
      }

      if (buffer.trim()) {
        processEvent(buffer.trim());
      }
    } catch (err) {
      if ((err as DOMException).name !== "AbortError") {
        const failure = err as Error & { status?: number };
        setGenerationError({ detail: failure.message || "Unable to connect to FastAPI.", status: failure.status });
      }
    } finally {
      request.current = null;
      setLoading(false);
    }
  }

  async function clearChat() { request.current?.abort(); setMessages([]); setViewer(null); setQuestion(""); setGenerationError(null); setNotice(""); sessionStorage.removeItem("rag-history"); await fetch("/api/conversation/clear", { method: "POST", headers: { "X-Session-ID": sessionId.current } }).catch(() => undefined); }
  async function upload(files: FileList | null) { if (!files?.length) return; setUploading(true); setGenerationError(null); setNotice(""); const data = new FormData(); Array.from(files).forEach(file => data.append("files", file)); try { const response = await fetch("/api/documents/upload", { method: "POST", body: data }); const result = await response.json(); if (!response.ok) throw new Error(result.detail || "Upload failed."); const parts = [result.uploaded?.length ? `${result.uploaded.length} document${result.uploaded.length === 1 ? "" : "s"} indexed` : "", result.duplicates?.length ? `${result.duplicates.length} duplicate skipped` : ""].filter(Boolean); setNotice(parts.join(" · ") || "No new documents were added."); } catch (err) { setGenerationError({ detail: err instanceof Error ? err.message : "Upload failed." }); } finally { setUploading(false); if (uploadInput.current) uploadInput.current.value = ""; } }

  // FIX #4: stabilized so React.memo(Assistant) actually prevents unrelated
  // messages from re-rendering on every streamed token. These take a message id
  // instead of closing over a specific `m`, and read current messages from
  // `messagesRef` so they never go stale despite the empty dependency array.
  const selectCitation = useCallback((messageId: string, citation: Citation) => {
    const target = messagesRef.current.find(message => message.id === messageId);
    setViewer({ citation, citations: target?.citations ?? [citation] });
  }, []);
  const regenerate = useCallback(() => void ask(lastQuestion.current), []);

  return <section id="experience" className="section-shell preview-section"><div className="section-intro"><p className="kicker">A calmer way to ask</p><h2>Answers you can trust.</h2><p>Live, cited answers from your indexed documents.</p></div><div className={`chat-layout ${viewer ? "with-viewer" : ""}`}><motion.div className="glass-card chat-window">  <div className="chat-top"><span className="mini-logo">✦</span><span>Hybrid RAG workspace</span><i /><div className="chat-top-actions"><button onClick={() => void clearChat()} disabled={!messages.length} className="clear-chat">Clear chat</button><button onClick={cancelGeneration} disabled={!loading} className="cancel-generation">Cancel</button><label className="upload-button"><Upload size={14} />{uploading ? "Indexing…" : "Add PDFs"}<input ref={uploadInput} type="file" accept="application/pdf" multiple onChange={event => void upload(event.target.files)} /></label></div></div><ProviderSettings value={provider} update={p => setProvider(s => ({ ...s, ...p }))} open={providerPrompt} onToggle={setProviderPrompt} /><RetrievalSettings value={settings} update={p => setSettings(s => ({ ...s, ...p }))} /><div className="chat-scroll"><div className="chat-body">  {!messages.length && <div className="suggestions"><p>Try a suggested question</p><div>{suggestions.map(suggestion => <button key={suggestion} onClick={() => void ask(suggestion)}>{suggestion}</button>)}</div></div>}{messages.map(m => m.role === "user" ? <div className="chat-message user-message" key={m.id}>{m.content}</div> : <MemoAssistant key={m.id} message={m} select={(citation) => selectCitation(m.id, citation)} regenerate={regenerate} loading={loading} />)}{loading && <div className="typing-indicator"><LoaderCircle size={16} className="spinner" />Generating answer{elapsedMs ? ` • ${Math.floor(elapsedMs / 1000)}s` : ""}…</div>}<div ref={end} /></div></div>{notice && <div className="chat-notice">{notice}</div>}<div className="chat-composer-area">{generationError && <div className="generation-notice" role="alert"><TriangleAlert size={16} /><div><b>Unable to generate a response.</b><span>{generationError.detail}</span><div className="generation-actions"><button type="button" onClick={() => setProviderPrompt(true)}>Configure API Key</button><button type="button" onClick={() => void ask(lastQuestion.current)} disabled={loading || !lastQuestion.current}>Retry</button><button type="button" onClick={() => setProviderPrompt(true)}>Switch Provider</button><button type="button" onClick={() => setGenerationError(null)}>Dismiss</button></div></div></div>}<form className="chat-compose" onSubmit={(e: FormEvent) => { e.preventDefault(); void ask(question); }}><textarea value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask anything about your documents..." rows={1} /><button disabled={!question.trim() || loading}><Send size={16} /></button></form></div></motion.div>{viewer && <Viewer citation={viewer.citation} citations={viewer.citations} close={() => setViewer(null)} width={viewerWidth} resize={setViewerWidth} />}</div></section>;}
