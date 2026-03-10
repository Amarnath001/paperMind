"use client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5000";

const TOKEN_KEY = "papermind_token";

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (!token) {
    window.localStorage.removeItem(TOKEN_KEY);
  } else {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  setToken(null);
}

export function getAuthHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    ...getAuthHeader(),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message =
      (data && (data.error || data.message)) ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data as T;
}

export { API_BASE_URL };

// Jobs API helpers

export interface Job {
  id: string;
  workspace_id: string;
  paper_id: string | null;
  type: string;
  status: string;
  progress: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export function fetchJobs(params: {
  workspaceId?: string;
  paperId?: string;
}): Promise<Job[]> {
  const search = new URLSearchParams();
  if (params.workspaceId) search.set("workspace_id", params.workspaceId);
  if (params.paperId) search.set("paper_id", params.paperId);
  const qs = search.toString();
  const path = qs ? `/jobs?${qs}` : "/jobs";
  return apiFetch<Job[]>(path);
}

// Search API helpers

export interface SearchResult {
  chunk_id: string;
  paper_id: string;
  paper_title: string;
  chunk_index: number;
  text: string;
  similarity: number;
}

export interface SearchRequest {
  workspace_id: string;
  query: string;
  limit?: number;
}

export function searchChunks(
  req: SearchRequest,
): Promise<{ results: SearchResult[] }> {
  return apiFetch<{ results: SearchResult[] }>("/search", {
    method: "POST",
    body: JSON.stringify(req),
  });
}


