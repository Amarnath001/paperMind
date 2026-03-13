"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import {
  apiFetch,
  clearToken,
  fetchJobs,
  Job,
  searchChunks,
  SearchResult,
} from "@/src/lib/api";

interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

interface Paper {
  id: string;
  title: string;
  filename: string;
  status: string;
  created_at: string;
}

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const workspaceId = params.id;
  const router = useRouter();

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [jobsByPaper, setJobsByPaper] = useState<Record<string, Job[]>>({});
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);

  async function load() {
    setError(null);
    try {
      const [ws, ps] = await Promise.all([
        apiFetch<Workspace>(`/workspaces/${workspaceId}`),
        apiFetch<Paper[]>(`/papers?workspace_id=${workspaceId}`),
      ]);
      setWorkspace(ws);
      setPapers(ps);

      // Load jobs for any papers that are still processing
      const processingPaperIds = ps
        .filter((p) => p.status === "processing")
        .map((p) => p.id);

      if (processingPaperIds.length > 0) {
        const allJobs: Record<string, Job[]> = {};
        await Promise.all(
          processingPaperIds.map(async (paperId) => {
            try {
              const jobs = await fetchJobs({ paperId, workspaceId });
              allJobs[paperId] = jobs;
            } catch {
              // Ignore job fetch errors on this pass
            }
          }),
        );
        setJobsByPaper(allJobs);
      } else {
        setJobsByPaper({});
      }
    } catch (err: any) {
      if (err.message?.toLowerCase().includes("unauthorized")) {
        clearToken();
        router.push("/login");
        return;
      }
      setError(err.message || "Failed to load workspace");
    }
  }

  useEffect(() => {
    if (workspaceId) {
      void load();
    }
  }, [workspaceId]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const res = await searchChunks({
        workspace_id: workspaceId,
        query: searchQuery,
      });
      setSearchResults(res.results);
    } catch (err: any) {
      setError(err.message || "Failed to search");
    } finally {
      setIsSearching(false);
    }
  }

  async function handleDeletePaper(paperId: string) {
    const ok = globalThis.window?.confirm(
      "Delete this paper? This will remove its chunks, jobs, and insights.",
    );
    if (!ok) return;
    setError(null);
    try {
      await apiFetch(`/papers/${paperId}`, { method: "DELETE" });
      await load();
    } catch (err: any) {
      setError(err.message || "Failed to delete paper");
    }
  }

  return (
    <div className="page-layout">
      <header className="page-header">
        <div>
          <h1>{workspace?.name ?? "Workspace"}</h1>
          <p>Library of uploaded papers.</p>
        </div>
        <nav>
          <a href="/dashboard">Back to dashboard</a>
          <a href={`/workspace/${workspaceId}/insights`}>Insights</a>
          <a href={`/workspace/${workspaceId}/chat`}>Chat</a>
          <a href={`/upload?workspace_id=${workspaceId}`}>Upload paper</a>
        </nav>
      </header>

      {error && <p className="auth-error">{error}</p>}

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2>{searchResults ? "Search Results" : "Papers"}</h2>
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem" }}>
            <input
              type="text"
              placeholder="Ask a question..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={isSearching}
            />
            <button type="submit" disabled={isSearching || !searchQuery.trim()}>
              {isSearching ? "Searching..." : "Search"}
            </button>
            {searchResults && (
              <button
                type="button"
                onClick={() => { setSearchResults(null); setSearchQuery(""); }}
                style={{ background: "#4B5563" }}
              >
                Clear
              </button>
            )}
          </form>
        </div>

        {searchResults ? (
          searchResults.length === 0 ? (
            <p>No relevant excerpts found.</p>
          ) : (
            <ul className="paper-list">
              {searchResults.map((res) => (
                <li key={res.chunk_id}>
                  <div>
                    <strong>{res.paper_title}</strong>
                    <div className="paper-meta" style={{ marginBottom: "0.5rem" }}>
                      Chunk {res.chunk_index} · Similarity: {(res.similarity * 100).toFixed(1)}%
                    </div>
                    <p style={{ margin: 0, fontSize: "0.9rem", color: "#4B5563" }}>
                      {res.text.length > 300 ? res.text.slice(0, 300) + "..." : res.text}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )
        ) : papers.length === 0 ? (
          <p>No papers uploaded yet.</p>
        ) : (
          <ul className="paper-list">
            {papers.map((p) => (
              <li
                key={p.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "0.75rem",
                }}
              >
                <div>
                  <strong>{p.title}</strong>
                  <div className="paper-meta">
                    {p.filename} ·{" "}
                    <span className={`status-badge status-${p.status}`}>
                      {p.status}
                      {p.status === "processing" &&
                        (() => {
                          const jobs = jobsByPaper[p.id] || [];
                          const job = jobs[0];
                          if (!job) return null;
                          return ` · ${job.progress}%`;
                        })()}
                    </span>{" "}
                    · {new Date(p.created_at).toLocaleString()}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeletePaper(p.id)}
                  style={{
                    borderRadius: "999px",
                    border: "1px solid #F97373",
                    padding: "0.25rem 0.75rem",
                    fontSize: "0.8rem",
                    color: "#B91C1C",
                    background: "#FEF2F2",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

