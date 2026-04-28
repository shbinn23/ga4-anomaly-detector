import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_loader import load_anomaly_data, filter_anomalies
from components.charts import render_anomaly_chart

st.set_page_config(page_title="GA4 AI Control Center", layout="wide")

def main():
    st.title("🛡️ Google Analytics AI Monitoring Dashboard")

    # 1. 데이터 로드 및 필터링
    all_data = load_anomaly_data()
    if not all_data:
        st.info("현재 분석된 데이터가 없습니다. n8n 워크플로우를 먼저 실행하세요.")
        return

    anomalies = filter_anomalies(all_data)

    # 2. 상단 헤더 지표
    c1, c2, c3 = st.columns(3)
    c1.metric("총 모니터링 Property", f"{len(all_data)}개")
    c2.metric("위험 탐지 Property", f"{len(anomalies)}건", delta=len(anomalies), delta_color="inverse")
    c3.metric("최종 업데이트", datetime.now().strftime("%H:%M"))

    st.markdown("---")

    # 3. 3열 그리드 시각화
    if anomalies:
        st.subheader(f"📍 이상 트래픽 집중 관제 ({len(anomalies)}건)")

        # 데이터를 3개씩 나누어 행 단위로 렌더링
        anomaly_items = list(anomalies.items())
        for i in range(0, len(anomaly_items), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(anomaly_items):
                    prop_id, res = anomaly_items[i + j]
                    with cols[j]:
                        chart_df = pd.DataFrame(res['forecast_data'])
                        fig = render_anomaly_chart(chart_df, res['property_name'])
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                        st.caption(f"ID: {prop_id} | 실제 세션: {res['last_sessions']:,}")
    else:
        st.success("✅ 현재 모든 Property가 정상 범위를 유지하고 있습니다.")

if __name__ == "__main__":
    main()