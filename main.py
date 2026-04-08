from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
from prophet import Prophet

# 1. FastAPI 인스턴스 생성
app = FastAPI(title="GA4 Anomaly Detection API")

# --- 데이터 계약 (Data Contracts) ---
class DailySession(BaseModel):
    date: str
    sessions: float

class AnomalyRequest(BaseModel):
    property_id: str
    target_date: str
    history_data: List[DailySession] = Field(..., description="과거 시계열 데이터 리스트")

class AnomalyResponse(BaseModel):
    property_id: str
    target_date: str
    is_anomaly: bool
    # 차트 렌더링을 위한 시계열 배열
    dates: List[str]
    actual_sessions: List[Optional[float]]
    ai_pure: List[float]
    ai_lower: List[float]
    ai_upper: List[float]

# --- 서버 상태 확인 (Health Check) ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "GA4 Anomaly Detection API is running"}

# --- 엔드포인트 로직 ---
@app.post("/api/v1/analyze", response_model=AnomalyResponse)
def analyze_traffic(payload: AnomalyRequest):
    try:
        # 데이터 변환
        df = pd.DataFrame([{"ds": item.date, "y": item.sessions} for item in payload.history_data])
        df['ds'] = pd.to_datetime(df['ds'])

        # 타겟 일자 분리
        target_row = df.iloc[-1]
        train_df = df.iloc[:-1]

        # Prophet 모델 학습 (신뢰구간 80%)
        model = Prophet(yearly_seasonality=False, daily_seasonality=False, interval_width=0.80)
        model.fit(train_df)

        # 예측 수행
        future = model.make_future_dataframe(periods=1)
        forecast = model.predict(future)

        # 타겟 일자 이상치 판별
        prediction = forecast.iloc[-1]
        is_anomaly = bool(target_row['y'] < prediction['yhat_lower'] or target_row['y'] > prediction['yhat_upper'])

        # 결과 배열 추출 (리스트 형태로 변환)
        dates = forecast['ds'].dt.strftime('%Y-%m-%d').tolist()
        ai_pure = forecast['yhat'].round(2).tolist()
        ai_lower = forecast['yhat_lower'].round(2).tolist()
        ai_upper = forecast['yhat_upper'].round(2).tolist()
        actual_sessions = df['y'].tolist()

        return AnomalyResponse(
            property_id=payload.property_id,
            target_date=payload.target_date,
            is_anomaly=is_anomaly,
            dates=dates,
            actual_sessions=actual_sessions,
            ai_pure=ai_pure,
            ai_lower=ai_lower,
            ai_upper=ai_upper
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))