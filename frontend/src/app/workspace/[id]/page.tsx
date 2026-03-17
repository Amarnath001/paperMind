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
import { ContentContainer, PageHeader } from "@/src/components/layout/Page";
import { Badge } from "@/src/components/ui/Badge";
import { Button } from "@/src/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/src/components/ui/Card";
import { EmptyState } from "@/src/components/ui/EmptyState";
import { Input } from "@/src/components/ui/Input";

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

function statusTone(status: string) {
  switch (status) {
    case "ready":
      return "success";
    case "processing":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
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
    <ContentContainer>
      <PageHeader
        title={workspace?.name ?? "Workspace"}
        subtitle="Your library of papers, chat, and insights."
        actions={
          <>
            <Button variant="secondary" onClick={() => router.push("/dashboard")}>
              Back
            </Button>
            <Button
              variant="secondary"
              onClick={() => router.push(`/workspace/${workspaceId}/chat`)}
            >
              Open chat
            </Button>
            <Button
              variant="secondary"
              onClick={() => router.push(`/workspace/${workspaceId}/insights`)}
            >
              Insights
            </Button>
            <Button onClick={() => router.push(`/upload?workspace_id=${workspaceId}`)}>
              Upload
            </Button>
          </>
        }
      />

      {error ? <div className="ui-error" style={{ marginBottom: "0.75rem" }}>{error}</div> : null}

      <Card>
        <CardHeader
          title={searchResults ? "Search results" : "Papers"}
          subtitle={
            searchResults
              ? "Relevant excerpts from your library."
              : "All papers in this workspace."
          }
          right={
            <form onSubmit={handleSearch} className="ui-inline-form">
              <div className="ui-inline-form__field">
                <Input
                  aria-label="Search"
                  placeholder="Ask a question…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  disabled={isSearching}
                />
              </div>
              <Button
                size="sm"
                type="submit"
                disabled={isSearching || !searchQuery.trim()}
              >
                {isSearching ? "Searching…" : "Search"}
              </Button>
              {searchResults ? (
                <Button
                  size="sm"
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setSearchResults(null);
                    setSearchQuery("");
                  }}
                >
                  Clear
                </Button>
              ) : null}
            </form>
          }
        />
        <CardBody>
          {(() => {
            if (searchResults) {
              if (searchResults.length === 0) {
                return (
                  <EmptyState
                    title="No matches"
                    description="Try a broader question or upload more papers."
                  />
                );
              }
              return (
                <ul className="ui-list">
                  {searchResults.map((res) => (
                    <li key={res.chunk_id} className="ui-list-row">
                      <div style={{ fontWeight: 650 }}>{res.paper_title}</div>
                      <div className="ui-muted">
                        Chunk {res.chunk_index} · Similarity{" "}
                        {(res.similarity * 100).toFixed(1)}%
                      </div>
                      <div className="ui-muted" style={{ marginTop: "0.35rem" }}>
                        {res.text.length > 320
                          ? res.text.slice(0, 320) + "…"
                          : res.text}
                      </div>
                    </li>
                  ))}
                </ul>
              );
            }

            if (papers.length === 0) {
              return (
                <EmptyState
                  title="No papers yet"
                  description="Upload a PDF to start chat, search, and insights."
                  action={
                    <Button
                      onClick={() =>
                        router.push(`/upload?workspace_id=${workspaceId}`)
                      }
                    >
                      Upload first paper
                    </Button>
                  }
                />
              );
            }

            return (
              <ul className="ui-list">
                {papers.map((p) => {
                  const jobs = jobsByPaper[p.id] || [];
                  const job = jobs[0];
                  const progress =
                    p.status === "processing" && job ? ` · ${job.progress}%` : "";

                  return (
                    <li key={p.id} className="ui-list-row ui-row-split">
                      <div>
                        <div style={{ fontWeight: 650 }}>{p.title}</div>
                        <div className="ui-muted">
                          {p.filename} ·{" "}
                          {new Date(p.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="ui-row-split__right">
                        <Badge tone={statusTone(p.status)}>
                          {p.status}
                          {progress}
                        </Badge>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDeletePaper(p.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            );
          })()}
        </CardBody>
      </Card>
    </ContentContainer>
  );
}

