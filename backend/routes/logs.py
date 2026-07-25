from fastapi import APIRouter, HTTPException
from models.schemas import AccessLog
from typing import List
from datetime import datetime

router = APIRouter()

logs_db: List[AccessLog] = []

@router.get("/logs", response_model=List[AccessLog])
def get_logs():
    return logs_db

@router.post("/logs", response_model=AccessLog)
def create_log(log: AccessLog):
    logs_db.append(log)
    return log

@router.get("/logs/today")
def get_today_logs():
    today = datetime.now().date()
    return [log for log in logs_db if log.timestamp.date() == today]

@router.get("/logs/latest")
def get_latest_logs(limit: int = 10):
    return logs_db[-limit:] if logs_db else []