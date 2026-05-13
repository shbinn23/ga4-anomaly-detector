"use client";

import type { ReactNode } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { normalizeForecastData } from "@/lib/forecast";
import { formatDisplayValue } from "@/lib/format";
import type { AnalysisRecord } from "@/lib/types";

const chartConfig = {
  y: {
    label: "Actual",
    color: "var(--chart-actual)",
  },
  yhat: {
    label: "Forecast",
    color: "var(--chart-forecast)",
  },
  yhat_upper: {
    label: "Upper",
    color: "var(--chart-band)",
  },
  yhat_lower: {
    label: "Lower",
    color: "var(--chart-band)",
  },
};

export function ForecastChart({
  analysis,
  meta,
  valueFormat = "number",
}: {
  analysis: AnalysisRecord | null;
  meta?: ReactNode;
  valueFormat?: "number" | "percentage";
}) {
  const data = normalizeForecastData(analysis?.result.forecast_data);
  const valueFormatter = (value: unknown) =>
    typeof value === "number" ? formatDisplayValue(value, valueFormat) : String(value ?? "-");
  const anomalyPoints = data.filter((point) => point.is_anomaly);
  const anomalyDates = new Set(anomalyPoints.map((point) => point.ds));

  return (
    <Card className="min-w-0 overflow-hidden">
      <CardHeader>
        <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">Forecast trace</CardTitle>
        <CardDescription>
          Actual value, expected center line, confidence interval, and anomaly points.
        </CardDescription>
        {meta}
      </CardHeader>
      <CardContent className="min-w-0 overflow-hidden">
        {data.length ? (
          <ChartContainer config={chartConfig} className="h-72 w-full min-w-0 overflow-hidden">
            <ComposedChart data={data} margin={{ left: 4, right: 10, top: 12, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="ds"
                tickLine={false}
                axisLine={false}
                tickMargin={10}
                interval="preserveStartEnd"
                minTickGap={36}
                stroke="var(--muted-foreground)"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                width={44}
                stroke="var(--muted-foreground)"
                tickFormatter={(value) => valueFormatter(value)}
              />
              <ChartTooltip content={<ChartTooltipContent anomalyDates={anomalyDates} valueFormatter={valueFormatter} />} />
              <Area
                dataKey="yhat_upper"
                type="monotone"
                fill="var(--chart-band)"
                fillOpacity={0.16}
                stroke="transparent"
                dot={false}
                activeDot={false}
              />
              <Area
                dataKey="yhat_lower"
                type="monotone"
                fill="var(--card)"
                fillOpacity={1}
                stroke="transparent"
                dot={false}
                activeDot={false}
              />
              <Line
                dataKey="yhat"
                type="monotone"
                stroke="var(--chart-forecast)"
                strokeWidth={2}
                dot={false}
              />
              <Line
                dataKey="y"
                type="monotone"
                stroke="var(--chart-actual)"
                strokeWidth={2}
                dot={false}
              />
              {anomalyPoints.map((point) => (
                <ReferenceDot
                  key={point.ds}
                  x={point.ds}
                  y={point.y}
                  r={4}
                  fill="var(--chart-anomaly)"
                  stroke="var(--anomaly-muted)"
                  strokeWidth={2}
                />
              ))}
            </ComposedChart>
          </ChartContainer>
        ) : (
          <div className="flex min-h-80 items-center justify-center rounded-lg border border-dashed bg-muted/35 text-sm text-muted-foreground">
            No forecast series available.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
