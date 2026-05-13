import { countAnomalyPoints, lastAnomalyDate, latestForecastPoint } from "@/lib/forecast";
import type { AnalysisRecord, AnalysisTableRow, SummaryStats } from "@/lib/types";

export function buildSummaryStats(analyses: AnalysisRecord[]): SummaryStats {
  const anomalous = analyses.filter((item) => item.result.has_anomaly);
  const latestResultDate = analyses
    .map((item) => item.result.latest_point?.ds || item.result.target_date)
    .filter((date): date is string => Boolean(date))
    .sort()
    .at(-1) ?? "-";

  return {
    totalAnalyses: analyses.length,
    anomalyCount: anomalous.length,
    latestResultDate,
    affectedSegments: new Set(
      anomalous.map((item) => item.result.property_id || item.result.property_name || item.id),
    ).size,
  };
}

export function buildAnalysisRows(analyses: AnalysisRecord[]): AnalysisTableRow[] {
  return analyses.map(({ id, result }) => {
    const latest = result.latest_point ?? latestForecastPoint(result.forecast_data);
    const deviation =
      latest && latest.yhat !== 0 ? ((latest.y - latest.yhat) / latest.yhat) * 100 : null;

    return {
      id,
      domain: result.domain || "-",
      mode: result.mode || "-",
      metricName: result.metric_name || "-",
      dimension: result.dimension ?? "-",
      dimensionValue: result.dimension_value ?? "-",
      anomalyCount: countAnomalyPoints(result.forecast_data),
      lastAnomalyDate: lastAnomalyDate(result.forecast_data),
      latestY: latest?.y ?? null,
      latestYhat: latest?.yhat ?? null,
      latestDeviation: deviation,
      direction: deviation === null ? "unknown" : deviation > 0 ? "up" : deviation < 0 ? "down" : "flat",
    };
  });
}

export function chooseFeaturedAnalysis(analyses: AnalysisRecord[]) {
  return analyses.find((item) => item.result.has_anomaly && item.result.forecast_data) || analyses.find((item) => item.result.forecast_data) || null;
}
