import { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  readonly title: ReactNode;
  readonly description?: ReactNode;
  readonly action?: ReactNode;
}) {
  return (
    <div className="ui-empty">
      <div className="ui-empty__title">{title}</div>
      {description ? <div className="ui-empty__desc">{description}</div> : null}
      {action ? <div className="ui-empty__action">{action}</div> : null}
    </div>
  );
}

