export default function Home() {
  return (
    <main className="auth-layout">
      <section className="auth-card">
        <h1>PaperMind</h1>
        <p className="ui-hint" style={{ marginTop: "0.35rem" }}>
          Research intelligence workspace for papers, chat, and insights.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.25rem" }}>
          <a href="/signup" className="auth-primary-link">
            Create account
          </a>
          <a href="/login" className="auth-secondary-link">
            Log in
          </a>
        </div>
      </section>
    </main>
  );
}
