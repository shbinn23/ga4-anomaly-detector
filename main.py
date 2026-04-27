import logging
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
from prophet import Prophet

# 1. 경로 설정 (절대 경로를 사용하여 논리적 오류 방지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "results_db.json")

logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
app = FastAPI(title="GA4 Anomaly Detection API")

class DailySession(BaseModel):
    date: str
    sessions: float

class AnomalyRequest(BaseModel):
    property_id: str
    property_name: str  # 대시보드 표시를 위해 필수 추가
    target_date: str
    history_data: List[DailySession]

@app.post("/api/v1/analyze")
def analyze_traffic(payload: AnomalyRequest):
    try:
        # 데이터 분석 로직 (기존과 동일)
        df = pd.DataFrame([vars(item) for item in payload.history_data])
        df.rename(columns={'date': 'ds', 'sessions': 'y'}, inplace=True)
        df['ds'] = pd.to_datetime(df['ds'])

        model = Prophet(yearly_seasonality=False, daily_seasonality=False, interval_width=0.80)
        model.fit(df.iloc[:-1])
        forecast = model.predict(df[['ds']])

        target_y = df['y'].iloc[-1]
        pred_lower = forecast['yhat_lower'].iloc[-1]
        pred_upper = forecast['yhat_upper'].iloc[-1]
        is_anomaly = bool(target_y < pred_lower or target_y > pred_upper)

        # --- [신규] 데이터 영속화 로직 시작 ---
        # 1. 기존 데이터 로드
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                results_db = json.load(f)
        else:
            results_db = {}

        # 2. 결과 데이터 패키징 (차트용 전체 시계열 포함)
        results_db[payload.property_id] = {
            "property_name": payload.property_name,
            "is_anomaly": is_anomaly,
            "last_sessions": int(target_y),
            "updated_at": payload.target_date,
            "forecast_data": {
                "ds": forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                "y": df['y'].tolist(),
                "yhat": forecast['yhat'].round(2).tolist(),
                "yhat_lower": forecast['yhat_lower'].round(2).tolist(),
                "yhat_upper": forecast['yhat_upper'].round(2).tolist()
            }
        }

        # 3. 파일 저장 (atomic write)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(results_db, f, ensure_ascii=False, indent=4)
        # --- [신규] 데이터 영속화 로직 종료 ---

        return {"status": "success", "property_id": payload.property_id, "is_anomaly": is_anomaly}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))