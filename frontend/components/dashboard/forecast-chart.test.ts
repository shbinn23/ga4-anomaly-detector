import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { normalizeForecastData } from "../../lib/forecast";
import type { ForecastData } from "../../lib/types";

const commonForecast: ForecastData = {
  ds: ["2026-05-01", "2026-05-02"],
  y: [100, 150],
  yhat: [100, 100],
  yhat_lower: [80, 80],
  yhat_upper: [120, 120],
  is_anomaly: [false, true],
};

describe("ForecastChart data boundary", () => {
  it("depends on common forecast fields only", () => {
    const source = readFileSync(
      resolve(process.cwd(), "components/dashboard/forecast-chart.tsx"),
      "utf-8",
    );

    expect(source).toContain("forecast_data");
    expect(source).toContain("yhat_lower");
    expect(source).toContain("yhat_upper");
    expect(source).not.toContain("metric_name");
    expect(source).not.toContain("dimensions");
  });

  it("accepts detection forecast_data", () => {
    expect(normalizeForecastData(commonForecast)).toHaveLength(2);
  });

  it("accepts diagnosis forecast_data", () => {
    expect(normalizeForecastData({ ...commonForecast, y: [40, 20] })[1]).toMatchObject({
      ds: "2026-05-02",
      y: 20,
      is_anomaly: true,
    });
  });
});
