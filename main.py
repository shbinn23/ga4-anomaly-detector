import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
from prophet import Prophet

# 1. Prophet의 수다스러운 디버그 로그 차단 (서버 디스크 I/O 및 메모리 절약)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

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
    dates: List[str]
    actual_sessions: List[Optional[float]]
    ai_pure: List[float]
    ai_lower: List[float]
    ai_upper: List[float]

@app.get("/")
def read_root():
    return {"status": "ok", "message": "GA4 Anomaly Detection API is running"}

# --- 엔드포인트 로직 ---
@app.post("/api/v1/analyze", response_model=AnomalyResponse)
def analyze_traffic(payload: AnomalyRequest):
    try:
        # 1. Pydantic 객체를 DataFrame으로 고속 변환 (List Comprehension 활용)
        df = pd.DataFrame([vars(item) for item in payload.history_data])
        df.rename(columns={'date': 'ds', 'sessions': 'y'}, inplace=True)
        df['ds'] = pd.to_datetime(df['ds'])

        # 2. 타겟 일자(마지막 날)를 제외한 학습용 데이터 분리
        train_df = df.iloc[:-1]

        # 3. 순수 기본 Prophet 모델 학습 (80% 신뢰구간)
        # 커스텀 계절성 없이, Prophet이 기본적으로 감지하는 트렌드와 주간(Weekly) 패턴만 사용
        model = Prophet(yearly_seasonality=False, daily_seasonality=False, interval_width=0.80)
        model.fit(train_df)

        # 4. 메모리 낭비 제거: make_future_dataframe을 쓰지 않고 원본 날짜(ds)를 그대로 재사용하여 예측
        forecast = model.predict(df[['ds']])

        # 5. 타겟 일자 이상치 판별 (빠른 벡터 인덱싱)
        target_y = df['y'].iloc[-1]
        pred_lower = forecast['yhat_lower'].iloc[-1]
        pred_upper = forecast['yhat_upper'].iloc[-1]
        is_anomaly = bool(target_y < pred_lower or target_y > pred_upper)

        # 6. JSON 규격에 맞게 리스트로 추출 후 반환
        return AnomalyResponse(
            property_id=payload.property_id,
            target_date=payload.target_date,
            is_anomaly=is_anomaly,
            dates=forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
            actual_sessions=df['y'].tolist(),
            ai_pure=forecast['yhat'].round(2).tolist(),
            ai_lower=forecast['yhat_lower'].round(2).tolist(),
            ai_upper=forecast['yhat_upper'].round(2).tolist()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))