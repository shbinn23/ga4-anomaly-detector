import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "anomaly";

const toneClass: Record<BadgeTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  success: "border-border bg-[color:color-mix(in_srgb,var(--primary)_9%,var(--card))] text-[color:var(--primary)]",
  warning: "border-[color:color-mix(in_srgb,var(--warning)_26%,var(--border))] bg-[color:var(--warning-muted)] text-[color:var(--warning)]",
  danger: "border-[color:color-mix(in_srgb,var(--destructive)_24%,var(--border))] bg-[color:color-mix(in_srgb,var(--destructive)_9%,var(--card))] text-[color:var(--destructive)]",
  anomaly: "border-anomaly/20 bg-anomaly-muted text-anomaly-foreground",
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
