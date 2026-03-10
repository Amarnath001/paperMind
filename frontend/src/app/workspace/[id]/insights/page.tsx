"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { getWorkspaceInsights, WorkspaceInsights } from "@/src/lib/api";

export default function WorkspaceInsightsPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = params.id;

  const [insights, setInsights] = useState<WorkspaceInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getWorkspaceInsights(workspaceId);
        setInsights(data);
      } catch (err: any) {
        setError(err.message || "Failed to load insights");
      } finally {
        setLoading(false);
      }
    }

    if (workspaceId) {
      void load();
    }
  }, [workspaceId]);

  return (
    <main className="page-layout">
      <header className="page-header">
        <div>
          <h1>Workspace insights</h1>
          <p>High-level view of papers, topics, and clusters.</p>
        </div>
        <nav>
          <a href={`/workspace/${workspaceId}`}>Back to workspace</a>
        </nav>
      </header>

      {error && <p className="auth-error">{error}</p>}

      {loading || !insights ? (
        <p>Loading insights...</p>
      ) : (
        <>
          <section className="card">
            <h2>Overview</h2>
            <p>Total papers: <strong>{insights.total_papers}</strong></p>
            {insights.topics.length > 0 && (
              <>
                <h3 style={{ marginTop: "1rem" }}>Top topics</h3>
                <ul className="paper-list">
                  {insights.topics.slice(0, 10).map((t) => (
                    <li key={t.topic}>
                      <div>
                        <strong>{t.topic}</strong>
                        <span className="paper-meta"> · {t.count} papers</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>

          <section className="card">
            <h2>Clusters</h2>
            {insights.clusters.length === 0 ? (
              <p>No clusters available yet. Try uploading and ingesting more papers.</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
                {insights.clusters.map((cluster) => (
                  <div
                    key={cluster.cluster_id}
                    style={{
                      flex: "1 1 260px",
                      borderRadius: "0.75rem",
                      border: "1px solid #E5E7EB",
                      padding: "0.75rem",
                    }}
                  >
                    <h3 style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>
                      Cluster {cluster.cluster_id}
                    </h3>
                    <ul className="paper-list">
                      {cluster.papers.map((p) => (
                        <li key={p.id}>
                          <div>
                            <strong>{p.title}</strong>
                            {p.summary && (
                              <p
                                style={{
                                  margin: "0.25rem 0 0",
                                  fontSize: "0.85rem",
                                  color: "#4B5563",
                                }}
                              >
                                {p.summary.length > 200
                                  ? p.summary.slice(0, 200) + "..."
                                  : p.summary}
                              </p>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card">
            <h2>Recent papers</h2>
            {insights.recent_papers.length === 0 ? (
              <p>No papers yet.</p>
            ) : (
              <ul className="paper-list">
                {insights.recent_papers.map((p) => (
                  <li key={p.id}>
                    <div>
                      <strong>{p.title}</strong>
                      <div className="paper-meta">
                        {p.cluster_id !== null && p.cluster_id !== undefined
                          ? `Cluster ${p.cluster_id} · `
                          : ""}
                        {new Date(p.created_at).toLocaleString()}
                      </div>
                      {p.summary && (
                        <p
                          style={{
                            margin: "0.25rem 0 0",
                            fontSize: "0.9rem",
                            color: "#4B5563",
                          }}
                        >
                          {p.summary.length > 260
                            ? p.summary.slice(0, 260) + "..."
                            : p.summary}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}

