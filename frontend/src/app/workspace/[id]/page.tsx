"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiFetch, clearToken } from "@/src/lib/api";

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
                    {p.filename} · {p.status} ·{" "}
                    {new Date(p.created_at).toLocaleString()}
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

