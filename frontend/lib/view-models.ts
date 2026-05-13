import { countAnomalyPoints, lastAnomalyDate, latestForecastPoint } from "@/lib/forecast";
import type { AnalysisRecord, AnalysisTableRow, SummaryStats } from "@/lib/types";

export function buildSummaryStats(analyses: AnalysisRecord[]): SummaryStats {
  const anomalous = analyses.filter((item) => item.result.is_anomaly);
  const latest = analyses.at(-1);

  return {
    totalAnalyses: analyses.length,
    anomalyCount: anomalous.length,
    latestLabel: latest?.result.property_name || latest?.result.property_id || latest?.id || "-",
    affectedSegments: new Set(
      anomalous.map((item) => item.result.property_id || item.result.property_name || item.id),
    ).size,
  };
}

export function buildAnalysisRows(analyses: AnalysisRecord[]): AnalysisTableRow[] {
  return analyses.map(({ id, result }) => {
    const dimensions = result.dimensions || {};
    const [dimension, dimensionValue] = Object.entries(dimensions)[0] || ["Property", result.property_name || result.property_id || id];
    const latest = latestForecastPoint(result.forecast_data);
    const deviation =
      latest && latest.yhat !== 0 ? ((latest.y - latest.yhat) / latest.yhat) * 100 : null;

    return {
      id,
      dimension,
      dimensionValue: String(dimensionValue ?? "-"),
      anomalyCount: countAnomalyPoints(result.forecast_data),
      lastAnomalyDate: lastAnomalyDate(result.forecast_data),
      latestY: latest?.y ?? null,
      latestYhat: latest?.yhat ?? null,
      deviation,
      direction: deviation === null ? "unknown" : deviation > 0 ? "up" : deviation < 0 ? "down" : "flat",
    };
  });
}

export function chooseFeaturedAnalysis(analyses: AnalysisRecord[]) {
  return analyses.find((item) => item.result.is_anomaly && item.result.forecast_data) || analyses.find((item) => item.result.forecast_data) || null;
}
