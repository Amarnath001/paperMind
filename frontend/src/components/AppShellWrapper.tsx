"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";

import AppShell from "@/src/components/AppShell";

export default function AppShellWrapper({
  children,
}: {
  readonly children: ReactNode;
}) {
  const pathname = usePathname();

  const isBare =
    pathname === "/" ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/signup");

  if (isBare) {
    return <>{children}</>;
  }

  return <AppShell>{children}</AppShell>;
}

