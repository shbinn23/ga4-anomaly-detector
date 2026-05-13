export type ApiHealth = {
  status: string;
};

export type ForecastData = {
  ds: string[];
  y: number[];
  yhat: number[];
  yhat_lower: number[];
  yhat_upper: number[];
  is_anomaly?: boolean[];
};

export type AnalysisResult = {
  analysis_id?: string;
  domain?: string;
  mode?: string;
  property_id?: string;
  property_name?: string | null;
  metric_name?: string;
  dimensions?: Record<string, unknown>;
  is_anomaly?: boolean;
  actual_value?: number;
  lower_bound?: number;
  upper_bound?: number;
  target_date?: string;
  last_sessions?: number;
  updated_at?: string;
  forecast_data?: ForecastData;
};

export type AnalysisRecord = {
  id: string;
  result: AnalysisResult;
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
  latestLabel: string;
  affectedSegments: number;
};

export type AnalysisTableRow = {
  id: string;
  dimension: string;
  dimensionValue: string;
  anomalyCount: number;
  lastAnomalyDate: string;
  latestY: number | null;
  latestYhat: number | null;
  deviation: number | null;
  direction: "up" | "down" | "flat" | "unknown";
};
