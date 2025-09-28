# app/streamlit_app.py
from __future__ import annotations

import os
import io
import json
from datetime import date, timedelta
from typing import Dict, Any, List
from pathlib import Path
from app.seed.seed_data import seed_demo

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ---- DB bootstrap (support: exported collections or get_db()) ----
try:
    import app.db as db_mod
except Exception as e:
    raise RuntimeError(
        "Could not import 'app.db'. Run from project root "
        "(e.g., `streamlit run app/streamlit_app.py`) and ensure app/__init__.py exists."
    ) from e

MONGO_DB = None
if hasattr(db_mod, "employees") and hasattr(db_mod, "shifts"):
    EMP_COL = db_mod.employees
    SHIFT_COL = db_mod.shifts
    MONGO_DB = getattr(db_mod, "db", None)
elif hasattr(db_mod, "get_db"):
    MONGO_DB = db_mod.get_db()
    EMP_COL = MONGO_DB["employees"]
    SHIFT_COL = MONGO_DB["shifts"]
else:
    raise RuntimeError("app.db must export (employees, shifts) or a get_db() function.")

from app.scheduler import propose_plan, compute_weekly_hours

st.set_page_config(
    page_title="HeraShift – AI Leave & Coverage Planner",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- helpers ----------
def _env_health() -> Dict[str, Any]:
    return {
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", ""),
        "GEMINI_API_URL": os.getenv("GEMINI_API_URL", ""),
        "GEMINI_API_KEY?": bool(os.getenv("GEMINI_API_KEY")),
        "Mongo URI present": bool(os.getenv("MONGODB_URI")),
    }

def _rename_shift_columns_inplace(sh_df: pd.DataFrame) -> None:
    rename_map = {}
    if "assignedEmployeeId" in sh_df.columns and "assigned_id" not in sh_df.columns:
        rename_map["assignedEmployeeId"] = "assigned_id"
    if "assignedEmployeeName" in sh_df.columns and "assigned_name" not in sh_df.columns:
        rename_map["assignedEmployeeName"] = "assigned_name"
    if "teamId" in sh_df.columns and "team" not in sh_df.columns:
        rename_map["teamId"] = "team"
    if rename_map:
        sh_df.rename(columns=rename_map, inplace=True)

@st.cache_data(show_spinner=False)
def _fetch_data() -> Dict[str, pd.DataFrame]:
    try:
        emps = list(EMP_COL.find({}, {"_id": 0})) if EMP_COL is not None else []
        sh = list(SHIFT_COL.find({}, {"_id": 0})) if SHIFT_COL is not None else []
    except Exception as e:
        raise RuntimeError(
            "Failed to fetch data from MongoDB. Click 'Refresh data' after fixing the connection.\n\n"
            f"{e}"
        )
    emp_df = pd.DataFrame(emps) if emps else pd.DataFrame(
        columns=["id", "name", "teamId", "role", "skills", "maxHoursPerWeek"]
    )
    sh_df = pd.DataFrame(sh) if sh else pd.DataFrame(
        columns=["id", "date", "team", "role", "assigned_id", "assigned_name", "hours", "skillsRequired"]
    )

    _rename_shift_columns_inplace(sh_df)

    # Guarantee columns needed by filters/UI exist
    required_cols = [
        ("date", ""),
        ("team", ""),
        ("role", ""),
        ("assigned_id", None),
        ("assigned_name", None),
        ("hours", 8),
    ]
    for col, default in required_cols:
        if col not in sh_df.columns:
            sh_df[col] = default

    # Normalize types and NA handling
    for c in ["id", "team", "role", "assigned_id", "assigned_name"]:
        if c in sh_df.columns:
            sh_df[c] = sh_df[c].astype("string").where(sh_df[c].notna(), None)
    if "date" in sh_df.columns:
        sh_df["date"] = sh_df["date"].astype(str)

    for c in ["id", "teamId", "role", "name"]:
        if c in emp_df.columns:
            emp_df[c] = emp_df[c].astype("string").where(emp_df[c].notna(), None)

    return {"employees": emp_df, "shifts": sh_df}

def _clear_cache_and_reload():
    _fetch_data.clear()
    st.toast("Reloading updated data…", icon="♻️")
    st.rerun()

def _date_range_inclusive(start: date, end: date) -> List[str]:
    out = []
    d = start
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out

def _download_bytes(name: str, content: bytes, mime: str):
    st.download_button(label=f"Download {name}", data=content, file_name=name, mime=mime)

def _seed_demo():
    if EMP_COL.count_documents({}) == 0:
        EMP_COL.insert_many([
            {"id": "emp-001", "name": "Alice",   "teamId": "team-1", "role": "engineer", "skills": ["react", "ui"], "maxHoursPerWeek": 40},
            {"id": "emp-002", "name": "Priya",   "teamId": "team-1", "role": "engineer", "skills": ["css", "react"], "maxHoursPerWeek": 40},
            {"id": "emp-003", "name": "Sam",     "teamId": "team-2", "role": "backend",  "skills": ["python", "api"], "maxHoursPerWeek": 40},
            {"id": "emp-004", "name": "Reyansh", "teamId": "team-2", "role": "backend",  "skills": ["db", "python"], "maxHoursPerWeek": 40},
            {"id": "emp-005", "name": "Zara",    "teamId": "team-3", "role": "devops",   "skills": ["k8s", "ci"], "maxHoursPerWeek": 40},
        ])
    if SHIFT_COL.count_documents({}) == 0:
        base = date.today() - timedelta(days=7)
        rows = []
        for i in range(14):
            d = (base + timedelta(days=i)).isoformat()
            rows.append({"date": d, "team": "team-1", "role": "engineer", "assignedEmployeeId": None})
            rows.append({"date": d, "team": "team-2", "role": "backend",  "assignedEmployeeId": None})
            rows.append({"date": d, "team": "team-3", "role": "devops",   "assignedEmployeeId": None})
        SHIFT_COL.insert_many(rows)

# ---------- sidebar ----------
with st.sidebar:
    st.subheader("Health")
    st.json(_env_health())
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Refresh data", use_container_width=True):
            _clear_cache_and_reload()
    with col_b:
        if st.button("🌱 Seed demo", use_container_width=True):
            try:
                seed_demo()  # always wipes + reseeds
                st.success("✅ Demo data reseeded successfully!")
                _clear_cache_and_reload()
            except Exception as e:
                st.error(f"❌ Seeding failed: {e}")

# ---------- main ----------
st.title("HeraShift – AI Leave & Coverage Planner")

data = _fetch_data()
emp_df: pd.DataFrame = data["employees"].copy()
sh_df: pd.DataFrame = data["shifts"].copy()

st.success(f"Mongo connected • employees: **{len(emp_df)}** • shifts: **{len(sh_df)}**", icon="✅")

col_emp, col_shift = st.columns([1, 1.3], gap="large")

# Employees table
with col_emp:
    st.subheader("Employees")
    show_emp = emp_df.copy()
    if "skills" in show_emp.columns:
        show_emp["skills"] = show_emp["skills"].apply(lambda s: s if isinstance(s, list) else ([] if s is None else s))
    st.dataframe(
        show_emp[["id", "name", "teamId", "role", "skills", "maxHoursPerWeek"]],
        use_container_width=True,
        hide_index=True,
    )

# Shifts with filters (defensive)
with col_shift:
    st.subheader("Shifts")
    uniq_dates = sorted(sh_df["date"].dropna().astype(str).unique().tolist()) if "date" in sh_df.columns else []
    uniq_roles = sorted(sh_df["role"].dropna().astype(str).unique().tolist()) if "role" in sh_df.columns else []
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        date_choice = st.selectbox("Filter by date", options=["(all)"] + uniq_dates, index=0)
    with col_f2:
        role_choice = st.selectbox("Filter by role", options=["(all)"] + uniq_roles, index=0)

    show_shifts = sh_df.copy()
    if date_choice != "(all)" and "date" in show_shifts.columns:
        show_shifts = show_shifts[show_shifts["date"].astype(str) == date_choice]
    if role_choice != "(all)" and "role" in show_shifts.columns:
        show_shifts = show_shifts[show_shifts["role"] == role_choice]

    display_cols = [c for c in ["date", "team", "role", "assigned_id", "assigned_name"] if c in show_shifts.columns]
    st.dataframe(show_shifts[display_cols], use_container_width=True, hide_index=True)

# PTO planner
st.markdown("---")
st.header("Create PTO Request")

if emp_df.empty:
    st.warning("No employees found.")
    st.caption("Seed the database (left sidebar → **Seed demo**) or run: `python -m app.seed.seed_data`, then click **Refresh data**.")
else:
    with st.form("pto_form", clear_on_submit=False):
        emp_options = [f'{row["id"]} — {row["name"]} ({row["teamId"]}/{row["role"]})' for _, row in emp_df.iterrows()]
        emp_label = st.selectbox("Employee", options=emp_options, index=0)
        selected_emp_id = emp_label.split(" — ")[0].strip()

        if selected_emp_id not in emp_df["id"].tolist():
            st.error("Selected employee is no longer available. Please refresh and try again.")
            submitted = st.form_submit_button("Propose Coverage", type="primary")
        else:
            emp_row = emp_df.set_index("id").loc[selected_emp_id]
            role_needed = str(emp_row["role"])
            team_needed = str(emp_row["teamId"])

            start_d = st.date_input("Start", value=date.today())
            end_d = st.date_input("End", value=date.today() + timedelta(days=2))
            notes = st.text_input("Notes (optional)", value="")
            with st.expander("Advanced constraints", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    hours_per_shift = st.number_input("Hours per shift", 1, 24, 8, 1)
                with c2:
                    weekly_cap = st.number_input("Max hours / week", 8, 80, int(emp_row.get("maxHoursPerWeek") or 40), 1)
                with c3:
                    min_rest_hours = st.number_input("Min rest between shifts (hrs)", 0, 24, 12, 1)
                objective = st.selectbox("Assignment objective", ["least_overtime_risk", "fairness", "continuity", "none"], index=0)
            submitted = st.form_submit_button("Propose Coverage", type="primary")

    if "submitted" in locals() and submitted:
        if end_d < start_d:
            st.error("End date cannot be before start date.")
        else:
            cover_dates = _date_range_inclusive(start_d, end_d)
            with st.container(border=True):
                st.caption("PTO request:")
                st.code(json.dumps({"employee_id": selected_emp_id, "dates": cover_dates, "notes": notes}, indent=2), language="json")

            result = propose_plan(
                employees_df=emp_df,
                shifts_df=sh_df,
                pto_emp_id=selected_emp_id,
                pto_dates=cover_dates,
                role_needed=role_needed,
                team_needed=team_needed,
                objective=objective,
                weekly_cap=int(weekly_cap),
                hours_per_shift=int(hours_per_shift),
                min_rest_hours=int(min_rest_hours),
            )

            plan_rows: List[Dict[str, Any]] = result["plan"]  # type: ignore
            conflicts: List[Dict[str, Any]] = result["conflicts"]  # type: ignore
            preview_df: pd.DataFrame = result["preview_shifts_df"]  # type: ignore

            st.subheader("Proposed Coverage")
            if plan_rows:
                plan_df = pd.DataFrame(plan_rows)
                name_map = emp_df.set_index("id")["name"].to_dict()
                plan_df["assigned_name"] = plan_df["assigned_employee_id"].map(name_map)
                st.dataframe(plan_df, use_container_width=True, hide_index=True)

                plan_json = json.dumps(plan_rows, indent=2).encode("utf-8")
                _download_bytes("plan.json", plan_json, "application/json")
                csv_io = io.StringIO()
                plan_df.to_csv(csv_io, index=False)
                _download_bytes("plan.csv", csv_io.getvalue().encode("utf-8"), "text/csv")
            else:
                st.info("No coverage found for this PTO window with the current constraints/objective.")

            with st.expander("Conflicts", expanded=False):
                if conflicts:
                    st.json(conflicts)
                else:
                    st.write("None")

            st.session_state["__preview_plan"] = plan_rows

            st.markdown("### Apply plan to shifts")
            col_apply = st.columns([1, 3])[0]
            with col_apply:
                do_apply = st.button("Apply plan now", type="primary", disabled=not plan_rows)

            if do_apply and plan_rows:
                name_map = emp_df.set_index("id")["name"].to_dict()
                applied = 0
                for r in plan_rows:
                    upd = {
                        "$set": {
                            "assignedEmployeeId": r["assigned_employee_id"],
                            "assignedEmployeeName": name_map.get(r["assigned_employee_id"], ""),
                        }
                    }
                    res = SHIFT_COL.update_one(
                        {"date": r["date"], "team": r["team"], "role": r["role"], "assignedEmployeeId": None},
                        upd,
                    )
                    if res.modified_count == 0:
                        res2 = SHIFT_COL.update_one(
                            {"date": r["date"], "team": r["team"], "role": r["role"], "assignedEmployeeId": {"$exists": False}},
                            upd,
                        )
                        applied += res2.modified_count
                    else:
                        applied += res.modified_count

                st.success(f"Applied {applied} shift assignments.", icon="✅")
                _clear_cache_and_reload()

# Weekly hours dashboard
st.markdown("---")
st.subheader("Weekly hours (current assignments)")

wk_hours = compute_weekly_hours(sh_df, hours_per_shift=8)
if wk_hours:
    rows = [{"week_start": wk, "employee_id": eid, "hours": hrs} for (eid, wk), hrs in wk_hours.items()]
    wk_df = pd.DataFrame(rows)
    name_map = emp_df.set_index("id")["name"].to_dict()
    cap_map = emp_df.set_index("id")["maxHoursPerWeek"].to_dict()
    wk_df["name"] = wk_df["employee_id"].map(name_map)
    wk_df["cap"] = wk_df["employee_id"].map(cap_map).fillna(40).astype(int)
    wk_df = wk_df[["week_start", "employee_id", "name", "hours", "cap"]].sort_values(["week_start", "employee_id"])
    st.dataframe(wk_df, use_container_width=True, hide_index=True)
else:
    st.caption("No assigned shifts yet.")
