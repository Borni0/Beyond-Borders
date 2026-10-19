import * as React from "react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-teal text-white hover:bg-teal-dark focus-visible:bg-teal-dark disabled:bg-slate-300",
  secondary:
    "bg-white text-midnight border border-border hover:bg-ivory disabled:bg-slate-100",
  ghost:
    "bg-transparent text-midnight hover:bg-ivory disabled:text-slate-300",
  danger:
    "bg-red text-white hover:bg-red-700 focus-visible:bg-red-700 disabled:bg-slate-300",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { className, variant = "primary", size = "md", isLoading = false, children, disabled, ...rest },
    ref,
  ) {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-lg font-medium",
          "transition-colors duration-150",
          "disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        disabled={disabled || isLoading}
        aria-busy={isLoading || undefined}
        {...rest}
      >
        {isLoading ? (
          <span
            className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent"
            aria-hidden="true"
          />
        ) : null}
        {children}
      </button>
    );
  },
);