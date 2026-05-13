from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TimeSeriesValue:
    date: str
    value: float


@dataclass(frozen=True)
class TimeSeriesTask:
    """Canonical unit consumed by the ML layer: one metric over time."""

    analysis_id: str
    domain: str
    mode: str
    property_id: str
    property_name: Optional[str]
    metric_name: str
    dimensions: Dict[str, Any]
    series: List[TimeSeriesValue]
    target_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TimeSeriesAnalysisResult:
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
