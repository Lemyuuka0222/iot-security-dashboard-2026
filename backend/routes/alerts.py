from fastapi import APIRouter
from models.schemas import Alert
from typing import List

router = APIRouter()

alerts_db: List[Alert] = []

@router.get("/alerts", response_model=List[Alert])
def get_alerts():
    return alerts_db

@router.post("/alerts", response_model=Alert)
def create_alert(alert: Alert):
    alerts_db.append(alert)
    return alert

@router.get("/alerts/active")
def get_active_alerts():
    return alerts_db[-5:] if alerts_db else []