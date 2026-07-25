import requests
import random
import time
from datetime import datetime

API_URL = "http://localhost:8000"

PERSONAS = [
    "Carlos Lopez", "Maria Garcia", "Juan Perez", "Ana Martinez",
    "Pedro Hernandez", "Laura Sanchez", "Miguel Rodriguez", "Sofia Ramirez"
]

METHODS = ["rfid", "facial", "manual"]
TYPES = ["entry", "exit"]

def send_log(person, type_, method, helmet, status):
    log = {
        "person": person,
        "type": type_,
        "method": method,
        "helmet": helmet,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    try:
        r = requests.post(f"{API_URL}/api/logs", json=log)
        return r.status_code == 200
    except:
        return False

def send_alert(alert_type, message, severity="medium"):
    alert = {
        "type": alert_type,
        "message": message,
        "severity": severity,
        "timestamp": datetime.now().isoformat()
    }
    try:
        r = requests.post(f"{API_URL}/api/alerts", json=alert)
        return r.status_code == 200
    except:
        return False

print("Iniciando simulador de datos...")
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

    if send_log(person, type_, method, helmet, status):
        event_count += 1
        print(f"[{event_count:03d}] {person} - {type_} - {method} - {'Con casco' if helmet else 'SIN CASCO'} - {status}")

    if not helmet and status == "authorized":
        send_alert(
            "SEGURIDAD",
            f"{person} ingreso SIN CASCO de seguridad",
            "high"
        )
        print(f"  [!] ALERTA: {person} sin casco!")

    if status == "denied":
        send_alert(
            "ACCESO DENEGADO",
            f"Intento de acceso denegado para {person} via {method}",
            "medium"
        )
        print(f"  [!] Acceso denegado: {person}")

    time.sleep(random.uniform(1, 3))
