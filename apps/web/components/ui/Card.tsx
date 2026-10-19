import * as React from "react";

import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: keyof React.JSX.IntrinsicElements;
}

export function Card({ className, as = "div", ...rest }: CardProps) {
  const Tag = as as React.ElementType;
  return (
    <Tag
      className={cn(
        "rounded-2xl border border-border bg-white p-6 shadow-sm",
        className,
      )}
      {...rest}
    />
  );
}

export function CardHeader({ className, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mb-4 flex flex-col gap-1", className)} {...rest} />;
}

export function CardTitle({ className, ...rest }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2 className={cn("text-lg font-semibold text-midnight", className)} {...rest} />
  );
}

export function CardDescription({
  className,
  ...rest
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-slate", className)} {...rest} />;
}

export function CardContent({ className, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-4", className)} {...rest} />;
}