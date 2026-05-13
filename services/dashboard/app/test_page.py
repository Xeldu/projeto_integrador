"""
Shared logic for temperature and pressure test pages.
Call render_test_page(sensor_type, unit) from each page file.
"""
import time
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from api_client import (
    get_machines, get_live_channels, get_live_history,
    start_test, add_test_readings, finish_test, get_test, get_tests_today,
)
from charts import multichannel_timeseries, test_chart, fit_thermal_curve

N_CHANNELS        = 7
SNAPSHOT_INTERVAL = 10   # 10 minutes
DELTA_STOP        = 0.1   # °C — auto-stop threshold
LIVE_REFRESH      = 10    # seconds between live chart updates


def _readings_df(test: dict) -> pd.DataFrame:
    rows = test.get("readings", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["value"]     = df["value"].astype(float)
    return df


def _generate_html_report(test: dict, df: pd.DataFrame, fit: dict, unit: str) -> str:
    """Generate a complete HTML report with interactive Plotly chart."""
    from plotly.io import to_html
    
    machine = test["machine"]
    ref_ch  = test["reference_channel"]
    
    # Generate Plotly HTML
    fig = test_chart(df, ref_ch, fit, unit=unit, height=480)
    plotly_html = to_html(fig, include_plotlyjs='cdn', div_id="test-chart")
    
    # Machine info HTML
    machine_html = f"""
    <h2>Machine Information</h2>
    <table style="border-collapse: collapse; width: 100%;">
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>Name:</strong></td>
            <td style="padding: 8px;">{machine["name"]}</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>Power:</strong></td>
            <td style="padding: 8px;">{machine.get('power_kw') or '—'} kW</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>Voltage:</strong></td>
            <td style="padding: 8px;">{machine.get('voltage_v') or '—'} V</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>Current:</strong></td>
            <td style="padding: 8px;">{machine.get('current_a') or '—'} A</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>Resistance:</strong></td>
            <td style="padding: 8px;">{machine.get('resistance_ohm') or '—'} Ω</td>
        </tr>
    """
    
    extra = machine.get("extra_fields") or []
    for ef in extra:
        machine_html += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>{ef["name"]}:</strong></td>
            <td style="padding: 8px;">{ef['value']} {ef['unit']}</td>
        </tr>
        """
    
    if machine.get("notes"):
        machine_html += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px;"><strong>Notes:</strong></td>
            <td style="padding: 8px;">{machine['notes']}</td>
        </tr>
        """
    
    machine_html += "</table>"
    
    # Curve fit HTML
    curve_html = "<h2>Thermal Curve Analysis</h2>"
    if fit["success"]:
        curve_html += f"""
        <table style="border-collapse: collapse; width: 100%;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;"><strong>Ambient T:</strong></td>
                <td style="padding: 8px;">{fit['T_amb']} {unit}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;"><strong>ΔT rise:</strong></td>
                <td style="padding: 8px;">{fit['delta_T']} {unit}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;"><strong>τ (time constant):</strong></td>
                <td style="padding: 8px;">{fit['tau_minutes']} min</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;"><strong>R²:</strong></td>
                <td style="padding: 8px;">{fit['r_squared']}</td>
            </tr>
        </table>
        <p><code>{fit['equation']}</code></p>
        <p><em>τ = thermal time constant. Motor reaches ~63% of total rise after 1τ, ~95% after 3τ, ~99% after 5τ.</em></p>
        """
    else:
        curve_html += f"<p>Curve fit not available: {fit.get('reason', 'unknown')}</p>"
    
    # Table HTML
    pivot = df.pivot_table(index="timestamp", columns="channel",
                           values="value", aggfunc="mean")
    pivot.columns = [f"Ch {c} ({unit})" for c in pivot.columns]
    pivot.index = pivot.index.strftime("%Y-%m-%d %H:%M:%S")
    table_html = pivot.to_html(border=1, justify='center')
    
    # Complete HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Test #{test['id']} Report</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #1f77b4;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #555;
                margin-top: 30px;
            }}
            table {{
                margin: 15px 0;
            }}
            code {{
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 4px;
                display: block;
                overflow-x: auto;
            }}
            #test-chart {{
                width: 100%;
                height: 600px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test #{test['id']} — {machine['name']}</h1>
            <p><strong>Status:</strong> {test['status']} | <strong>Reference Channel:</strong> Ch {ref_ch}</p>
            
            {machine_html}
            
            <h2>Readings Chart</h2>
            {plotly_html}
            
            {curve_html}
            
            <h2>Measurements Table</h2>
            {table_html}
        </div>
    </body>
    </html>
    """
    
    return html


def render_report(test: dict, unit: str):
    """Full report: machine info, chart, curve fit, table, PNG export."""
    df      = _readings_df(test)
    machine = test["machine"]
    ref_ch  = test["reference_channel"]

    # Machine info
    st.markdown("#### Machine")
    extra = machine.get("extra_fields") or []
    base_cols = 5 + len(extra)
    mcols = st.columns(base_cols)
    mcols[0].metric("Name",        machine["name"])
    mcols[1].metric("Power",       f"{machine.get('power_kw') or '—'} kW")
    mcols[2].metric("Voltage",     f"{machine.get('voltage_v') or '—'} V")
    mcols[3].metric("Current",     f"{machine.get('current_a') or '—'} A")
    mcols[4].metric("Resistance",  f"{machine.get('resistance_ohm') or '—'} Ω")
    for idx, ef in enumerate(extra):
        mcols[5 + idx].metric(ef["name"], f"{ef['value']} {ef['unit']}")
    if machine.get("notes"):
        st.caption(f"Notes: {machine['notes']}")

    if df.empty:
        st.warning("No readings recorded in this test.")
        return

    # Curve fit
    fit = fit_thermal_curve(df, ref_ch)

    # Chart
    st.markdown("#### Readings chart")
    fig = test_chart(df, ref_ch, fit, unit=unit, height=480)
    st.plotly_chart(fig, use_container_width=True)

    # Export options
    exp_col1, exp_col2 = st.columns(2)
    
    # HTML Export (interactive report)
    html_report = _generate_html_report(test, df, fit, unit)
    exp_col1.download_button(
        "📊 Export as HTML (interactive)",
        data=html_report,
        file_name=f"test_{test['id']}_report.html",
        mime="text/html",
    )
    
    # PNG Export (chart only)
    img_bytes = fig.to_image(format="png", width=1400, height=700, scale=2)
    exp_col2.download_button(
        "📥 Export chart as PNG",
        data=img_bytes,
        file_name=f"test_{test['id']}_chart.png",
        mime="image/png",
    )

    # Curve fit results
    st.markdown("#### Thermal curve analysis — reference channel")
    if fit["success"]:
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Ambient T",       f"{fit['T_amb']} {unit}")
        fc2.metric("ΔT rise",         f"{fit['delta_T']} {unit}")
        fc3.metric("τ (time const.)", f"{fit['tau_minutes']} min")
        fc4.metric("R²",              str(fit["r_squared"]))
        st.code(fit["equation"], language="text")
        st.caption(
            "τ = thermal time constant. Motor reaches ~63% of total rise after 1τ, "
            "~95% after 3τ, ~99% after 5τ."
        )
    else:
        st.info(f"Curve fit not available: {fit.get('reason', 'unknown')}")

    # Table
    st.markdown("#### Measurements table")
    pivot = df.pivot_table(index="timestamp", columns="channel",
                           values="value", aggfunc="mean")
    pivot.columns = [f"Ch {c} ({unit})" for c in pivot.columns]
    pivot.index   = pivot.index.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(pivot, use_container_width=True)


def render_test_page(sensor_type: str, unit: str):
    st.set_page_config(layout="wide")

    icon  = "🌡" if sensor_type == "temperature" else "⚙"
    key_test = f"active_test_{sensor_type}"
    key_snap = f"last_snapshot_{sensor_type}"
    key_prev = f"prev_snapshot_{sensor_type}"

    for k, v in [(key_test, None), (key_snap, None), (key_prev, None)]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Sidebar: today's tests ────────────────────────────
    with st.sidebar:
        st.markdown(f"### {icon} Today's tests")
        today_tests = get_tests_today(type=sensor_type)
        if today_tests:
            for t in today_tests:
                label = f"#{t['id']} — {t['machine']['name']} [{t['status']}]"
                if st.button(label, key=f"sidebar_open_{sensor_type}_{t['id']}"):
                    full = get_test(t["id"])
                    if full:
                        st.session_state[f"report_{sensor_type}_{t['id']}"] = full
        else:
            st.caption("No tests today yet.")

    # ── Title bar ─────────────────────────────────────────
    st.title(f"{icon} {sensor_type.capitalize()} — Live & Test")

    # ── Test start / status bar ───────────────────────────
    active_test = st.session_state[key_test]

    if active_test is None:
        machines = get_machines()
        if not machines:
            st.warning("No machines registered. Go to the **Machines** page first.")
        else:
            with st.container(border=True):
                col_a, col_b, col_c = st.columns([3, 2, 1])
                machine_names = {m["name"]: m["id"] for m in machines}
                sel_machine = col_a.selectbox("Machine", list(machine_names.keys()),
                                              label_visibility="visible")
                sel_channel = col_b.selectbox("Reference channel",
                                              list(range(1, N_CHANNELS + 1)))
                col_c.markdown("<br>", unsafe_allow_html=True)
                if col_c.button("▶ Start test", type="primary", use_container_width=True):
                    machine_id = machine_names[sel_machine]
                    test = start_test(machine_id, sensor_type, sel_channel)
                    if test:
                        st.session_state[key_test] = test
                        st.session_state[key_snap] = time.time()
                        st.session_state[key_prev] = None
                        st.success(f"Test #{test['id']} started!")
                        st.rerun()
                    else:
                        st.error("Failed to start test.")
    else:
        test_id = active_test["id"]
        ref_ch  = active_test["reference_channel"]
        with st.container(border=True):
            tc1, tc2, tc3, tc4 = st.columns([3, 2, 2, 1])
            tc1.metric("Machine",         active_test["machine"]["name"])
            tc2.metric("Reference ch.",   f"Ch {ref_ch}")
            tc3.empty()   # countdown fills here via fragment
            if tc4.button("⏹ Stop", type="secondary", use_container_width=True):
                finished = finish_test(test_id)
                st.session_state[key_test] = None
                if finished:
                    st.session_state[f"report_{sensor_type}_{test_id}"] = finished
                st.rerun()

    st.divider()

    # ── Live fragment: chart + metrics + countdown ────────
    @st.fragment(run_every=LIVE_REFRESH)
    def live_section():
        live      = get_live_channels()
        hist_df   = get_live_history(n_points=80)

        # Channel metrics row
        m_cols = st.columns(N_CHANNELS)
        for i in range(N_CHANNELS):
            ch  = i + 1
            val = live.get(ch)
            
            # Obter valor anterior do session_state
            prev_key = f"prev_val_ch_{ch}"
            prev_val = st.session_state.get(prev_key)
            
            # Calcular delta
            delta = None
            if val is not None and prev_val is not None:
                delta = round(val - prev_val, 2)
            
            # Mostrar métrica com delta
            m_cols[i].metric(
                f"Ch {ch}", 
                f"{val} {unit}" if val is not None else "—",
                delta=delta
            )
            
            # Armazenar valor atual para próxima iteração
            if val is not None:
                st.session_state[prev_key] = val

        # Live time series chart — full width
        active = st.session_state.get(key_test)
        ref    = active["reference_channel"] if active else None
        fig    = multichannel_timeseries(hist_df, unit,
                                         reference_channel=ref, height=420)
        st.plotly_chart(fig, use_container_width=True)

        # Countdown + snapshot logic (only when test is running)
        if active:
            test_id = active["id"]
            ref_ch  = active["reference_channel"]
            elapsed   = time.time() - st.session_state[key_snap]
            remaining = max(0, SNAPSHOT_INTERVAL - elapsed)
            mins, secs = int(remaining // 60), int(remaining % 60)
            st.info(f"⏱ Next snapshot in **{mins}m {secs}s**")

            if elapsed >= SNAPSHOT_INTERVAL:
                readings_payload = [
                    {"test_id": test_id, "channel": ch,
                     "value": val, "unit": unit}
                    for ch, val in live.items()
                ]
                add_test_readings(test_id, readings_payload)
                st.session_state[key_snap] = time.time()

                current_ref = live.get(ref_ch)
                prev_ref    = st.session_state[key_prev]

                if (current_ref is not None and prev_ref is not None
                        and abs(current_ref - prev_ref) < DELTA_STOP):
                    finished = finish_test(test_id)
                    st.session_state[key_test] = None
                    st.session_state[key_prev] = None
                    if finished:
                        st.session_state[f"report_{sensor_type}_{test_id}"] = finished
                    st.success(f"✅ Test #{test_id} finished — Δ < {DELTA_STOP}{unit}")
                    st.rerun()
                else:
                    if current_ref is not None:
                        st.session_state[key_prev] = current_ref

                # Show in-progress test chart
                test_data = get_test(test_id)
                if test_data:
                    df = _readings_df(test_data)
                    if not df.empty:
                        st.markdown("#### Test progress")
                        st.plotly_chart(
                            test_chart(df, ref_ch, unit=unit, height=380),
                            use_container_width=True,
                        )

    live_section()

    # ── Reports ───────────────────────────────────────────
    report_keys = sorted(k for k in st.session_state
                         if k.startswith(f"report_{sensor_type}_"))
    for rk in report_keys:
        test_data = st.session_state[rk]
        fa = test_data.get("finished_at")
        ts = fa[:16] if fa else "running"
        label = (f"📋 Test #{test_data['id']} — "
                 f"{test_data['machine']['name']} — {ts} [{test_data['status']}]")
        with st.expander(label, expanded=(test_data["status"] == "running")):
            render_report(test_data, unit)
