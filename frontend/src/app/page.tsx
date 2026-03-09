export default function Home() {
  return (
    <main className="auth-layout">
      <section className="auth-card">
        <h1>PaperMind – Research Intelligence Platform</h1>
        <p style={{ marginBottom: "1.25rem", color: "#4b5563" }}>
          Multi-Agent AI for research paper ingestion, embeddings, clustering,
          and RAG.
        </p>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <a href="/signup" className="auth-primary-link">
            Get started
          </a>
          <a href="/login" className="auth-secondary-link">
            Log in
          </a>
        </div>
      </section>
    </main>
  );
}
