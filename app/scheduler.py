# app/scheduler.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Any, List, Tuple

import pandas as pd


# ---------- utils ----------
def _iso_to_date(s: str) -> date:
    return date.fromisoformat(str(s))


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _normalize_shifts_df(shifts_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure consistent snake_case column names and defaults."""
    df = shifts_df.copy()

    # Rename camelCase → snake_case
    if "assignedEmployeeId" in df.columns:
        df = df.rename(columns={"assignedEmployeeId": "assigned_id"})
    if "assignedEmployeeName" in df.columns:
        df = df.rename(columns={"assignedEmployeeName": "assigned_name"})
    if "teamId" in df.columns:
        df = df.rename(columns={"teamId": "team"})

    # Guarantee essential columns
    for col, default in [
        ("date", ""),
        ("team", ""),
        ("role", ""),
        ("assigned_id", None),
        ("assigned_name", None),
    ]:
        if col not in df.columns:
            df[col] = default

    # Normalize types
    df["date"] = df["date"].astype(str)
    for c in ["team", "role", "assigned_id", "assigned_name"]:
        if c in df.columns:
            df[c] = df[c].astype("string").where(df[c].notna(), None)

    return df


# ---------- weekly + monthly hours ----------
def compute_weekly_hours(shifts_df: pd.DataFrame, hours_per_shift: int = 8) -> Dict[Tuple[str, str], int]:
    """
    Returns {(employee_id, week_start_iso): hours}.
    Only counts shifts with a valid assigned_id.
    """
    df = _normalize_shifts_df(shifts_df)
    out: Dict[Tuple[str, str], int] = {}

    for _, row in df.iterrows():
        emp = row.get("assigned_id")
        d_str = row.get("date")

        if emp is None or pd.isna(emp) or str(emp).strip() == "":
            continue
        if d_str is None or pd.isna(d_str) or str(d_str).strip() == "":
            continue

        try:
            d = _iso_to_date(d_str)
        except Exception:
            continue

        wk = _week_start(d).isoformat()
        out[(emp, wk)] = out.get((emp, wk), 0) + int(hours_per_shift)
    return out


def _month_to_date_hours(shifts_df: pd.DataFrame, hours_per_shift: int = 8) -> Dict[Tuple[str, str], int]:
    """Returns {(employee_id, YYYY-MM): hours}"""
    df = _normalize_shifts_df(shifts_df)
    out: Dict[Tuple[str, str], int] = {}
    for _, row in df.iterrows():
        emp = row.get("assigned_id")
        d_str = row.get("date")

        if emp is None or pd.isna(emp) or str(emp).strip() == "":
            continue
        if d_str is None or pd.isna(d_str) or str(d_str).strip() == "":
            continue

        try:
            d = _iso_to_date(d_str)
        except Exception:
            continue

        key = (emp, f"{d.year:04d}-{d.month:02d}")
        out[key] = out.get(key, 0) + int(hours_per_shift)
    return out


# ---------- helpers ----------
def _already_assigned_on_date(df: pd.DataFrame, emp_id: str, d_iso: str) -> bool:
    subset = df[(df["date"].astype(str) == str(d_iso)) & (df["assigned_id"] == emp_id)]
    return not subset.empty


def _worked_previous_day_same_team_role(df: pd.DataFrame, emp_id: str, team: str, role: str, d_iso: str) -> bool:
    try:
        d = _iso_to_date(d_iso)
    except Exception:
        return False
    prev = (d - timedelta(days=1)).isoformat()
    subset = df[
        (df["date"].astype(str) == prev)
        & (df["team"] == team)
        & (df["role"] == role)
        & (df["assigned_id"] == emp_id)
    ]
    return not subset.empty


def _violates_rest(df: pd.DataFrame, emp_id: str, d_iso: str, min_rest_hours: int) -> bool:
    """Simple rest rule: if min_rest_hours >= 24, block working consecutive days."""
    if min_rest_hours <= 0:
        return False
    if min_rest_hours < 24:
        return False

    try:
        d = _iso_to_date(d_iso)
    except Exception:
        return False

    prev = (d - timedelta(days=1)).isoformat()
    nextd = (d + timedelta(days=1)).isoformat()
    prev_assigned = _already_assigned_on_date(df, emp_id, prev)
    next_assigned = _already_assigned_on_date(df, emp_id, nextd)
    return prev_assigned or next_assigned


# ---------- main planner ----------
def propose_plan(
    employees_df: pd.DataFrame,
    shifts_df: pd.DataFrame,
    pto_emp_id: str,
    pto_dates: List[str],
    role_needed: str,
    team_needed: str,
    objective: str = "least_overtime_risk",
    weekly_cap: int = 40,
    hours_per_shift: int = 8,
    min_rest_hours: int = 12,
) -> Dict[str, Any]:
    """
    Deterministic assignment engine:
      • Cover PTO shifts for same team/role
      • Skip double-booking
      • Respect weekly caps + min rest
      • Objectives: least_overtime_risk | fairness | continuity | none
    """
    emp_df = employees_df.copy()
    sh_df = _normalize_shifts_df(shifts_df)

    # Normalize employees
    for c in ["id", "teamId", "role", "name"]:
        if c in emp_df.columns:
            emp_df[c] = emp_df[c].astype("string").where(emp_df[c].notna(), None)
    if "maxHoursPerWeek" not in emp_df.columns:
        emp_df["maxHoursPerWeek"] = 40

    # Find shifts to cover
    target_mask = (
        sh_df["date"].isin([str(d) for d in pto_dates])
        & (sh_df["team"] == str(team_needed))
        & (sh_df["role"] == str(role_needed))
        & ((sh_df["assigned_id"].isna()) | (sh_df["assigned_id"] == str(pto_emp_id)))
    )
    target = sh_df[target_mask].copy().sort_values("date")

    # Pre-compute usage
    wk_hours = compute_weekly_hours(sh_df, hours_per_shift=hours_per_shift)
    mt_hours = _month_to_date_hours(sh_df, hours_per_shift=hours_per_shift)

    # Candidate pool: same team + role, not PTO emp
    pool = emp_df[
        (emp_df["teamId"] == str(team_needed))
        & (emp_df["role"] == str(role_needed))
        & (emp_df["id"] != str(pto_emp_id))
    ].copy()

    plan: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    for _, row in target.iterrows():
        d_iso = str(row["date"])
        team = str(row["team"])
        role = str(row["role"])

        viable = []
        for _, cand in pool.iterrows():
            cand_id = str(cand["id"])

            if _already_assigned_on_date(sh_df, cand_id, d_iso):
                continue
            if _violates_rest(sh_df, cand_id, d_iso, min_rest_hours):
                continue

            per_cap = int(cand.get("maxHoursPerWeek") or weekly_cap)
            cap_to_use = min(int(weekly_cap), per_cap)

            try:
                d = _iso_to_date(d_iso)
            except Exception:
                continue

            wk = _week_start(d).isoformat()
            used = wk_hours.get((cand_id, wk), 0)
            if used + hours_per_shift > cap_to_use:
                continue

            month_key = (cand_id, f"{d.year:04d}-{d.month:02d}")
            mtd = mt_hours.get(month_key, 0)
            cont = _worked_previous_day_same_team_role(sh_df, cand_id, team, role, d_iso)
            viable.append(
                {"cand_id": cand_id, "wk_used": used, "mtd_used": mtd, "continuity": cont}
            )

        if not viable:
            conflicts.append({"date": d_iso, "team": team, "role": role, "reason": "no viable candidate"})
            continue

        # Objective sort
        if objective == "least_overtime_risk":
            viable.sort(key=lambda x: (x["wk_used"], x["mtd_used"]))
        elif objective == "fairness":
            viable.sort(key=lambda x: (x["mtd_used"], x["wk_used"]))
        elif objective == "continuity":
            viable.sort(key=lambda x: (not x["continuity"], x["wk_used"], x["mtd_used"]))

        chosen = viable[0]["cand_id"]
        plan.append(
            {
                "date": d_iso,
                "team": team,
                "role": role,
                "assigned_employee_id": chosen,
                "notes": f"Covering {role} shift due to {pto_emp_id}'s PTO.",
            }
        )

        # Update usage trackers only (don’t mutate sh_df)
        wk = _week_start(_iso_to_date(d_iso)).isoformat()
        wk_hours[(chosen, wk)] = wk_hours.get((chosen, wk), 0) + int(hours_per_shift)
        month_key = (chosen, f"{_iso_to_date(d_iso).year:04d}-{_iso_to_date(d_iso).month:02d}")
        mt_hours[month_key] = mt_hours.get(month_key, 0) + int(hours_per_shift)

    return {"plan": plan, "conflicts": conflicts, "preview_shifts_df": target}
