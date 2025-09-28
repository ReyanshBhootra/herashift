# app/seed/seed_data.py
"""
Seed demo data for HeraShift.
ALWAYS clears employees + shifts and inserts fresh data.
"""

from datetime import date, timedelta
from app.db import get_db


def seed_demo():
    db = get_db()
    employees = db["employees"]
    shifts = db["shifts"]

    # Wipe old
    employees.delete_many({})
    shifts.delete_many({})

    # Insert employees
    employees.insert_many([
        {"id": "emp-001", "name": "Alice",   "teamId": "team-1", "role": "engineer", "skills": ["react", "ui"], "maxHoursPerWeek": 40},
        {"id": "emp-002", "name": "Priya",   "teamId": "team-1", "role": "engineer", "skills": ["css", "react"], "maxHoursPerWeek": 40},
        {"id": "emp-003", "name": "Sam",     "teamId": "team-2", "role": "backend",  "skills": ["python", "api"], "maxHoursPerWeek": 40},
        {"id": "emp-004", "name": "Reyansh", "teamId": "team-2", "role": "backend",  "skills": ["db", "python"], "maxHoursPerWeek": 40},
        {"id": "emp-005", "name": "Zara",    "teamId": "team-3", "role": "devops",   "skills": ["k8s", "ci"], "maxHoursPerWeek": 40},
    ])

    # Insert shifts (14 days window, 3 teams per day)
    base = date.today() - timedelta(days=7)
    rows = []
    for i in range(14):
        d = (base + timedelta(days=i)).isoformat()
        rows.append({"date": d, "team": "team-1", "role": "engineer", "assignedEmployeeId": None})
        rows.append({"date": d, "team": "team-2", "role": "backend",  "assignedEmployeeId": None})
        rows.append({"date": d, "team": "team-3", "role": "devops",   "assignedEmployeeId": None})
    shifts.insert_many(rows)

    print(f"✅ Demo data reseeded: employees=5, shifts={len(rows)}")


if __name__ == "__main__":
    seed_demo()
