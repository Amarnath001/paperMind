"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, clearToken } from "@/src/lib/api";
import { ContentContainer, PageHeader } from "@/src/components/layout/Page";
import { Button } from "@/src/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/src/components/ui/Card";
import { EmptyState } from "@/src/components/ui/EmptyState";
import { Input } from "@/src/components/ui/Input";

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
    <ContentContainer>
      <PageHeader
        title="Dashboard"
        subtitle="Your workspaces and research libraries."
        actions={
          <Button variant="secondary" onClick={() => router.push("/upload")}>
            Upload paper
          </Button>
        }
      />

      <div className="ui-grid-2">
        <Card>
          <CardHeader
            title="Create workspace"
            subtitle="Keep papers, chat, and insights organized by project."
          />
          <CardBody>
            <div className="ui-stack">
              <Input
                label="Workspace name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. LLM research"
              />
              {error ? <div className="ui-error">{error}</div> : null}
              <Button onClick={handleCreateWorkspace} disabled={loading}>
                {loading ? "Creating…" : "Create workspace"}
              </Button>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Your workspaces" subtitle="Jump back in where you left off." />
          <CardBody>
            {workspaces.length === 0 ? (
              <EmptyState
                title="No workspaces yet"
                description="Create a workspace to upload papers and start chatting with citations."
              />
            ) : (
              <ul className="ui-list">
                {workspaces.map((ws) => (
                  <li key={ws.id} className="ui-list-row">
                    <button
                      type="button"
                      className="ui-linklike"
                      onClick={() => router.push(`/workspace/${ws.id}`)}
                    >
                      {ws.name}
                    </button>
                    <div className="ui-muted">
                      Role: {ws.role} · Created {new Date(ws.created_at).toLocaleString()}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </ContentContainer>
  );
}

