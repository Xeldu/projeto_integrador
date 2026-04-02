from datetime import date

import streamlit as st

from api_client import get_recent, get_stats, get_csv, is_api_alive, reset_readings
from charts import realtime_chart, rolling_chart

st.set_page_config(
    page_title="Temperature Logger",
    page_icon="🌡️",
    layout="wide",
)

# ── Sidebar (runs once, never re-fragments) ───────────────
with st.sidebar:
    st.title("🌡️ Temperature Logger")
    st.markdown("---")

    device_filter = st.text_input("Device ID filter", value="")
    refresh_rate  = st.select_slider("Refresh every (s)", options=[3, 5, 10, 30], value=5)
    limit         = st.slider("Points to display", 50, 500, 200, step=50)

    st.markdown("---")
    st.markdown("### Export CSV")
    export_day = st.date_input("Day", value=date.today())
    if st.button("Download CSV", use_container_width=True):
        data = get_csv(str(export_day), device_filter or None)
        if data:
            st.download_button(
                "💾 Save file",
                data=data,
                file_name=f"readings_{export_day}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.warning("No data for this day.")

    st.markdown("---")
    st.markdown("### Sessão")
    if st.button(
        "Reiniciar",
        use_container_width=True,
        help="Apaga todas as medições\ne inicia uma nova sessão.",
    ):
        if reset_readings():
            st.success("Sessão reiniciada!")
        else:
            st.error("Falha ao reiniciar.")

    st.markdown("---")
    if is_api_alive():
        st.success("API online")
    else:
        st.error("API offline")

# ── Dashboard (atualiza sem recarregar a página inteira) ──
@st.fragment(run_every=refresh_rate)
def dashboard(device_filter, limit):
    device_id = device_filter or None
    df    = get_recent(device_id, limit=limit)
    stats = get_stats(device_id)

    # ── KPIs ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    if not df.empty:
        current = float(df["temperature"].iloc[-1])
        prev    = float(df["temperature"].iloc[-2]) if len(df) > 1 else current
        c1.metric("Current", f"{current:.1f} °C", f"{current - prev:+.2f}")
    else:
        c1.metric("Current", "—")

    c2.metric("Min (all)", f"{stats.get('min', '—')} °C" if stats else "—")
    c3.metric("Max (all)", f"{stats.get('max', '—')} °C" if stats else "—")
    c4.metric("Avg (all)", f"{stats.get('avg', '—')} °C" if stats else "—")

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────
    if df.empty:
        st.info("Waiting for data from the simulator…")
    else:
        st.subheader("Live readings")
        st.plotly_chart(realtime_chart(df), use_container_width=True)

        st.subheader("Raw vs rolling average")
        st.plotly_chart(rolling_chart(df), use_container_width=True)

        with st.expander(f"Table — last {min(len(df), 50)} readings"):
            display = df[["timestamp", "device_id", "temperature"]].tail(50).copy()
            display = display.sort_values("timestamp", ascending=False)
            display.columns = ["Timestamp", "Device", "°C"]
            st.dataframe(display, use_container_width=True, hide_index=True)

dashboard(device_filter, limit)
