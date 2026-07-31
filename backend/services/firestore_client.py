import requests
from datetime import datetime, timezone

PROJECT_ID = "iot-security-dashboard-f4c31"
API_KEY = "AIzaSyBaCk0gP31rLu1nN-p1h_g9eDvl8H1EeKA"
FIREBASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"


def _fields_to_firestore(data):
    fields = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            fields[key] = {"doubleValue": value}
        elif isinstance(value, list):
            fields[key] = {
                "arrayValue": {
                    "values": [{"doubleValue": float(v)} for v in value]
                }
            }
        elif isinstance(value, datetime):
            fields[key] = {"timestampValue": value.strftime("%Y-%m-%dT%H:%M:%SZ")}
        else:
            fields[key] = {"stringValue": str(value)}
    return fields


def _parse_value(value):
    if "stringValue" in value:
        return value["stringValue"]
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "arrayValue" in value:
        return [v.get("doubleValue", v.get("integerValue", 0)) for v in value["arrayValue"].get("values", [])]
    if "nullValue" in value:
        return None
    return None


def _parse_doc(doc):
    data = {"id": doc["name"].split("/")[-1]}
    for key, value in doc.get("fields", {}).items():
        data[key] = _parse_value(value)
    return data


def _request(method, url, body=None):
    params = {"key": API_KEY}
    try:
        r = requests.request(method, url, params=params, json=body, timeout=15)
        return r.status_code in (200, 201), r.json() if r.content else {}
    except requests.RequestException:
        return False, {}


def get_users():
    ok, data = _request("GET", f"{FIREBASE_URL}/users")
    if not ok:
        return []
    return [_parse_doc(doc) for doc in data.get("documents", [])]


def get_user_by_rfid(uid):
    users = get_users()
    for u in users:
        if u.get("rfid") and str(u["rfid"]).upper() == str(uid).upper():
            return u
    return None


def user_exists_rfid(uid):
    return get_user_by_rfid(uid) is not None


def add_user(name, role, rfid, encoding):
    doc = {
        "name": name,
        "role": role or "Empleado",
        "rfid": rfid.upper(),
        "encoding": encoding,
        "registered_at": datetime.now(timezone.utc)
    }
    return _request("POST", f"{FIREBASE_URL}/users", {"fields": _fields_to_firestore(doc)})


def update_user(doc_id, name, role, encoding):
    doc = {"name": name, "role": role or "Empleado", "encoding": encoding}
    return _request("PATCH", f"{FIREBASE_URL}/users/{doc_id}", {"fields": _fields_to_firestore(doc)})


def add_log(person, type_, method, helmet, status):
    doc = {
        "person": person,
        "type": type_,
        "method": method,
        "helmet": helmet,
        "status": status,
        "timestamp": datetime.now(timezone.utc)
    }
    return _request("POST", f"{FIREBASE_URL}/logs", {"fields": _fields_to_firestore(doc)})


def add_alert(type_, message, severity, person=None):
    doc = {
        "type": type_,
        "message": message,
        "severity": severity,
        "status": "active",
        "person": person or "",
        "timestamp": datetime.now(timezone.utc)
    }
    return _request("POST", f"{FIREBASE_URL}/alerts", {"fields": _fields_to_firestore(doc)})
