import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from api_client import get_machines, create_machine, update_machine, delete_machine

st.set_page_config(layout="wide")
st.title("🏭 Machines")


def extra_fields_editor(prefix: str, existing: list[dict] | None = None) -> list[dict]:
    """Renders dynamic rows for custom fields. Returns list of {name, value, unit}."""
    existing = existing or []
    key_count = f"{prefix}_extra_count"
    if key_count not in st.session_state:
        st.session_state[key_count] = max(1, len(existing))

    count = st.session_state[key_count]
    fields = []

    for i in range(count):
        prev = existing[i] if i < len(existing) else {}
        c1, c2, c3 = st.columns([3, 3, 2])
        name  = c1.text_input("Field name",  value=prev.get("name", ""),  key=f"{prefix}_ef_name_{i}")
        value = c2.text_input("Value",        value=prev.get("value", ""), key=f"{prefix}_ef_val_{i}")
        unit  = c3.text_input("Unit",         value=prev.get("unit", ""),  key=f"{prefix}_ef_unit_{i}")
        if name:
            fields.append({"name": name, "value": value, "unit": unit})

    col_add, col_rem = st.columns([1, 1])
    if col_add.button("＋ Add field", key=f"{prefix}_add"):
        st.session_state[key_count] += 1
        st.rerun()
    if count > 1 and col_rem.button("－ Remove last", key=f"{prefix}_rem"):
        st.session_state[key_count] -= 1
        st.rerun()

    return fields


# ── Register ──────────────────────────────────────────────
with st.expander("➕ Register new machine", expanded=False):
    tab_base, tab_extra = st.tabs(["Basic fields", "Outros"])

    with st.form("new_machine_form"):
        with tab_base:
            c1, c2 = st.columns(2)
            name  = c1.text_input("Name *")
            notes = c2.text_input("Notes")
            c3, c4, c5, c6 = st.columns(4)
            power      = c3.number_input("Power (kW)",     min_value=0.0, step=0.1,  value=None)
            voltage    = c4.number_input("Voltage (V)",    min_value=0.0, step=1.0,  value=None)
            current    = c5.number_input("Current (A)",    min_value=0.0, step=0.1,  value=None)
            resistance = c6.number_input("Resistance (Ω)", min_value=0.0, step=0.01, value=None)

        with tab_extra:
            st.caption("Add custom fields (name, value, unit) for this machine.")
            extra = extra_fields_editor("new")

        submitted = st.form_submit_button("Save machine", type="primary")

    if submitted:
        if not name:
            st.error("Name is required.")
        else:
            result = create_machine({
                "name": name, "notes": notes or None,
                "power_kw": power, "voltage_v": voltage,
                "current_a": current, "resistance_ohm": resistance,
                "extra_fields": extra or None,
            })
            if result:
                st.success(f"Machine '{name}' registered!")
                st.rerun()
            else:
                st.error("Failed to register machine (name may already exist).")

st.divider()

# ── List ──────────────────────────────────────────────────
machines = get_machines()

if not machines:
    st.info("No machines registered yet.")
else:
    st.subheader(f"{len(machines)} machine(s) registered")
    for m in machines:
        extra_m = m.get("extra_fields") or []
        with st.expander(f"**{m['name']}**  —  id #{m['id']}"):
            tab_view, tab_edit, tab_del = st.tabs(["View", "Edit", "Delete"])

            with tab_view:
                v1, v2, v3, v4 = st.columns(4)
                v1.metric("Power",      f"{m.get('power_kw') or '—'} kW")
                v2.metric("Voltage",    f"{m.get('voltage_v') or '—'} V")
                v3.metric("Current",    f"{m.get('current_a') or '—'} A")
                v4.metric("Resistance", f"{m.get('resistance_ohm') or '—'} Ω")
                if extra_m:
                    st.markdown("**Custom fields**")
                    ex_cols = st.columns(min(len(extra_m), 4))
                    for idx, ef in enumerate(extra_m):
                        ex_cols[idx % 4].metric(ef["name"], f"{ef['value']} {ef['unit']}")
                if m.get("notes"):
                    st.caption(f"Notes: {m['notes']}")
                st.caption(f"Registered: {m['created_at'][:16]}")

            with tab_edit:
                et_base, et_extra = st.tabs(["Basic fields", "Outros"])
                with st.form(f"edit_{m['id']}"):
                    with et_base:
                        e1, e2 = st.columns(2)
                        e_name  = e1.text_input("Name",  value=m["name"])
                        e_notes = e2.text_input("Notes", value=m.get("notes") or "")
                        e3, e4, e5, e6 = st.columns(4)
                        e_pow = e3.number_input("Power (kW)",     value=float(m["power_kw"] or 0), step=0.1)
                        e_vol = e4.number_input("Voltage (V)",    value=float(m["voltage_v"] or 0), step=1.0)
                        e_cur = e5.number_input("Current (A)",    value=float(m["current_a"] or 0), step=0.1)
                        e_res = e6.number_input("Resistance (Ω)", value=float(m["resistance_ohm"] or 0), step=0.01)
                    with et_extra:
                        st.caption("Edit custom fields.")
                        e_extra = extra_fields_editor(f"edit_{m['id']}", existing=extra_m)

                    if st.form_submit_button("Update", type="primary"):
                        ok = update_machine(m["id"], {
                            "name": e_name, "notes": e_notes or None,
                            "power_kw": e_pow or None, "voltage_v": e_vol or None,
                            "current_a": e_cur or None, "resistance_ohm": e_res or None,
                            "extra_fields": e_extra or None,
                        })
                        if ok:
                            st.success("Updated!")
                            st.rerun()
                        else:
                            st.error("Update failed.")

            with tab_del:
                st.warning(f"Delete **{m['name']}**? This cannot be undone.")
                if st.button("Confirm delete", key=f"del_{m['id']}", type="primary"):
                    if delete_machine(m["id"]):
                        st.success("Deleted.")
                        st.rerun()
                    else:
                        st.error("Delete failed (machine may have associated tests).")
