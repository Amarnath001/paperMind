export default function Home() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <h1
        style={{
          fontSize: "2.5rem",
          fontWeight: 700,
          marginBottom: "0.5rem",
        }}
      >
        PaperMind – Research Intelligence Platform
      </h1>
      <p
        style={{
          color: "#666",
          fontSize: "1.125rem",
        }}
      >
        Multi-Agent AI for research paper ingestion, embeddings, clustering, and RAG
      </p>
    </main>
  );
}
