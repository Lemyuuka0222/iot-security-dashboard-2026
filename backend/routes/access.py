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
VERIFY_TTL = 45


class EspEvent(BaseModel):
    action: str  # login | register | cancel | rfid
    uid: str = None


class NamePayload(BaseModel):
    name: str = ""


class State:
    def __init__(self):
        self.phase = "idle"  # idle | scanning_face | register_face | register_rfid | verify_rfid | result
        self.result = None
        self.temp_encoding = None
        self.temp_name = None
        self.pending_user = None
        self.phase_since = time.time()
        self.recent = deque(maxlen=8)
        self.lock = threading.Lock()

    def set_phase(self, phase):
        self.phase = phase
        self.phase_since = time.time()

    def clear_temp(self):
        self.temp_encoding = None
        self.temp_name = None
        self.pending_user = None

    def to_dict(self):
        self.check_timeout()
        view = {"phase": self.phase, "recent": list(self.recent)}
        if self.phase == "result":
            view["result"] = self.result
        if self.phase == "register_rfid":
            view["register"] = {"name": self.temp_name or ""}
        if self.phase == "verify_rfid":
            view["verify"] = {"name": self.pending_user.get("name", "") if self.pending_user else ""}
        if self.phase in ("scanning_face", "register_face", "register_rfid", "verify_rfid", "result"):
            view["pill"] = self.pill_text()
            view["pillKind"] = self.pill_kind()
        return view

    def pill_text(self):
        return {
            "scanning_face": "VERIFICANDO...",
            "register_face": "REGISTRANDO ROSTRO",
            "register_rfid": "ESPERE TARJETA",
            "verify_rfid": "ACERQUE TARJETA",
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
        elif self.phase == "verify_rfid" and now - self.phase_since > VERIFY_TTL:
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


def _find_user_by_face(encoding):
    for u in fs.get_users():
        if u.get("encoding") and _compare(encoding, u["encoding"]):
            return u
    return None


def _result(authorized, message, short, user=None, photo=None, uid=None, registered=False):
    return {
        "authorized": authorized,
        "message": message,
        "short": short,
        "photo": photo,
        "user": user,
        "uid": uid,
        "registered": registered,
    }


def _finish_result(res):
    state.result = res
    state.set_phase("result")
    return res


def _log_access(person, method, helmet, status, alert_msg=None, alert_type="ACCESO DENEGADO"):
    fs.add_log(person, "entry", method, helmet, status)
    _add_recent(person, method, status)
    if alert_msg:
        fs.add_alert(alert_type, alert_msg, "medium", person=person)


def _deny(message, short, person="Desconocido", method="rfid", uid=None, photo=None):
    _log_access(person, method, False, "denied", alert_msg=message)
    return _finish_result(_result(False, message, short, None, photo, uid))


def _authorize(user, method, helmet, message="Bienvenido", photo=None, uid=None):
    name = user["name"]
    fs.add_log(name, "entry", method, bool(helmet), "authorized")
    _add_recent(name, method, "authorized")
    if helmet is False:
        fs.add_alert("SEGURIDAD", f"{name} ingreso SIN CASCO", "high", person=name)
        message = "Bienvenido, use casco"
    return _finish_result(_result(
        True, message, "CONCEDIDO",
        {"name": name, "role": user.get("role", "Empleado")}, photo, uid
    ))


# ================= Flujo: LOGIN (facial -> luego tarjeta) =================
def _login_facial():
    frame, encoding = _capture_face(max_wait=12)
    if encoding is None:
        return _deny("No se detectó un rostro", "SIN ROSTRO", method="facial")

    photo = _save_photo(frame) if frame is not None else None
    user = _find_user_by_face(encoding)
    if user is None:
        _log_access("Desconocido", "facial", False, "denied",
                    alert_msg="Rostro no registrado")
        return _finish_result(_result(False, "Rostro no registrado", "DENEGADO", None, photo))

    if not user.get("rfid"):
        _log_access(user["name"], "facial", False, "denied",
                    alert_msg=f"{user['name']} no tiene tarjeta asignada")
        return _finish_result(_result(False, "No tiene tarjeta asignada", "DENEGADO",
                                      {"name": user["name"], "role": user.get("role", "Empleado")}, photo))

    state.pending_user = user
    state.set_phase("verify_rfid")
    return {
        "phase": "verify_rfid",
        "message": "Acerca su tarjeta para confirmar",
        "user": {"name": user["name"], "role": user.get("role", "Empleado")},
    }


# ================= Flujo: RFID (tarjeta -> luego facial) =================
def _rfid_then_face(uid):
    user = fs.get_user_by_rfid(uid)
    if user is None:
        return _deny(f"Tarjeta {uid} no registrada", "DENEGADO", person=f"Tarjeta {uid[-4:]}", uid=uid)

    if not user.get("encoding"):
        _log_access(user["name"], "rfid", False, "denied",
                    alert_msg=f"{user['name']} no tiene rostro registrado")
        return _finish_result(_result(False, "No tiene rostro registrado", "DENEGADO",
                                      {"name": user["name"], "role": user.get("role", "Empleado")}, uid=uid))

    state.set_phase("scanning_face")
    state.pending_user = user
    frame, encoding = _capture_face(max_wait=12)
    state.pending_user = None

    if encoding is None:
        _log_access(user["name"], "rfid", False, "denied",
                    alert_msg=f"{user['name']} no mostró rostro")
        return _finish_result(_result(False, "No se detectó un rostro", "DENEGADO",
                                      {"name": user["name"], "role": user.get("role", "Empleado")}, uid=uid))

    photo = _save_photo(frame) if frame is not None else None
    if _compare(encoding, user["encoding"]):
        helmet = service.detect_helmet(frame) if frame is not None else None
        return _authorize(user, "dual", helmet, uid=uid, photo=photo)
    else:
        _log_access(user["name"], "rfid", False, "denied",
                    alert_msg=f"Rostro no coincide con la tarjeta de {user['name']}")
        return _finish_result(_result(False, "El rostro no coincide con la tarjeta", "DENEGADO",
                                      {"name": user["name"], "role": user.get("role", "Empleado")}, photo, uid))


# ================= Handler RFID =================
def _handle_rfid(uid):
    if not uid:
        return _finish_result(_result(False, "UID vacío", "ERROR"))

    if state.phase == "register_rfid":
        name = (state.temp_name or "").strip() or f"Empleado-{uid[-4:]}"
        if state.temp_encoding is None:
            return _finish_result(_result(False, "Primero capture el rostro", "ERROR", uid=uid))

        existing = fs.get_user_by_rfid(uid)
        if existing:
            fs.update_user(existing["id"], name, "Empleado", state.temp_encoding.tolist())
        else:
            fs.add_user(name, "Empleado", uid, state.temp_encoding.tolist())

        state.clear_temp()
        return _finish_result(_result(True, f"{name} registrado correctamente", "REGISTRADO",
                                      {"name": name, "role": "Empleado"}, uid=uid, registered=True))

    if state.phase == "verify_rfid":
        user = state.pending_user
        state.pending_user = None
        state.set_phase("idle")
        if user and user.get("rfid") and str(user["rfid"]).upper() == str(uid).upper():
            return _authorize(user, "dual", None, message="Bienvenido", uid=uid)
        else:
            return _deny("La tarjeta no corresponde al rostro", "DENEGADO",
                         person=user["name"] if user else "Desconocido", method="facial", uid=uid)

    return _rfid_then_face(uid)


# ================= Endpoints =================
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
            return _login_facial()
        elif action == "register":
            state.set_phase("register_face")
            frame, encoding = _capture_face(max_wait=15)
            if encoding is None:
                state.set_phase("idle")
                return _finish_result(_result(False, "No se detectó un rostro", "SIN ROSTRO"))
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
