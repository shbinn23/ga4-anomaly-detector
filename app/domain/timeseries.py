from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


def calculate_point_anomalies(forecast_data: Dict[str, List[Any]]) -> List[bool]:
    return [
        actual < lower or actual > upper
        for actual, lower, upper in zip(
            forecast_data.get("y", []),
            forecast_data.get("yhat_lower", []),
            forecast_data.get("yhat_upper", []),
        )
    ]


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

    @model_validator(mode="before")
    @classmethod
    def fill_missing_point_anomalies(cls, data):
        if isinstance(data, dict):
            forecast_data = data.get("forecast_data")
            if isinstance(forecast_data, dict) and "is_anomaly" not in forecast_data:
                data = dict(data)
                data["forecast_data"] = dict(forecast_data)
                data["forecast_data"]["is_anomaly"] = calculate_point_anomalies(forecast_data)
        return data


TimeSeriesTask = AnalysisTask
TimeSeriesValue = TimeSeriesPoint
TimeSeriesAnalysisResult = AnalysisResult
