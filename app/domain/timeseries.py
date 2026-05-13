from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimeSeriesPoint(BaseModel):
    date: str
    value: float


class ForecastPoint(BaseModel):
    ds: str
    y: float
    yhat: float
    yhat_lower: float
    yhat_upper: float
    is_anomaly: bool = False


class AnalysisTask(BaseModel):
    """Canonical unit consumed by the ML layer: one metric over time."""

    analysis_id: str
    domain: str
    mode: str
    property_id: str
    property_name: Optional[str]
    metric_name: str
    dimensions: Dict[str, Any]
    series: List[TimeSeriesPoint] = Field(min_length=2)
    target_date: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    analysis_id: str
    domain: str
    mode: str
    property_id: str
    property_name: Optional[str]
    metric_name: str
    dimensions: Dict[str, Any]
    is_anomaly: bool
    actual_value: float
    lower_bound: float
    upper_bound: float
    target_date: str
    forecast_data: Dict[str, List[Any]]


TimeSeriesTask = AnalysisTask
TimeSeriesValue = TimeSeriesPoint
TimeSeriesAnalysisResult = AnalysisResult
