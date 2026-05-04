import streamlit as st

_CSS = """
<style>
    /* ── 사이드바 완전 제거 ─────────────────────────── */
    [data-testid="stSidebar"]         { display: none !important; }
    [data-testid="collapsedControl"]  { display: none !important; }

    /* ── 콘텐츠 중앙 집중 + 좌우 여백 및 폰트 축소 ────── */
    html, body, [class*="css"] {
        font-size: 14px !important; /* 전체 폰트 크기 축소 */
    }
    
    .block-container {
        max-width: 1300px     !important; /* 중앙 집중형 너비 */
        padding-top: 2rem     !important;
        padding-bottom: 2rem  !important;
        margin: 0 auto        !important; 
    }

    /* ── 컨테이너 및 텍스트 마진 최적화 ───────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-radius: 8px !important;
        padding: 1rem !important;
        background-color: #ffffff;
    }
    
    /* ── 메트릭 위젯(st.metric) 컴팩트화 ──────────────── */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }

    /* ── 버튼(Deep dive) 스타일링 ───────────────────── */
    .stButton > button {
        border-radius: 20px !important;
        border: 1px solid #d1d5db !important;
        background-color: transparent !important;
        color: #374151 !important;
        font-weight: 600 !important;
        padding: 0.2rem 1rem !important;
        font-size: 0.85rem !important;
    }
    .stButton > button:hover {
        border-color: #6366F1 !important;
        color: #6366F1 !important;
    }
</style>
"""

def apply_styles():
    st.markdown(_CSS, unsafe_allow_html=True)