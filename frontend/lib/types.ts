export type ApiHealth = {
  status: string;
};

export type ForecastData = {
  ds: string[];
  y: number[];
  yhat: number[];
  yhat_lower: number[];
  yhat_upper: number[];
  is_anomaly: boolean[];
};

export type AnalysisResult = {
  id?: string;
  source?: string;
  group_key?: string;
  analysis_id: string;
  domain: string;
  mode: string;
  property_id?: string;
  property_name?: string | null;
  theme_id?: string | null;
  metric_name: string;
  metric_type?: string | null;
  dimension: string | null;
  dimension_value: string | null;
  dimensions: Record<string, unknown>;
  has_anomaly: boolean;
  is_anomaly: boolean;
  actual_value?: number;
  lower_bound?: number;
  upper_bound?: number;
  target_date?: string;
  target_point?: ForecastPoint | null;
  is_current_anomaly: boolean;
  alert_status: "normal" | "watch" | "alert";
  historical_anomaly_count: number;
  recent_anomaly_count: number;
  latest_point?: ForecastPoint | null;
  forecast_data: ForecastData;
};

export type AnalysisRecord = {
  id: string;
  result: AnalysisResult;
};

export type DashboardResultsResponse = {
  items: AnalysisResult[];
};

export type DashboardData = {
  health: ApiHealth | null;
  analyses: AnalysisRecord[];
  errors: string[];
};

export type ForecastPoint = {
  ds: string;
  y: number;
  yhat: number;
  yhat_lower: number;
  yhat_upper: number;
  is_anomaly: boolean;
};

export type SummaryStats = {
  totalAnalyses: number;
  anomalousPropertyCount: number;
  anomalousThemeCount: number;
  latestAnomalyDate: string;
};

export type AnalysisTableRow = {
  id: string;
  groupKey: string;
  propertyName: string;
  hasAnomaly: boolean;
  isCurrentAnomaly: boolean;
  alertStatus: "normal" | "watch" | "alert";
  domain: string;
  theme: string;
  mode: string;
  metricName: string;
  valueFormat: "number" | "percentage";
  dimension: string;
  dimensionValue: string;
  anomalyCount: number;
  recentAnomalyCount: number;
  lastAnomalyDate: string;
  latestY: number | null;
  latestYhat: number | null;
  latestLower: number | null;
  latestUpper: number | null;
  latestDeviation: number | null;
  direction: "up" | "down" | "flat" | "unknown";
  detailHref?: string;
  detailLabel?: string;
  detailDisabled?: boolean;
};

export type DashboardGroup = {
  groupKey: string;
  detection: AnalysisRecord | null;
  diagnoses: AnalysisRecord[];
};

export type DashboardSections = {
  all: AnalysisRecord[];
  detections: AnalysisRecord[];
  diagnoses: AnalysisRecord[];
  groups: DashboardGroup[];
};

export type ThemeSummary = {
  theme: string;
  label: string;
  description: string;
  href: string;
  totalCount: number;
  detectionCount: number;
  diagnosisCount: number;
  anomalyCount: number;
};

export type PropertyThemeCell = {
  theme: string;
  themeLabel: string;
  valueFormat: "number" | "percentage";
  status: "anomaly" | "watch" | "normal" | "missing";
  href: string;
  label: string;
  breachRate: number | null;
  direction: "up" | "down" | "flat" | "unknown";
  actual: number | null;
  lower: number | null;
  upper: number | null;
};

export type PropertyThemeRow = {
  propertyId: string;
  propertyName: string;
  themes: PropertyThemeCell[];
  alertThemeCount: number;
  maxBreachRate: number;
};

export type MainOverview = {
  stats: SummaryStats;
  themeSummaries: ThemeSummary[];
  propertyThemeMatrix: PropertyThemeRow[];
  sessionsTrending: SessionsTrending;
};

export type SessionsTrendingItem = {
  id: string;
  propertyName: string;
  score: number | null;
  actual: number;
  lower: number;
  upper: number;
  direction: "up" | "down";
  href: string;
};

export type SessionsTrending = {
  higher: SessionsTrendingItem[];
  lower: SessionsTrendingItem[];
};

export type ThemeDetectionPage = {
  theme: string;
  detections: AnalysisRecord[];
  rows: AnalysisTableRow[];
  chartItems: AnalysisChartItem[];
};

export type DiagnosisPage = {
  groupKey: string;
  detection: AnalysisRecord | null;
  diagnoses: AnalysisRecord[];
  rows: AnalysisTableRow[];
  chartItems: AnalysisChartItem[];
};

export type AnalysisChartItem = {
  analysis: AnalysisRecord;
  row: AnalysisTableRow;
};

export type ReportItem = AnalysisTableRow & {
  theme: string;
  themeLabel: string;
  reportDate: string;
  headline: string;
  body: string;
  sentence: string;
  diagnosisSentence: string;
  absoluteDeviation: number | null;
  breachRate: number | null;
  detectionHref?: string;
  diagnosisHref?: string;
  diagnosisCandidates: AnalysisTableRow[];
};

export type PropertySummaryReport = {
  propertyName: string;
  reportDate: string;
  themeLabels: string[];
  headline: string;
  themeSummaries: Array<{
    theme: string;
    themeLabel: string;
    metricName: string;
    directionLabel: string;
    breachRate: number | null;
    detectionHref?: string;
    diagnosisHref?: string;
  }>;
  diagnosisCandidates: AnalysisTableRow[];
};

export type ReportsPage = {
  reportDate: string;
  summaryReports: PropertySummaryReport[];
  propertyReports: Array<{
    propertyId: string;
    propertyName: string;
    reports: ReportItem[];
  }>;
  themeReports: Array<{
    theme: string;
    reports: ReportItem[];
  }>;
};
