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
    metric_name: str
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    series: List[SeriesPoint] = Field(min_length=2)
    target_date: Optional[date] = None
    target_events: Optional[List[str]] = None

    @model_validator(mode="after")
    def target_date_must_match_last_point(self):
        if self.target_date is not None and self.series[-1].date != self.target_date:
            raise ValueError("target_date must match the last series point date")
        return self


class GenericAnalysisResponse(BaseModel):
    status: str
    analysis_id: str
    is_anomaly: bool
    result: Dict[str, Any]
    next_action: Optional[Dict[str, Any]] = None
