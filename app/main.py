from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from .db import employees, shifts, pto_requests, coverage_forecasts
from .models import PTORequest, PTOPlanResponse, ScheduleOption
from .scheduler import propose_options
from .call_gemini import summarize_hr_note
from .azure_forecast import forecast_risk

app = FastAPI(title="HeraShift API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "service": "HeraShift"}

@app.post("/request-pto", response_model=PTORequest)
def request_pto(req: PTORequest):
    emp = employees.find_one({"id": req.employeeId})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    rec = req.dict()
    pto_requests.insert_one(rec)
    return req

@app.post("/propose-schedule", response_model=PTOPlanResponse)
def propose_schedule(request_id: str):
    req = pto_requests.find_one({"id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="PTO request not found")

    emp = employees.find_one({"id": req["employeeId"]})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    start = date.fromisoformat(str(req["start"]))
    end = date.fromisoformat(str(req["end"]))

    options = propose_options(emp, start, end)
    best = max(options, key=lambda x: x["coverageScore"])
    approved = best["coverageScore"] >= 0.6

    note = summarize_hr_note(emp["name"], best["start"], best["end"],
                             f"{'Approved' if approved else 'Needs change'} (coverage {best['coverageScore']})")

    cov = forecast_risk(emp["teamId"], start)
    coverage_forecasts.update_one(
        {"teamId": cov["teamId"], "date": cov["date"]},
        {"$set": cov}, upsert=True
    )

    status = "approved" if approved else "pending"
    pto_requests.update_one({"id": request_id}, {"$set": {"status": status}})

    chosen = ScheduleOption(**best)
    return PTOPlanResponse(
        requestId=request_id,
        approved=approved,
        chosenOption=chosen,
        message=note
    )

@app.get("/heatmap")
def heatmap(team_id: str, day: str):
    rec = coverage_forecasts.find_one({"teamId": team_id, "date": day})
    return rec or {"teamId": team_id, "date": day, "riskScore": None}
