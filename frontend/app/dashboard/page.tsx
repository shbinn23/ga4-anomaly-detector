import { AlertTriangle } from "lucide-react";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { EmptyState } from "@/components/dashboard/empty-state";
import { ForecastChart } from "@/components/dashboard/forecast-chart";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { Card, CardContent } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { buildAnalysisRows, buildDashboardSections, buildSummary } from "@/lib/view-models";

export default async function DashboardPage() {
  const data = await getDashboardData();
  const sections = buildDashboardSections(data.analyses);
  const stats = buildSummary(sections);
  const detectionRows = buildAnalysisRows(sections.detections);
  const diagnosisRows = buildAnalysisRows(sections.diagnoses);

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
              A quiet view of analysis health, forecast ranges, and segments that need attention.
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

        <SummaryCards stats={stats} />

        {data.analyses.length ? (
          <>
            <section className="grid gap-5">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Step 1</p>
                <h2 className="serif-heading text-3xl">Detection</h2>
              </div>
              {sections.detections.length ? (
                <>
                  <ForecastChart analysis={sections.featuredDetection} />
                  <AnalysisTable rows={detectionRows} title="Detection results" />
                </>
              ) : (
                <EmptyState
                  title="No detection results"
                  description="No Step 1 detection analyses were returned by the dashboard API."
                />
              )}
            </section>

            <section className="grid gap-5">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Step 2</p>
                <h2 className="serif-heading text-3xl">Diagnosis</h2>
              </div>
              {sections.diagnoses.length ? (
                <>
                  <ForecastChart analysis={sections.featuredDiagnosis} />
                  <AnalysisTable rows={diagnosisRows} title="Diagnosis results" />
                </>
              ) : (
                <EmptyState
                  title="No diagnosis results"
                  description="No Step 2 diagnosis analyses were returned by the dashboard API."
                />
              )}
            </section>
          </>
        ) : (
          <EmptyState
            title="No analysis results yet"
            description="The frontend is connected to the API, but no result endpoint returned analysis data. Existing Streamlit and backend flows remain unchanged."
          />
        )}
      </div>
    </main>
  );
}
