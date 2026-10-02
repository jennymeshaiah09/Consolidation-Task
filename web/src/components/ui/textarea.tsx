import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<"textarea">>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-36 w-full rounded-2xl border border-ink/10 bg-white/80 px-4 py-3 text-sm outline-none transition focus:border-coral/50 focus:ring-4 focus:ring-coral/10",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
