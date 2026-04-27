import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import datetime

# 설정 및 데이터 로드
DB_FILE = "results_db.json"
st.set_page_config(page_title="GA4 AI Control Center", layout="wide")

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def render_main_trend(df, property_name):
    """FORTRESS 스타일의 GA4 세션 추이 차트 생성"""
    fig = go.Figure()

    # 1. AI 신뢰 구간 (Shaded Area)
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_upper'], mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_lower'], mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(99, 102, 241, 0.1)',
        name='AI 예측 범위 (80%)', hoverinfo='skip'
    ))

    # 2. AI 예측선 (Dashed Line)
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat'],
        line=dict(color='#6366F1', width=2, dash='dot'),
        name='AI 기대치'
    ))

    # 3. 실제 세션 데이터 (Solid Line)
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['y'],
        line=dict(color='#F43F5E', width=3.5),
        name='실제 세션 수'
    ))

    fig.update_layout(
        title=f"<b>{property_name}</b> 세션 트렌드 분석",
        template="plotly_white",
        height=450,
        hovermode="x unified"
    )
    return fig

def main():
    st.title("🛡️ GA4 FORTRESS 센터")
    data = load_data()

    if not data:
        st.info("데이터가 없습니다. n8n 워크플로우를 먼저 실행하세요.")
        return

    # 상단 요약 지표 (Metrics)
    total = len(data)
    anomalies = sum(1 for v in data.values() if v.get('is_anomaly'))

    m1, m2, m3 = st.columns(3)
    m1.metric("총 모니터링 프로퍼티", f"{total}개")
    m2.metric("🚨 현재 이상 탐지", f"{anomalies}건", delta=f"{anomalies}건", delta_color="inverse")
    m3.metric("마지막 업데이트", datetime.now().strftime("%H:%M"))

    st.markdown("---")

    # 사이드바: 프로퍼티 선택
    st.sidebar.header("Filter & Select")
    selected_id = st.sidebar.selectbox(
        "분석할 프로퍼티 선택",
        options=list(data.keys()),
        format_func=lambda x: data[x]['property_name']
    )

    # 메인 섹션: 트렌드 차트
    target_data = data[selected_id]
    # 실제 구현 시에는 FastAPI가 저장한 상세 시계열 데이터(history_data)를 기반으로 DataFrame 생성
    # 여기서는 예시 구조만 제안합니다.
    st.subheader(f"📈 {target_data['property_name']} 상세 분석")

    #     # 실제 차트 렌더링 (FastAPI가 전송한 예측 데이터를 시각화)
    # fig = render_main_trend(pd.DataFrame(target_data['forecast']), target_data['property_name'])
    # st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 하단 전체 목록 (Control Center Table)
    st.subheader("📋 전체 프로퍼티 관리 현황")
    df_display = pd.DataFrame.from_dict(data, orient='index')
    st.dataframe(
        df_display[['property_name', 'last_sessions', 'is_anomaly', 'updated_at']],
        use_container_width=True,
        hide_index=True
    )

if __name__ == "__main__":
    main()