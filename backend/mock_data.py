import requests
import random
import time
from datetime import datetime

PROJECT_ID = "iot-security-dashboard-f4c31"
API_KEY = "AIzaSyBaCk0gP31rLu1nN-p1h_g9eDvl8H1EeKA"
FIREBASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

PERSONAS = [
    "Carlos Lopez", "Maria Garcia", "Juan Perez", "Ana Martinez",
    "Pedro Hernandez", "Laura Sanchez", "Miguel Rodriguez", "Sofia Ramirez"
]

METHODS = ["rfid", "facial", "manual"]
TYPES = ["entry", "exit"]

def send_to_firestore(collection, data):
    now = datetime.now()
    body = {
        "fields": {
            "person": {"stringValue": data["person"]},
            "type": {"stringValue": data["type"]},
            "method": {"stringValue": data["method"]},
            "helmet": {"booleanValue": data["helmet"]},
            "status": {"stringValue": data["status"]},
            "timestamp": {"timestampValue": now.isoformat() + "Z"}
        }
    }
    url = f"{FIREBASE_URL}/{collection}?key={API_KEY}"
    r = requests.post(url, json=body)
    return r.status_code == 200

print("Enviando datos a Firebase Firestore...")
print("Presiona Ctrl+C para detener")

event_count = 0

while True:
    person = random.choice(PERSONAS)
    method = random.choice(METHODS)
    type_ = random.choice(TYPES)

    helmet = True
    status = "authorized"

    if method == "rfid" and random.random() < 0.15:
        status = "denied"
    elif method == "facial" and random.random() < 0.1:
        status = "denied"

    if method == "facial" and random.random() < 0.2 and status == "authorized":
        helmet = False

    data = {
        "person": person,
        "type": type_,
        "method": method,
        "helmet": helmet,
        "status": status
    }

    if send_to_firestore("logs", data):
        event_count += 1
        print(f"[{event_count:03d}] {person} - {type_} - {method} - {'Con casco' if helmet else 'SIN CASCO'} - {status}")

    if not helmet and status == "authorized":
        alert_data = {
            "person": person,
            "type": "SEGURIDAD",
            "message": f"{person} ingreso SIN CASCO",
            "severity": "high",
            "status": "active"
        }
        if send_to_firestore("alerts", alert_data):
            print(f"  [!] ALERTA: {person} sin casco!")

    if status == "denied":
        alert_data = {
            "person": person,
            "type": "ACCESO DENEGADO",
            "message": f"Intento denegado para {person} via {method}",
            "severity": "medium",
            "status": "active"
        }
        if send_to_firestore("alerts", alert_data):
            print(f"  [!] Acceso denegado: {person}")

    time.sleep(random.uniform(1, 3))
