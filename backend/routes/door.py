from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

door_state = {"state": "closed"}

class DoorResponse(BaseModel):
    success: bool
    state: str

@router.get("/door", response_model=DoorResponse)
def get_door_state():
    return DoorResponse(success=True, state=door_state["state"])

@router.post("/door/open", response_model=DoorResponse)
def open_door():
    door_state["state"] = "open"
    return DoorResponse(success=True, state="open")

@router.post("/door/close", response_model=DoorResponse)
def close_door():
    door_state["state"] = "closed"
    return DoorResponse(success=True, state="closed")