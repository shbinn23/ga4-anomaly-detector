import Link from "next/link";
import { DashboardShell, PageActionLink, PageTabs } from "@/components/dashboard/dashboard-shell";
import { EmptyState } from "@/components/dashboard/empty-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardData } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { ReportItem } from "@/lib/types";
import { buildReportsPage } from "@/lib/view-models";

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const query = await searchParams;
  const activeView = query.view === "details" ? "details" : "summary";
  const data = await getDashboardData();
  const reports = buildReportsPage(data.analyses);
  const reportItems = reports.propertyReports.flatMap((property) => property.reports);

  return (
    <DashboardShell
      actions={<PageActionLink href="/dashboard" muted>Back to overview</PageActionLink>}
      activeHref="/dashboard/reports"
      description={`${reports.reportDate} 기준으로 현재 이상 신호가 확인된 항목을 운영 리포트 형식으로 정리했습니다.`}
      title="Reports"
    >

        {reports.propertyReports.length ? (
          <>
            <PageTabs
              items={[
                { href: "/dashboard/reports?view=summary", label: "종합 리포트", active: activeView === "summary" },
                { href: "/dashboard/reports?view=details", label: "세부 리포트", active: activeView === "details" },
              ]}
            />

            <Card>
              <CardHeader>
                <CardTitle className="text-3xl font-semibold tracking-[-0.03em]">운영 리포트 요약</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 text-sm text-muted-foreground md:grid-cols-3">
                <span>기준일 {reports.reportDate}</span>
                <span>현재 이상 항목 {reportItems.length}</span>
                <span>대상 프로퍼티 {reports.propertyReports.length}</span>
              </CardContent>
            </Card>

            {activeView === "summary" ? (
              <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {reports.summaryReports.map((report) => (
                  <Card key={`${report.propertyName}:${report.reportDate}`}>
                    <CardHeader>
                      <div className="flex flex-wrap items-center gap-2">
                        {report.themeLabels.map((label) => (
                          <Badge key={label} tone="anomaly">{label}</Badge>
                        ))}
                      </div>
                      <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">{report.propertyName}</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-4 text-sm leading-6">
                      <p>{report.headline}</p>
                      <div className="grid gap-2 text-muted-foreground">
                        {report.themeSummaries.map((item) => (
                          <div className="grid gap-1 border-b pb-2" key={`${report.propertyName}:${item.theme}`}>
                            <span className="font-medium text-foreground">{item.themeLabel} · {item.metricName}</span>
                            <span>
                              {item.directionLabel}
                              {item.breachRate !== null ? (
                                <span className="font-semibold text-anomaly-foreground"> · 약 {item.breachRate.toFixed(1)}%</span>
                              ) : null}
                            </span>
                            <div className="flex flex-wrap gap-3">
                              {item.detectionHref ? (
                                <Link href={item.detectionHref} className="font-medium text-foreground underline-offset-4 hover:underline">
                                  1단계 추이 보기
                                </Link>
                              ) : null}
                              {item.diagnosisHref ? (
                                <Link href={item.diagnosisHref} className="font-medium text-foreground underline-offset-4 hover:underline">
                                  2단계 진단 보기
                                </Link>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                      {report.diagnosisCandidates.length ? (
                        <div className="text-muted-foreground">
                          주요 원인 후보: {report.diagnosisCandidates.map((item) => item.dimensionValue).join(", ")}
                        </div>
                      ) : (
                        <p className="text-muted-foreground">현재 연결된 세부 진단 결과는 없습니다.</p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </section>
            ) : (
              <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {reportItems.slice(0, 40).map((report) => (
                  <Card key={report.id}>
                    <CardHeader>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={report.alertStatus === "alert" ? "anomaly" : "neutral"}>{report.themeLabel}</Badge>
                        <span className="text-sm text-muted-foreground">{report.metricName}</span>
                      </div>
                      <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">{report.headline}</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-4 text-sm leading-6">
                      <ReportBody report={report} />
                      <p className="text-muted-foreground">{report.diagnosisSentence}</p>
                      {report.diagnosisCandidates.length ? (
                        <div className="text-muted-foreground">
                          주요 원인 후보: {report.diagnosisCandidates.map((item) => item.dimensionValue).join(", ")}
                        </div>
                      ) : null}
                      <div className="flex flex-wrap gap-3 pt-1">
                        <Link href={report.detectionHref ?? `/dashboard/themes/${report.theme}`} className="font-medium underline-offset-4 hover:underline">
                          1단계 추이 보기
                        </Link>
                        {report.diagnosisHref ? (
                          <Link href={report.diagnosisHref} className="font-medium underline-offset-4 hover:underline">
                            2단계 진단 보기
                          </Link>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </section>
            )}
          </>
        ) : (
          <EmptyState title="No anomaly reports" description="No anomalous stored results are available for reports." />
        )}
    </DashboardShell>
  );
}

function ReportBody({ report }: { report: ReportItem }) {
  const actual = formatNumber(report.latestY);
  const lower = formatNumber(report.latestLower);
  const upper = formatNumber(report.latestUpper);
  const boundaryLabel = report.direction === "down" ? "하단" : "상단";
  const breachLabel = report.breachRate === null
    ? report.direction === "down" ? "하회" : "초과"
    : `${report.breachRate.toFixed(1)}% ${report.direction === "down" ? "하회" : "초과"}`;

  return (
    <p>
      {report.reportDate} 기준 {report.propertyName} 프로퍼티의 {report.metricName}는 {actual}로,
      예측 범위 {lower} ~ {upper}의 {boundaryLabel}을 {report.breachRate === null ? "" : "약 "}
      <span className="font-semibold text-anomaly-foreground">{breachLabel}</span>
      했습니다.
    </p>
  );
}
