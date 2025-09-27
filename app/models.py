from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class Employee(BaseModel):
    id: str
    name: str
    teamId: str
    role: str
    skills: List[str] = []
    maxHoursPerWeek: int = 40

class Shift(BaseModel):
    id: str
    date: date
    teamId: str
    roleNeeded: str
    assignedEmployeeId: Optional[str] = None

class PTORequest(BaseModel):
    id: str
    employeeId: str
    start: date
    end: date
    status: str = "pending"  # pending/approved/rejected

class ScheduleOption(BaseModel):
    start: date
    end: date
    coverageScore: float = Field(ge=0, le=1)

class PTOPlanResponse(BaseModel):
    requestId: str
    approved: bool
    chosenOption: Optional[ScheduleOption] = None
    message: str
