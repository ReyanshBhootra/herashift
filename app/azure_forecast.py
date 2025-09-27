from datetime import date
def forecast_risk(team_id: str, target: date) -> dict:
    # Simple deterministic placeholder risk score (0.00 - 0.29)
    risk = (abs(hash(team_id + target.isoformat())) % 30) / 100.0
    return {"teamId": team_id, "date": target.isoformat(), "riskScore": round(risk, 2)}
