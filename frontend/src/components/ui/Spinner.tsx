export function Spinner({ label }: { readonly label?: string }) {
  return <span className="ui-spinner" aria-label={label || "Loading"} />;
}

