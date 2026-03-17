"use client";

import { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { clearToken } from "@/src/lib/api";

export default function AppShell({
  children,
}: {
  readonly children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  function handleSignOut() {
    clearToken();
    router.push("/login");
  }

  const activeWorkspaceId =
    pathname.startsWith("/workspace/") ? pathname.split("/")[2] : null;

  function goChat() {
    if (activeWorkspaceId) {
      router.push(`/workspace/${activeWorkspaceId}/chat`);
      return;
    }
    router.push("/dashboard");
  }

  function goInsights() {
    if (activeWorkspaceId) {
      router.push(`/workspace/${activeWorkspaceId}/insights`);
      return;
    }
    router.push("/dashboard");
  }

  return (
    <div className="shell">
      <aside className="shell-sidebar">
        <button
          type="button"
          className="shell-sidebar-brand"
          onClick={() => router.push("/dashboard")}
        >
          <span className="shell-sidebar-logo">PM</span>
          <span className="shell-sidebar-text">
            <span className="shell-sidebar-name">PaperMind</span>
            <span className="shell-sidebar-subtitle">
              Research intelligence
            </span>
          </span>
        </button>

        <nav className="shell-sidebar-nav">
          <button
            type="button"
            className="shell-nav-item"
            onClick={() => router.push("/dashboard")}
          >
            Dashboard
          </button>
          <button
            type="button"
            className="shell-nav-item"
            onClick={() => router.push("/upload")}
          >
            Upload
          </button>
          <button type="button" className="shell-nav-item" onClick={goChat}>
            Chat
          </button>
          <button
            type="button"
            className="shell-nav-item"
            onClick={goInsights}
          >
            Insights
          </button>
        </nav>
      </aside>

      <div className="shell-main">
        <header className="shell-topbar">
          <div className="shell-topbar-left">
            <span className="shell-product">PaperMind</span>
          </div>
          <div className="shell-topbar-right">
            <button
              type="button"
              className="shell-signout"
              onClick={handleSignOut}
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="shell-content">{children}</main>
      </div>
    </div>
  );
}

