"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import {
  askQuestion,
  ChatMessage,
  Conversation,
  listConversations,
  listMessages,
  createConversation,
} from "@/src/lib/api";

export default function WorkspaceChatPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = params.id;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadConversations() {
    setLoadingConversations(true);
    setError(null);
    try {
      const data = await listConversations(workspaceId);
      setConversations(data);
      if (!selectedConversationId && data.length > 0) {
        setSelectedConversationId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load conversations");
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadMessages(conversationId: string) {
    setLoadingMessages(true);
    setError(null);
    try {
      const data = await listMessages(conversationId);
      setMessages(data);
    } catch (err: any) {
      setError(err.message || "Failed to load messages");
    } finally {
      setLoadingMessages(false);
    }
  }

  useEffect(() => {
    if (workspaceId) {
      void loadConversations();
    }
  }, [workspaceId]);

  useEffect(() => {
    if (selectedConversationId) {
      void loadMessages(selectedConversationId);
    } else {
      setMessages([]);
    }
  }, [selectedConversationId]);

  async function handleNewConversation() {
    setError(null);
    try {
      const conv = await createConversation(workspaceId);
      setConversations((prev) => [conv, ...prev]);
      setSelectedConversationId(conv.id);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || "Failed to create conversation");
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    if (!selectedConversationId) {
      // create a conversation implicitly
      await handleNewConversation();
    }
    const convId = selectedConversationId ?? conversations[0]?.id;
    if (!convId) return;

    setSending(true);
    setError(null);
    try {
      const res = await askQuestion({
        workspaceId,
        conversationId: convId,
        question,
      });
      setSelectedConversationId(res.conversation_id);
      setMessages((prev) => [...prev, ...res.messages]);
      setQuestion("");
    } catch (err: any) {
      setError(err.message || "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  function renderCitations(msg: ChatMessage) {
    if (!msg.citations || !Array.isArray(msg.citations) || msg.citations.length === 0) {
      return null;
    }
    const labels = Array.from(
      new Set(
        msg.citations
          .map((c: any) => c.label)
          .filter((label: unknown): label is string => typeof label === "string"),
      ),
    );
    return (
      <div style={{ marginTop: "0.35rem", fontSize: "0.75rem", color: "#6B7280" }}>
        Sources{" "}
        {labels.map((label, idx) => (
          <span key={label}>
            <strong>{label}</strong>
            {idx < labels.length - 1 ? ", " : ""}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="page-layout">
      <header className="page-header">
        <div>
          <h1>Workspace chat</h1>
          <p>Ask questions over the papers in this workspace.</p>
        </div>
        <nav>
          <a href={`/workspace/${workspaceId}`}>Back to workspace</a>
        </nav>
      </header>

      {error && <p className="auth-error">{error}</p>}

      <section className="card chat-layout">
        <aside className="chat-sidebar">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
            <h2 style={{ fontSize: "1rem" }}>Conversations</h2>
            <button type="button" onClick={handleNewConversation} disabled={loadingConversations}>
              New
            </button>
          </div>
          {loadingConversations ? (
            <p>Loading...</p>
          ) : conversations.length === 0 ? (
            <p style={{ fontSize: "0.9rem", color: "#6B7280" }}>No conversations yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {conversations.map((conv) => (
                <li key={conv.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedConversationId(conv.id)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "0.4rem 0.5rem",
                      marginBottom: "0.25rem",
                      borderRadius: "0.4rem",
                      border: "none",
                      background:
                        selectedConversationId === conv.id ? "#E5E7EB" : "transparent",
                      cursor: "pointer",
                      fontSize: "0.9rem",
                    }}
                  >
                    {conv.title || "Untitled conversation"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <div className="chat-main">
          <div className="chat-messages">
            {loadingMessages ? (
              <p>Loading messages...</p>
            ) : messages.length === 0 ? (
              <p style={{ fontSize: "0.9rem", color: "#6B7280" }}>
                Start by asking a question about the papers in this workspace.
              </p>
            ) : (
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {messages.map((msg) => (
                  <li
                    key={msg.id}
                    style={{
                      marginBottom: "0.75rem",
                      textAlign: msg.role === "user" ? "right" : "left",
                    }}
                  >
                    <div
                      style={{
                        display: "inline-block",
                        padding: "0.5rem 0.75rem",
                        borderRadius: "0.75rem",
                        background:
                          msg.role === "user" ? "#111827" : "#F3F4F6",
                        color: msg.role === "user" ? "#FFFFFF" : "#111827",
                        maxWidth: "80%",
                        fontSize: "0.9rem",
                      }}
                    >
                      <div style={{ marginBottom: "0.25rem", fontWeight: 500 }}>
                        {msg.role === "user" ? "You" : "Assistant"}
                      </div>
                      <div>{msg.content}</div>
                      {msg.role === "assistant" && renderCitations(msg)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form onSubmit={handleSend} className="chat-input">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about the papers in this workspace..."
              disabled={sending}
            />
            <button type="submit" disabled={sending || !question.trim()}>
              {sending ? "Thinking..." : "Send"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

