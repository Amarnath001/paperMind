import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperMind – Research Intelligence Platform",
  description: "Multi-Agent Research Intelligence Platform for processing research papers",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
