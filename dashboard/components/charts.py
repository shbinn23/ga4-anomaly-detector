import plotly.graph_objects as go
import pandas as pd

# ── 기존 전체 차트 (상세 분석 페이지용) ────────────────────────────

def render_anomaly_chart(df: pd.DataFrame, title: str):
    """3열 그리드에 최적화된 경량화 트렌드 차트를 생성합니다."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_upper'], mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_lower'], mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(244, 63, 94, 0.05)',
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat'],
        line=dict(color='#6366F1', width=1, dash='dot'),
        name='AI Target'
    ))
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['y'],
        line=dict(color='#F43F5E', width=2.5),
        name='Actual'
    ))

    fig.update_layout(
        title=f"🚨 <b>{title}</b>",
        template="plotly_white",
        height=320,
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
        showlegend=False
    )
    return fig


# ── 스파크라인 (카드 및 Trending Tickers용) ─────────────────────────

def render_sparkline(y_values: list, is_down: bool = False, height: int = 48) -> go.Figure:
    """축 없는 미니 스파크라인. is_down=True이면 빨간색, False이면 초록색."""
    color = "#F43F5E" if is_down else "#22C55E"
    fill_color = "rgba(244,63,94,0.08)" if is_down else "rgba(34,197,94,0.08)"

    fig = go.Figure(go.Scatter(
        y=y_values,
        mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=fill_color,
        hoverinfo="skip",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, showgrid=False, fixedrange=True),
        yaxis=dict(visible=False, showgrid=False, fixedrange=True),
        showlegend=False,
    )
    return fig
