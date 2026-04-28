from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class TimeSeriesPoint:
    """시계열 데이터의 최소 단위"""
    ds: str
    y: float

@dataclass
class DetectionResult:
    """이상 탐지 결과의 내부 도메인 모델"""
    property_id: str
    property_name: str
    is_anomaly: bool
    actual_value: float
    predicted_value: float
    lower_bound: float
    upper_bound: float
    target_date: str