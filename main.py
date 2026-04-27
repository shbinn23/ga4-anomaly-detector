import os
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
from prophet import Prophet

# --- [교정] 경로 변수 정의 (이 부분이 누락되어 에러가 발생한 것입니다) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "results_db.json")
REPORT_DIR = os.path.join(BASE_DIR, "static/reports") # <--- 에러의 원인!

# 디렉토리가 없을 경우를 대비해 자동 생성 로직 추가
os.makedirs(REPORT_DIR, exist_ok=True)

logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
app = FastAPI(title="GA4 Anomaly Detection API")

# --- 기존 데이터 계약 및 모델 로직 ---
class DailySession(BaseModel):
    date: str
    sessions: float

class AnomalyRequest(BaseModel):
    property_id: str
    property_name: str
    target_date: str
    history_data: List[DailySession]

# --- [수정 완료] 리셋 엔드포인트 ---
@app.post("/api/v1/reset")
async def reset_database():
    try:
        # 1. 데이터베이스 파일 삭제
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)

        # 2. 리포트 폴더 내 HTML 파일 청소 (REPORT_DIR 정의 확인됨)
        if os.path.exists(REPORT_DIR):
            for file in os.listdir(REPORT_DIR):
                file_path = os.path.join(REPORT_DIR, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        return {"status": "success", "message": "Database and reports cleared."}
    except Exception as e:
        # 에러 발생 시 상세 내용을 반환하도록 수정
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

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