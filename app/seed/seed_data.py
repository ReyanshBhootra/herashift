import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import date, timedelta
import uuid

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "herashift")

client = MongoClient(MONGODB_URI)
db = client[MONGO_DB]

def clear_collections():
    db.employees.delete_many({})
    db.shifts.delete_many({})
    db.pto_requests.delete_many({})
    db.coverage_forecasts.delete_many({})

def seed():
    clear_collections()
    teams = [
        {"teamId": "team-1", "name": "Frontend"},
        {"teamId": "team-2", "name": "Backend"},
        {"teamId": "team-3", "name": "Infra"},
    ]
    employees = [
        {"id": "emp-001", "name": "Alice", "teamId": "team-1", "role": "engineer", "skills": ["react", "ui"], "maxHoursPerWeek": 40},
        {"id": "emp-002", "name": "Priya", "teamId": "team-1", "role": "engineer", "skills": ["css", "react"], "maxHoursPerWeek": 40},
        {"id": "emp-003", "name": "Sam", "teamId": "team-2", "role": "backend", "skills": ["python", "api"], "maxHoursPerWeek": 40},
        {"id": "emp-004", "name": "Reyansh", "teamId": "team-2", "role": "backend", "skills": ["db", "python"], "maxHoursPerWeek": 40},
        {"id": "emp-005", "name": "Zara", "teamId": "team-3", "role": "devops", "skills": ["k8s", "ci"], "maxHoursPerWeek": 40},
    ]
    db.employees.insert_many(employees)

    start = date.today()
    shifts = []
    for t in teams:
        for d in range(14):
            dt = start + timedelta(days=d)
            shift = {
                "id": str(uuid.uuid4()),
                "date": dt.isoformat(),
                "teamId": t["teamId"],
                "roleNeeded": "engineer" if t["teamId"] == "team-1" else ("backend" if t["teamId"] == "team-2" else "devops"),
                "assignedEmployeeId": None
            }
            shifts.append(shift)
    if shifts:
        db.shifts.insert_many(shifts)

    print("Seeded employees and shifts:")
    print(f"employees: {db.employees.count_documents({})}")
    print(f"shifts: {db.shifts.count_documents({})}")

if __name__ == "__main__":
    seed()
