from pathlib import Path

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.database import SessionLocal, Incident

RUNBOOK_DIR = Path("/app/knowledge_base/runbooks")
SAMPLE_APP_URL = "http://sample-app:8001"


def check_database_health():
    try:
        response = requests.get(
            f"{SAMPLE_APP_URL}/health",
            timeout=5
        )
        response.raise_for_status()

        health = response.json()

        return (
            health.get("status") == "unhealthy"
            and health.get("database") == "unavailable"
        )

    except requests.RequestException:
        return False


def retrieve_runbook(query):
    documents = []

    if not RUNBOOK_DIR.exists():
        return "No runbooks available."

    for file in RUNBOOK_DIR.glob("*.txt"):
        content = file.read_text(encoding="utf-8")
        documents.append({
            "name": file.name,
            "content": content
        })

    if not documents:
        return "No runbooks available."

    texts = [doc["content"] for doc in documents]

    vectorizer = TfidfVectorizer(stop_words="english")
    vectors = vectorizer.fit_transform(texts + [query])

    scores = cosine_similarity(
        vectors[-1],
        vectors[:-1]
    )[0]

    best_index = scores.argmax()

    if scores[best_index] == 0:
        return "No matching runbook found."

    return documents[best_index]["content"]


def investigate_incident(incident_id):
    db = SessionLocal()

    try:
        incident = db.query(Incident).filter(
            Incident.id == incident_id
        ).first()

        if not incident:
            return {
                "incident_id": incident_id,
                "error": "Incident not found"
            }

        query = " ".join([
            incident.alert_name or "",
            incident.summary or "",
            incident.description or ""
        ])

        database_failure = (
            "database" in query.lower()
            or "connection" in query.lower()
            or check_database_health()
        )

        if database_failure:
            root_cause = (
                "Database connectivity failure detected. "
                "The application health endpoint reports "
                "that the database is unavailable."
            )

            runbook_query = (
                query + " database connection failure database unavailable"
            )

        else:
            root_cause = (
                "Root cause requires further investigation "
                "using application logs and metrics."
            )

            runbook_query = query

        runbook = retrieve_runbook(runbook_query)

        return {
            "incident_id": incident.id,
            "root_cause": root_cause,
            "matched_runbook": runbook,
            "recommended_action": (
                "check_database_connectivity"
                if database_failure
                else "investigate_application"
            ),
            "status": "investigated"
        }

    finally:
        db.close()