"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import {
  askQuestion,
  ChatMessage,
  Conversation,
  listConversations,
  listMessages,
  createConversation,
} from "@/src/lib/api";
import { ContentContainer, PageHeader } from "@/src/components/layout/Page";
import { Button } from "@/src/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/src/components/ui/Card";
import { EmptyState } from "@/src/components/ui/EmptyState";
import { Input } from "@/src/components/ui/Input";

function threadButtonClass(isActive: boolean) {
  return isActive
    ? "pm-chat-thread__btn pm-chat-thread__btn--active"
    : "pm-chat-thread__btn";
}

function bubbleClass(role: ChatMessage["role"]) {
  if (role === "user") return "pm-chat-bubble pm-chat-bubble--user";
  return "pm-chat-bubble pm-chat-bubble--assistant";
}

export default function WorkspaceChatPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = params.id;
  const router = useRouter();

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
      <div className="ui-muted" style={{ marginTop: "0.35rem" }}>
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

  let sidebarContent: React.ReactNode = null;
  if (loadingConversations) {
    sidebarContent = <div className="ui-muted">Loading…</div>;
  } else if (conversations.length === 0) {
    sidebarContent = (
      <EmptyState
        title="No conversations yet"
        description="Create a conversation to start asking questions."
        action={<Button onClick={handleNewConversation}>Create conversation</Button>}
      />
    );
  } else {
    sidebarContent = (
      <ul className="ui-list">
        {conversations.map((conv) => (
          <li key={conv.id} className="pm-chat-thread">
            <button
              type="button"
              className={threadButtonClass(selectedConversationId === conv.id)}
              onClick={() => setSelectedConversationId(conv.id)}
            >
              {conv.title || "Untitled conversation"}
            </button>
          </li>
        ))}
      </ul>
    );
  }

  let messageContent: React.ReactNode = null;
  if (loadingMessages) {
    messageContent = <div className="ui-muted">Loading messages…</div>;
  } else if (messages.length === 0) {
    messageContent = (
      <EmptyState
        title="Ask your first question"
        description="Try: “What are the main contributions of the latest paper?”"
      />
    );
  } else {
    messageContent = (
      <ul className="pm-chat-bubbles">
        {messages.map((msg) => (
          <li key={msg.id} className={bubbleClass(msg.role)}>
            <div className="pm-chat-bubble__meta">
              {msg.role === "user" ? "You" : "Assistant"}
            </div>
            <div className="pm-chat-bubble__content">{msg.content}</div>
            {msg.role === "assistant" ? renderCitations(msg) : null}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <ContentContainer>
      <PageHeader
        title="Chat"
        subtitle="Ask questions over the papers in this workspace."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => router.push(`/workspace/${workspaceId}`)}
            >
              Back
            </Button>
            <Button
              variant="secondary"
              onClick={handleNewConversation}
              disabled={loadingConversations}
            >
              New conversation
            </Button>
          </>
        }
      />

      {error ? <div className="ui-error" style={{ marginBottom: "0.75rem" }}>{error}</div> : null}

      <div className="pm-chat-grid">
        <Card className="pm-chat-sidebar">
          <CardHeader title="Conversations" subtitle="Workspace threads" />
          <CardBody>
            {sidebarContent}
          </CardBody>
        </Card>

        <Card className="pm-chat-main">
          <CardHeader
            title="Assistant"
            subtitle="Grounded answers with citations when available."
          />
          <CardBody>
            <div className="pm-chat-messages">
              {messageContent}
            </div>

            <form onSubmit={handleSend} className="pm-chat-composer">
              <Input
                aria-label="Message"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about the papers in this workspace…"
                disabled={sending}
              />
              <Button type="submit" disabled={sending || !question.trim()}>
                {sending ? "Thinking…" : "Send"}
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </ContentContainer>
  );
}

