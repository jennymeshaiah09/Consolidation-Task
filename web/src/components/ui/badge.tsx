import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-coral/20 bg-coral/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-coral",
        className,
      )}
      {...props}
    />
  );
}
