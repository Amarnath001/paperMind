"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, clearToken } from "@/src/lib/api";

interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  role: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadWorkspaces() {
    setError(null);
    try {
      const data = await apiFetch<Workspace[]>("/workspaces");
      setWorkspaces(data);
    } catch (err: any) {
      if (err.message?.toLowerCase().includes("unauthorized")) {
        clearToken();
        router.push("/login");
        return;
      }
      setError(err.message || "Failed to load workspaces");
    }
  }

  useEffect(() => {
    void loadWorkspaces();
  }, []);

  async function handleCreateWorkspace() {
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await apiFetch<Workspace>("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setName("");
      await loadWorkspaces();
    } catch (err: any) {
      setError(err.message || "Failed to create workspace");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-layout">
      <header className="page-header">
        <div>
          <h1>Workspaces</h1>
          <p>Your research spaces in PaperMind.</p>
        </div>
        <nav>
          <a href="/upload">Upload paper</a>
        </nav>
      </header>

      <section className="card">
        <h2>Create a new workspace</h2>
        <div className="workspace-form">
          <input
            type="text"
            placeholder="Workspace name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button onClick={handleCreateWorkspace} disabled={loading}>
            {loading ? "Creating..." : "Create"}
          </button>
        </div>
        {error && <p className="auth-error">{error}</p>}
      </section>

      <section className="card">
        <h2>Your workspaces</h2>
        {workspaces.length === 0 ? (
          <p>No workspaces yet. Create one to get started.</p>
        ) : (
          <ul className="workspace-list">
            {workspaces.map((ws) => (
              <li key={ws.id}>
                <a href={`/workspace/${ws.id}`}>{ws.name}</a>
                <span className="workspace-meta">
                  Role: {ws.role} · Created{" "}
                  {new Date(ws.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

