"use client";

import { ReactNode } from "react";
import { useRouter } from "next/navigation";

import { clearToken } from "@/src/lib/api";

export default function AppShell({ children }: { readonly children: ReactNode }) {
  const router = useRouter();

  function handleSignOut() {
    clearToken();
    router.push("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-shell-header">
        <button
          type="button"
          className="app-shell-brand"
          onClick={() => router.push("/dashboard")}
        >
          <span className="app-shell-logo">PM</span>
          <div className="app-shell-title">
            <span className="app-name">PaperMind</span>
            <span className="app-tagline">Research intelligence workspace</span>
          </div>
        </button>
        <nav className="app-shell-nav">
          <button
            type="button"
            className="app-shell-link"
            onClick={() => router.push("/dashboard")}
          >
            Dashboard
          </button>
          <button
            type="button"
            className="app-shell-link"
            onClick={() => router.push("/upload")}
          >
            Upload
          </button>
          <button
            type="button"
            className="app-shell-signout"
            onClick={handleSignOut}
          >
            Sign out
          </button>
        </nav>
      </header>
      <main className="app-shell-main">{children}</main>
    </div>
  );
}

