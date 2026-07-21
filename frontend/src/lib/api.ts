const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  data?: Record<string, unknown>[] | null;
  timestamp: Date;
}

export interface ChatResponse {
  answer: string;
  sql: string | null;
  data: Record<string, unknown>[] | null;
}

export interface Stats {
  total_campaigns: number;
  total_adsets: number;
  total_ads: number;
  total_rows: number;
  files_imported: number;
  date_range_start: string | null;
  date_range_end: string | null;
}

export interface ImportRecord {
  filename: string;
  rows_imported: number;
  table_name: string;
  imported_at: string;
}

export async function sendChat(
  question: string,
  history: { role: string; content: string }[]
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
  return res.json();
}

export async function uploadCSV(file: File): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`Stats failed: ${res.statusText}`);
  return res.json();
}

export async function getImports(): Promise<ImportRecord[]> {
  const res = await fetch(`${API_BASE}/imports`);
  if (!res.ok) throw new Error(`Imports failed: ${res.statusText}`);
  return res.json();
}

export async function syncDrive(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/sync`, { method: "POST" });
  if (!res.ok) throw new Error(`Sync failed: ${res.statusText}`);
  return res.json();
}
