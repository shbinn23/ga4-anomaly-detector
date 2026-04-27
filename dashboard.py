import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import datetime

# 설정 및 데이터 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "results_db.json")

st.set_page_config(page_title="GA4 Anomalies Tracker", layout="wide")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def render_anomaly_chart(df, property_name):
    """그리드용 경량화된 트렌드 차트"""
    fig = go.Figure()
    # AI 신뢰 구간
    fig.add_trace(go.Scatter(x=df['ds'], y=df['yhat_upper'], mode='lines', line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=df['ds'], y=df['yhat_lower'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(244, 63, 94, 0.05)', showlegend=False))
    # 예측선 및 실제 데이터
    fig.add_trace(go.Scatter(x=df['ds'], y=df['yhat'], line=dict(color='#6366F1', width=1, dash='dot'), name='AI Target'))
    fig.add_trace(go.Scatter(x=df['ds'], y=df['y'], line=dict(color='#F43F5E', width=2.5), name='Actual'))

    fig.update_layout(
        title=f"🚨 <b>{property_name}</b>",
        template="plotly_white", height=300, margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified", showlegend=False
    )
    return fig

def main():
    st.title("🛡️ GA4 이상 탐지 집중 관제소")
    data = load_data()

    if not data:
        st.info("데이터가 없습니다. n8n 파이프라인을 가동하십시오.")
        return

    # 1. 이상치 데이터 필터링 (Logic: is_anomaly == True)
    anomalies = {k: v for k, v in data.items() if v.get('is_anomaly') == True}
    total_count = len(data)
    anomaly_count = len(anomalies)

    # 2. 상단 요약 배너
    c1, c2, c3 = st.columns(3)
    c1.metric("전체 모니터링", f"{total_count}개")
    c2.metric("위험 프로퍼티 (🚨)", f"{anomaly_count}개", delta=anomaly_count, delta_color="inverse")
    c3.metric("최종 갱신", datetime.now().strftime("%H:%M"))

    st.markdown("---")

    # 3. 3열 그리드 시각화 로직
    if anomaly_count > 0:
        st.subheader(f"📍 발견된 이상 탐지 항목 ({anomaly_count})")

        # 3열씩 루프를 돌며 배치
        cols = st.columns(3)
        for i, (pid, res) in enumerate(anomalies.items()):
            col_idx = i % 3
            with cols[col_idx]:
                chart_df = pd.DataFrame(res['forecast_data'])
                fig = render_anomaly_chart(chart_df, res['property_name'])
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.caption(f"Last Actual: {res['last_sessions']:,} | Updated: {res['updated_at']}")
    else:
        st.success("✅ 모든 프로퍼티가 AI 예측 범위 내에서 안정적으로 운영되고 있습니다.")

if __name__ == "__main__":
    main()