from datetime import timedelta, date
from .db import employees, shifts
from typing import List, Dict

def count_assigned_shifts(team_id: str, target_date: str) -> int:
    return shifts.count_documents({"teamId": team_id, "date": target_date, "assignedEmployeeId": {"$ne": None}})

def simple_coverage_score(team_id: str, start: date, end: date) -> float:
    """Score in [0,1], higher is better (less risk)."""
    d = start
    score = 1.0
    days = 0
    while d <= end:
        days += 1
        assigned = count_assigned_shifts(team_id, d.isoformat())
        if assigned == 0:
            score -= 0.25
        elif assigned == 1:
            score -= 0.05
        d += timedelta(days=1)
    score = max(0.0, min(score, 1.0))
    return round(score, 2)

def propose_options(emp: Dict, start: date, end: date) -> List[Dict]:
    """Return candidate date ranges + coverage score. Add slides of ±2 days."""
    candidates = []
    offsets = [0, -2, 2]  # exact, earlier, later
    for o in offsets:
        s = start + timedelta(days=o)
        e = end + timedelta(days=o)
        score = simple_coverage_score(emp["teamId"], s, e)
        candidates.append({"start": s.isoformat(), "end": e.isoformat(), "coverageScore": score})
    candidates.sort(key=lambda x: x["coverageScore"], reverse=True)
    return candidates

def assign_backup(team_id: str, target_date: str) -> None:
    """
    Naive assignment: find any employee from same team not assigned on that date,
    and assign them to the shift. This modifies the DB.
    """
    possible = list(employees.find({"teamId": team_id}))
    for p in possible:
        existing = shifts.find_one({"teamId": team_id, "date": target_date, "assignedEmployeeId": p["id"]})
        if existing:
            continue
        result = shifts.update_one(
            {"teamId": team_id, "date": target_date, "assignedEmployeeId": None},
            {"$set": {"assignedEmployeeId": p["id"]}}
        )
        if result.modified_count:
            return
