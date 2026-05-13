import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.optimize import curve_fit

CHANNEL_COLORS = [
    "#4f8ef7", "#f97316", "#22c55e", "#a855f7",
    "#ef4444", "#06b6d4", "#eab308",
]


def multichannel_timeseries(df: pd.DataFrame, unit: str,
                             reference_channel: int | None = None,
                             height: int = 400) -> go.Figure:
    """Time series chart showing all channels over time."""
    fig = go.Figure()
    if df.empty:
        fig.update_layout(height=height, plot_bgcolor="white", paper_bgcolor="white",
                          xaxis=dict(title="time"), yaxis=dict(title=unit))
        return fig

    channels = sorted(df["channel"].unique())
    for i, ch in enumerate(channels):
        ch_df = df[df["channel"] == ch].sort_values("timestamp")
        is_ref = ch == reference_channel
        fig.add_trace(go.Scatter(
            x=ch_df["timestamp"],
            y=ch_df["value"].astype(float),
            mode="lines+markers",
            name=f"Ch {ch}" + (" (ref)" if is_ref else ""),
            line=dict(
                color=CHANNEL_COLORS[i % len(CHANNEL_COLORS)],
                width=2.5 if is_ref else 1.8,
            ),
            marker=dict(size=5 if is_ref else 4),
        ))

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(title="time", gridcolor="#e5e7eb", showgrid=True),
        yaxis=dict(title=unit,   gridcolor="#e5e7eb", showgrid=True),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.15, x=0),
    )
    return fig


def test_chart(df: pd.DataFrame, reference_channel: int,
               curve_fit_result: dict | None = None,
               unit: str = "°C", height: int = 450) -> go.Figure:
    """Multi-channel time series for a finished/running test, with optional curve fit."""
    fig = go.Figure()
    if df.empty:
        return fig

    channels = sorted(df["channel"].unique())
    for i, ch in enumerate(channels):
        ch_df = df[df["channel"] == ch].sort_values("timestamp")
        is_ref = ch == reference_channel
        fig.add_trace(go.Scatter(
            x=ch_df["timestamp"],
            y=ch_df["value"].astype(float),
            mode="lines+markers",
            name=f"Ch {ch}" + (" (ref)" if is_ref else ""),
            line=dict(
                color=CHANNEL_COLORS[i % len(CHANNEL_COLORS)],
                width=2.5 if is_ref else 1.8,
                dash="solid" if is_ref else "dot",
            ),
            marker=dict(size=6 if is_ref else 4),
        ))

    if curve_fit_result and curve_fit_result.get("success"):
        ref_df = df[df["channel"] == reference_channel].sort_values("timestamp")
        t0     = ref_df["timestamp"].iloc[0]
        ts_fit = [t0 + pd.Timedelta(seconds=s)
                  for s in curve_fit_result["t_fit"]]
        fig.add_trace(go.Scatter(
            x=ts_fit,
            y=curve_fit_result["y_fit"],
            mode="lines",
            name="Fitted curve",
            line=dict(color="#f43f5e", width=2, dash="dashdot"),
        ))

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(title="time",  gridcolor="#e5e7eb", showgrid=True),
        yaxis=dict(title=unit,    gridcolor="#e5e7eb", showgrid=True),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.15, x=0),
    )
    return fig


def thermal_model(t, T_amb, delta_T, tau):
    return T_amb + delta_T * (1 - np.exp(-t / tau))


def fit_thermal_curve(df: pd.DataFrame, channel: int) -> dict:
    # Ensure channel is int and filter data for this channel only
    channel = int(channel)
    ch_df = df[df["channel"].astype(int) == channel].sort_values("timestamp").copy()
    
    if len(ch_df) < 2:
        return {"success": False, "reason": f"Not enough points for channel {channel} (need ≥ 2)"}
    
    if len(ch_df) < 4:
        return {"success": False, "reason": f"Not enough points for channel {channel} (need ≥ 4 for accurate fit)"}

    ch_df["t_sec"] = (ch_df["timestamp"] - ch_df["timestamp"].iloc[0]).dt.total_seconds()
    t = ch_df["t_sec"].values.astype(float)
    y = ch_df["value"].astype(float).values

    T_amb_guess   = float(y[0])
    delta_T_guess = float(y[-1] - y[0])
    tau_guess     = float(t[-1] / 3) if t[-1] > 0 else 600.0

    try:
        popt, pcov = curve_fit(
            thermal_model, t, y,
            p0=[T_amb_guess, delta_T_guess, tau_guess],
            bounds=([0, 0, 1], [200, 300, 1e6]),
            maxfev=10000,
        )
        T_amb, delta_T, tau = popt
        perr  = np.sqrt(np.diag(pcov))
        t_fit = np.linspace(0, t[-1] * 1.05, 300)
        y_fit = thermal_model(t_fit, *popt)

        y_pred = thermal_model(t, *popt)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        return {
            "success":     True,
            "T_amb":       round(float(T_amb),    2),
            "delta_T":     round(float(delta_T),  2),
            "tau_seconds": round(float(tau),       1),
            "tau_minutes": round(float(tau) / 60,  2),
            "T_steady":    round(float(T_amb + delta_T), 2),
            "r_squared":   round(float(r2),        4),
            "equation":    f"T(t) = {T_amb:.2f} + {delta_T:.2f} × (1 − e^(−t/{tau:.1f}s))",
            "t_seconds":   t.tolist(),
            "t_fit":       t_fit.tolist(),
            "y_fit":       y_fit.tolist(),
            "perr":        perr.tolist(),
        }
    except Exception as e:
        return {"success": False, "reason": str(e)}
