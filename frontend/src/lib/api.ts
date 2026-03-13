"use client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5001";

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

// Chat / RAG API helpers

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  citations?: any;
  created_at: string;
}

export interface Citation {
  chunk_id: string;
  paper_id: string;
  paper_title: string;
  chunk_index: number;
  label: string;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  retrieved_chunks: SearchResult[];
  conversation_id: string;
  messages: ChatMessage[];
}

export function createConversation(
  workspaceId: string,
  title?: string,
): Promise<Conversation> {
  return apiFetch<Conversation>("/chat/conversations", {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId, title }),
  });
}

export function listConversations(
  workspaceId: string,
): Promise<Conversation[]> {
  return apiFetch<Conversation[]>(`/chat/conversations?workspace_id=${workspaceId}`);
}

export function listMessages(
  conversationId: string,
): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(
    `/chat/conversations/${conversationId}/messages`,
  );
}

export function askQuestion(params: {
  workspaceId: string;
  conversationId?: string;
  question: string;
  limit?: number;
  paperId?: string;
}): Promise<AskResponse> {
  const body: any = {
    workspace_id: params.workspaceId,
    question: params.question,
    limit: params.limit,
  };
  if (params.conversationId) body.conversation_id = params.conversationId;
  if (params.paperId) body.paper_id = params.paperId;

  return apiFetch<AskResponse>("/chat/ask", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Insights API helpers

export interface InsightTopic {
  topic: string;
  count: number;
}

export interface InsightPaper {
  id: string;
  title: string;
  summary: string | null;
  topics: string[] | null;
  cluster_id: number | null;
  created_at: string;
}

export interface ClusterGroup {
  cluster_id: number;
  papers: InsightPaper[];
}

export interface WorkspaceInsights {
  total_papers: number;
  clusters: ClusterGroup[];
  topics: InsightTopic[];
  recent_papers: InsightPaper[];
}

export function getWorkspaceInsights(
  workspaceId: string,
): Promise<WorkspaceInsights> {
  return apiFetch<WorkspaceInsights>(`/insights/workspace/${workspaceId}`);
}



