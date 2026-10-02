import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-11 w-full rounded-2xl border border-ink/10 bg-white/80 px-4 text-sm outline-none transition focus:border-coral/50 focus:ring-4 focus:ring-coral/10",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
