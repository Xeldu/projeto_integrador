import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import streamlit as st
from api_client import get_tests, get_test
from charts import test_chart, fit_thermal_curve
from test_page import render_report

st.title("📅 Test history")

# ── Filters ───────────────────────────────────────────────
st.subheader("Search")
fc1, fc2, fc3, fc4 = st.columns(4)
f_type  = fc1.selectbox("Type", ["all", "temperature", "pressure"])
f_status= fc2.selectbox("Status", ["all", "finished", "running", "aborted"])
f_from  = fc3.date_input("From", value=date.today() - timedelta(days=30))
f_to    = fc4.date_input("To",   value=date.today())

tests = get_tests(
    type=None if f_type == "all" else f_type,
    status=None if f_status == "all" else f_status,
    date_from=str(f_from),
    date_to=str(f_to),
)

st.divider()

if not tests:
    st.info("No tests found for the selected filters.")
else:
    st.subheader(f"{len(tests)} test(s) found")
    for t in tests:
        started  = t["started_at"][:16]
        finished = t["finished_at"][:16] if t.get("finished_at") else "—"
        label    = (f"#{t['id']} | {t['type'].capitalize()} | "
                    f"{t['machine']['name']} | "
                    f"{started} → {finished} | [{t['status']}]")

        with st.expander(label):
            full = get_test(t["id"])
            if full:
                unit = "°C" if full["type"] == "temperature" else "bar"
                render_report(full, unit)
            else:
                st.error("Could not load test data.")
