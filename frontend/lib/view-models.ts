import { countAnomalyPoints, lastAnomalyDate, latestForecastPoint } from "@/lib/forecast";
import type {
  AnalysisRecord,
  AnalysisTableRow,
  DashboardGroup,
  DashboardSections,
  DiagnosisPage,
  ForecastPoint,
  MainOverview,
  PropertyThemeRow,
  ReportItem,
  ReportsPage,
  SummaryStats,
  ThemeDetectionPage,
  ThemeSummary,
} from "@/lib/types";

export const SUPPORTED_THEMES = ["sessions", "ecommerce"] as const;

export function encodeGroupKey(groupKey: string) {
  return encodeURIComponent(groupKey);
}

export function decodeGroupKey(groupKey: string) {
  return decodeURIComponent(groupKey);
}

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

export function buildMainOverview(items: AnalysisRecord[]): MainOverview {
  const sections = buildDashboardSections(items);
  return {
    stats: buildSummary(sections),
    themeSummaries: buildThemeSummaries(items),
    propertyThemeMatrix: buildPropertyThemeMatrix(items),
  };
}

export function buildThemeSummaries(items: AnalysisRecord[]): ThemeSummary[] {
  return SUPPORTED_THEMES.map((theme) => {
    const themeItems = items.filter((item) => item.result.domain === theme);
    return {
      theme,
      href: `/dashboard/themes/${theme}`,
      totalCount: themeItems.length,
      detectionCount: themeItems.filter((item) => item.result.mode === "detection").length,
      diagnosisCount: themeItems.filter((item) => item.result.mode === "diagnosis").length,
      anomalyCount: themeItems.filter((item) => item.result.has_anomaly).length,
    };
  });
}

export function buildPropertyThemeMatrix(items: AnalysisRecord[]): PropertyThemeRow[] {
  const rows = new Map<string, PropertyThemeRow>();

  for (const item of items) {
    const propertyId = item.result.property_id || item.id;
    const propertyName = item.result.property_name || propertyId;
    if (!rows.has(propertyId)) {
      rows.set(propertyId, {
        propertyId,
        propertyName,
        themes: SUPPORTED_THEMES.map((theme) => ({
          theme,
          status: "missing",
          href: `/dashboard/themes/${theme}`,
        })),
      });
    }

    const row = rows.get(propertyId);
    const cell = row?.themes.find((themeCell) => themeCell.theme === item.result.domain);
    if (cell) {
      cell.status = item.result.has_anomaly ? "anomaly" : cell.status === "anomaly" ? "anomaly" : "normal";
    }
  }

  return Array.from(rows.values()).sort((left, right) =>
    left.propertyName.localeCompare(right.propertyName),
  );
}

export function buildThemeDetectionPage(
  items: AnalysisRecord[],
  theme: string,
): ThemeDetectionPage {
  const detections = getDetectionResults(
    items.filter((item) => item.result.domain === theme && item.result.mode === "detection"),
  );
  const diagnoses = getDiagnosisResults(
    items.filter((item) => item.result.domain === theme && item.result.mode === "diagnosis"),
  );
  const diagnosisGroups = groupDiagnosisByDetection(detections, diagnoses);
  const rows = buildAnalysisRows(detections).map((row) => {
    const group = diagnosisGroups.find((item) => item.groupKey === row.groupKey);
    const hasDiagnosis = Boolean(group?.diagnoses.length);
    return {
      ...row,
      detailHref: hasDiagnosis ? `/dashboard/diagnosis/${encodeGroupKey(row.groupKey)}` : undefined,
      detailLabel: hasDiagnosis ? "원인 분석 보기" : "원인 분석 없음",
      detailDisabled: !hasDiagnosis,
    };
  });

  return {
    theme,
    detections,
    rows,
    featuredDetection: chooseFeaturedAnalysis(detections),
  };
}

export function buildDiagnosisPage(items: AnalysisRecord[], encodedGroupKey: string): DiagnosisPage {
  const groupKey = decodeGroupKey(encodedGroupKey);
  const detections = getDetectionResults(items);
  const diagnoses = getDiagnosisResults(items);
  const group = groupDiagnosisByDetection(detections, diagnoses).find(
    (item) => item.groupKey === groupKey,
  );
  const groupDiagnoses = group?.diagnoses ?? diagnoses.filter((item) => getGroupKey(item) === groupKey);

  return {
    groupKey,
    detection: group?.detection ?? null,
    diagnoses: groupDiagnoses,
    rows: buildAnalysisRows(groupDiagnoses),
    featuredDiagnosis: chooseFeaturedAnalysis(groupDiagnoses),
  };
}

export function buildReportsPage(items: AnalysisRecord[]): ReportsPage {
  const sections = buildDashboardSections(items);
  const groups = groupDiagnosisByDetection(sections.detections, sections.diagnoses);
  const anomalousRows = buildAnalysisRows(items.filter((item) => item.result.has_anomaly));
  const reports = anomalousRows.map((row): ReportItem => {
    const group = groups.find((item) => item.groupKey === row.groupKey);
    const diagnosisCandidates = buildAnalysisRows(group?.diagnoses ?? []).slice(0, 3);
    return {
      ...row,
      theme: row.domain,
      detectionHref: `/dashboard/themes/${row.domain}`,
      diagnosisHref: diagnosisCandidates.length ? `/dashboard/diagnosis/${encodeGroupKey(row.groupKey)}` : undefined,
      diagnosisCandidates,
    };
  });

  const propertyReports = Array.from(groupBy(reports, (item) => item.propertyName).entries())
    .map(([propertyName, propertyItems]) => ({
      propertyId: propertyItems[0]?.id ?? propertyName,
      propertyName,
      reports: propertyItems,
    }))
    .sort((left, right) => left.propertyName.localeCompare(right.propertyName));

  const themeReports = SUPPORTED_THEMES.map((theme) => ({
    theme,
    reports: reports.filter((item) => item.theme === theme),
  }));

  return { propertyReports, themeReports };
}

export function buildSummary(sections: DashboardSections): SummaryStats {
  const anomalousItems = sections.all.filter((item) => item.result.has_anomaly);
  const latestAnomalyDate = anomalousItems
    .map((item) => lastAnomalyDate(item.result.forecast_data))
    .filter((date) => date !== "-")
    .sort()
    .at(-1) ?? "-";

  return {
    totalAnalyses: sections.all.length,
    anomalousPropertyCount: new Set(
      anomalousItems.map((item) => item.result.property_id || item.result.property_name || item.id),
    ).size,
    anomalousThemeCount: new Set(anomalousItems.map((item) => item.result.domain)).size,
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
      hasAnomaly: result.has_anomaly,
      domain: result.domain || "-",
      mode: result.mode || "-",
      metricName: result.metric_name || "-",
      dimension: result.dimension ?? "-",
      dimensionValue: result.dimension_value ?? "-",
      anomalyCount: countAnomalyPoints(result.forecast_data),
      lastAnomalyDate: lastAnomalyDate(result.forecast_data),
      latestY: latest?.y ?? null,
      latestYhat: latest?.yhat ?? null,
      latestLower: latest?.yhat_lower ?? null,
      latestUpper: latest?.yhat_upper ?? null,
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

function groupBy<T>(items: T[], getKey: (item: T) => string) {
  return items.reduce((map, item) => {
    const key = getKey(item);
    map.set(key, [...(map.get(key) ?? []), item]);
    return map;
  }, new Map<string, T[]>());
}
