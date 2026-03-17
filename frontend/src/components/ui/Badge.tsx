import { ReactNode } from "react";

type Tone = "neutral" | "info" | "success" | "warning" | "danger";

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  readonly children: ReactNode;
  readonly tone?: Tone;
  readonly className?: string;
}) {
  return (
    <span className={["ui-badge", `ui-badge--${tone}`, className].join(" ")}>
      {children}
    </span>
  );
}

