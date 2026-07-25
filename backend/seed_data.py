import requests
import random
from datetime import datetime, timedelta

PROJECT_ID = "iot-security-dashboard-f4c31"
API_KEY = "AIzaSyBaCk0gP31rLu1nN-p1h_g9eDvl8H1EeKA"
FIREBASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

PERSONAS = [
    "Carlos Lopez", "Maria Garcia", "Juan Perez", "Ana Martinez",
    "Pedro Hernandez", "Laura Sanchez", "Miguel Rodriguez", "Sofia Ramirez"
]

METHODS = ["rfid", "facial", "manual"]
TYPES = ["entry", "exit"]

def send_to_firestore(collection, data, timestamp):
    fields = {"timestamp": {"timestampValue": timestamp.isoformat() + "Z"}}
    for key, value in data.items():
        if isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        else:
            fields[key] = {"stringValue": str(value)}
    url = f"{FIREBASE_URL}/{collection}?key={API_KEY}"
    r = requests.post(url, json={"fields": fields})
    return r.status_code == 200

now = datetime.utcnow()
count = 0

for hours_ago in range(48, 0, -1):
    for _ in range(random.randint(2, 6)):
        ts = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59), seconds=random.randint(0, 59))
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

        if send_to_firestore("logs", data, ts):
            count += 1
            print(f"[{count:03d}] {ts.hour:02d}:{ts.minute:02d} - {person} - {type_} - {method} - {status}")

        if not helmet and status == "authorized":
            alert_data = {
                "person": person,
                "type": "SEGURIDAD",
                "message": f"{person} ingreso SIN CASCO",
                "severity": "high",
                "status": "active"
            }
            if send_to_firestore("alerts", alert_data, ts):
                print(f"  [!] ALERTA: {person} sin casco")

        if status == "denied":
            alert_data = {
                "person": person,
                "type": "ACCESO DENEGADO",
                "message": f"Intento denegado para {person} via {method}",
                "severity": "medium",
                "status": "active"
            }
            if send_to_firestore("alerts", alert_data, ts):
                print(f"  [!] Alerta: acceso denegado {person}")

print(f"\nTotal registros enviados: {count}")
