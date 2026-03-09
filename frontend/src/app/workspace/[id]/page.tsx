"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiFetch, clearToken, fetchJobs, Job } from "@/src/lib/api";

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

  return (
    <main className="page-layout">
      <header className="page-header">
        <div>
          <h1>{workspace?.name ?? "Workspace"}</h1>
          <p>Library of uploaded papers.</p>
        </div>
        <nav>
          <a href="/dashboard">Back to dashboard</a>
          <a href={`/upload?workspace_id=${workspaceId}`}>Upload paper</a>
        </nav>
      </header>

      {error && <p className="auth-error">{error}</p>}

      <section className="card">
        <h2>Papers</h2>
        {papers.length === 0 ? (
          <p>No papers uploaded yet.</p>
        ) : (
          <ul className="paper-list">
            {papers.map((p) => (
              <li key={p.id}>
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
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

