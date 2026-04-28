import plotly.graph_objects as go
import pandas as pd

def render_anomaly_chart(df: pd.DataFrame, title: str):
    """3열 그리드에 최적화된 경량화 트렌드 차트를 생성합니다."""
    fig = go.Figure()

    # 1. AI 신뢰 구간 (Shaded Area)
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_upper'], mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat_lower'], mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(244, 63, 94, 0.05)',
        showlegend=False, hoverinfo='skip'
    ))

    # 2. AI 기대선 (Dashed)
    fig.add_trace(go.Scatter(
        x=df['ds'], y=df['yhat'],
        line=dict(color='#6366F1', width=1, dash='dot'),
        name='AI Target'
    ))

    # 3. 실제 데이터 (Solid)
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