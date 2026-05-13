from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DailySession(BaseModel):
    date: str
    sessions: float

class AnomalyRequest(BaseModel):
    property_id: str
    property_name: str
    target_date: str
    history_data: List[DailySession]

class ForecastData(BaseModel):
    ds: List[str]
    y: List[float]
    yhat: List[float]
    yhat_lower: List[float]
    yhat_upper: List[float]
    is_anomaly: List[bool]

class BatchAnomalyRequest(BaseModel):
    """n8n에서 보내는 10개 단위 배치 요청을 수용합니다."""
    batch_size: int
    properties: List[AnomalyRequest]

class AnalysisResult(BaseModel):
    property_name: str
    is_anomaly: bool
    last_sessions: int
    updated_at: str
    forecast_data: ForecastData

class ChannelData(BaseModel):
    date: str
    sessions: float  # Prophet 연산을 위해 float 권장

class ChannelPropertyRequest(BaseModel):
    property_id: str
    property_name: str
    # n8n에서 { "Organic Search": [...], "Direct": [...] } 형태로 보낼 경우
    grouped_channels: Dict[str, List[ChannelData]]

class ChannelUpdateTask(BaseModel):
    """n8n 수신 최상위 페이로드"""
    total_count: int
    data: List[ChannelPropertyRequest]
