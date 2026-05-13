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
  SessionsTrending,
  SessionsTrendingItem,
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
  };
}

export function buildMainOverview(items: AnalysisRecord[]): MainOverview {
  const sections = buildDashboardSections(items);
  return {
    stats: buildSummary(sections),
    themeSummaries: buildThemeSummaries(items),
    propertyThemeMatrix: buildPropertyThemeMatrix(items),
    sessionsTrending: buildSessionsTrending(items),
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
      anomalyCount: themeItems.filter((item) => item.result.alert_status === "alert").length,
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
          label: "데이터 없음",
          breachRate: null,
          direction: "unknown",
          actual: null,
          lower: null,
          upper: null,
        })),
        alertThemeCount: 0,
        maxBreachRate: 0,
      });
    }

    const row = rows.get(propertyId);
    const cell = row?.themes.find((themeCell) => themeCell.theme === item.result.domain);
    const candidate = buildHealthCell(item);
    if (cell && candidate && healthRank(candidate.status) >= healthRank(cell.status)) {
      Object.assign(cell, candidate);
    }
  }

  return Array.from(rows.values())
    .map((row) => ({
      ...row,
      alertThemeCount: row.themes.filter((theme) => theme.status === "anomaly").length,
      maxBreachRate: Math.max(0, ...row.themes.map((theme) => theme.breachRate ?? 0)),
    }))
    .sort((left, right) =>
      right.alertThemeCount - left.alertThemeCount ||
      right.maxBreachRate - left.maxBreachRate ||
      left.propertyName.localeCompare(right.propertyName),
    );
}

export function buildSessionsTrending(items: AnalysisRecord[]): SessionsTrending {
  const trendingItems = items
    .filter((item) =>
      item.result.domain === "sessions" &&
      item.result.mode === "detection" &&
      item.result.alert_status === "alert",
    )
    .map((item): SessionsTrendingItem | null => {
      const breach = calculateBoundaryBreach(item);
      if (!breach || breach.direction === "flat" || breach.score === null) {
        return null;
      }
      const score = breach.score;

      return {
        id: item.id,
        propertyName: item.result.property_name || item.result.property_id || item.id,
        score,
        actual: breach.actual,
        lower: breach.lower,
        upper: breach.upper,
        direction: breach.direction,
        href: "/dashboard/themes/sessions?tab=chart",
      };
    })
    .filter((item): item is SessionsTrendingItem => Boolean(item));

  const sortByScore = (left: SessionsTrendingItem, right: SessionsTrendingItem) =>
    (right.score ?? 0) - (left.score ?? 0) || left.propertyName.localeCompare(right.propertyName);

  return {
    higher: trendingItems.filter((item) => item.direction === "up").sort(sortByScore).slice(0, 5),
    lower: trendingItems.filter((item) => item.direction === "down").sort(sortByScore).slice(0, 5),
  };
}

export function calculateBoundaryBreach(item: AnalysisRecord) {
  const point = getTargetPoint(item);
  if (!point) {
    return null;
  }

  if (point.y > point.yhat_upper) {
    return {
      direction: "up" as const,
      score: safeBoundaryScore(point.y - point.yhat_upper, point.yhat_upper),
      actual: point.y,
      lower: point.yhat_lower,
      upper: point.yhat_upper,
    };
  }

  if (point.y < point.yhat_lower) {
    return {
      direction: "down" as const,
      score: safeBoundaryScore(point.yhat_lower - point.y, point.yhat_lower),
      actual: point.y,
      lower: point.yhat_lower,
      upper: point.yhat_upper,
    };
  }

  return {
    direction: "flat" as const,
    score: 0,
    actual: point.y,
    lower: point.yhat_lower,
    upper: point.yhat_upper,
  };
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
    chartItems: buildChartItems(detections, rows),
  };
}

export function buildDiagnosisPage(
  items: AnalysisRecord[],
  encodedGroupKey: string,
): DiagnosisPage {
  const groupKey = decodeGroupKey(encodedGroupKey);
  const detections = getDetectionResults(items);
  const diagnoses = getDiagnosisResults(items);
  const group = groupDiagnosisByDetection(detections, diagnoses).find(
    (item) => item.groupKey === groupKey,
  );
  const groupDiagnoses = group?.diagnoses ?? diagnoses.filter((item) => getGroupKey(item) === groupKey);
  const rows = buildAnalysisRows(groupDiagnoses);

  return {
    groupKey,
    detection: group?.detection ?? null,
    diagnoses: groupDiagnoses,
    rows,
    chartItems: buildChartItems(groupDiagnoses, rows),
  };
}

export function buildReportsPage(items: AnalysisRecord[]): ReportsPage {
  const sections = buildDashboardSections(items);
  const groups = groupDiagnosisByDetection(sections.detections, sections.diagnoses);
  const reportDate = getReportDate(items);
  const reportItems = items.filter((item) => {
    const target = getTargetPoint(item);
    return item.result.mode === "detection" && target?.ds === reportDate && item.result.is_current_anomaly;
  });
  const reports = buildAnalysisRows(reportItems).map((row): ReportItem => {
    const group = groups.find((item) => item.groupKey === row.groupKey);
    const diagnosisCandidates = buildAnalysisRows(
      (group?.diagnoses ?? []).filter((item) => {
        const target = getTargetPoint(item);
        return target?.ds === reportDate && item.result.is_current_anomaly;
      }),
    ).slice(0, 3);
    return {
      ...row,
      theme: row.domain,
      themeLabel: themeLabel(row.domain),
      reportDate,
      headline: buildReportHeadline(row),
      body: buildReportBody(row, reportDate),
      sentence: buildReportBody(row, reportDate),
      diagnosisSentence: buildDiagnosisSentence(diagnosisCandidates),
      absoluteDeviation:
        row.latestY !== null && row.latestYhat !== null ? row.latestY - row.latestYhat : null,
      breachRate: calculateBreachRate(row),
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

  return { reportDate, summaryReports: buildPropertySummaryReports(reports, reportDate), propertyReports, themeReports };
}

export function buildSummary(sections: DashboardSections): SummaryStats {
  const anomalousItems = sections.all.filter((item) => item.result.alert_status === "alert");
  const latestAnomalyDate = anomalousItems
    .map((item) => getTargetPoint(item)?.ds ?? "-")
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
    const target = getTargetPoint({ id, result });
    const deviation = calculateDeviation(target);

    return {
      id,
      groupKey: getGroupKey({ id, result }),
      propertyName: result.property_name || result.property_id || "-",
      hasAnomaly: result.has_anomaly,
      isCurrentAnomaly: result.is_current_anomaly,
      alertStatus: result.alert_status,
      domain: result.domain || "-",
      mode: result.mode || "-",
      metricName: result.metric_name || "-",
      dimension: result.dimension ?? "-",
      dimensionValue: result.dimension_value ?? "-",
      anomalyCount: countAnomalyPoints(result.forecast_data),
      recentAnomalyCount: result.recent_anomaly_count,
      lastAnomalyDate: lastAnomalyDate(result.forecast_data),
      latestY: target?.y ?? null,
      latestYhat: target?.yhat ?? null,
      latestLower: target?.yhat_lower ?? null,
      latestUpper: target?.yhat_upper ?? null,
      latestDeviation: deviation,
      direction: deviation === null ? "unknown" : deviation > 0 ? "up" : deviation < 0 ? "down" : "flat",
    };
  });
}

export const buildSummaryStats = buildSummary;

function buildChartItems(analyses: AnalysisRecord[], rows: AnalysisTableRow[]) {
  const analysesById = new Map(analyses.map((item) => [item.id, item]));
  return rows
    .filter((row) => row.alertStatus === "alert")
    .map((row) => {
      const analysis = analysesById.get(row.id);
      return analysis ? { analysis, row } : null;
    })
    .filter((item): item is NonNullable<typeof item> => Boolean(item));
}

function sortOperationalResults(items: AnalysisRecord[]) {
  return [...items].sort((left, right) => {
    const leftRow = sortableFields(left);
    const rightRow = sortableFields(right);

    return (
      alertRank(right.result.alert_status) - alertRank(left.result.alert_status) ||
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
    deviation: calculateDeviation(getTargetPoint(item)),
  };
}

function alertRank(status: AnalysisRecord["result"]["alert_status"]) {
  return status === "alert" ? 2 : status === "watch" ? 1 : 0;
}

function healthRank(status: PropertyThemeRow["themes"][number]["status"]) {
  return status === "anomaly" ? 3 : status === "watch" ? 2 : status === "normal" ? 1 : 0;
}

function buildHealthCell(item: AnalysisRecord): PropertyThemeRow["themes"][number] | null {
  if (item.result.mode !== "detection") {
    return null;
  }

  const breach = calculateBoundaryBreach(item);
  const status = item.result.alert_status === "alert"
    ? "anomaly"
    : item.result.alert_status === "watch"
      ? "watch"
      : "normal";
  const direction = breach?.direction ?? "unknown";
  const breachRate = breach?.score === null || breach?.score === undefined ? null : breach.score * 100;

  return {
    theme: item.result.domain,
    status,
    href: `/dashboard/themes/${item.result.domain}`,
    label: healthCellLabel(status, direction, breachRate),
    breachRate,
    direction,
    actual: breach?.actual ?? null,
    lower: breach?.lower ?? null,
    upper: breach?.upper ?? null,
  };
}

function healthCellLabel(
  status: PropertyThemeRow["themes"][number]["status"],
  direction: PropertyThemeRow["themes"][number]["direction"],
  breachRate: number | null,
) {
  if (status === "missing") return "데이터 없음";
  if (status === "watch") return "관찰 필요";
  if (status === "normal") return "예상 범위 내";

  const rate = breachRate === null ? "" : ` ${formatSignedPercent(direction === "down" ? -breachRate : breachRate)}`;
  return direction === "down" ? `예상 범위 하회${rate}` : `예상 범위 상회${rate}`;
}

function formatSignedPercent(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function safeBoundaryScore(diff: number, boundary: number) {
  if (!Number.isFinite(diff) || !Number.isFinite(boundary) || boundary === 0) {
    return null;
  }
  return diff / Math.abs(boundary);
}

function getTargetPoint(item: AnalysisRecord): ForecastPoint | null {
  return item.result.target_point ?? item.result.latest_point ?? latestForecastPoint(item.result.forecast_data);
}

function calculateDeviation(point: ForecastPoint | null) {
  return point && point.yhat !== 0 ? ((point.y - point.yhat) / point.yhat) * 100 : null;
}

function getReportDate(items: AnalysisRecord[]) {
  return items
    .map((item) => getTargetPoint(item)?.ds)
    .filter((date): date is string => Boolean(date))
    .sort()
    .at(-1) ?? "-";
}

function buildReportSentence(row: AnalysisTableRow, reportDate: string) {
  return buildReportBody(row, reportDate);
}

function buildPropertySummaryReports(reports: ReportItem[], reportDate: string) {
  return Array.from(groupBy(reports, (item) => item.propertyName).entries())
    .map(([propertyName, propertyItems]) => {
      const sortedItems = [...propertyItems].sort((left, right) =>
        themeLabel(left.theme).localeCompare(themeLabel(right.theme)),
      );
      const diagnosisCandidates = uniqueCandidates(
        sortedItems.flatMap((item) => item.diagnosisCandidates),
      );

      return {
        propertyName,
        reportDate,
        themeLabels: sortedItems.map((item) => item.themeLabel),
        headline: buildPropertySummaryHeadline(propertyName, reportDate, sortedItems),
        themeSummaries: sortedItems.map((item) => ({
          theme: item.theme,
          themeLabel: item.themeLabel,
          metricName: item.metricName,
          directionLabel: item.direction === "down" ? "예측 범위 하단을 하회했습니다" : "예측 범위 상단을 초과했습니다",
          breachRate: item.breachRate,
          detectionHref: item.detectionHref,
          diagnosisHref: item.diagnosisHref,
        })),
        diagnosisCandidates,
      };
    })
    .sort((left, right) =>
      right.themeSummaries.length - left.themeSummaries.length ||
      maxBreachRate(right.themeSummaries) - maxBreachRate(left.themeSummaries) ||
      left.propertyName.localeCompare(right.propertyName),
    );
}

function buildPropertySummaryHeadline(propertyName: string, reportDate: string, reports: ReportItem[]) {
  const labels = reports.map((item) => item.themeLabel);
  const themeText = labels.length > 1
    ? `${labels.slice(0, -1).join(", ")}과 ${labels.at(-1)}`
    : labels[0] ?? "주요";

  return `${propertyName}에서는 ${reportDate} 기준 ${themeText} 지표에서 이상 신호가 확인되었습니다.`;
}

function uniqueCandidates(candidates: AnalysisTableRow[]) {
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    const key = `${candidate.groupKey}:${candidate.dimension}:${candidate.dimensionValue}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function maxBreachRate(items: Array<{ breachRate: number | null }>) {
  return Math.max(0, ...items.map((item) => item.breachRate ?? 0));
}

function buildReportHeadline(row: AnalysisTableRow) {
  const directionText = row.direction === "down"
    ? "예상 범위보다 낮게 관측되었습니다."
    : "예상 범위보다 높게 관측되었습니다.";

  return `${row.propertyName}의 ${themeLabel(row.domain)} 지표가 ${directionText}`;
}

function buildReportBody(row: AnalysisTableRow, reportDate: string) {
  const actual = formatReportNumber(row.latestY);
  const lower = formatReportNumber(row.latestLower);
  const upper = formatReportNumber(row.latestUpper);
  const breachRate = calculateBreachRate(row);

  if (row.direction === "down") {
    const breachText = breachRate === null
      ? "하단을 하회했습니다."
      : `하단을 약 ${breachRate.toFixed(1)}% 하회했습니다.`;
    return `${reportDate} 기준 ${row.propertyName} 프로퍼티의 ${row.metricName}는 ${actual}로, 예측 범위 ${lower} ~ ${upper}의 ${breachText}`;
  }

  const breachText = breachRate === null
    ? "상단을 초과했습니다."
    : `상단을 약 ${breachRate.toFixed(1)}% 초과했습니다.`;
  return `${reportDate} 기준 ${row.propertyName} 프로퍼티의 ${row.metricName}는 ${actual}로, 예측 범위 ${lower} ~ ${upper}의 ${breachText}`;
}

function buildDiagnosisSentence(candidates: AnalysisTableRow[]) {
  if (!candidates.length) {
    return "현재 연결된 세부 진단 결과는 없습니다.";
  }

  const candidateNames = candidates.map((item) => item.dimensionValue).join(", ");
  return `세부 진단에서는 ${candidateNames}에서 같은 날짜에 이상 신호가 함께 확인되었습니다.`;
}

function calculateBreachRate(row: AnalysisTableRow) {
  if (row.latestY === null) return null;
  if (row.latestYhat === 0) return null;

  if (row.direction === "down") {
    if (!row.latestLower) return null;
    return ((row.latestLower - row.latestY) / Math.abs(row.latestLower)) * 100;
  }

  if (!row.latestUpper) return null;
  return ((row.latestY - row.latestUpper) / Math.abs(row.latestUpper)) * 100;
}

function formatReportNumber(value: number | null) {
  return value === null ? "-" : new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 }).format(value);
}

function themeLabel(theme: string) {
  return theme === "sessions" ? "세션" : theme === "ecommerce" ? "이커머스 이벤트" : theme;
}

function getGroupKey(item: AnalysisRecord) {
  return item.result.group_key || [
    item.result.property_id || item.id,
    item.result.domain,
    item.result.metric_name,
    item.result.target_point?.ds || item.result.target_date || item.result.latest_point?.ds || "",
  ].join(":");
}

function groupBy<T>(items: T[], getKey: (item: T) => string) {
  return items.reduce((map, item) => {
    const key = getKey(item);
    map.set(key, [...(map.get(key) ?? []), item]);
    return map;
  }, new Map<string, T[]>());
}
