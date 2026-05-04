import streamlit as st
import pandas as pd
import json

from utils.data_loader import load_anomaly_data, get_trending, filter_anomalies, compute_change_rate
from components.charts import render_sparkline, render_anomaly_chart
from components.styles import apply_styles
st.set_page_config(page_title="GA4 AI Control Center", layout="wide", initial_sidebar_state="collapsed")
_SPARK_CONFIG = {"displayModeBar": False, "staticPlot": True}

# ── 0. 상태 관리 (State Management) ───────────────────────────────────
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'overview'
if 'selected_property' not in st.session_state:
    st.session_state.selected_property = None

def navigate_to(view_name: str, prop_id: str = None):
    """화면 전환 및 선택된 프로퍼티 상태를 업데이트하는 라우터 함수"""
    st.session_state.current_view = view_name
    if prop_id:
        st.session_state.selected_property = prop_id
    st.rerun()

# ── 유틸 함수 ─────────────────────────────────────────────────────────
def country_flag(code: str) -> str:
    code = code.upper().strip()
    if len(code) < 2 or not code[:2].isalpha(): return "🌐"
    return chr(0x1F1E6 + ord(code[0]) - ord("A")) + chr(0x1F1E6 + ord(code[1]) - ord("A"))

def rate_color(rate: float) -> str:
    return "#F43F5E" if rate < 0 else "#22C55E"

def colored_rate(rate: float, size: str = "1em") -> str:
    sign = "+" if rate >= 0 else ""
    return f"<span style='color:{rate_color(rate)}; font-weight:700; font-size:{size}'>{sign}{rate:.1f}%</span>"


# =====================================================================
# Level 1: Overview (메인 대시보드)
# =====================================================================
def render_sessions_card(all_data):
    with st.container(border=True, height=420): # [교정] UI 무결성을 위한 높이 강제 고정
        st.markdown("<h5 style='margin-bottom:0;'>SESSIONS</h5>", unsafe_allow_html=True)
        st.write("")

        col_metrics, col_charts = st.columns([1.4, 2]) # [교정] 텍스트 짤림 방지 비율

        with col_metrics:
            total_sessions = sum([v["last_sessions"] for v in all_data.values()]) if all_data else 0
            st.metric("Total Sessions", f"{total_sessions:,}", "Anomaly (+12%)")
            st.metric("Daily Unique", "88k", "+5%")
            st.metric("Mobile %", "65%", "+8 pts")

        with col_charts:
            sample_y = list(all_data.values())[0]["forecast_data"]["y"] if all_data else [0]*10
            st.caption("Daily")
            st.plotly_chart(render_sparkline(sample_y[-14:], is_down=False, height=40), use_container_width=True, config=_SPARK_CONFIG, key="spark_sessions_daily")
            st.caption("Weekly")
            st.plotly_chart(render_sparkline(sample_y[-30::2], is_down=True, height=40), use_container_width=True, config=_SPARK_CONFIG, key="spark_sessions_weekly")
            st.caption("Mobile")
            st.plotly_chart(render_sparkline(sample_y[-14:], is_down=True, height=40), use_container_width=True, config=_SPARK_CONFIG, key="spark_sessions_mobile")

        st.write("")
        # [교정] Level 2로 이동하는 라우팅 함수 연결
        if st.button("Detail to Sessions", use_container_width=True, key="btn_sessions_detail"):
            navigate_to('sessions_detail')

# ── 2, 3, 4 섹션 (개발 대기 처리) ───────────────────────────────────────────
def render_pending_card(title: str):
    with st.container(border=True, height=420):
        st.markdown(f"<h5 style='margin-bottom:0;'>{title}</h5>", unsafe_allow_html=True)
        st.write("")
        st.write("")
        # 명시적인 개발 대기 알림
        st.info(f"**[ 🚧 개발 대기 ]**\n\n해당 도메인의 데이터 파이프라인이 아직 연결되지 않았습니다.\n\nPhase 2 - Step 5 (n8n 데이터 병렬 수집) 완료 후 대시보드에 연동됩니다.")

def render_events_card():
    render_pending_card("EVENT COUNT")

def render_revenue_card():
    render_pending_card("REVENUE")

def render_ecommerce_card():
    render_pending_card("ECOMMERCE EVENTS")

def render_trending_sidebar(all_data):
    with st.container(border=True, height=860):
        st.markdown("<h6 style='margin-bottom:0;'>TRENDING</h6>", unsafe_allow_html=True)
        st.write("")

        trending = get_trending(all_data, n=8) if all_data else []
        for pid, v, rate in trending:
            is_down = rate < 0
            code = v["property_name"][:2].upper()
            flag = country_flag(code)
            color = "#22C55E" if rate >= 0 else "#F43F5E"
            sign = "+" if rate >= 0 else ""

            st.markdown(
                f"<div style='display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: -10px;'>"
                f"<span style='font-size:0.9rem; font-weight:bold;'>{flag} {code}</span>"
                f"<span style='color:{color}; font-weight:800; font-size:1.1rem;'>{sign}{rate:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True
            )

            fig = render_sparkline(v["forecast_data"]["y"][-14:], is_down=is_down, height=35)
            st.plotly_chart(fig, use_container_width=True, config=_SPARK_CONFIG, key=f"trend_narrow_{pid}")
            st.markdown("<hr style='margin: 0.2em 0 0.8em 0; opacity: 0.3;'/>", unsafe_allow_html=True)

def view_overview(all_data):
    st.markdown("<h3>GA4 Traffic Board</h3>", unsafe_allow_html=True)
    st.write("")

    main_col, side_col = st.columns([8.2, 1.8])

    with main_col:
        r1c1, r1c2 = st.columns(2)
        with r1c1: render_sessions_card(all_data)
        with r1c2: render_events_card()

        r2c1, r2c2 = st.columns(2)
        with r2c1: render_revenue_card()
        with r2c2: render_ecommerce_card()

    with side_col:
        render_trending_sidebar(all_data)


# =====================================================================
# Level 2: Sessions Detail (기존 3열 그리드 이상치 화면)
# =====================================================================
def view_sessions_detail(all_data):
    col_back, col_title = st.columns([1, 10])
    with col_back:
        if st.button("← Back", key="btn_back_to_overview"):
            navigate_to('overview')
    with col_title:
        st.markdown("<h3 style='margin-top:-10px;'>🔍 Sessions Anomaly Detail</h3>", unsafe_allow_html=True)

    st.divider()

    anomalies = filter_anomalies(all_data)
    if not anomalies:
        st.success("✅ 현재 모든 Property가 정상 범위를 유지하고 있습니다.")
        return

    st.subheader(f"📍 이상 트래픽 집중 관제 · {len(anomalies)}건")
    st.write("")

    items = list(anomalies.items())
    for i in range(0, len(items), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j >= len(items): break
            prop_id, res = items[i + j]
            rate = compute_change_rate(res)

            with cols[j]:
                with st.container(border=True):
                    chart_df = pd.DataFrame(res["forecast_data"])
                    fig = render_anomaly_chart(chart_df, res["property_name"])
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"detail_sessions_chart_{prop_id}")

                    st.markdown(
                        f"<div style='font-size:0.9rem'>ID: `{prop_id}` | 실제: **{res['last_sessions']:,}** | {colored_rate(rate)}</div>",
                        unsafe_allow_html=True,
                    )

                    # [핵심] Level 3로 진입하기 위한 프로퍼티별 딥다이브 버튼
                    st.write("")
                    if st.button(f"Analyze Channels 〉", use_container_width=True, key=f"btn_analyze_{prop_id}"):
                        navigate_to('channel_detail', prop_id=prop_id)


# =====================================================================
# Level 3: Channel Detail (AI Anomaly Deep-Dive)
# =====================================================================
def view_channel_detail(all_data, prop_id):
    """
    특정 프로퍼티의 채널별 Prophet 분석 결과를 상세 렌더링합니다.
    이상 징후가 발견된 채널을 우선적으로 노출합니다.
    """
    # ── 1. 상단 내비게이션 및 헤더 ──────────────────────────────────────
    col_back, col_title = st.columns([1, 10])

    with col_back:
        # 세션 상세 화면으로 돌아가는 버튼
        if st.button("← Back", key="btn_back_to_sessions"):
            navigate_to('sessions_detail')

    with col_title:
        prop_info = all_data.get(prop_id, {})
        prop_name = prop_info.get("property_name", prop_id)
        st.markdown(f"<h3 style='margin-top:-10px;'>🌐 Channel AI Insight: {prop_name}</h3>", unsafe_allow_html=True)

    st.divider()

    # ── 2. 데이터 로드 (AI 분석 결과) ──────────────────────────────────
    try:
        with open('data/channel_anomaly_db.json', 'r') as f:
            db = json.load(f)

        # 현재 선택된 프로퍼티의 채널 분석 데이터 추출
        prop_analysis = db.get(prop_id, {})

        if not prop_analysis:
            st.info(f"선택하신 ID(`{prop_id}`)에 대한 채널별 AI 분석 데이터가 아직 적재되지 않았습니다.")
            st.caption("Phase 2 - Step 5 파이프라인 실행 후 데이터가 나타납니다.")
            return

        # ── 3. 채널 필터링 (이상 vs 정상) ───────────────────────────────
        anomalous_channels = {k: v for k, v in prop_analysis.items() if v.get("is_anomaly")}
        normal_channels = {k: v for k, v in prop_analysis.items() if not v.get("is_anomaly")}

        # ── 4. 이상 징후 채널 섹션 (우선 노출) ───────────────────────────
        st.subheader(f"🚨 Detected Anomalies ({len(anomalous_channels)})")

        if anomalous_channels:
            ch_names = list(anomalous_channels.keys())
            for i in range(0, len(ch_names), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j >= len(ch_names): break
                    name = ch_names[i + j]
                    res = anomalous_channels[name]

                    with cols[j]:
                        with st.container(border=True):
                            chart_df = pd.DataFrame(res["forecast_data"])
                            fig = render_anomaly_chart(chart_df, f"Channel: {name}")
                            st.plotly_chart(fig, use_container_width=True, key=f"ch_anom_{prop_id}_{name}")

                            st.error(f"⚠️ {name} 채널 이상 징후 감지")
                            st.caption(f"최종 세션: {res.get('last_sessions', 0):,}")
        else:
            st.success("✅ 모든 채널이 AI 예측 범위 내에서 안정적으로 작동하고 있습니다.")

        # ── 5. 정상 채널 섹션 (참조용 익스팬더) ──────────────────────────
        if normal_channels:
            st.write("")
            with st.expander("🔍 View Normal Channels (Reference)"):
                norm_names = list(normal_channels.keys())
                for i in range(0, len(norm_names), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j >= len(norm_names): break
                        name = norm_names[i + j]
                        res = normal_channels[name]

                        with cols[j]:
                            chart_df = pd.DataFrame(res["forecast_data"])
                            fig = render_anomaly_chart(chart_df, f"Normal: {name}")
                            st.plotly_chart(fig, use_container_width=True, key=f"ch_norm_{prop_id}_{name}")
                            st.caption(f"✓ {name} 정상")

    except FileNotFoundError:
        st.error("`data/channel_anomaly_db.json` 파일을 찾을 수 없습니다. 백엔드 적재 프로세스를 확인하세요.")
    except Exception as e:
        st.error(f"데이터 렌더링 중 오류 발생: {str(e)}")


# =====================================================================
# Main Router
# =====================================================================
def main():
    apply_styles()
    all_data = load_anomaly_data()

    # Controller: 현재 상태에 따라 뷰를 렌더링
    if st.session_state.current_view == 'overview':
        view_overview(all_data)
    elif st.session_state.current_view == 'sessions_detail':
        view_sessions_detail(all_data)
    elif st.session_state.current_view == 'channel_detail':
        view_channel_detail(all_data, st.session_state.selected_property)

if __name__ == "__main__":
    main()