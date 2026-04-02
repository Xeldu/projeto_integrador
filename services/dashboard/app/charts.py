import pandas as pd
import plotly.graph_objects as go


def realtime_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["temperature"],
        mode="lines+markers",
        line=dict(color="#4f8ef7", width=2),
        marker=dict(size=4),
        fill="tozeroy",
        fillcolor="rgba(79,142,247,0.07)",
        name="temperature",
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="time", showgrid=True, gridcolor="#e5e7eb"),
        yaxis=dict(title="°C",   showgrid=True, gridcolor="#e5e7eb"),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        uirevision="constant",
    )
    return fig


def rolling_chart(df: pd.DataFrame) -> go.Figure:
    df = df.copy()
    df["rolling"] = df["temperature"].rolling(window=6, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["temperature"],
        mode="lines", name="raw",
        line=dict(color="#a5b4fc", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["rolling"],
        mode="lines", name="6-pt avg",
        line=dict(color="#6366f1", width=2.5),
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="time", gridcolor="#e5e7eb"),
        yaxis=dict(title="°C",   gridcolor="#e5e7eb"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=1.1),
        uirevision="constant",
    )
    return fig
