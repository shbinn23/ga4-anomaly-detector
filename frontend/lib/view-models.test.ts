import { describe, expect, it } from "vitest";

import type { AnalysisRecord, ForecastData } from "./types";
import {
  buildAnalysisRows,
  buildDiagnosisPage,
  buildMainOverview,
  buildReportsPage,
  buildThemeDetectionPage,
  decodeGroupKey,
  encodeGroupKey,
  getDetectionResults,
  getDiagnosisResults,
  groupDiagnosisByDetection,
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
      metric_name: overrides.metric_name ?? "eventCount",
      dimension: overrides.dimension ?? "eventName",
      dimension_value: overrides.dimension_value ?? "purchase",
      dimensions: overrides.dimensions ?? {},
      has_anomaly: overrides.has_anomaly ?? true,
      is_anomaly: overrides.is_anomaly ?? true,
      actual_value: overrides.actual_value ?? latestPoint.y,
      lower_bound: overrides.lower_bound ?? latestPoint.yhat_lower,
      upper_bound: overrides.upper_bound ?? latestPoint.yhat_upper,
      target_date: overrides.target_date ?? latestPoint.ds,
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
    expect(overview.themeSummaries.map((item) => item.theme)).toEqual(["sessions", "ecommerce"]);
    expect(overview.propertyThemeMatrix[0]).toMatchObject({
      propertyName: "Property 1",
      themes: [
        { theme: "sessions", status: "anomaly" },
        { theme: "ecommerce", status: "normal" },
      ],
    });
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
});
