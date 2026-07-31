import os
import time
import threading
from collections import deque
from datetime import datetime

import cv2
import face_recognition
import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from services import firestore_client as fs
from services.security_service import SecurityService

router = APIRouter()

FACE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "faces")
os.makedirs(FACE_DIR, exist_ok=True)

service = SecurityService()

RESULT_TTL = 12
REGISTER_TTL = 60


class EspEvent(BaseModel):
    action: str  # login | register | cancel | rfid
    uid: str = None


class NamePayload(BaseModel):
    name: str = ""


class State:
    def __init__(self):
        self.phase = "idle"  # idle | scanning_face | register_face | register_rfid | result
        self.result = None
        self.temp_encoding = None
        self.temp_name = None
        self.phase_since = time.time()
        self.recent = deque(maxlen=8)
        self.lock = threading.Lock()

    def set_phase(self, phase):
        self.phase = phase
        self.phase_since = time.time()

    def clear_temp(self):
        self.temp_encoding = None
        self.temp_name = None

    def to_dict(self):
        self.check_timeout()
        view = {"phase": self.phase, "recent": list(self.recent)}
        if self.phase == "result":
            view["result"] = self.result
        if self.phase == "register_rfid":
            view["register"] = {"name": self.temp_name or ""}
        if self.phase in ("scanning_face", "register_face", "register_rfid", "result"):
            view["pill"] = self.pill_text()
            view["pillKind"] = self.pill_kind()
        return view

    def pill_text(self):
        return {
            "scanning_face": "VERIFICANDO...",
            "register_face": "REGISTRANDO ROSTRO",
            "register_rfid": "ESPERE TARJETA",
            "result": self.result.get("short", "") if self.result else "RESULTADO",
        }.get(self.phase, "SISTEMA LISTO")

    def pill_kind(self):
        if self.phase == "result":
            return "ok" if (self.result and self.result.get("authorized")) else "error"
        if self.phase != "idle":
            return "working"
        return ""

    def check_timeout(self):
        now = time.time()
        if self.phase == "result" and now - self.phase_since > RESULT_TTL:
            self.set_phase("idle")
            self.result = None
            self.clear_temp()
        elif self.phase in ("register_rfid", "register_face") and now - self.phase_since > REGISTER_TTL:
            self.set_phase("idle")
            self.clear_temp()
        elif self.phase == "scanning_face" and now - self.phase_since > 60:
            self.set_phase("idle")
            self.clear_temp()


state = State()


def _now_str():
    return datetime.now().strftime("%H:%M:%S")


def _add_recent(person, method, status):
    state.recent.appendleft({
        "person": person,
        "method": method,
        "status": status,
        "time": _now_str(),
    })


def _save_photo(frame):
    fname = f"access_{int(time.time())}.jpg"
    path = os.path.join(FACE_DIR, fname)
    cv2.imwrite(path, frame)
    return f"/faces/{fname}"


def _capture_face(max_wait=12):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None, None
    start = time.time()
    frame = None
    encoding = None
    while time.time() - start < max_wait:
        ret, f = cap.read()
        if ret:
            small = cv2.resize(f, (0, 0), fx=0.5, fy=0.5)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, locs)
            if encs:
                frame = f
                encoding = encs[0]
                break
        time.sleep(0.3)
    cap.release()
    return frame, encoding


def _compare(encoding, known_encoding, tolerance=0.5):
    try:
        matches = face_recognition.compare_faces(
            [np.array(known_encoding)], encoding, tolerance=tolerance
        )
        return bool(matches[0])
    except Exception:
        return False


def _login_facial():
    frame, encoding = _capture_face(max_wait=12)
    if encoding is None:
        return {"authorized": False, "message": "No se detectó un rostro", "short": "SIN ROSTRO", "photo": None, "user": None, "uid": None, "registered": False}

    photo = _save_photo(frame) if frame is not None else None
    helmet = service.detect_helmet(frame) if frame is not None else None

    users = fs.get_users()
    match = None
    for u in users:
        if u.get("encoding") and _compare(encoding, u["encoding"]):
            match = u
            break

    if match:
        name = match["name"]
        fs.add_log(name, "entry", "facial", bool(helmet), "authorized")
        if helmet is False:
            fs.add_alert("SEGURIDAD", f"{name} ingreso SIN CASCO", "high", person=name)
        _add_recent(name, "facial", "authorized")
        return {
            "authorized": True,
            "message": "Bienvenido" + ("" if helmet else ", use casco"),
            "short": "CONCEDIDO",
            "photo": photo,
            "user": {"name": name, "role": match.get("role", "Empleado")},
            "uid": None,
            "registered": False,
        }
    else:
        fs.add_log("Desconocido", "entry", "facial", False, "denied")
        fs.add_alert("ACCESO DENEGADO", "Rostro no registrado", "medium", person="Desconocido")
        _add_recent("Desconocido", "facial", "denied")
        return {
            "authorized": False,
            "message": "Rostro no registrado",
            "short": "DENEGADO",
            "photo": photo,
            "user": None,
            "uid": None,
            "registered": False,
        }


def _handle_rfid(uid):
    if not uid:
        return {"authorized": False, "message": "UID vacío", "short": "ERROR", "photo": None, "user": None, "uid": None, "registered": False}

    if state.phase == "register_rfid":
        name = (state.temp_name or "").strip() or f"Empleado-{uid[-4:]}"
        if state.temp_encoding is None:
            return {"authorized": False, "message": "Primero capture el rostro", "short": "ERROR", "photo": None, "user": None, "uid": uid, "registered": False}

        existing = fs.get_user_by_rfid(uid)
        if existing:
            fs.update_user(existing["id"], name, "Empleado", state.temp_encoding.tolist())
        else:
            fs.add_user(name, "Empleado", uid, state.temp_encoding.tolist())

        fs.add_log(name, "entry", "rfid", True, "authorized")
        _add_recent(name, "rfid", "authorized")
        state.clear_temp()
        result = {
            "authorized": True,
            "message": f"{name} registrado correctamente",
            "short": "REGISTRADO",
            "photo": None,
            "user": {"name": name, "role": "Empleado"},
            "uid": uid,
            "registered": True,
        }
        state.result = result
        state.set_phase("result")
        return result

    user = fs.get_user_by_rfid(uid)
    if user:
        fs.add_log(user["name"], "entry", "rfid", True, "authorized")
        _add_recent(user["name"], "rfid", "authorized")
        result = {
            "authorized": True,
            "message": "Bienvenido",
            "short": "CONCEDIDO",
            "photo": None,
            "user": {"name": user["name"], "role": user.get("role", "Empleado")},
            "uid": uid,
            "registered": False,
        }
        state.result = result
        state.set_phase("result")
        return result

    fs.add_log(f"Tarjeta {uid}", "entry", "rfid", False, "denied")
    fs.add_alert("ACCESO DENEGADO", f"Tarjeta no registrada: {uid}", "medium", person="Desconocido")
    _add_recent(f"Tarjeta {uid[-4:]}", "rfid", "denied")
    result = {
        "authorized": False,
        "message": "Tarjeta no registrada",
        "short": "DENEGADO",
        "photo": None,
        "user": None,
        "uid": uid,
        "registered": False,
    }
    state.result = result
    state.set_phase("result")
    return result


def _to_result(res):
    state.result = res
    state.set_phase("result")
    return res


@router.get("/access/state")
def get_state():
    with state.lock:
        return state.to_dict()


@router.post("/esp/event")
def esp_event(event: EspEvent):
    with state.lock:
        action = event.action
        if action == "login":
            state.set_phase("scanning_face")
            res = _login_facial()
            return _to_result(res)
        elif action == "register":
            state.set_phase("register_face")
            frame, encoding = _capture_face(max_wait=15)
            if encoding is None:
                state.set_phase("idle")
                return _to_result({"authorized": False, "message": "No se detectó un rostro", "short": "SIN ROSTRO", "photo": None, "user": None, "uid": None, "registered": False})
            state.temp_encoding = encoding
            if frame is not None:
                _save_photo(frame)
            state.set_phase("register_rfid")
            return {"phase": "register_rfid", "message": "Acerca la tarjeta RFID"}
        elif action == "cancel":
            state.set_phase("idle")
            state.result = None
            state.clear_temp()
            return {"phase": "idle", "message": "Operación cancelada"}
        elif action == "rfid":
            return _handle_rfid(event.uid)
        else:
            return {"phase": state.phase, "error": "acción desconocida"}


@router.post("/esp/rfid")
def esp_rfid(event: EspEvent):
    with state.lock:
        return _handle_rfid(event.uid)


@router.post("/access/name")
def set_name(payload: NamePayload):
    with state.lock:
        state.temp_name = payload.name.strip()[:40]
        return {"ok": True, "name": state.temp_name}
