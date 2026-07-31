import os
import socket

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import logs, alerts, door, access
import uvicorn

app = FastAPI(title="IoT Security Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(door.router, prefix="/api")
app.include_router(access.router, prefix="/api")

backend_dir = os.path.dirname(__file__)

data_dir = os.path.join(backend_dir, "data", "faces")
if os.path.exists(data_dir):
    app.mount("/faces", StaticFiles(directory=data_dir), name="faces")

access_dir = os.path.join(backend_dir, "..", "access")
if os.path.exists(access_dir):
    app.mount("/access", StaticFiles(directory=access_dir, html=True), name="access")

dashboard_path = os.path.join(backend_dir, "..", "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="dashboard")


def print_lan_ips():
    print("=" * 50)
    print("IoT Security - Interfaz de Acceso")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    print(f"Interfaz vertical : http://{ip}:8000/access")
    print(f"Dashboard         : http://{ip}:8000/")
    print(f"Configura esta IP en el ESP32: http://{ip}:8000")
    print("=" * 50)


if __name__ == "__main__":
    print_lan_ips()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
