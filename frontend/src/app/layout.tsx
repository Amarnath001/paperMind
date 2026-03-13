import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/src/components/AppShell";

export const metadata: Metadata = {
  title: "PaperMind – Research Intelligence Platform",
  description: "Multi-Agent Research Intelligence Platform for processing research papers",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const isBarePage =
    typeof globalThis === "undefined" ||
    typeof globalThis.window === "undefined" ||
    globalThis.window.location.pathname.startsWith("/login") ||
    globalThis.window.location.pathname.startsWith("/signup") ||
    globalThis.window.location.pathname === "/";

  return (
    <html lang="en">
      <body>
        {isBarePage ? <>{children}</> : <AppShell>{children}</AppShell>}
      </body>
    </html>
  );
}
