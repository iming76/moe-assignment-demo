import type { Document } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function uploadDocument(file: File): Promise<{
  documentId: string;
  state: string;
}> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface ProgressEvent {
  state: string;
  detail?: string;
  /** Present only on OCR_PROCESSING sub-progress updates. */
  completed?: number;
  total?: number;
}

/**
 * Subscribes to the backend's SSE pipeline-progress stream. Calls `onEvent`
 * for every stage transition (including a terminal "ERROR" state on
 * failure, surfaced via `detail`) and for OCR_PROCESSING sub-progress
 * updates (`completed`/`total` crops transcribed). Returns an unsubscribe
 * function.
 */
export function subscribeProgress(
  id: string,
  onEvent: (event: ProgressEvent) => void
): () => void {
  const source = new EventSource(`${API_BASE}/documents/${id}/progress`);
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data) as ProgressEvent;
    onEvent(payload);
    if (payload.state === "REVIEW_REQUIRED" || payload.state === "ERROR") {
      source.close();
    }
  };
  return () => source.close();
}

export async function fetchDocument(id: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/documents/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function artifactUrl(id: string, path: string): string {
  return `${API_BASE}/documents/${id}/artifacts/${path}`;
}

export async function submitCorrection(
  id: string,
  cropId: string,
  correctedText: string,
  reason?: string
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/documents/${id}/corrections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cropId, correctedText, reason }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function approveDocument(
  id: string
): Promise<{ state: string; output: string }> {
  const res = await fetch(`${API_BASE}/documents/${id}/approve`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
