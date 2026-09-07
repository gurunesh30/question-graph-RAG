import { env } from "./env";

export const API_BASE = env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers as any) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),
  ingestPdf: (file: File, model?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (model) fd.append("model", model);
    return fetch(`${API_BASE}/api/ingest-pdf`, { method: "POST", body: fd });
  },
  graphData: () => request("/api/graph-data"),
  score: () => request("/api/score"),
  generateMcq: (difficulty: string, count: number, mock = false) =>
    request("/api/generate-mcq", {
      method: "POST",
      body: JSON.stringify({ difficulty, count, mock }),
    }),
};