import { ReactNode } from "react";

export function ContentContainer({ children }: { readonly children: ReactNode }) {
  return <div className="ui-container">{children}</div>;
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  readonly title: ReactNode;
  readonly subtitle?: ReactNode;
  readonly actions?: ReactNode;
}) {
  return (
    <div className="ui-page-header">
      <div>
        <div className="ui-page-title">{title}</div>
        {subtitle ? <div className="ui-page-subtitle">{subtitle}</div> : null}
      </div>
      {actions ? <div className="ui-page-actions">{actions}</div> : null}
    </div>
  );
}

