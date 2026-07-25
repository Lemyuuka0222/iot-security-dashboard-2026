from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AccessLog(BaseModel):
    person: str
    type: str  # entry / exit
    method: str  # rfid / facial / manual
    helmet: bool
    status: str  # authorized / denied
    timestamp: datetime

class Alert(BaseModel):
    type: str
    message: str
    timestamp: datetime
    severity: str  # low / medium / high

class DoorCommand(BaseModel):
    command: str  # open / close

class DoorState(BaseModel):
    state: str  # open / closed