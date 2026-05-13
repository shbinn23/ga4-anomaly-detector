from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class SeriesPoint(BaseModel):
    date: date
    value: float = Field(ge=0)


class GenericAnalysisRequest(BaseModel):
    """Domain-agnostic single-metric time series request."""

    domain: str
    mode: str = "detection"
    property_id: str
    property_name: Optional[str] = None
    corporation: Optional[str] = None
    theme_id: Optional[str] = None
    metric_name: str
    metric_type: Optional[str] = None
    alert_direction_policy: str = "two_sided"
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    filters: Dict[str, Any] = Field(default_factory=dict)
    aggregation_method: str = "sum"
    series: List[SeriesPoint] = Field(min_length=2)
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    target_date: Optional[date] = None
    target_events: Optional[List[str]] = None

    @model_validator(mode="after")
    def target_date_must_match_last_point(self):
        if self.target_date is not None and self.series[-1].date != self.target_date:
            raise ValueError("target_date must match the last series point date")
        if self.date_start is not None and self.date_start != self.series[0].date:
            raise ValueError("date_start must match the first series point date")
        if self.date_end is not None and self.date_end != self.series[-1].date:
            raise ValueError("date_end must match the last series point date")
        return self


class GenericAnalysisResponse(BaseModel):
    status: str
    analysis_id: str
    is_anomaly: bool
    theme_id: Optional[str] = None
    target_date: Optional[str] = None
    target_point: Optional[Dict[str, Any]] = None
    alert_status: Optional[str] = None
    is_current_anomaly: Optional[bool] = None
    recent_anomaly_count: Optional[int] = None
    historical_anomaly_count: Optional[int] = None
    should_run_diagnosis: Optional[bool] = None
    result: Dict[str, Any]
    next_action: Optional[Dict[str, Any]] = None


class ThemeDiagnosisResponse(BaseModel):
    status: str
    theme_id: str
    domain: str
    mode: str
    property_id: str
    property_name: Optional[str] = None
    target_date: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)


class UnassignedTrafficRawRow(BaseModel):
    date: date
    sessionDefaultChannelGroup: str
    sessions: float = Field(ge=0)


class UnassignedTrafficDetectionRequest(BaseModel):
    """Raw GA4 rows for Unassigned Traffic detection."""

    property_id: str
    property_name: Optional[str] = None
    corporation: Optional[str] = None
    target_date: Optional[date] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    rows: List[UnassignedTrafficRawRow] = Field(min_length=1)

    @model_validator(mode="after")
    def dates_must_match_available_rows(self):
        sorted_dates = sorted({item.date for item in self.rows})
        if self.date_start is not None and self.date_start != sorted_dates[0]:
            raise ValueError("date_start must match the first raw row date")
        if self.date_end is not None and self.date_end != sorted_dates[-1]:
            raise ValueError("date_end must match the last raw row date")
        if self.target_date is not None and self.target_date not in sorted_dates:
            raise ValueError("target_date must exist in raw rows")
        return self


class UnassignedTrafficDiagnosisRawRow(BaseModel):
    date: date
    sessionSourceMedium: Optional[str] = None
    sessions: float = Field(ge=0)


class UnassignedTrafficDiagnosisRequest(BaseModel):
    """Raw GA4 rows for Unassigned Traffic diagnosis."""

    property_id: str
    property_name: Optional[str] = None
    corporation: Optional[str] = None
    target_date: Optional[date] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    top_n: int = Field(default=20, ge=1, le=100)
    min_total_value: float = Field(default=50, ge=0)
    rows: List[UnassignedTrafficDiagnosisRawRow] = Field(min_length=1)

    @model_validator(mode="after")
    def dates_must_match_available_rows(self):
        sorted_dates = sorted({item.date for item in self.rows})
        if self.date_start is not None and self.date_start != sorted_dates[0]:
            raise ValueError("date_start must match the first raw row date")
        if self.date_end is not None and self.date_end != sorted_dates[-1]:
            raise ValueError("date_end must match the last raw row date")
        if self.target_date is not None and self.target_date not in sorted_dates:
            raise ValueError("target_date must exist in raw rows")
        return self
