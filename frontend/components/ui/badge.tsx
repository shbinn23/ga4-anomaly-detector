import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "danger";

const toneClass: Record<BadgeTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  success: "border-border bg-[color:var(--muted)] text-foreground",
  warning: "border-border bg-accent text-accent-foreground",
  danger: "border-border bg-[color:color-mix(in_srgb,var(--destructive)_12%,var(--card))] text-[color:var(--destructive)]",
};

function Badge({
  className,
  tone = "neutral",
  ...props
}: React.ComponentProps<"span"> & { tone?: BadgeTone }) {
  return (
    <span
      data-slot="badge"
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-semibold leading-5",
        toneClass[tone],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
