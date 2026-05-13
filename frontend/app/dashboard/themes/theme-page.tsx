import Link from "next/link";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { DashboardShell, PageActionLink, PageTabs } from "@/components/dashboard/dashboard-shell";
import { EmptyState } from "@/components/dashboard/empty-state";
import { ForecastChart } from "@/components/dashboard/forecast-chart";
import { Card, CardContent } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import { buildThemeDetectionPage, SUPPORTED_THEMES } from "@/lib/view-models";

export async function ThemeDetectionView({
  theme,
  activeTab,
}: {
  theme: string;
  activeTab: "table" | "chart";
}) {
  const data = await getDashboardData();
  const page = buildThemeDetectionPage(data.analyses, theme);
  const supported = SUPPORTED_THEMES.includes(theme as (typeof SUPPORTED_THEMES)[number]);

  return (
    <DashboardShell
      actions={<PageActionLink href="/dashboard" muted>Back to overview</PageActionLink>}
      activeHref={`/dashboard/themes/${theme}`}
      description="Review property-level current alerts before opening Step 2 diagnosis."
      eyebrow="Step 1 Detection"
      key={theme}
      title={theme}
    >
      {!supported ? (
        <EmptyState title="Unknown theme" description="This dashboard only includes current stored themes." />
      ) : page.detections.length ? (
        <>
          <PageTabs
            items={[
              { href: `/dashboard/themes/${theme}?tab=chart`, label: "Chart", active: activeTab === "chart" },
              { href: `/dashboard/themes/${theme}?tab=table`, label: "Table", active: activeTab === "table" },
            ]}
          />

          {activeTab === "chart" ? (
            page.chartItems.length ? (
              <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {page.chartItems.map(({ analysis, row }) => (
                  <ForecastChart
                    analysis={analysis}
                    key={row.id}
                    meta={
                      <div className="grid gap-3 text-sm text-muted-foreground">
                        <div className="grid gap-1">
                          <span className="font-medium text-foreground">{row.propertyName}</span>
                          <span>{row.metricName}</span>
                          <span>Last anomaly {row.lastAnomalyDate}</span>
                          <span>
                            Deviation <span className="font-semibold text-anomaly-foreground">{formatPercent(row.latestDeviation)}</span>
                          </span>
                        </div>
                        {row.detailHref ? (
                          <Link
                            className="inline-flex h-9 w-fit items-center rounded-full bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-[color:color-mix(in_srgb,var(--primary)_88%,black)] active:scale-[0.98]"
                            href={row.detailHref}
                          >
                            원인 분석 보기
                          </Link>
                        ) : (
                          <span className="inline-flex h-9 w-fit items-center rounded-full border px-4 text-sm text-muted-foreground">
                            {row.detailLabel ?? "원인 분석 없음"}
                          </span>
                        )}
                      </div>
                    }
                  />
                ))}
              </section>
            ) : (
              <EmptyState title="No anomaly charts" description="No anomalous detection items are available for chart verification." />
            )
          ) : (
            <AnalysisTable rows={page.rows} title="Detection results" />
          )}
        </>
      ) : (
        <EmptyState title="No detection results" description="No Step 1 detection rows exist for this theme." />
      )}

      <Card>
        <CardContent className="p-5 text-sm text-muted-foreground">
          Diagnosis links are available only when stored Step 2 results are already connected to a detection group.
        </CardContent>
      </Card>
    </DashboardShell>
  );
}
