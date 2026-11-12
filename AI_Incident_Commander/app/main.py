
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from app.incident_receiver import router as incident_router
from app.remediation import router as remediation_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="AI Production Incident Commander",
    version="1.0.0"
)

app.include_router(incident_router)
app.include_router(remediation_router)
app.mount("/metrics", make_asgi_app())


@app.get("/")
async def home():
    return {
        "project": "AI Production Incident Commander",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
