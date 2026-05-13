import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { EmptyState } from "@/components/dashboard/empty-state";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { formatNumber, formatPercent } from "@/lib/format";
import type { PropertyThemeCell, SessionsTrendingItem } from "@/lib/types";
import { buildMainOverview } from "@/lib/view-models";

export default async function DashboardPage() {
  const data = await getDashboardData();
  const overview = buildMainOverview(data.analyses);

  return (
    <DashboardShell
      actions={<StatusBadge health={data.health} />}
      activeHref="/dashboard"
      description="Main overview for properties, themes, and current anomaly state."
      title="Overview"
    >

        {data.errors.length > 0 ? (
          <Card className="border-[color:var(--destructive)]/30 bg-[color:color-mix(in_srgb,var(--destructive)_7%,var(--card))]">
            <CardContent className="flex items-start gap-3 p-4 text-sm text-foreground">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-[color:var(--destructive)]" />
              <div>
                <div className="font-medium">Connection notice</div>
                <ul className="mt-1 list-inside list-disc text-muted-foreground">
                  {data.errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <SummaryCards stats={overview.stats} />

        {data.analyses.length ? (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">Sessions Trending</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 lg:grid-cols-2">
                <TrendingList
                  direction="up"
                  items={overview.sessionsTrending.higher}
                  title="예상 범위보다 높게 관측 Top 5"
                />
                <TrendingList
                  direction="down"
                  items={overview.sessionsTrending.lower}
                  title="예상 범위보다 낮게 관측 Top 5"
                />
              </CardContent>
            </Card>

            <section className="grid gap-3 md:grid-cols-2">
              {overview.themeSummaries.map((theme) => (
                <Card key={theme.theme}>
                  <CardHeader>
                    <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">{theme.theme}</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 text-sm text-muted-foreground">
                    <div className="grid grid-cols-2 gap-2">
                      <span>Total {theme.totalCount}</span>
                      <span>Anomalies {theme.anomalyCount}</span>
                      <span>Detection {theme.detectionCount}</span>
                      <span>Diagnosis {theme.diagnosisCount}</span>
                    </div>
                    <Link className="font-medium text-foreground underline-offset-4 hover:underline" href={theme.href}>
                      Open theme
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </section>

            <Card>
              <CardHeader>
                <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">Property Health Matrix</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <div className="hidden grid-cols-[minmax(12rem,1fr)_repeat(2,minmax(12rem,1fr))] gap-3 text-xs font-semibold uppercase tracking-[0.02em] text-muted-foreground md:grid">
                  <span>프로퍼티</span>
                  <span>sessions</span>
                  <span>ecommerce</span>
                </div>
                {overview.propertyThemeMatrix.slice(0, 24).map((row) => (
                  <div
                    className="grid gap-3 border-b py-3 text-sm md:grid-cols-[minmax(12rem,1fr)_repeat(2,minmax(12rem,1fr))]"
                    key={row.propertyId}
                  >
                    <div className="font-medium md:py-2">{row.propertyName}</div>
                    {row.themes.map((theme) => (
                      <HealthCell cell={theme} key={theme.theme} />
                    ))}
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center justify-between gap-4 p-5">
                <div>
                  <div className="text-2xl font-semibold tracking-[-0.02em]">Reports</div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Deterministic anomaly reports from stored analysis results.
                  </p>
                </div>
                <Link className="text-sm font-medium underline-offset-4 hover:underline" href="/dashboard/reports">
                  Open reports
                </Link>
              </CardContent>
            </Card>
          </>
        ) : (
          <EmptyState
            title="No analysis results yet"
            description="The frontend is connected to the API, but no dashboard results were returned."
          />
        )}
    </DashboardShell>
  );
}

function TrendingList({
  direction,
  items,
  title,
}: {
  direction: "up" | "down";
  items: SessionsTrendingItem[];
  title: string;
}) {
  return (
    <section className="grid gap-3">
      <div>
        <h2 className="text-base font-semibold tracking-[-0.01em]">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">기준일 target point 기준 current alert입니다.</p>
      </div>
      {items.length ? (
        <div className="grid gap-2">
          {items.map((item, index) => {
            const score = item.score === null ? null : item.score * 100;
            return (
              <div className="rounded-lg border bg-card p-3" key={item.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-muted-foreground">#{index + 1}</span>
                      <span className="truncate font-semibold">{item.propertyName}</span>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      actual {formatNumber(item.actual)} · normal {formatNumber(item.lower)} ~ {formatNumber(item.upper)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={direction === "up" ? "font-semibold text-anomaly-foreground" : "font-semibold text-anomaly-foreground"}>
                      {score === null ? "-" : formatPercent(direction === "down" ? -score : score)}
                    </div>
                    <Link className="text-xs font-medium text-primary underline-offset-4 hover:underline" href={item.href}>
                      추이 보기
                    </Link>
                  </div>
                </div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-anomaly"
                    style={{ width: `${Math.min(Math.abs(score ?? 0), 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
          현재 표시할 sessions alert가 없습니다.
        </div>
      )}
    </section>
  );
}

function HealthCell({ cell }: { cell: PropertyThemeCell }) {
  const content = (
    <div className={[
      "grid gap-1 rounded-lg border p-3 transition-colors",
      cell.status === "anomaly"
        ? "border-anomaly/20 bg-anomaly-muted text-anomaly-foreground"
        : cell.status === "watch"
          ? "border-[color:color-mix(in_srgb,var(--warning)_26%,var(--border))] bg-[color:var(--warning-muted)] text-[color:var(--warning)]"
          : cell.status === "normal"
            ? "bg-card text-foreground"
            : "bg-muted/55 text-muted-foreground",
    ].join(" ")}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold">{cell.theme}</span>
        <Badge tone={cell.status === "anomaly" ? "anomaly" : cell.status === "watch" ? "warning" : cell.status === "normal" ? "neutral" : "neutral"}>
          {cell.status === "anomaly" ? "alert" : cell.status}
        </Badge>
      </div>
      <div className="text-sm">{cell.label}</div>
      {cell.actual !== null ? (
        <div className="text-xs opacity-80">
          actual {formatNumber(cell.actual)} · {formatNumber(cell.lower)} ~ {formatNumber(cell.upper)}
        </div>
      ) : null}
    </div>
  );

  if (cell.status === "missing") {
    return content;
  }

  return <Link href={cell.href}>{content}</Link>;
}
