from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import logs, alerts, door
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

@app.get("/")
def root():
    return {"status": "online", "message": "IoT Security Dashboard API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)