"use client";

import * as React from "react";
import * as RechartsPrimitive from "recharts";
import { cn } from "@/lib/utils";

export type ChartConfig = {
  [key: string]: {
    label?: React.ReactNode;
    color?: string;
  };
};

const ChartContext = React.createContext<{ config: ChartConfig } | null>(null);

function useChart() {
  const context = React.useContext(ChartContext);
  if (!context) {
    throw new Error("useChart must be used within a ChartContainer");
  }
  return context;
}

function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: React.ComponentProps<"div"> & {
  config: ChartConfig;
  children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
}) {
  const uniqueId = React.useId();
  const chartId = `chart-${id || uniqueId.replace(/:/g, "")}`;

  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-slot="chart"
        data-chart={chartId}
        className={cn("flex aspect-[16/7] justify-center text-xs", className)}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer width="100%" height="100%">
          {children}
        </RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
}

function ChartStyle({ id, config }: { id: string; config: ChartConfig }) {
  const colorConfig = Object.entries(config).filter(([, config]) => config.color);
  if (!colorConfig.length) {
    return null;
  }

  return (
    <style
      dangerouslySetInnerHTML={{
        __html: `
[data-chart=${id}] {
${colorConfig.map(([key, item]) => `  --color-${key}: ${item.color};`).join("\n")}
}
`,
      }}
    />
  );
}

const ChartTooltip = RechartsPrimitive.Tooltip;

type ChartTooltipContentProps = {
  active?: boolean;
  payload?: Array<{
    dataKey?: unknown;
    name?: unknown;
    value?: unknown;
  }>;
  anomalyDates?: Set<string>;
  valueFormatter?: (value: unknown) => string;
  label?: React.ReactNode;
  className?: string;
};

function ChartTooltipContent({
  active,
  anomalyDates,
  payload,
  valueFormatter,
  label,
  className,
}: ChartTooltipContentProps) {
  const { config } = useChart();

  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className={cn("rounded-lg border bg-card px-3 py-2 text-xs", className)}>
      <div className="mb-1 flex items-center justify-between gap-4 font-medium text-foreground">
        <span>{label}</span>
        {typeof label === "string" && anomalyDates?.has(label) ? (
          <span className="text-anomaly-foreground">Anomaly</span>
        ) : null}
      </div>
      <div className="grid gap-1">
        {payload.map((item) => {
          const key = String(item.dataKey || item.name);
          const itemConfig = config[key];
          return (
            <div key={key} className="flex min-w-36 items-center justify-between gap-4 text-muted-foreground">
              <span>{itemConfig?.label || key}</span>
              <span className="font-medium tabular-nums text-foreground">
                {valueFormatter ? valueFormatter(item.value) : String(item.value ?? "-")}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export { ChartContainer, ChartTooltip, ChartTooltipContent };
