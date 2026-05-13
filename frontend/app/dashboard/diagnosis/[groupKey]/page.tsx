import Link from "next/link";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { EmptyState } from "@/components/dashboard/empty-state";
import { ForecastChart } from "@/components/dashboard/forecast-chart";
import { getDashboardData } from "@/lib/api";
import { buildDiagnosisPage } from "@/lib/view-models";

export default async function DiagnosisPage({ params }: { params: Promise<{ groupKey: string }> }) {
  const { groupKey } = await params;
  const data = await getDashboardData();
  const page = buildDiagnosisPage(data.analyses, groupKey);
  const themeHref = page.detection ? `/dashboard/themes/${page.detection.result.domain}` : "/dashboard";

  return (
    <main className="min-h-screen px-5 py-6 md:px-8 lg:px-10">
      <div className="mx-auto grid max-w-7xl gap-5">
        <header className="border-b pb-6">
          <div className="flex flex-wrap gap-3 text-sm font-medium text-muted-foreground">
            <Link className="underline-offset-4 hover:underline" href="/dashboard">Back to overview</Link>
            <Link className="underline-offset-4 hover:underline" href={themeHref}>Back to theme</Link>
          </div>
          <p className="mt-4 text-sm font-medium text-muted-foreground">Step 2 Diagnosis</p>
          <h1 className="serif-heading text-4xl leading-tight">{page.detection?.result.property_name ?? "Diagnosis"}</h1>
          <p className="mt-2 break-all text-sm text-muted-foreground">{page.groupKey}</p>
        </header>

        {page.diagnoses.length ? (
          <>
            <ForecastChart analysis={page.featuredDiagnosis} />
            <AnalysisTable rows={page.rows} title="Diagnosis results" />
          </>
        ) : (
          <EmptyState title="No diagnosis results" description="No stored Step 2 results are connected to this detection group." />
        )}
      </div>
    </main>
  );
}
