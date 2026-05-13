import { describe, expect, it } from "vitest";

import type { AnalysisRecord } from "./types";
import { buildAnalysisRows, buildSummaryStats } from "./view-models";

const baseForecast = {
  ds: ["2026-05-01", "2026-05-02"],
  y: [100, 150],
  yhat: [100, 100],
  yhat_lower: [80, 80],
  yhat_upper: [120, 120],
  is_anomaly: [false, true],
};

const records: AnalysisRecord[] = [
  {
    id: "generic-key",
    result: {
      id: "generic-key",
      source: "generic_analysis_db",
      analysis_id: "analysis-1",
      domain: "ecommerce",
      mode: "diagnosis",
      property_id: "prop-1",
      property_name: "Store",
      metric_name: "eventCount",
      dimension: "eventName",
      dimension_value: "purchase",
      dimensions: { eventName: "purchase" },
      has_anomaly: true,
      is_anomaly: true,
      actual_value: 150,
      lower_bound: 80,
      upper_bound: 120,
      target_date: "2026-05-02",
      latest_point: {
        ds: "2026-05-02",
        y: 180,
        yhat: 120,
        yhat_lower: 90,
        yhat_upper: 130,
        is_anomaly: true,
      },
      forecast_data: baseForecast,
    },
  },
];

describe("dashboard view models", () => {
  it("calculates summary stats from has_anomaly and latest_point", () => {
    expect(buildSummaryStats(records)).toEqual({
      totalAnalyses: 1,
      anomalyCount: 1,
      latestResultDate: "2026-05-02",
      affectedSegments: 1,
    });
  });

  it("calculates table rows from explicit dimension fields and latest_point", () => {
    expect(buildAnalysisRows(records)).toEqual([
      {
        id: "generic-key",
        domain: "ecommerce",
        mode: "diagnosis",
        metricName: "eventCount",
        dimension: "eventName",
        dimensionValue: "purchase",
        anomalyCount: 1,
        lastAnomalyDate: "2026-05-02",
        latestY: 180,
        latestYhat: 120,
        latestDeviation: 50,
        direction: "up",
      },
    ]);
  });
});
