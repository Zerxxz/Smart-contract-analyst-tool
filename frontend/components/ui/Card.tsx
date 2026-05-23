import { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "bg-[var(--panel)] border border-[var(--border)] rounded-lg",
        className
      )}
      {...rest}
    />
  );
}
