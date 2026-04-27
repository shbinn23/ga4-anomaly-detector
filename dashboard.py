import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import datetime

# 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "results_db.json")

st.set_page_config(page_title="GA4 AI Control Center", layout="wide")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def render_main_trend(df, property_name):
    fig = go.Figure()

    # 1. AI 신뢰 구간 (FORTRESS 스타일)
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_upper'], mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_lower'], mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(99, 102, 241, 0.08)',
        name='AI 예측 범위 (80%)', hoverinfo='skip'
    ))

    # 2. AI 예측선
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat'],
        line=dict(color='#6366F1', width=2, dash='dot'),
        name='AI 예측선'
    ))

    # 3. 실제 세션 데이터
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['y'],
        line=dict(color='#F43F5E', width=3.5),
        name='현재 실데이터'
    ))

    fig.update_layout(
        title=f"<b>{property_name}</b> 세션 트렌드 분석",
        template="plotly_white", height=500, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def main():
    st.title("🛡️ GA4 FORTRESS 센터")
    data = load_data()

    if not data:
        st.info("데이터가 없습니다. n8n 워크플로우를 먼저 실행하세요.")
        return

    # 지표 렌더링 (생략 - 기존 코드와 동일)
    # ...

    st.sidebar.header("Filter & Select")
    selected_id = st.sidebar.selectbox(
        "분석할 프로퍼티 선택",
        options=list(data.keys()),
        format_func=lambda x: data[x]['property_name']
    )

    target_data = data[selected_id]
    st.subheader(f"📈 {target_data['property_name']} 상세 분석")

    # [교정] 저장된 데이터를 DataFrame으로 변환하여 차트 생성
    chart_df = pd.DataFrame(target_data['forecast_data'])
    fig = render_main_trend(chart_df, target_data['property_name'])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # 하단 테이블 렌더링 (생략 - 기존 코드와 동일)
    # ...

if __name__ == "__main__":
    main()