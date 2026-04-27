import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import pandas as pd
from prophet import Prophet
import plotly.graph_objects as go

# 1. 설정 및 디렉토리 관리
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
REPORT_DIR = "static/reports"
DB_FILE = "results_db.json"
os.makedirs(REPORT_DIR, exist_ok=True)

app = FastAPI(title="GA4 Anomaly Control Center")
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")

# 85개 프로퍼티의 최신 상태를 저장할 인메모리 DB
# 서버 재시작 시 데이터 유지를 위해 파일 저장 로직 포함
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        results_db = json.load(f)
else:
    results_db = {}

class DailySession(BaseModel):
    date: str
    sessions: float

class AnomalyRequest(BaseModel):
    property_id: str
    property_name: str
    target_date: str
    history_data: List[DailySession]

# --- [API] 분석 및 결과 업데이트 ---
@app.post("/api/v1/analyze")
async def analyze_traffic(payload: AnomalyRequest):
    try:
        df = pd.DataFrame([vars(d) for d in payload.history_data])
        df['ds'] = pd.to_datetime(df['date'])
        df = df.sort_values('ds').reset_index(drop=True)

        # Prophet 분석
        m = Prophet(interval_width=0.8, yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False)
        m.fit(df[['ds', 'y']])
        forecast = m.predict(df[['ds']])

        # 이상치 판별
        last_actual = df['y'].iloc[-1]
        last_lower = forecast['yhat_lower'].iloc[-1]
        last_upper = forecast['yhat_upper'].iloc[-1]
        is_anomaly = not (last_lower <= last_actual <= last_upper)

        # Plotly 리포트 생성
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['ds'], y=df['y'], name='Actual', mode='lines+markers'))
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name='Predicted', line=dict(dash='dot')))
        fig.update_layout(title=f"Trend: {payload.property_name}", template="plotly_white")

        file_name = f"{payload.property_id}_report.html"
        fig.write_html(os.path.join(REPORT_DIR, file_name))

        # 데이터베이스 업데이트
        results_db[payload.property_id] = {
            "property_name": payload.property_name,
            "last_sessions": int(last_actual),
            "expected_range": f"{int(last_lower)} ~ {int(last_upper)}",
            "is_anomaly": is_anomaly,
            "report_url": f"/reports/{file_name}",
            "updated_at": payload.target_date
        }

        with open(DB_FILE, "w") as f:
            json.dump(results_db, f)

        return {"status": "success", "is_anomaly": is_anomaly}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- [UI] 메인 관제 대시보드 ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    df_results = pd.DataFrame.from_dict(results_db, orient='index')

    if df_results.empty:
        return "<html><body><h1>No data yet. Run n8n workflow.</h1></body></html>"

    # 이상치 개수 계산
    anomaly_count = df_results['is_anomaly'].sum()
    total_count = len(df_results)

    # HTML 템플릿 (Bootstrap 기반)
    rows = ""
    for pid, res in results_db.items():
        status_badge = '<span style="color:red; font-weight:bold;">⚠️ ANOMALY</span>' if res['is_anomaly'] else '<span style="color:green;">✅ NORMAL</span>'
        rows += f"""
        <tr>
            <td>{res['property_name']}</td>
            <td>{res['last_sessions']:,}</td>
            <td>{res['expected_range']}</td>
            <td>{status_badge}</td>
            <td><a href="{res['report_url']}" target="_blank" style="text-decoration:none; color:#007bff;">View Report</a></td>
            <td><small>{res['updated_at']}</small></td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GA4 Control Center</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f8f9fa; padding: 20px; }}
            .card {{ border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .table {{ background: white; border-radius: 10px; overflow: hidden; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1>📊 GA4 Anomaly Detection Dashboard</h1>
                <div class="text-end">
                    <span class="badge bg-danger fs-5">Anomalies: {anomaly_count}</span>
                    <span class="badge bg-primary fs-5">Total: {total_count}</span>
                </div>
            </div>
            <div class="card p-3">
                <table class="table table-hover mt-3">
                    <thead class="table-dark">
                        <tr>
                            <th>Property Name</th>
                            <th>Latest Sessions</th>
                            <th>Expected Range (80%)</th>
                            <th>Status</th>
                            <th>Analysis</th>
                            <th>Target Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """