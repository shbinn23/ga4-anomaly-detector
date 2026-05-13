from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from .timeseries import calculate_point_anomalies


class DashboardForecastData(BaseModel):
    ds: List[str]
    y: List[float]
    yhat: List[float]
    yhat_lower: List[float]
    yhat_upper: List[float]
    is_anomaly: List[bool]

    @model_validator(mode="before")
    @classmethod
    def fill_missing_point_anomalies(cls, data):
        if isinstance(data, dict) and "is_anomaly" not in data:
            data = dict(data)
            data["is_anomaly"] = calculate_point_anomalies(data)
        return data

    @model_validator(mode="after")
    def validate_column_lengths(self):
        lengths = {
            len(self.ds),
            len(self.y),
            len(self.yhat),
            len(self.yhat_lower),
            len(self.yhat_upper),
            len(self.is_anomaly),
        }
        if len(lengths) != 1:
            raise ValueError("forecast_data fields must have equal lengths")
        return self


class DashboardForecastPoint(BaseModel):
    ds: str
    y: float
    yhat: float
    yhat_lower: float
    yhat_upper: float
    is_anomaly: bool


class DashboardResultItem(BaseModel):
    id: str
    source: str
    group_key: str
    analysis_id: str
    domain: str
    mode: str
    property_id: Optional[str] = None
    property_name: Optional[str] = None
    metric_name: str
    dimension: Optional[str] = None
    dimension_value: Optional[str] = None
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    has_anomaly: bool
    is_anomaly: bool
    actual_value: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    target_date: Optional[str] = None
    latest_point: Optional[DashboardForecastPoint] = None
    forecast_data: DashboardForecastData


class DashboardResultsResponse(BaseModel):
    items: List[DashboardResultItem] = Field(default_factory=list)
