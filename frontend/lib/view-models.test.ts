import { describe, expect, it } from "vitest";

import type { AnalysisRecord, ForecastData } from "./types";
import {
  buildAnalysisRows,
  buildDiagnosisPage,
  buildMainOverview,
  buildPropertyThemeMatrix,
  buildReportsPage,
  buildSessionsTrending,
  buildThemeDetectionPage,
  calculateBoundaryBreach,
  decodeGroupKey,
  encodeGroupKey,
  getThemeDefinition,
  getDetectionResults,
  getDiagnosisResults,
  groupDiagnosisByDetection,
  isSupportedTheme,
} from "./view-models";

const forecast = (
  y: number,
  yhat: number,
  anomalyCount = 1,
  lastDate = "2026-05-02",
): ForecastData => ({
  ds: ["2026-05-01", lastDate],
  y: [100, y],
  yhat: [100, yhat],
  yhat_lower: [80, yhat - 10],
  yhat_upper: [120, yhat + 10],
  is_anomaly: [anomalyCount > 1, anomalyCount > 0],
});

const record = (overrides: Partial<AnalysisRecord["result"]> & { id: string }): AnalysisRecord => {
  const itemForecast = overrides.forecast_data ?? forecast(150, 100);
  const latestPoint = overrides.latest_point ?? {
    ds: itemForecast.ds.at(-1) ?? "2026-05-02",
    y: itemForecast.y.at(-1) ?? 0,
    yhat: itemForecast.yhat.at(-1) ?? 0,
    yhat_lower: itemForecast.yhat_lower.at(-1) ?? 0,
    yhat_upper: itemForecast.yhat_upper.at(-1) ?? 0,
    is_anomaly: itemForecast.is_anomaly.at(-1) ?? false,
  };

  return {
    id: overrides.id,
    result: {
      id: overrides.id,
      source: "generic_analysis_db",
      group_key: overrides.group_key,
      analysis_id: overrides.analysis_id ?? overrides.id,
      domain: overrides.domain ?? "ecommerce",
      mode: overrides.mode ?? "diagnosis",
      property_id: overrides.property_id ?? "prop-1",
      property_name: overrides.property_name ?? "Store",
      theme_id: overrides.theme_id,
      metric_name: overrides.metric_name ?? "eventCount",
      metric_type: overrides.metric_type,
      dimension: overrides.dimension ?? "eventName",
      dimension_value: overrides.dimension_value ?? "purchase",
      dimensions: overrides.dimensions ?? {},
      has_anomaly: overrides.has_anomaly ?? true,
      is_anomaly: overrides.is_anomaly ?? true,
      actual_value: overrides.actual_value ?? latestPoint.y,
      lower_bound: overrides.lower_bound ?? latestPoint.yhat_lower,
      upper_bound: overrides.upper_bound ?? latestPoint.yhat_upper,
      target_date: overrides.target_date ?? latestPoint.ds,
      target_point: overrides.target_point ?? latestPoint,
      is_current_anomaly: overrides.is_current_anomaly ?? latestPoint.is_anomaly,
      alert_status: overrides.alert_status ?? (latestPoint.is_anomaly ? "alert" : "normal"),
      historical_anomaly_count: overrides.historical_anomaly_count ?? itemForecast.is_anomaly.filter(Boolean).length,
      recent_anomaly_count: overrides.recent_anomaly_count ?? itemForecast.is_anomaly.slice(-7).filter(Boolean).length,
      latest_point: latestPoint,
      forecast_data: itemForecast,
    },
  };
};

describe("dashboard view models", () => {
  it("separates mode=detection items into Step 1", () => {
    const detection = record({ id: "detection", mode: "detection", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis" });

    expect(getDetectionResults([diagnosis, detection]).map((item) => item.id)).toEqual(["detection"]);
  });

  it("separates mode=diagnosis items into Step 2", () => {
    const detection = record({ id: "detection", mode: "detection", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis" });

    expect(getDiagnosisResults([diagnosis, detection]).map((item) => item.id)).toEqual(["diagnosis"]);
  });

  it("includes anomalous detection and diagnosis items in section summaries", () => {
    const detection = record({ id: "detection", mode: "detection", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis" });
    const overview = buildMainOverview([diagnosis, detection]);

    expect(overview.stats).toEqual({
      totalAnalyses: 2,
      anomalousPropertyCount: 1,
      anomalousThemeCount: 1,
      latestAnomalyDate: "2026-05-02",
    });
    expect(overview.themeSummaries.find((item) => item.theme === "ecommerce")?.anomalyCount).toBe(2);
  });

  it("builds summary from alert_status instead of historical has_anomaly", () => {
    const historicalOnly = record({
      id: "historical",
      has_anomaly: true,
      is_current_anomaly: false,
      alert_status: "normal",
      forecast_data: forecast(100, 100, 1),
      latest_point: {
        ds: "2026-05-02",
        y: 100,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: false,
      },
    });
    const currentAlert = record({ id: "alert", property_id: "prop-2", property_name: "Store 2" });

    const overview = buildMainOverview([historicalOnly, currentAlert]);

    expect(overview.stats.anomalousPropertyCount).toBe(1);
    expect(overview.themeSummaries.find((item) => item.theme === "ecommerce")?.anomalyCount).toBe(1);
  });

  it("links detection and diagnosis by group_key", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "group-1", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis", group_key: "group-1" });

    expect(groupDiagnosisByDetection([detection], [diagnosis])).toEqual([
      { groupKey: "group-1", detection, diagnoses: [diagnosis] },
    ]);
  });

  it("creates fallback group data when group_key is absent", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: undefined, dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis", group_key: undefined });

    const groups = groupDiagnosisByDetection([detection], [diagnosis]);

    expect(groups).toHaveLength(1);
    expect(groups[0].detection?.id).toBe("detection");
    expect(groups[0].diagnoses.map((item) => item.id)).toEqual(["diagnosis"]);
  });

  it("sorts detection and diagnosis by anomaly, count, date, and absolute deviation", () => {
    const low = record({ id: "low", mode: "detection", has_anomaly: false, forecast_data: forecast(105, 100, 0), dimension: null, dimension_value: null });
    const old = record({ id: "old", mode: "detection", forecast_data: forecast(130, 100, 1, "2026-05-01"), dimension: null, dimension_value: null });
    const high = record({ id: "high", mode: "detection", forecast_data: forecast(180, 100, 2), dimension: null, dimension_value: null });

    expect(getDetectionResults([low, old, high]).map((item) => item.id)).toEqual(["high", "old", "low"]);
    expect(getDiagnosisResults([
      record({ id: "diag-low", mode: "diagnosis", has_anomaly: false, forecast_data: forecast(105, 100, 0) }),
      record({ id: "diag-high", mode: "diagnosis", forecast_data: forecast(180, 100, 2) }),
    ]).map((item) => item.id)).toEqual(["diag-high", "diag-low"]);
  });

  it("uses latest_point for deviation and direction", () => {
    const rows = buildAnalysisRows([
      record({
        id: "diagnosis",
        latest_point: {
          ds: "2026-05-02",
          y: 180,
          yhat: 120,
          yhat_lower: 90,
          yhat_upper: 130,
          is_anomaly: true,
        },
      }),
    ]);

    expect(rows[0]).toMatchObject({
      hasAnomaly: true,
      latestY: 180,
      latestYhat: 120,
      latestDeviation: 50,
      direction: "up",
      dimension: "eventName",
      dimensionValue: "purchase",
    });
  });

  it("builds main summary, theme cards, and property-theme matrix", () => {
    const overview = buildMainOverview([
      record({ id: "sessions-detection", domain: "sessions", mode: "detection", property_id: "p1", property_name: "Property 1", dimension: null, dimension_value: null }),
      record({ id: "ecommerce-detection", domain: "ecommerce", mode: "detection", property_id: "p1", property_name: "Property 1", dimension: null, dimension_value: null, has_anomaly: false, forecast_data: forecast(100, 100, 0) }),
    ]);

    expect(overview.stats.totalAnalyses).toBe(2);
    expect(overview.themeSummaries.map((item) => item.theme)).toEqual(["sessions", "ecommerce", "unassigned-traffic"]);
    expect(overview.propertyThemeMatrix[0]).toMatchObject({
      propertyName: "Property 1",
      themes: [
        { theme: "sessions", status: "anomaly" },
        { theme: "ecommerce", status: "normal" },
        { theme: "unassigned-traffic", status: "missing" },
      ],
    });
  });

  it("adds Unassigned Traffic to the theme registry and route support", () => {
    expect(isSupportedTheme("unassigned-traffic")).toBe(true);
    expect(getThemeDefinition("unassigned-traffic")).toMatchObject({
      slug: "unassigned-traffic",
      themeId: "unassigned_traffic",
      domain: "traffic_quality",
      label: "Unassigned Traffic",
    });
  });

  it("adds Unassigned Traffic to theme summaries and health matrix as percentage", () => {
    const overview = buildMainOverview([
      record({
        id: "unassigned-detection",
        domain: "traffic_quality",
        theme_id: "unassigned_traffic",
        mode: "detection",
        metric_name: "unassigned_session_share",
        metric_type: "derived_ratio",
        property_id: "p1",
        property_name: "Property 1",
        dimension: null,
        dimension_value: null,
        latest_point: {
          ds: "2026-05-02",
          y: 0.25,
          yhat: 0.1,
          yhat_lower: 0.05,
          yhat_upper: 0.12,
          is_anomaly: true,
        },
        forecast_data: {
          ds: ["2026-05-01", "2026-05-02"],
          y: [0.1, 0.25],
          yhat: [0.1, 0.1],
          yhat_lower: [0.05, 0.05],
          yhat_upper: [0.12, 0.12],
          is_anomaly: [false, true],
        },
      }),
    ]);

    expect(overview.themeSummaries.find((item) => item.theme === "unassigned-traffic")).toMatchObject({
      label: "Unassigned Traffic",
      href: "/dashboard/themes/unassigned-traffic",
      anomalyCount: 1,
    });
    expect(overview.propertyThemeMatrix[0].themes.find((item) => item.theme === "unassigned-traffic")).toMatchObject({
      status: "anomaly",
      valueFormat: "percentage",
      actual: 0.25,
    });
  });

  it("builds sessions trending from sessions detection alerts only", () => {
    const sessionsAlert = record({
      id: "sessions-alert",
      domain: "sessions",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: { ds: "2026-05-02", y: 150, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: true },
    });
    const ecommerceAlert = record({
      id: "ecommerce-alert",
      domain: "ecommerce",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: { ds: "2026-05-02", y: 170, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: true },
    });
    const sessionsDiagnosis = record({
      id: "sessions-diagnosis",
      domain: "sessions",
      mode: "diagnosis",
      latest_point: { ds: "2026-05-02", y: 170, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: true },
    });

    expect(buildSessionsTrending([ecommerceAlert, sessionsDiagnosis, sessionsAlert]).higher.map((item) => item.id)).toEqual(["sessions-alert"]);
  });

  it("sorts sessions higher trending by upper breach top five", () => {
    const items = [1, 5, 3, 8, 2, 13].map((score) =>
      record({
        id: `up-${score}`,
        domain: "sessions",
        mode: "detection",
        property_name: `Property ${score}`,
        dimension: null,
        dimension_value: null,
        latest_point: { ds: "2026-05-02", y: 100 + score, yhat: 80, yhat_lower: 70, yhat_upper: 100, is_anomaly: true },
      }),
    );

    expect(buildSessionsTrending(items).higher.map((item) => item.id)).toEqual(["up-13", "up-8", "up-5", "up-3", "up-2"]);
  });

  it("sorts sessions lower trending by lower breach top five", () => {
    const items = [1, 7, 2, 10, 4, 12].map((score) =>
      record({
        id: `down-${score}`,
        domain: "sessions",
        mode: "detection",
        property_name: `Property ${score}`,
        dimension: null,
        dimension_value: null,
        latest_point: { ds: "2026-05-02", y: 100 - score, yhat: 120, yhat_lower: 100, yhat_upper: 140, is_anomaly: true },
      }),
    );

    expect(buildSessionsTrending(items).lower.map((item) => item.id)).toEqual(["down-12", "down-10", "down-7", "down-4", "down-2"]);
  });

  it("excludes normal, watch, and historical-only items from sessions trending", () => {
    const normal = record({
      id: "normal",
      domain: "sessions",
      mode: "detection",
      alert_status: "normal",
      is_current_anomaly: false,
      has_anomaly: true,
      dimension: null,
      dimension_value: null,
      latest_point: { ds: "2026-05-02", y: 100, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: false },
    });
    const watch = record({
      id: "watch",
      domain: "sessions",
      mode: "detection",
      alert_status: "watch",
      is_current_anomaly: false,
      dimension: null,
      dimension_value: null,
      latest_point: { ds: "2026-05-02", y: 110, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: false },
    });

    expect(buildSessionsTrending([normal, watch])).toEqual({ higher: [], lower: [] });
  });

  it("handles zero boundary percentage safely", () => {
    const zeroBoundary = record({
      id: "zero",
      domain: "sessions",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: { ds: "2026-05-02", y: 20, yhat: 0, yhat_lower: 0, yhat_upper: 0, is_anomaly: true },
    });

    expect(calculateBoundaryBreach(zeroBoundary)?.score).toBeNull();
    expect(buildSessionsTrending([zeroBoundary])).toEqual({ higher: [], lower: [] });
  });

  it("groups property health matrix by property and theme status", () => {
    const matrix = buildPropertyThemeMatrix([
      record({ id: "sessions", domain: "sessions", mode: "detection", property_id: "p1", property_name: "Property 1", dimension: null, dimension_value: null }),
      record({
        id: "ecommerce",
        domain: "ecommerce",
        mode: "detection",
        property_id: "p1",
        property_name: "Property 1",
        alert_status: "watch",
        is_current_anomaly: false,
        dimension: null,
        dimension_value: null,
        latest_point: { ds: "2026-05-02", y: 100, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: false },
      }),
    ]);

    expect(matrix[0]).toMatchObject({
      propertyName: "Property 1",
      themes: [
        { theme: "sessions", status: "anomaly" },
        { theme: "ecommerce", status: "watch", label: "관찰 필요" },
        { theme: "unassigned-traffic", status: "missing" },
      ],
    });
  });

  it("sorts properties with both sessions and ecommerce alerts first", () => {
    const bothSessions = record({ id: "both-s", domain: "sessions", mode: "detection", property_id: "p1", property_name: "Both", dimension: null, dimension_value: null });
    const bothEcommerce = record({ id: "both-e", domain: "ecommerce", mode: "detection", property_id: "p1", property_name: "Both", dimension: null, dimension_value: null });
    const single = record({
      id: "single",
      domain: "sessions",
      mode: "detection",
      property_id: "p2",
      property_name: "Single",
      dimension: null,
      dimension_value: null,
      latest_point: { ds: "2026-05-02", y: 300, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: true },
    });

    expect(buildPropertyThemeMatrix([single, bothEcommerce, bothSessions]).map((row) => row.propertyName)).toEqual(["Both", "Single"]);
  });

  it("adds upper and lower breach text to alert health cells", () => {
    const matrix = buildPropertyThemeMatrix([
      record({
        id: "up",
        domain: "sessions",
        mode: "detection",
        property_id: "p1",
        property_name: "Property 1",
        dimension: null,
        dimension_value: null,
        latest_point: { ds: "2026-05-02", y: 150, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: true },
      }),
      record({
        id: "down",
        domain: "ecommerce",
        mode: "detection",
        property_id: "p1",
        property_name: "Property 1",
        dimension: null,
        dimension_value: null,
        latest_point: { ds: "2026-05-02", y: 60, yhat: 100, yhat_lower: 80, yhat_upper: 120, is_anomaly: true },
      }),
    ]);

    expect(matrix[0].themes[0].label).toContain("예상 범위 상회");
    expect(matrix[0].themes[1].label).toContain("예상 범위 하회");
    expect(matrix[0].themes[0].breachRate).toBeCloseTo(25);
    expect(matrix[0].themes[1].breachRate).toBeCloseTo(25);
  });

  it("builds theme detection pages for current themes only", () => {
    const items = [
      record({ id: "sessions-detection", domain: "sessions", mode: "detection", dimension: null, dimension_value: null }),
      record({ id: "sessions-diagnosis", domain: "sessions", mode: "diagnosis" }),
      record({ id: "ecommerce-detection", domain: "ecommerce", mode: "detection", dimension: null, dimension_value: null }),
    ];

    expect(buildThemeDetectionPage(items, "sessions").detections.map((item) => item.id)).toEqual(["sessions-detection"]);
    expect(buildThemeDetectionPage(items, "ecommerce").detections.map((item) => item.id)).toEqual(["ecommerce-detection"]);
  });

  it("sorts anomalous detection first and marks diagnosis links", () => {
    const detectionWithDiagnosis = record({ id: "with", mode: "detection", group_key: "group:with", dimension: null, dimension_value: null });
    const detectionWithoutDiagnosis = record({ id: "without", mode: "detection", group_key: "group:without", has_anomaly: false, forecast_data: forecast(100, 100, 0), dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis", group_key: "group:with" });

    const page = buildThemeDetectionPage([detectionWithoutDiagnosis, diagnosis, detectionWithDiagnosis], "ecommerce");

    expect(page.rows.map((row) => row.id)).toEqual(["with", "without"]);
    expect(page.rows[0]).toMatchObject({ detailLabel: "원인 분석 보기", detailDisabled: false });
    expect(page.rows[1]).toMatchObject({ detailLabel: "원인 분석 없음", detailDisabled: true });
  });

  it("builds diagnosis page from encoded groupKey", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "prop:ecommerce:eventCount:2026-05-02", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis", group_key: "prop:ecommerce:eventCount:2026-05-02" });
    const other = record({ id: "other", mode: "diagnosis", group_key: "other" });

    const encoded = encodeGroupKey("prop:ecommerce:eventCount:2026-05-02");
    const page = buildDiagnosisPage([detection, diagnosis, other], encoded);

    expect(decodeGroupKey(encoded)).toBe("prop:ecommerce:eventCount:2026-05-02");
    expect(page.diagnoses.map((item) => item.id)).toEqual(["diagnosis"]);
  });

  it("builds deterministic property reports with detection evidence and diagnosis candidates", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "group-1", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis", group_key: "group-1", dimension_value: "purchase" });

    const first = buildReportsPage([diagnosis, detection]);
    const second = buildReportsPage([diagnosis, detection]);

    expect(first).toEqual(second);
    expect(first.propertyReports[0].reports[0]).toMatchObject({
      detectionHref: "/dashboard/themes/ecommerce",
      diagnosisHref: "/dashboard/diagnosis/group-1",
    });
    expect(first.propertyReports[0].reports[0].diagnosisCandidates[0]).toMatchObject({
      dimensionValue: "purchase",
    });
  });

  it("uses the maximum latest_point date as report_date", () => {
    const oldItem = record({
      id: "old",
      latest_point: {
        ds: "2026-05-01",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });
    const latestItem = record({
      id: "latest",
      latest_point: {
        ds: "2026-05-03",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });

    expect(buildReportsPage([oldItem, latestItem]).reportDate).toBe("2026-05-03");
  });

  it("builds reports only from report_date latest_point anomalies", () => {
    const latestAnomaly = record({
      id: "latest-anomaly",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: {
        ds: "2026-05-03",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });
    const latestNormal = record({
      id: "latest-normal",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: {
        ds: "2026-05-03",
        y: 100,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: false,
      },
    });
    const oldAnomaly = record({
      id: "old-anomaly",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: {
        ds: "2026-05-02",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });

    const reports = buildReportsPage([oldAnomaly, latestNormal, latestAnomaly]);

    expect(reports.propertyReports[0].reports.map((item) => item.id)).toEqual(["latest-anomaly"]);
  });

  it("creates deterministic GA4 operations report sentences for increase and decrease direction", () => {
    const up = record({
      id: "up",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      property_name: "Property Up",
      latest_point: {
        ds: "2026-05-03",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });
    const down = record({
      id: "down",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      property_name: "Property Down",
      latest_point: {
        ds: "2026-05-03",
        y: 60,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });

    const reports = buildReportsPage([up, down]).propertyReports.flatMap((item) =>
      item.reports,
    );
    const headlines = reports.map((report) => report.headline);
    const bodies = reports.map((report) => report.body);

    expect(headlines).toContain("Property Up의 이커머스 이벤트 지표가 예상 범위보다 높게 관측되었습니다.");
    expect(headlines).toContain("Property Down의 이커머스 이벤트 지표가 예상 범위보다 낮게 관측되었습니다.");
    expect(bodies).toContain("2026-05-03 기준 Property Up 프로퍼티의 eventCount는 180로, 예측 범위 80 ~ 120의 상단을 약 50.0% 초과했습니다.");
    expect(bodies).toContain("2026-05-03 기준 Property Down 프로퍼티의 eventCount는 60로, 예측 범위 80 ~ 120의 하단을 약 25.0% 하회했습니다.");
  });

  it("uses absolute deviation wording when yhat is zero", () => {
    const item = record({
      id: "zero-yhat",
      mode: "detection",
      dimension: null,
      dimension_value: null,
      latest_point: {
        ds: "2026-05-03",
        y: 10,
        yhat: 0,
        yhat_lower: 0,
        yhat_upper: 1,
        is_anomaly: true,
      },
    });

    const report = buildReportsPage([item]).propertyReports[0].reports[0];

    expect(report.latestDeviation).toBeNull();
    expect(report.absoluteDeviation).toBe(10);
    expect(report.body).toContain("상단을 초과했습니다.");
  });

  it("links diagnosis top candidates by the same group_key and report_date anomaly", () => {
    const detection = record({
      id: "detection",
      mode: "detection",
      group_key: "group-1",
      dimension: null,
      dimension_value: null,
      latest_point: {
        ds: "2026-05-03",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });
    const candidate = record({
      id: "candidate",
      mode: "diagnosis",
      group_key: "group-1",
      dimension_value: "purchase",
      latest_point: {
        ds: "2026-05-03",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });
    const oldCandidate = record({
      id: "old-candidate",
      mode: "diagnosis",
      group_key: "group-1",
      dimension_value: "old",
      latest_point: {
        ds: "2026-05-02",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });
    const otherGroup = record({
      id: "other-group",
      mode: "diagnosis",
      group_key: "group-2",
      dimension_value: "other",
      latest_point: {
        ds: "2026-05-03",
        y: 180,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: true,
      },
    });

    const report = buildReportsPage([detection, candidate, oldCandidate, otherGroup])
      .propertyReports[0].reports.find((item) => item.id === "detection");

    expect(report?.diagnosisCandidates.map((item) => item.id)).toEqual(["candidate"]);
    expect(report?.diagnosisSentence).toBe("세부 진단에서는 purchase에서 같은 날짜에 이상 신호가 함께 확인되었습니다.");
  });

  it("groups report summary by property detection alerts", () => {
    const sessions = record({
      id: "sessions-alert",
      domain: "sessions",
      mode: "detection",
      property_name: "Store A",
      dimension: null,
      dimension_value: null,
    });
    const ecommerce = record({
      id: "ecommerce-alert",
      domain: "ecommerce",
      mode: "detection",
      property_name: "Store A",
      dimension: null,
      dimension_value: null,
    });

    const page = buildReportsPage([sessions, ecommerce]);

    expect(page.summaryReports).toHaveLength(1);
    expect(page.summaryReports[0]).toMatchObject({
      propertyName: "Store A",
      themeLabels: ["세션", "이커머스 이벤트"],
    });
    expect(page.summaryReports[0].headline).toContain("세션과 이커머스 이벤트 지표에서 이상 신호가 확인되었습니다.");
  });

  it("sorts multi-theme summary reports before single-theme reports", () => {
    const bothSessions = record({
      id: "both-sessions",
      domain: "sessions",
      mode: "detection",
      property_name: "Both",
      dimension: null,
      dimension_value: null,
    });
    const bothEcommerce = record({
      id: "both-ecommerce",
      domain: "ecommerce",
      mode: "detection",
      property_name: "Both",
      dimension: null,
      dimension_value: null,
    });
    const single = record({
      id: "single",
      domain: "sessions",
      mode: "detection",
      property_name: "Single",
      dimension: null,
      dimension_value: null,
    });

    const page = buildReportsPage([single, bothEcommerce, bothSessions]);

    expect(page.summaryReports.map((item) => item.propertyName)).toEqual(["Both", "Single"]);
  });

  it("keeps diagnosis items as summary candidates instead of summary cards", () => {
    const detection = record({
      id: "summary-detection",
      mode: "detection",
      group_key: "summary-group",
      property_name: "Summary Store",
      dimension: null,
      dimension_value: null,
    });
    const diagnosis = record({
      id: "summary-diagnosis",
      mode: "diagnosis",
      group_key: "summary-group",
      property_name: "Summary Store",
      dimension_value: "purchase",
    });

    const page = buildReportsPage([diagnosis, detection]);

    expect(page.summaryReports).toHaveLength(1);
    expect(page.summaryReports[0].diagnosisCandidates.map((item) => item.id)).toEqual(["summary-diagnosis"]);
  });

  it("keeps details report cards as detection alert items", () => {
    const detection = record({
      id: "detail-detection",
      mode: "detection",
      dimension: null,
      dimension_value: null,
    });
    const diagnosis = record({ id: "detail-diagnosis", mode: "diagnosis" });

    const page = buildReportsPage([detection, diagnosis]);

    expect(page.propertyReports.flatMap((item) => item.reports).map((item) => item.id)).toEqual(["detail-detection"]);
  });

  it("includes every alert detection item in the theme chart grid", () => {
    const first = record({ id: "first", domain: "sessions", mode: "detection", forecast_data: forecast(180, 100, 2), dimension: null, dimension_value: null });
    const second = record({ id: "second", domain: "sessions", mode: "detection", forecast_data: forecast(150, 100, 1), dimension: null, dimension_value: null });
    const normal = record({ id: "normal", domain: "sessions", mode: "detection", has_anomaly: false, forecast_data: forecast(100, 100, 0), dimension: null, dimension_value: null });

    const page = buildThemeDetectionPage([normal, second, first], "sessions");

    expect(page.chartItems.map((item) => item.row.id)).toEqual(["first", "second"]);
    expect(page.chartItems.map((item) => item.analysis.id)).toEqual(["first", "second"]);
  });

  it("excludes non-anomalous detection items from the theme chart grid", () => {
    const anomaly = record({ id: "anomaly", domain: "sessions", mode: "detection", dimension: null, dimension_value: null });
    const normal = record({ id: "normal", domain: "sessions", mode: "detection", has_anomaly: false, forecast_data: forecast(100, 100, 0), dimension: null, dimension_value: null });

    const page = buildThemeDetectionPage([normal, anomaly], "sessions");

    expect(page.chartItems.map((item) => item.row.id)).toEqual(["anomaly"]);
  });

  it("excludes historical-only non-alert detection items from the theme chart grid", () => {
    const historicalOnly = record({
      id: "historical",
      domain: "sessions",
      mode: "detection",
      has_anomaly: true,
      is_current_anomaly: false,
      alert_status: "watch",
      forecast_data: forecast(100, 100, 1),
      latest_point: {
        ds: "2026-05-02",
        y: 100,
        yhat: 100,
        yhat_lower: 80,
        yhat_upper: 120,
        is_anomaly: false,
      },
      dimension: null,
      dimension_value: null,
    });
    const alert = record({ id: "alert", domain: "sessions", mode: "detection", dimension: null, dimension_value: null });

    const page = buildThemeDetectionPage([historicalOnly, alert], "sessions");

    expect(page.rows.map((item) => item.id)).toEqual(["alert", "historical"]);
    expect(page.chartItems.map((item) => item.row.id)).toEqual(["alert"]);
  });

  it("uses the same diagnosis destination for theme table rows and chart cards", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "group-1", dimension: null, dimension_value: null });
    const diagnosis = record({ id: "diagnosis", mode: "diagnosis", group_key: "group-1" });

    const page = buildThemeDetectionPage([detection, diagnosis], "ecommerce");

    expect(page.rows[0].detailHref).toBe("/dashboard/diagnosis/group-1");
    expect(page.chartItems[0].row.detailHref).toBe(page.rows[0].detailHref);
  });

  it("marks detection chart cards without diagnosis as disabled", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "group-1", dimension: null, dimension_value: null });

    const page = buildThemeDetectionPage([detection], "ecommerce");

    expect(page.chartItems[0].row).toMatchObject({
      detailHref: undefined,
      detailLabel: "원인 분석 없음",
      detailDisabled: true,
    });
  });

  it("includes every anomalous diagnosis item in the diagnosis chart grid", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "group-1", dimension: null, dimension_value: null });
    const first = record({ id: "first", mode: "diagnosis", group_key: "group-1", dimension_value: "Organic Search", forecast_data: forecast(180, 100, 2) });
    const second = record({ id: "second", mode: "diagnosis", group_key: "group-1", dimension_value: "Paid Search", forecast_data: forecast(150, 100, 1) });
    const normal = record({ id: "normal", mode: "diagnosis", group_key: "group-1", has_anomaly: false, forecast_data: forecast(100, 100, 0) });

    const page = buildDiagnosisPage([detection, normal, second, first], encodeGroupKey("group-1"));

    expect(page.chartItems.map((item) => item.row.id)).toEqual(["first", "second"]);
  });

  it("excludes other groupKey items from the diagnosis chart grid", () => {
    const detection = record({ id: "detection", mode: "detection", group_key: "group-1", dimension: null, dimension_value: null });
    const included = record({ id: "included", mode: "diagnosis", group_key: "group-1" });
    const excluded = record({ id: "excluded", mode: "diagnosis", group_key: "group-2" });

    const page = buildDiagnosisPage([detection, included, excluded], encodeGroupKey("group-1"));

    expect(page.chartItems.map((item) => item.row.id)).toEqual(["included"]);
  });

  it("limits chart items to the current route context anomaly items", () => {
    const sessionsDetection = record({ id: "sessions-detection", domain: "sessions", mode: "detection", dimension: null, dimension_value: null });
    const ecommerceDetection = record({ id: "ecommerce-detection", domain: "ecommerce", mode: "detection", dimension: null, dimension_value: null });
    const sessionDiagnosis = record({ id: "sessions-diagnosis", domain: "sessions", mode: "diagnosis", group_key: "group-1" });
    const allItems = [sessionsDetection, ecommerceDetection, sessionDiagnosis];

    expect(buildThemeDetectionPage(allItems, "sessions").chartItems.map((item) => item.row.id)).toEqual(["sessions-detection"]);
    expect(buildThemeDetectionPage(allItems, "ecommerce").chartItems.map((item) => item.row.id)).toEqual(["ecommerce-detection"]);
  });

  it("shows Unassigned detection items in the Unassigned theme chart grid", () => {
    const detection = record({
      id: "unassigned-detection",
      domain: "traffic_quality",
      theme_id: "unassigned_traffic",
      mode: "detection",
      metric_name: "unassigned_session_share",
      metric_type: "derived_ratio",
      dimension: null,
      dimension_value: null,
    });

    const page = buildThemeDetectionPage([detection], "unassigned-traffic");

    expect(page.chartItems.map((item) => item.row.id)).toEqual(["unassigned-detection"]);
    expect(page.rows[0]).toMatchObject({
      theme: "unassigned-traffic",
      valueFormat: "percentage",
    });
  });

  it("shows Unassigned diagnosis Source Medium values including not set", () => {
    const detection = record({
      id: "unassigned-detection",
      domain: "traffic_quality",
      theme_id: "unassigned_traffic",
      mode: "detection",
      group_key: "prop:traffic_quality:unassigned_traffic:2026-05-02",
      metric_name: "unassigned_session_share",
      metric_type: "derived_ratio",
      dimension: null,
      dimension_value: null,
    });
    const diagnosis = record({
      id: "unassigned-diagnosis",
      domain: "traffic_quality",
      theme_id: "unassigned_traffic",
      mode: "diagnosis",
      group_key: "prop:traffic_quality:unassigned_traffic:2026-05-02",
      metric_name: "sessions",
      metric_type: "raw_count",
      dimension: "sessionSourceMedium",
      dimension_value: "(not set)",
    });

    const page = buildDiagnosisPage([detection, diagnosis], encodeGroupKey("prop:traffic_quality:unassigned_traffic:2026-05-02"));

    expect(page.rows[0]).toMatchObject({
      dimension: "sessionSourceMedium",
      dimensionValue: "(not set)",
      valueFormat: "number",
    });
  });

  it("includes Unassigned detection alerts in reports without creating diagnosis cards", () => {
    const detection = record({
      id: "unassigned-report-detection",
      domain: "traffic_quality",
      theme_id: "unassigned_traffic",
      mode: "detection",
      group_key: "prop:traffic_quality:unassigned_traffic:2026-05-02",
      metric_name: "unassigned_session_share",
      metric_type: "derived_ratio",
      dimension: null,
      dimension_value: null,
    });
    const diagnosis = record({
      id: "unassigned-report-diagnosis",
      domain: "traffic_quality",
      theme_id: "unassigned_traffic",
      mode: "diagnosis",
      group_key: "prop:traffic_quality:unassigned_traffic:2026-05-02",
      metric_name: "sessions",
      dimension: "sessionSourceMedium",
      dimension_value: "(empty)",
    });

    const page = buildReportsPage([detection, diagnosis]);
    const detailReports = page.propertyReports.flatMap((item) => item.reports);

    expect(detailReports.map((item) => item.id)).toEqual(["unassigned-report-detection"]);
    expect(detailReports[0]).toMatchObject({
      theme: "unassigned-traffic",
      themeLabel: "Unassigned Traffic",
      valueFormat: "percentage",
      diagnosisCandidates: [expect.objectContaining({ dimensionValue: "(empty)" })],
    });
    expect(detailReports[0].body).toContain("Unassigned 비율");
  });
});
