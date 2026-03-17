"use client";

import { FormEvent, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { API_BASE_URL, getAuthHeader } from "@/src/lib/api";
import { ContentContainer, PageHeader } from "@/src/components/layout/Page";
import { Button } from "@/src/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/src/components/ui/Card";
import { Input } from "@/src/components/ui/Input";
import { Badge } from "@/src/components/ui/Badge";

function UploadForm() {
  const searchParams = useSearchParams();
  const defaultWorkspaceId = searchParams.get("workspace_id") ?? "";
  const router = useRouter();

  const [workspaceId, setWorkspaceId] = useState(defaultWorkspaceId);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!workspaceId) {
      setError("Workspace ID is required");
      return;
    }
    if (!file) {
      setError("Please select a PDF file to upload");
      return;
    }

    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("title", title);
    formData.append("file", file);

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/papers/upload`, {
        method: "POST",
        headers: {
          ...getAuthHeader(),
        },
        body: formData,
      });

      const text = await response.text();
      const data = text ? JSON.parse(text) : null;

      if (!response.ok) {
        throw new Error(
          (data && (data.error || data.message)) ||
          `Upload failed with status ${response.status}`,
        );
      }

      setSuccess("Upload successful. Ingestion has been queued.");
      setTitle("");
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      router.push(`/workspace/${workspaceId}`);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ContentContainer>
      <PageHeader
        title="Upload"
        subtitle="Upload a PDF into a workspace to enable chat, search, and insights."
        actions={
          <Button variant="secondary" onClick={() => router.push("/dashboard")}>
            Back
          </Button>
        }
      />

      <Card>
        <CardHeader
          title="Upload a paper"
          subtitle={
            <>
              PDFs are stored securely and processed to create embeddings for
              semantic search.
            </>
          }
          right={
            workspaceId ? (
              <Badge tone="info">Workspace: {workspaceId}</Badge>
            ) : (
              <Badge tone="neutral">Select a workspace</Badge>
            )
          }
        />
        <CardBody>
          <form onSubmit={handleSubmit} className="ui-stack">
            <Input
              label="Workspace ID"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              placeholder="Paste workspace id"
              required
            />

            <Input
              label="Title (optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Paper title"
            />

            <div className="ui-field">
              <label className="ui-label" htmlFor="paper-file">
                PDF file
              </label>
              <input
                id="paper-file"
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                onChange={(e) => {
                  const selected = e.target.files?.[0] ?? null;
                  setFile(selected);
                }}
                required
              />
              <div className="ui-hint">
                Max 20MB. Only PDF files are supported.
              </div>
            </div>

            {error ? <div className="ui-error">{error}</div> : null}
            {success ? <div className="ui-hint">{success}</div> : null}

            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <Button type="submit" disabled={loading}>
                {loading ? "Uploading…" : "Upload"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => router.push(`/workspace/${workspaceId}`)}
                disabled={!workspaceId}
              >
                Go to workspace
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </ContentContainer>
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div>Loading upload form...</div>}>
      <UploadForm />
    </Suspense>
  );
}

