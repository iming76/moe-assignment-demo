import type { Document } from "@moe-research/types";

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
