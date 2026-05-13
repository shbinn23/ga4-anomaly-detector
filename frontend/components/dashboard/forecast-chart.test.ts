import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

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
});
