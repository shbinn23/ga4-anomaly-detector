import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("dashboard page composition", () => {
  it("renders Monitoring Workspace navigation links", () => {
    const source = readFileSync(resolve(process.cwd(), "components/dashboard/workspace-nav.tsx"), "utf-8");

    expect(source).toContain("Monitoring Workspace");
    expect(source).toContain("Overview");
    expect(source).toContain("/dashboard");
    expect(source).toContain("Sessions");
    expect(source).toContain("/dashboard/themes/sessions");
    expect(source).toContain("Ecommerce");
    expect(source).toContain("/dashboard/themes/ecommerce");
    expect(source).toContain("Unassigned Traffic");
    expect(source).toContain("/dashboard/themes/unassigned-traffic");
    expect(source).toContain("Reports");
    expect(source).toContain("/dashboard/reports");
  });

  it("uses plain Next links for workspace navigation and disables prefetch", () => {
    const source = readFileSync(resolve(process.cwd(), "components/dashboard/workspace-nav.tsx"), "utf-8");
    const linkSource = readFileSync(resolve(process.cwd(), "components/dashboard/navigation-link.tsx"), "utf-8");
    const themeSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/[theme]/page.tsx"), "utf-8");

    expect(source).not.toContain("usePathname");
    expect(source).not.toContain('"use client"');
    expect(source).toContain("NavigationLink");
    expect(linkSource).toContain("next/link");
    expect(source).toContain("prefetch={false}");
    expect(themeSource).toContain('dynamic = "force-dynamic"');
    expect(themeSource).toContain("revalidate = 0");
    expect(source).toContain('href: "/dashboard/themes/ecommerce"');
  });

  it("keeps workspace navigation hrefs absolute and clickable", () => {
    const source = readFileSync(resolve(process.cwd(), "components/dashboard/workspace-nav.tsx"), "utf-8");

    expect(source).toContain('href: "/dashboard"');
    expect(source).toContain('href: "/dashboard/themes/sessions"');
    expect(source).toContain('href: "/dashboard/themes/ecommerce"');
    expect(source).toContain('href: "/dashboard/themes/unassigned-traffic"');
    expect(source).toContain('href: "/dashboard/reports"');
    expect(source).not.toContain("pointer-events-none");
    expect(source).not.toContain("disabled");
    expect(source).not.toContain("aria-disabled");
    expect(source).not.toContain("preventDefault");
  });

  it("keeps shared navigation links from disabling active items", () => {
    const shellSource = readFileSync(resolve(process.cwd(), "components/dashboard/dashboard-shell.tsx"), "utf-8");
    const linkSource = readFileSync(resolve(process.cwd(), "components/dashboard/navigation-link.tsx"), "utf-8");

    expect(shellSource).toContain("NavigationLink");
    expect(shellSource).not.toContain("pointer-events-none");
    expect(shellSource).not.toContain("disabled");
    expect(shellSource).not.toContain("aria-disabled");
    expect(linkSource).not.toContain("preventDefault");
  });

  it("renders Monitoring Workspace navigation inside the shared page header", () => {
    const shellSource = readFileSync(resolve(process.cwd(), "components/dashboard/dashboard-shell.tsx"), "utf-8");
    const dashboardSource = readFileSync(resolve(process.cwd(), "app/dashboard/page.tsx"), "utf-8");
    const themeSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/[theme]/page.tsx"), "utf-8");
    const themeViewSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/theme-page.tsx"), "utf-8");
    const diagnosisSource = readFileSync(resolve(process.cwd(), "app/dashboard/diagnosis/[groupKey]/page.tsx"), "utf-8");
    const reportsSource = readFileSync(resolve(process.cwd(), "app/dashboard/reports/page.tsx"), "utf-8");

    expect(shellSource).toContain("<header");
    expect(shellSource.indexOf("<WorkspaceNav")).toBeGreaterThan(shellSource.indexOf("<header"));
    expect(dashboardSource).toContain("<DashboardShell");
    expect(themeSource).toContain("ThemeDetectionView");
    expect(themeViewSource).toContain("<DashboardShell");
    expect(diagnosisSource).toContain("<DashboardShell");
    expect(reportsSource).toContain("<DashboardShell");
  });

  it("delegates grouping and sorting to view models", () => {
    const source = readFileSync(resolve(process.cwd(), "app/dashboard/page.tsx"), "utf-8");

    expect(source).toContain("buildMainOverview");
    expect(source).toContain("DashboardShell");
    expect(source).toContain("Sessions Trending");
    expect(source).toContain("Property Health Matrix");
    expect(source).not.toContain("ForecastChart");
    expect(source).not.toContain("AnalysisTable");
    expect(source).not.toContain("Step 1");
    expect(source).not.toContain("Step 2");
    expect(source).not.toContain(".filter(");
    expect(source).not.toContain(".sort(");
    expect(source).not.toContain("mode ===");
  });

  it("uses route-scoped chart grids instead of selected representative charts", () => {
    const themeSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/theme-page.tsx"), "utf-8");
    const diagnosisSource = readFileSync(resolve(process.cwd(), "app/dashboard/diagnosis/[groupKey]/page.tsx"), "utf-8");

    expect(themeSource).toContain("lg:grid-cols-2");
    expect(themeSource).toContain("chartItems.map");
    expect(themeSource.match(/<ForecastChart/g)).toHaveLength(1);
    expect(themeSource).not.toContain("analysis_id");
    expect(themeSource).not.toContain("selectedChartAnalysis");
    expect(themeSource).not.toContain("featuredDetection");

    expect(diagnosisSource).toContain("lg:grid-cols-2");
    expect(diagnosisSource).toContain("chartItems.map");
    expect(diagnosisSource.match(/<ForecastChart/g)).toHaveLength(1);
    expect(diagnosisSource).not.toContain("analysis_id");
    expect(diagnosisSource).not.toContain("selectedChartAnalysis");
    expect(diagnosisSource).not.toContain("featuredDiagnosis");
  });

  it("keeps chart cards clipped and responsive inside grid cells", () => {
    const chartSource = readFileSync(resolve(process.cwd(), "components/dashboard/forecast-chart.tsx"), "utf-8");
    const chartContainerSource = readFileSync(resolve(process.cwd(), "components/ui/chart.tsx"), "utf-8");

    expect(chartSource).toContain("min-w-0 overflow-hidden");
    expect(chartSource).toContain("h-72 w-full min-w-0 overflow-hidden");
    expect(chartSource).not.toContain("100vw");
    expect(chartSource).not.toContain("absolute");
    expect(chartContainerSource).toContain('width="100%"');
    expect(chartContainerSource).toContain('height="100%"');
  });

  it("keeps frontend from reading storage JSON directly", () => {
    const source = [
      readFileSync(resolve(process.cwd(), "app/dashboard/page.tsx"), "utf-8"),
      readFileSync(resolve(process.cwd(), "app/dashboard/themes/[theme]/page.tsx"), "utf-8"),
      readFileSync(resolve(process.cwd(), "app/dashboard/diagnosis/[groupKey]/page.tsx"), "utf-8"),
      readFileSync(resolve(process.cwd(), "app/dashboard/reports/page.tsx"), "utf-8"),
    ].join("\n");

    expect(source).not.toContain(["json", "load"].join("."));
    expect(source).not.toContain(["json", "loads"].join("."));
  });

  it("supports summary and details report views through query string tabs", () => {
    const source = readFileSync(resolve(process.cwd(), "app/dashboard/reports/page.tsx"), "utf-8");

    expect(source).toContain('query.view === "details" ? "details" : "summary"');
    expect(source).toContain("/dashboard/reports?view=summary");
    expect(source).toContain("/dashboard/reports?view=details");
    expect(source).toContain("종합 리포트");
    expect(source).toContain("세부 리포트");
    expect(source).toContain("summaryReports");
    expect(source).toContain("reportItems.slice");
  });

  it("keeps theme page tabs as query-string links", () => {
    const source = readFileSync(resolve(process.cwd(), "app/dashboard/themes/theme-page.tsx"), "utf-8");
    const sessionsSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/sessions/page.tsx"), "utf-8");
    const ecommerceSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/ecommerce/page.tsx"), "utf-8");
    const unassignedSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/unassigned-traffic/page.tsx"), "utf-8");
    const dynamicSource = readFileSync(resolve(process.cwd(), "app/dashboard/themes/[theme]/page.tsx"), "utf-8");

    expect(source).toContain('href: `/dashboard/themes/${theme}?tab=chart`');
    expect(source).toContain('href: `/dashboard/themes/${theme}?tab=table`');
    expect(source.indexOf('label: "Chart"')).toBeLessThan(source.indexOf('label: "Table"'));
    expect(sessionsSource).toContain('query.tab === "table" ? "table" : "chart"');
    expect(ecommerceSource).toContain('query.tab === "table" ? "table" : "chart"');
    expect(unassignedSource).toContain('theme="unassigned-traffic"');
    expect(unassignedSource).toContain('query.tab === "table" ? "table" : "chart"');
    expect(dynamicSource).toContain('query.tab === "table" ? "table" : "chart"');
    expect(source).toContain("PageTabs");
  });

  it("keeps diagnosis tabs chart-first with chart fallback", () => {
    const source = readFileSync(resolve(process.cwd(), "app/dashboard/diagnosis/[groupKey]/page.tsx"), "utf-8");

    expect(source).toContain('query.tab === "table" ? "table" : "chart"');
    expect(source).toContain('href: `/dashboard/diagnosis/${groupKey}?tab=chart`');
    expect(source).toContain('href: `/dashboard/diagnosis/${groupKey}?tab=table`');
    expect(source.indexOf('label: "Chart"')).toBeLessThan(source.indexOf('label: "Table"'));
  });

  it("uses anomaly styling for alert UI without making normal and watch red", () => {
    const tableSource = readFileSync(resolve(process.cwd(), "components/dashboard/analysis-table.tsx"), "utf-8");
    const badgeSource = readFileSync(resolve(process.cwd(), "components/ui/badge.tsx"), "utf-8");
    const reportsSource = readFileSync(resolve(process.cwd(), "app/dashboard/reports/page.tsx"), "utf-8");

    expect(badgeSource).toContain('"anomaly"');
    expect(badgeSource).toContain("bg-anomaly-muted");
    expect(tableSource).toContain('row.alertStatus === "alert" ? "anomaly"');
    expect(tableSource).toContain('row.alertStatus === "watch" ? "warning"');
    expect(tableSource).toContain(': "neutral"');
    expect(reportsSource).toContain('tone={report.alertStatus === "alert" ? "anomaly" : "neutral"}');
    expect(reportsSource).toContain("text-anomaly-foreground");
  });

  it("keeps reports tabs as query-string links with summary as the default view", () => {
    const source = readFileSync(resolve(process.cwd(), "app/dashboard/reports/page.tsx"), "utf-8");

    expect(source).toContain('query.view === "details" ? "details" : "summary"');
    expect(source).toContain('href: "/dashboard/reports?view=summary"');
    expect(source).toContain('href: "/dashboard/reports?view=details"');
    expect(source).toContain('activeView === "summary"');
    expect(source).toContain('activeView === "details"');
  });
});
