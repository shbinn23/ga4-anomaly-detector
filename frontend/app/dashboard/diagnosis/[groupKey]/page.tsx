import Link from "next/link";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { DashboardShell, PageActionLink, PageTabs } from "@/components/dashboard/dashboard-shell";
import { EmptyState } from "@/components/dashboard/empty-state";
import { ForecastChart } from "@/components/dashboard/forecast-chart";
import { getDashboardData } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import { buildDiagnosisPage } from "@/lib/view-models";

export default async function DiagnosisPage({
  params,
  searchParams,
}: {
  params: Promise<{ groupKey: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { groupKey } = await params;
  const query = await searchParams;
  const activeTab = query.tab === "table" ? "table" : "chart";
  const data = await getDashboardData();
  const page = buildDiagnosisPage(data.analyses, groupKey);
  const themeHref = page.detection ? `/dashboard/themes/${page.detection.result.domain}` : "/dashboard";

  return (
    <DashboardShell
      actions={
        <>
          <PageActionLink href="/dashboard" muted>Back to overview</PageActionLink>
          <PageActionLink href={themeHref} muted>Back to theme</PageActionLink>
        </>
      }
      activeHref={themeHref}
      description={<span className="break-all">{page.groupKey}</span>}
      eyebrow="Step 2 Diagnosis"
      title={page.detection?.result.property_name ?? "Diagnosis"}
    >

        {page.diagnoses.length ? (
          <>
            <PageTabs
              items={[
                { href: `/dashboard/diagnosis/${groupKey}?tab=chart`, label: "Chart", active: activeTab === "chart" },
                { href: `/dashboard/diagnosis/${groupKey}?tab=table`, label: "Table", active: activeTab === "table" },
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
                        <div className="grid gap-1 text-sm text-muted-foreground">
                          <span className="font-medium text-foreground">{row.dimension}</span>
                          <span>{row.dimensionValue}</span>
                          <span>Last anomaly {row.lastAnomalyDate}</span>
                          <span>
                            Deviation <span className="font-semibold text-anomaly-foreground">{formatPercent(row.latestDeviation)}</span>
                          </span>
                        </div>
                      }
                    />
                  ))}
                </section>
              ) : (
                <EmptyState title="No anomaly charts" description="No anomalous diagnosis items are available for chart verification." />
              )
            ) : (
              <AnalysisTable rows={page.rows} title="Diagnosis results" />
            )}
          </>
        ) : (
          <EmptyState title="No diagnosis results" description="No stored Step 2 results are connected to this detection group." />
        )}
    </DashboardShell>
  );
}
