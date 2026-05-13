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
  analysis_id: string;
  domain: string;
  mode: string;
  property_id?: string;
  property_name?: string | null;
  metric_name: string;
  dimension: string | null;
  dimension_value: string | null;
  dimensions: Record<string, unknown>;
  has_anomaly: boolean;
  is_anomaly: boolean;
  actual_value?: number;
  lower_bound?: number;
  upper_bound?: number;
  target_date?: string;
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
  anomalyCount: number;
  latestResultDate: string;
  affectedSegments: number;
};

export type AnalysisTableRow = {
  id: string;
  domain: string;
  mode: string;
  metricName: string;
  dimension: string;
  dimensionValue: string;
  anomalyCount: number;
  lastAnomalyDate: string;
  latestY: number | null;
  latestYhat: number | null;
  latestDeviation: number | null;
  direction: "up" | "down" | "flat" | "unknown";
};
