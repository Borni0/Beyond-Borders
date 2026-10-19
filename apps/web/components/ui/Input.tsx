import * as React from "react";

import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ className, invalid, ...rest }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "h-10 w-full rounded-lg border bg-white px-3 text-sm text-midnight placeholder:text-slate-400",
          "transition-colors duration-150",
          invalid
            ? "border-red focus-visible:border-red"
            : "border-border focus-visible:border-teal",
          className,
        )}
        aria-invalid={invalid || undefined}
        {...rest}
      />
    );
  },
);

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export function Label({ className, children, required, ...rest }: LabelProps) {
  return (
    <label
      className={cn("text-sm font-medium text-midnight", className)}
      {...rest}
    >
      {children}
      {required ? (
        <span aria-hidden="true" className="ml-0.5 text-red">
          *
        </span>
      ) : null}
    </label>
  );
}

interface FieldProps {
  label: string;
  htmlFor: string;
  error?: string | null;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}

export function Field({ label, htmlFor, error, hint, required, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={htmlFor} required={required}>
        {label}
      </Label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} role="alert" className="text-xs text-red">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-slate">{hint}</p>
      ) : null}
    </div>
  );
}