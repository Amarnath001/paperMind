"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { getWorkspaceInsights, WorkspaceInsights } from "@/src/lib/api";
import { ContentContainer, PageHeader } from "@/src/components/layout/Page";
import { Badge } from "@/src/components/ui/Badge";
import { Button } from "@/src/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/src/components/ui/Card";
import { EmptyState } from "@/src/components/ui/EmptyState";

export default function WorkspaceInsightsPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = params.id;
  const router = useRouter();

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

  const overviewCards = insights
    ? [
        { label: "Total papers", value: insights.total_papers },
        { label: "Topics", value: insights.topics.length },
        { label: "Clusters", value: insights.clusters.length },
      ]
    : [];

  return (
    <ContentContainer>
      <PageHeader
        title="Insights"
        subtitle="Overview metrics, topics, clusters, and recent papers."
        actions={
          <Button
            variant="secondary"
            onClick={() => router.push(`/workspace/${workspaceId}`)}
          >
            Back
          </Button>
        }
      />

      {error ? <div className="ui-error" style={{ marginBottom: "0.75rem" }}>{error}</div> : null}

      {loading || !insights ? (
        <div className="ui-muted">Loading insights…</div>
      ) : (
        <>
          <div className="pm-insights-overview">
            {overviewCards.map((c) => (
              <Card key={c.label}>
                <CardBody>
                  <div className="pm-metric">
                    <div className="pm-metric__label">{c.label}</div>
                    <div className="pm-metric__value">{c.value}</div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>

          <div className="pm-insights-grid">
            <Card>
              <CardHeader title="Top topics" subtitle="Most frequent topics across papers." />
              <CardBody>
                {insights.topics.length === 0 ? (
                  <EmptyState
                    title="No topics yet"
                    description="Upload and process papers to extract topics."
                  />
                ) : (
                  <div className="pm-chip-row">
                    {insights.topics.slice(0, 16).map((t) => (
                      <Badge key={t.topic} tone="neutral">
                        {t.topic} · {t.count}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Recent papers" subtitle="Latest additions with summaries." />
              <CardBody>
                {insights.recent_papers.length === 0 ? (
                  <EmptyState title="No papers yet" description="Upload a PDF to get started." />
                ) : (
                  <ul className="ui-list">
                    {insights.recent_papers.map((p) => (
                      <li key={p.id} className="ui-list-row">
                        <div style={{ fontWeight: 650 }}>{p.title}</div>
                        <div className="ui-muted">
                          {p.cluster_id !== null && p.cluster_id !== undefined
                            ? `Cluster ${p.cluster_id} · `
                            : ""}
                          {new Date(p.created_at).toLocaleString()}
                        </div>
                        {p.summary ? (
                          <div className="ui-muted" style={{ marginTop: "0.35rem" }}>
                            {p.summary.length > 260 ? p.summary.slice(0, 260) + "…" : p.summary}
                          </div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </CardBody>
            </Card>
          </div>

          <Card style={{ marginTop: "1rem" } as any}>
            <CardHeader title="Clusters" subtitle="Grouped papers by semantic similarity." />
            <CardBody>
              {insights.clusters.length === 0 ? (
                <EmptyState
                  title="No clusters available"
                  description="Clusters appear when clustering is enabled and enough papers exist."
                />
              ) : (
                <div className="pm-cluster-grid">
                  {insights.clusters.map((cluster) => (
                    <Card key={cluster.cluster_id} className="pm-cluster-card">
                      <CardHeader
                        title={`Cluster ${cluster.cluster_id}`}
                        subtitle={`${cluster.papers.length} papers`}
                      />
                      <CardBody>
                        <ul className="ui-list">
                          {cluster.papers.map((p) => (
                            <li key={p.id} className="ui-list-row">
                              <div style={{ fontWeight: 650 }}>{p.title}</div>
                              {p.summary ? (
                                <div className="ui-muted" style={{ marginTop: "0.25rem" }}>
                                  {p.summary.length > 200 ? p.summary.slice(0, 200) + "…" : p.summary}
                                </div>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </ContentContainer>
  );
}

