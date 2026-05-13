import Link from "next/link";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { EmptyState } from "@/components/dashboard/empty-state";
import { ForecastChart } from "@/components/dashboard/forecast-chart";
import { Card, CardContent } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { buildThemeDetectionPage, SUPPORTED_THEMES } from "@/lib/view-models";

export default async function ThemePage({ params }: { params: Promise<{ theme: string }> }) {
  const { theme } = await params;
  const data = await getDashboardData();
  const page = buildThemeDetectionPage(data.analyses, theme);
  const supported = SUPPORTED_THEMES.includes(theme as (typeof SUPPORTED_THEMES)[number]);

  return (
    <main className="min-h-screen px-5 py-6 md:px-8 lg:px-10">
      <div className="mx-auto grid max-w-7xl gap-5">
        <header className="border-b pb-6">
          <Link className="text-sm font-medium text-muted-foreground underline-offset-4 hover:underline" href="/dashboard">
            Back to overview
          </Link>
          <p className="mt-4 text-sm font-medium text-muted-foreground">Step 1 Detection</p>
          <h1 className="serif-heading text-4xl leading-tight">{theme}</h1>
        </header>

        {!supported ? (
          <EmptyState title="Unknown theme" description="This dashboard only includes current stored themes." />
        ) : page.detections.length ? (
          <>
            <ForecastChart analysis={page.featuredDetection} />
            <AnalysisTable rows={page.rows} title="Detection results" />
          </>
        ) : (
          <EmptyState title="No detection results" description="No Step 1 detection rows exist for this theme." />
        )}

        <Card>
          <CardContent className="p-5 text-sm text-muted-foreground">
            Diagnosis links are available only when stored Step 2 results are already connected to a detection group.
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
