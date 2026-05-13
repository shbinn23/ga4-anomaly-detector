import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/empty-state";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { buildMainOverview } from "@/lib/view-models";

export default async function DashboardPage() {
  const data = await getDashboardData();
  const overview = buildMainOverview(data.analyses);

  return (
    <main className="min-h-screen px-5 py-6 md:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-4 border-b pb-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="mb-2 text-sm font-medium text-muted-foreground">GA4 anomaly operations</p>
            <h1 className="serif-heading text-4xl leading-tight md:text-5xl">
              Monitoring workspace
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              Main overview for properties, themes, and anomaly state.
            </p>
          </div>
          <StatusBadge health={data.health} />
        </header>

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
            <section className="grid gap-3 md:grid-cols-2">
              {overview.themeSummaries.map((theme) => (
                <Card key={theme.theme}>
                  <CardHeader>
                    <CardTitle className="serif-heading text-2xl">{theme.theme}</CardTitle>
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
                <CardTitle className="serif-heading text-2xl">Property x Theme status</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                {overview.propertyThemeMatrix.slice(0, 24).map((row) => (
                  <div
                    className="grid gap-2 border-b py-3 text-sm md:grid-cols-[minmax(10rem,1fr)_2fr]"
                    key={row.propertyId}
                  >
                    <div className="font-medium">{row.propertyName}</div>
                    <div className="flex flex-wrap gap-2">
                      {row.themes.map((theme) => (
                        <Link href={theme.href} key={theme.theme}>
                          <Badge tone={theme.status === "anomaly" ? "warning" : theme.status === "normal" ? "success" : "neutral"}>
                            {theme.theme}: {theme.status}
                          </Badge>
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center justify-between gap-4 p-5">
                <div>
                  <div className="serif-heading text-2xl">Reports</div>
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
      </div>
    </main>
  );
}
