import Link from "next/link";
import { EmptyState } from "@/components/dashboard/empty-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { formatNumber, formatPercent } from "@/lib/format";
import { buildReportsPage } from "@/lib/view-models";

export default async function ReportsPage() {
  const data = await getDashboardData();
  const reports = buildReportsPage(data.analyses);

  return (
    <main className="min-h-screen px-5 py-6 md:px-8 lg:px-10">
      <div className="mx-auto grid max-w-7xl gap-5">
        <header className="border-b pb-6">
          <Link className="text-sm font-medium text-muted-foreground underline-offset-4 hover:underline" href="/dashboard">
            Back to overview
          </Link>
          <h1 className="serif-heading mt-4 text-4xl leading-tight">Reports</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Stored anomaly evidence grouped by property and theme.
          </p>
        </header>

        {reports.propertyReports.length ? (
          <>
            <section className="grid gap-4">
              <h2 className="serif-heading text-3xl">Property reports</h2>
              {reports.propertyReports.slice(0, 20).map((property) => (
                <Card key={property.propertyName}>
                  <CardHeader>
                    <CardTitle className="serif-heading text-2xl">{property.propertyName}</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3">
                    {property.reports.slice(0, 5).map((report) => (
                      <div className="grid gap-2 border-b pb-3 text-sm" key={report.id}>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={report.hasAnomaly ? "warning" : "neutral"}>{report.theme}</Badge>
                          <span className="font-medium">{report.metricName}</span>
                          <span className="text-muted-foreground">{report.mode}</span>
                        </div>
                        <div className="grid gap-1 text-muted-foreground md:grid-cols-4">
                          <span>Actual {formatNumber(report.latestY)}</span>
                          <span>Expected {formatNumber(report.latestYhat)}</span>
                          <span>Lower {formatNumber(report.latestLower)}</span>
                          <span>Upper {formatNumber(report.latestUpper)}</span>
                          <span>Deviation {formatPercent(report.latestDeviation)}</span>
                          <span>Last anomaly {report.lastAnomalyDate}</span>
                        </div>
                        <div className="flex flex-wrap gap-3">
                          <Link href={report.detectionHref ?? `/dashboard/themes/${report.theme}`} className="font-medium underline-offset-4 hover:underline">
                            Detection detail
                          </Link>
                          {report.diagnosisHref ? (
                            <Link href={report.diagnosisHref} className="font-medium underline-offset-4 hover:underline">
                              Diagnosis detail
                            </Link>
                          ) : (
                            <span className="text-muted-foreground">No diagnosis candidates</span>
                          )}
                        </div>
                        {report.diagnosisCandidates.length ? (
                          <div className="text-muted-foreground">
                            Top candidates: {report.diagnosisCandidates.map((item) => `${item.dimensionValue} (${item.anomalyCount})`).join(", ")}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </section>

            <section className="grid gap-4">
              <h2 className="serif-heading text-3xl">Theme reports</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {reports.themeReports.map((theme) => (
                  <Card key={theme.theme}>
                    <CardHeader>
                      <CardTitle className="serif-heading text-2xl">{theme.theme}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                      {theme.reports.length} anomalous report items
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          </>
        ) : (
          <EmptyState title="No anomaly reports" description="No anomalous stored results are available for reports." />
        )}
      </div>
    </main>
  );
}
