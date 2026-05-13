import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import type { SummaryStats } from "@/lib/types";

const labels = [
  ["Total analyses", "totalAnalyses"],
  ["Anomaly detected", "anomalyCount"],
  ["Latest result", "latestResultDate"],
  ["Affected segments", "affectedSegments"],
] as const;

export function SummaryCards({ stats }: { stats: SummaryStats }) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {labels.map(([label, key]) => {
        const value = stats[key];
        return (
          <Card key={key}>
            <CardHeader>
              <CardTitle className="text-muted-foreground">{label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="serif-heading truncate text-3xl">
                {typeof value === "number" ? formatNumber(value) : value}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}
