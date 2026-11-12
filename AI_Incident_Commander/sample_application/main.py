from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import logging
import time
import random
import os

app = FastAPI(title="Messaging Application")

os.makedirs("/app/sample_application/logs", exist_ok=True)

logging.basicConfig(
    filename="/app/sample_application/logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

MESSAGES_SENT = Counter(
    "messages_sent_total",
    "Total successful messages"
)

MESSAGES_FAILED = Counter(
    "messages_failed_total",
    "Total failed messages"
)

REQUEST_TIME = Histogram(
    "message_request_duration_seconds",
    "Message request processing time"
)

# 1 = Database available, 0 = Database unavailable
DATABASE_AVAILABLE = Gauge(
    "database_available",
    "Database availability: 1=available, 0=unavailable"
)

app.mount("/metrics", make_asgi_app())

database_available = True
DATABASE_AVAILABLE.set(1)


@app.get("/")
def home():
    return {"message": "Messaging Application Running"}


@app.get("/health")
def health():
    if not database_available:
        return {
            "status": "unhealthy",
            "database": "unavailable"
        }

    return {
        "status": "healthy",
        "database": "available"
    }


@app.post("/send-message")
def send_message(message: str):
    start_time = time.time()

    try:
        if not database_available:
            raise Exception("Database connection failed")

        time.sleep(0.2)

        if random.random() < 0.2:
            raise Exception("Simulated message failure")

        MESSAGES_SENT.inc()
        logging.info(f"Message sent: {message}")

        return {
            "status": "success",
            "message": message
        }

    except Exception as e:
        MESSAGES_FAILED.inc()
        logging.error(f"Message failed: {str(e)}")

        return {
            "status": "failed",
            "error": str(e)
        }

    finally:
        REQUEST_TIME.observe(time.time() - start_time)


@app.post("/admin/simulate-database-failure")
def simulate_database_failure():
    global database_available

    database_available = False
    DATABASE_AVAILABLE.set(0)

    logging.error("Simulated database failure activated")

    return {
        "status": "failure_simulated",
        "database": "unavailable"
    }


@app.post("/admin/remediate-database")
def remediate_database():
    global database_available

    database_available = True
    DATABASE_AVAILABLE.set(1)

    logging.info("Simulated database recovery executed")

    return {
        "status": "remediation_executed",
        "database": "available"
    }
