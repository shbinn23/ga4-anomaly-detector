import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("dashboard page composition", () => {
  it("delegates grouping and sorting to view models", () => {
    const source = readFileSync(resolve(process.cwd(), "app/dashboard/page.tsx"), "utf-8");

    expect(source).toContain("buildDashboardSections");
    expect(source).toContain("buildSummary");
    expect(source).not.toContain(".filter(");
    expect(source).not.toContain(".sort(");
    expect(source).not.toContain("mode ===");
  });
});
