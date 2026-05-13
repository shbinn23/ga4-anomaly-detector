import { countAnomalyPoints, lastAnomalyDate, latestForecastPoint } from "@/lib/forecast";
import type {
  AnalysisRecord,
  AnalysisTableRow,
  DashboardGroup,
  DashboardSections,
  ForecastPoint,
  SummaryStats,
} from "@/lib/types";

export function getDetectionResults(items: AnalysisRecord[]): AnalysisRecord[] {
  return sortOperationalResults(items.filter((item) => item.result.mode === "detection"));
}

export function getDiagnosisResults(items: AnalysisRecord[]): AnalysisRecord[] {
  return sortOperationalResults(items.filter((item) => item.result.mode === "diagnosis"));
}

export function groupDiagnosisByDetection(
  detections: AnalysisRecord[],
  diagnoses: AnalysisRecord[],
): DashboardGroup[] {
  const groups = new Map<string, DashboardGroup>();

  for (const detection of detections) {
    const groupKey = getGroupKey(detection);
    groups.set(groupKey, { groupKey, detection, diagnoses: [] });
  }

  for (const diagnosis of diagnoses) {
    const groupKey = getGroupKey(diagnosis);
    const group = groups.get(groupKey) ?? { groupKey, detection: null, diagnoses: [] };
    group.diagnoses.push(diagnosis);
    groups.set(groupKey, group);
  }

  return Array.from(groups.values());
}

export function buildDashboardSections(items: AnalysisRecord[]): DashboardSections {
  const detections = getDetectionResults(items);
  const diagnoses = getDiagnosisResults(items);
  const groups = groupDiagnosisByDetection(detections, diagnoses);

  return {
    all: items,
    detections,
    diagnoses,
    groups,
    featuredDetection: chooseFeaturedAnalysis(detections),
    featuredDiagnosis: chooseFeaturedAnalysis(diagnoses),
  };
}

export function buildSummary(sections: DashboardSections): SummaryStats {
  const latestAnomalyDate = sections.all
    .filter((item) => item.result.has_anomaly)
    .map((item) => lastAnomalyDate(item.result.forecast_data))
    .filter((date) => date !== "-")
    .filter((date): date is string => Boolean(date))
    .sort()
    .at(-1) ?? "-";

  return {
    totalAnalyses: sections.all.length,
    detectionAnomalyCount: sections.detections.filter((item) => item.result.has_anomaly).length,
    diagnosisAnomalyCount: sections.diagnoses.filter((item) => item.result.has_anomaly).length,
    latestAnomalyDate,
  };
}

export function buildAnalysisRows(analyses: AnalysisRecord[]): AnalysisTableRow[] {
  return analyses.map(({ id, result }) => {
    const latest = getLatestPoint({ id, result });
    const deviation = calculateDeviation(latest);

    return {
      id,
      groupKey: getGroupKey({ id, result }),
      propertyName: result.property_name || result.property_id || "-",
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

export const buildSummaryStats = buildSummary;

function sortOperationalResults(items: AnalysisRecord[]) {
  return [...items].sort((left, right) => {
    const leftRow = sortableFields(left);
    const rightRow = sortableFields(right);

    return (
      Number(right.result.has_anomaly) - Number(left.result.has_anomaly) ||
      rightRow.anomalyCount - leftRow.anomalyCount ||
      rightRow.lastAnomalyDate.localeCompare(leftRow.lastAnomalyDate) ||
      Math.abs(rightRow.deviation ?? 0) - Math.abs(leftRow.deviation ?? 0)
    );
  });
}

function sortableFields(item: AnalysisRecord) {
  return {
    anomalyCount: countAnomalyPoints(item.result.forecast_data),
    lastAnomalyDate: lastAnomalyDate(item.result.forecast_data),
    deviation: calculateDeviation(getLatestPoint(item)),
  };
}

function getLatestPoint(item: AnalysisRecord): ForecastPoint | null {
  return item.result.latest_point ?? latestForecastPoint(item.result.forecast_data);
}

function calculateDeviation(point: ForecastPoint | null) {
  return point && point.yhat !== 0 ? ((point.y - point.yhat) / point.yhat) * 100 : null;
}

function getGroupKey(item: AnalysisRecord) {
  return item.result.group_key || [
    item.result.property_id || item.id,
    item.result.domain,
    item.result.metric_name,
    item.result.latest_point?.ds || item.result.target_date || "",
  ].join(":");
}
