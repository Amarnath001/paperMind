import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <section className={["ui-card", className].filter(Boolean).join(" ")}>
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  subtitle,
  right,
}: {
  readonly title: ReactNode;
  readonly subtitle?: ReactNode;
  readonly right?: ReactNode;
}) {
  return (
    <div className="ui-card__header">
      <div>
        <div className="ui-card__title">{title}</div>
        {subtitle ? <div className="ui-card__subtitle">{subtitle}</div> : null}
      </div>
      {right ? <div className="ui-card__right">{right}</div> : null}
    </div>
  );
}

export function CardBody({ children }: { readonly children: ReactNode }) {
  return <div className="ui-card__body">{children}</div>;
}

