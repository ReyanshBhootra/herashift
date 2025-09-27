import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="HeraShift Demo", layout="centered")
st.title("HeraShift — Demo")

with st.expander("Make a PTO request"):
    emp_id = st.selectbox("Employee", ["emp-001", "emp-002", "emp-003", "emp-004", "emp-005"])
    start = st.date_input("Start date")
    end = st.date_input("End date")
    if st.button("Request PTO"):
        payload = {
            "id": f"pto-{emp_id}-{start.isoformat()}",
            "employeeId": emp_id,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "status": "pending"
        }
        try:
            r = requests.post(f"{API_BASE}/request-pto", json=payload, timeout=10)
            r.raise_for_status()
            st.success("PTO created. Now propose schedule.")
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")
with st.expander("Propose schedule / run planner"):
    pto_id = st.text_input("PTO Request ID (example: pto-emp-001-2025-11-10)", "")
    if st.button("Propose schedule"):
        try:
            r = requests.post(f"{API_BASE}/propose-schedule", params={"request_id": pto_id}, timeout=20)
            r.raise_for_status()
            st.json(r.json())
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")
with st.expander("Heatmap / forecast"):
    team = st.selectbox("Team", ["team-1", "team-2", "team-3"])
    day = st.date_input("Day to inspect")
    if st.button("Get heatmap risk"):
        try:
            r = requests.get(f"{API_BASE}/heatmap", params={"team_id": team, "day": day.isoformat()}, timeout=5)
            r.raise_for_status()
            st.json(r.json())
        except Exception as e:
            st.error(f"Error: {e}")
