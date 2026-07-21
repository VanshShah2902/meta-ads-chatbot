"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  sendChat,
  uploadCSV,
  getStats,
  type ChatMessage,
  type Stats,
} from "@/lib/api";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await sendChat(question, history);

      const botMsg: ChatMessage = {
        role: "assistant",
        content: response.answer,
        sql: response.sql,
        data: response.data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg: ChatMessage = {
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}. Make sure the backend is running on http://localhost:8000`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus("Uploading...");
    try {
      const result = await uploadCSV(file);
      setUploadStatus(
        `Imported ${(result as { rows_imported?: number }).rows_imported ?? 0} rows into ${(result as { table?: string }).table ?? "database"}`
      );
      getStats()
        .then(setStats)
        .catch(() => {});
    } catch (err) {
      setUploadStatus(
        `Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    }
  };

  const SUGGESTIONS = [
    "What was the total spend last month?",
    "Which campaign had the highest ROAS?",
    "Show me daily purchases for all campaigns",
    "What's the average CPA across all campaigns?",
    "Top 5 campaigns by spend",
  ];

  return (
    <div className="flex flex-col h-screen relative">
      {/* Animated background */}
      <div className="app-bg" />

      {/* Floating orbs */}
      <div
        className="floating-orb"
        style={{
          width: 300,
          height: 300,
          top: "10%",
          left: "5%",
          background: "var(--gradient-1)",
        }}
      />
      <div
        className="floating-orb"
        style={{
          width: 200,
          height: 200,
          bottom: "15%",
          right: "10%",
          background: "var(--gradient-2)",
          animationDelay: "3s",
        }}
      />
      <div
        className="floating-orb"
        style={{
          width: 150,
          height: 150,
          top: "50%",
          right: "30%",
          background: "var(--gradient-3)",
          animationDelay: "5s",
        }}
      />

      {/* Header */}
      <header className="glass-strong flex items-center justify-between px-6 py-3 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white text-sm glow-primary send-btn">
            MA
          </div>
          <div>
            <h1 className="font-semibold text-base gradient-text">
              Meta Ads Chatbot
            </h1>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {stats
                ? `${stats.total_rows.toLocaleString()} rows · ${stats.total_campaigns} campaigns · ${stats.total_ads} ads`
                : "Connecting..."}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="suggestion-btn px-3 py-1.5 rounded-lg text-sm font-medium cursor-pointer"
          >
            Upload CSV
          </button>
        </div>
      </header>

      {/* Upload panel */}
      {showUpload && (
        <div
          className="glass px-6 py-3 z-10"
        >
          <div className="flex items-center gap-4">
            <label className="cursor-pointer">
              <span className="send-btn px-3 py-1.5 rounded-lg text-sm font-medium text-white inline-block">
                Choose CSV File
              </span>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
            {uploadStatus && (
              <span className="text-sm" style={{ color: "var(--accent)" }}>
                {uploadStatus}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 z-10">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold mb-3 gradient-text">
                Ask about your Meta Ads data
              </h2>
              <p className="text-base" style={{ color: "var(--muted)" }}>
                Powered by AI — query campaigns, adsets, and ads in plain English
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-3 max-w-2xl">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus();
                  }}
                  className="suggestion-btn px-4 py-2.5 rounded-xl text-sm cursor-pointer"
                >
                  {s}
                </button>
              ))}
            </div>
            {stats && stats.total_rows === 0 && (
              <p
                className="text-sm mt-4 px-4 py-2 rounded-lg glass"
                style={{ color: "var(--accent)" }}
              >
                No data loaded yet. Upload a CSV to get started.
              </p>
            )}
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            {loading && (
              <div className="flex gap-2 items-start">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 send-btn glow-subtle">
                  AI
                </div>
                <div className="bot-bubble px-4 py-3 rounded-2xl rounded-tl-sm">
                  <div className="flex gap-1.5">
                    <span
                      className="w-2 h-2 rounded-full bounce-dot"
                      style={{ background: "var(--accent)" }}
                    />
                    <span
                      className="w-2 h-2 rounded-full bounce-dot"
                      style={{ background: "var(--primary)" }}
                    />
                    <span
                      className="w-2 h-2 rounded-full bounce-dot"
                      style={{ background: "var(--accent-secondary)" }}
                    />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="glass-strong px-6 py-3 z-10">
        <div className="max-w-3xl mx-auto flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your Meta Ads data..."
            rows={1}
            className="input-field flex-1 px-4 py-2.5 rounded-xl resize-none text-sm"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="send-btn px-5 py-2.5 rounded-xl text-white font-medium text-sm cursor-pointer"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [showSql, setShowSql] = useState(false);
  const [showData, setShowData] = useState(false);
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-2 items-start ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 send-btn glow-subtle">
          AI
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? "order-first" : ""}`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser ? "rounded-tr-sm text-white user-bubble" : "rounded-tl-sm bot-bubble"
          }`}
        >
          <div
            dangerouslySetInnerHTML={{
              __html: message.content
                .replace(/\*\*(.*?)\*\*/g, "<strong style='color:var(--accent)'>$1</strong>")
                .replace(/\n/g, "<br/>"),
            }}
          />
        </div>

        {!isUser && (message.sql || message.data) && (
          <div className="flex gap-3 mt-2 ml-1">
            {message.sql && (
              <button
                onClick={() => setShowSql(!showSql)}
                className="text-xs cursor-pointer transition-all hover:opacity-100 opacity-70"
                style={{ color: "var(--accent)" }}
              >
                {showSql ? "Hide SQL" : "Show SQL"}
              </button>
            )}
            {message.data && message.data.length > 0 && (
              <button
                onClick={() => setShowData(!showData)}
                className="text-xs cursor-pointer transition-all hover:opacity-100 opacity-70"
                style={{ color: "var(--accent-secondary)" }}
              >
                {showData ? "Hide Data" : `Show Data (${message.data.length} rows)`}
              </button>
            )}
          </div>
        )}

        {showSql && message.sql && (
          <pre
            className="mt-2 p-3 rounded-xl text-xs overflow-x-auto font-mono glass"
            style={{ color: "var(--sql-text)" }}
          >
            {message.sql}
          </pre>
        )}

        {showData && message.data && message.data.length > 0 && (
          <div className="mt-2 rounded-xl overflow-x-auto glass">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: "var(--table-header)" }}>
                  {Object.keys(message.data[0]).map((key) => (
                    <th
                      key={key}
                      className="px-3 py-2 text-left font-medium whitespace-nowrap"
                      style={{ color: "var(--accent)" }}
                    >
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.data.slice(0, 20).map((row, i) => (
                  <tr
                    key={i}
                    className="border-t"
                    style={{ borderColor: "var(--table-border)" }}
                  >
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-3 py-1.5 whitespace-nowrap">
                        {val === null || val === undefined ? "—" : String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {message.data.length > 20 && (
              <p
                className="px-3 py-2 text-xs text-center"
                style={{ color: "var(--muted)" }}
              >
                Showing 20 of {message.data.length} rows
              </p>
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
          style={{
            background: "rgba(255,255,255,0.1)",
            color: "var(--accent)",
            border: "1px solid rgba(255,255,255,0.15)",
          }}
        >
          You
        </div>
      )}
    </div>
  );
}
