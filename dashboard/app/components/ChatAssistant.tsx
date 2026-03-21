"use client";

import { useState, useEffect, useRef, useCallback, type KeyboardEvent } from "react";

/* ════════════════════════════════════════════════════════════════
   CHAT ASSISTANT — FinClaw AI
   Production-grade chat panel with SSE streaming
   ════════════════════════════════════════════════════════════════ */

// ── Types ──────────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  error?: boolean;
}

type PanelState = "collapsed" | "expanded";
type ConfigState = "loading" | "configured" | "not_configured";

const MAX_MESSAGES = 50;

// ── Simple Markdown Renderer ───────────────────────────────────

function renderMarkdown(text: string): string {
  // Escape HTML first
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks (```lang\ncode\n```)
  html = html.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_match, lang, code) =>
      `<pre class="chat-code-block"><code class="language-${lang || "text"}">${code.trim()}</code></pre>`
  );

  // Inline code
  html = html.replace(
    /`([^`]+)`/g,
    '<code class="chat-inline-code">$1</code>'
  );

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");

  // Headers (## → h3, ### → h4, limit to h3-h5 for chat context)
  html = html.replace(/^#{4,}\s+(.+)$/gm, '<h5 class="chat-h5">$1</h5>');
  html = html.replace(/^###\s+(.+)$/gm, '<h4 class="chat-h4">$1</h4>');
  html = html.replace(/^##\s+(.+)$/gm, '<h3 class="chat-h3">$1</h3>');

  // Unordered lists (- item or * item)
  html = html.replace(
    /((?:^[\t ]*[-*]\s+.+$\n?)+)/gm,
    (match) => {
      const items = match
        .trim()
        .split('\n')
        .map((line) => line.replace(/^[\t ]*[-*]\s+/, ''))
        .map((item) => `<li>${item}</li>`)
        .join('');
      return `<ul class="chat-list">${items}</ul>`;
    }
  );

  // Ordered lists (1. item, 2. item)
  html = html.replace(
    /((?:^\d+\.\s+.+$\n?)+)/gm,
    (match) => {
      const items = match
        .trim()
        .split('\n')
        .map((line) => line.replace(/^\d+\.\s+/, ''))
        .map((item) => `<li>${item}</li>`)
        .join('');
      return `<ol class="chat-list">${items}</ol>`;
    }
  );

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr class="chat-hr"/>');

  // Links
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="chat-link">$1</a>'
  );

  // Line breaks → paragraphs (double newline = paragraph break)
  html = html
    .split(/\n{2,}/)
    .map((p) => `<p>${p.replace(/\n/g, "<br/>")}</p>`)
    .join("");

  return html;
}

// ── Unique ID Generator ────────────────────────────────────────

let _idCounter = 0;
function uid(): string {
  return `msg_${Date.now()}_${++_idCounter}`;
}

// ── Setup Instructions Panel ───────────────────────────────────

function SetupInstructions() {
  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-sm text-sm text-gray-400 space-y-4">
        <p className="text-gray-300 font-medium">
          AI-powered analysis requires an LLM API key.
        </p>

        <div className="space-y-3">
          <p className="text-gray-500 text-xs uppercase tracking-wider font-medium">
            Setup
          </p>
          <ol className="space-y-2 text-gray-400 list-decimal list-inside">
            <li>
              Create{" "}
              <code className="chat-inline-code">.env.local</code> in the
              dashboard directory
            </li>
            <li>
              Add your API key:
              <pre className="chat-code-block mt-1">
                <code>FINCLAW_LLM_API_KEY=sk-xxx</code>
              </pre>
            </li>
            <li>Restart the dashboard</li>
          </ol>
        </div>

        <div className="space-y-2 pt-2 border-t border-gray-800/50">
          <p className="text-gray-500 text-xs uppercase tracking-wider font-medium">
            Supported Providers
          </p>
          <ul className="space-y-1 text-gray-500 text-xs">
            <li>OpenAI (gpt-4.1, gpt-4.1-mini)</li>
            <li>Anthropic (claude-sonnet-4)</li>
            <li>DeepSeek (deepseek-chat, deepseek-reasoner)</li>
            <li>Google Gemini (gemini-2.5-pro)</li>
            <li>Groq, Ollama, any OpenAI-compatible API</li>
          </ul>
        </div>

        <p className="text-gray-600 text-xs">
          Configure provider in{" "}
          <code className="chat-inline-code">finclaw.config.ts</code>
        </p>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────

export default function ChatAssistant() {
  const [panel, setPanel] = useState<PanelState>("collapsed");
  const [configured, setConfigured] = useState<ConfigState>("loading");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ── Check LLM status on mount ──
  useEffect(() => {
    let cancelled = false;
    fetch("/api/chat/status")
      .then((r) => r.json())
      .then((data: { configured: boolean }) => {
        if (!cancelled) {
          setConfigured(data.configured ? "configured" : "not_configured");
        }
      })
      .catch(() => {
        if (!cancelled) setConfigured("not_configured");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Auto-scroll on new messages ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Auto-resize textarea ──
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
    }
  }, [input]);

  // ── Focus input when panel expands ──
  useEffect(() => {
    if (panel === "expanded" && configured === "configured") {
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  }, [panel, configured]);

  // ── Cleanup abort controller ──
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ── Send message ──
  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };

    setMessages((prev) => {
      const next = [...prev, userMsg];
      // Trim to MAX_MESSAGES
      return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next;
    });
    setInput("");
    setIsStreaming(true);

    // Build messages for API (only role + content)
    const apiMessages = [...messages, userMsg].slice(-20).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const assistantId = uid();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", timestamp: Date.now() },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: apiMessages }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let errorMessage = "Something went wrong. Please try again.";
        try {
          const errData = await res.json();
          if (errData.error === "invalid_api_key") {
            errorMessage = "Invalid API key. Check FINCLAW_LLM_API_KEY in .env.local.";
          } else if (errData.error === "rate_limited") {
            errorMessage = "Rate limit exceeded. Please wait a moment.";
          } else if (errData.error === "llm_not_configured") {
            errorMessage = "LLM not configured. Add FINCLAW_LLM_API_KEY to .env.local.";
            setConfigured("not_configured");
          } else if (errData.message) {
            errorMessage = errData.message;
          }
        } catch {
          // response wasn't JSON
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: errorMessage, error: true }
              : m
          )
        );
        setIsStreaming(false);
        return;
      }

      // Parse SSE stream
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;

          const data = trimmed.slice(6);
          if (data === "[DONE]") break;

          try {
            const parsed = JSON.parse(data);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + delta }
                    : m
                )
              );
            }
          } catch {
            // skip malformed SSE chunks
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // User cancelled — leave partial response as-is
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: "Network error. Check your connection and try again.",
                  error: true,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [input, isStreaming, messages]);

  // ── Retry last failed message ──
  const retryLast = useCallback(() => {
    setMessages((prev) => {
      // Find last error message and remove it
      const lastErrIdx = [...prev].reverse().findIndex((m) => m.error);
      if (lastErrIdx === -1) return prev;
      const idx = prev.length - 1 - lastErrIdx;
      return prev.slice(0, idx);
    });
    // Re-send: find the last user message
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (lastUser) {
      setInput(lastUser.content);
    }
  }, [messages]);

  // ── Handle keyboard ──
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Render ──
  if (panel === "collapsed") {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-50 chat-collapsed-bar">
        <div className="max-w-7xl mx-auto px-4">
          <button
            onClick={() => setPanel("expanded")}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            {/* Chat icon */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="shrink-0 text-gray-500"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>Ask about markets...</span>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="ml-auto text-gray-600"
            >
              <polyline points="18 15 12 9 6 15" />
            </svg>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 right-0 z-50 chat-panel-enter" style={{ width: 420 }}>
      <div className="chat-panel flex flex-col h-[min(600px,80vh)] m-3 rounded-lg border border-gray-800/60 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800/50 bg-[#0d0d14]">
          <div className="flex items-center gap-2">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-teal-400"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span className="text-sm font-medium text-gray-200">
              FinClaw AI
            </span>
          </div>
          <button
            onClick={() => {
              abortRef.current?.abort();
              setPanel("collapsed");
            }}
            className="text-gray-500 hover:text-gray-300 transition-colors p-1"
            aria-label="Close chat"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body */}
        {configured === "loading" ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="chat-loading-dot" />
          </div>
        ) : configured === "not_configured" ? (
          <SetupInstructions />
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 chat-messages-scroll">
              {messages.length === 0 && (
                <div className="text-center text-gray-600 text-xs mt-8 space-y-2">
                  <p className="text-gray-500">FinClaw AI</p>
                  <p>Ask about any stock, market trend, or investment topic.</p>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`chat-message-enter ${
                    msg.role === "user" ? "flex justify-end" : "flex justify-start"
                  }`}
                >
                  {msg.role === "user" ? (
                    <div className="max-w-[85%] px-3 py-2 rounded-lg bg-slate-700/80 text-sm text-gray-100 whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="max-w-[90%] text-sm text-gray-300">
                      {msg.error ? (
                        <div className="flex items-start gap-2">
                          <span className="text-red-400/80">{msg.content}</span>
                          <button
                            onClick={retryLast}
                            className="shrink-0 text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded px-2 py-0.5 mt-0.5 transition-colors"
                          >
                            Retry
                          </button>
                        </div>
                      ) : msg.content ? (
                        <div
                          className="chat-markdown"
                          dangerouslySetInnerHTML={{
                            __html: renderMarkdown(msg.content),
                          }}
                        />
                      ) : (
                        <span className="chat-thinking">Thinking</span>
                      )}
                    </div>
                  )}
                </div>
              ))}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-800/50 p-3 bg-[#0d0d14]">
              <div className="flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything about markets..."
                  disabled={isStreaming}
                  rows={1}
                  className="flex-1 resize-none bg-gray-900/80 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 focus:ring-1 focus:ring-slate-500/30 transition-all disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={isStreaming || !input.trim()}
                  className="shrink-0 p-2 rounded-lg bg-teal-600/80 text-white hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  aria-label="Send message"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
