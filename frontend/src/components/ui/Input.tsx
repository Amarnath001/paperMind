"use client";

import { forwardRef, InputHTMLAttributes } from "react";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string | null;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, className = "", id, ...props }, ref) => {
    const inputId = id || props.name || undefined;

    return (
      <div className="ui-field">
        {label ? (
          <label className="ui-label" htmlFor={inputId}>
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          className={["ui-input", error ? "ui-input--error" : "", className]
            .filter(Boolean)
            .join(" ")}
          {...props}
        />
        {error ? <div className="ui-error">{error}</div> : null}
        {!error && hint ? <div className="ui-hint">{hint}</div> : null}
      </div>
    );
  },
);

Input.displayName = "Input";

