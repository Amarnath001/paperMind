"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { API_BASE_URL, getAuthHeader } from "@/src/lib/api";

export default function UploadPage() {
  const searchParams = useSearchParams();
  const defaultWorkspaceId = searchParams.get("workspace_id") ?? "";
  const router = useRouter();

  const [workspaceId, setWorkspaceId] = useState(defaultWorkspaceId);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <main className="page-layout">
      <header className="page-header">
        <div>
          <h1>Upload paper</h1>
          <p>Upload a PDF into one of your workspaces.</p>
        </div>
        <nav>
          <a href="/dashboard">Back to dashboard</a>
        </nav>
      </header>

      <section className="card">
        <form onSubmit={handleSubmit} className="upload-form">
          <label>
            Workspace ID
            <input
              type="text"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              placeholder="Workspace ID"
              required
            />
          </label>
          <label>
            Title (optional)
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Paper title"
            />
          </label>
          <label>
            PDF file
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={(e) => {
                const selected = e.target.files?.[0] ?? null;
                setFile(selected);
              }}
              required
            />
          </label>
          {error && <p className="auth-error">{error}</p>}
          {success && <p className="auth-success">{success}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "Uploading..." : "Upload"}
          </button>
        </form>
      </section>
    </main>
  );
}

