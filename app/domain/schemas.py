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

class AnalysisResult(BaseModel):
    property_name: str
    is_anomaly: bool
    last_sessions: int
    updated_at: str
    forecast_data: ForecastData