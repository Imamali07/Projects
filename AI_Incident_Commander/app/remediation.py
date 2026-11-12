
import json
import logging
from datetime import datetime

import requests
from fastapi import APIRouter, HTTPException
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    inspect,
    text
)

from app.database import Base, SessionLocal, Incident, engine

router = APIRouter(tags=["Remediation"])

logging.basicConfig(level=logging.INFO)

SAMPLE_APP_URL = "http://sample-app:8001"


class RemediationRequest(Base):
    __tablename__ = "remediation_requests"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    action = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(30), default="pending")
    result = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    execution_status = Column(String(30), default="not_started")
    verification_status = Column(String(30), default="not_checked")
    execution_report = Column(Text, default="")
    executed_at = Column(DateTime, nullable=True)


# Create table and migrate existing database columns.
Base.metadata.create_all(bind=engine)

existing_columns = {
    column["name"]
    for column in inspect(engine).get_columns("remediation_requests")
}

migrations = {
    "execution_status": (
        "ALTER TABLE remediation_requests "
        "ADD COLUMN execution_status VARCHAR(30) DEFAULT 'not_started'"
    ),
    "verification_status": (
        "ALTER TABLE remediation_requests "
        "ADD COLUMN verification_status VARCHAR(30) DEFAULT 'not_checked'"
    ),
    "execution_report": (
        "ALTER TABLE remediation_requests "
        "ADD COLUMN execution_report TEXT DEFAULT ''"
    ),
    "executed_at": (
        "ALTER TABLE remediation_requests ADD COLUMN executed_at DATETIME"
    )
}

with engine.begin() as connection:
    for column_name, migration_sql in migrations.items():
        if column_name not in existing_columns:
            connection.execute(text(migration_sql))


def detect_database_failure(incident):
    """
    Detect database failure using incident details and
    the sample application's health endpoint.
    """

    query = " ".join([
        incident.alert_name or "",
        incident.summary or "",
        incident.description or ""
    ]).lower()

    # Check incident information first.
    if any(keyword in query for keyword in [
        "database",
        "connection",
        "db unavailable",
        "database unavailable"
    ]):
        return True

    # Check actual application health.
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
        logging.warning(
            "Unable to check sample application health "
            "for incident %s",
            incident.id
        )
        return False


def create_remediation_for_incident(incident_id):
    db = SessionLocal()

    try:
        existing = db.query(RemediationRequest).filter_by(
            incident_id=incident_id
        ).first()

        if existing:
            return existing.id

        incident = db.query(Incident).filter_by(
            id=incident_id
        ).first()

        if not incident:
            return None

        database_failure = detect_database_failure(incident)

        if database_failure:
            action = "check_database_connectivity"

            description = (
                "Database connectivity failure detected. "
                "Check database availability, network connectivity, "
                "connection pool usage, and credentials. "
                "Follow the Database Connection Failure runbook."
            )

        else:
            action = "investigate_application"

            description = (
                "Review application logs and metrics, identify the "
                "failure source, and follow the matching runbook."
            )

        request = RemediationRequest(
            incident_id=incident_id,
            action=action,
            description=description,
            status="pending"
        )

        db.add(request)
        db.commit()
        db.refresh(request)

        return request.id

    finally:
        db.close()


def execute_approved_remediation(db, item):

    report = {
        "remediation_id": item.id,
        "incident_id": item.incident_id,
        "action": item.action,
        "approval_status": "approved",
        "started_at": datetime.utcnow().isoformat(),
        "pre_execution_health": None,
        "execution_result": None,
        "post_execution_health": None,
        "verification": None
    }

    # Only configured automated actions can execute.
    if item.action != "check_database_connectivity":

        item.execution_status = "manual_required"
        item.verification_status = "not_applicable"

        report["execution_result"] = (
            "No automated executor is configured for this action."
        )

        report["verification"] = "Manual investigation required."

        item.execution_report = json.dumps(report, indent=2)
        item.executed_at = datetime.utcnow()
        item.result = "Approved. Manual remediation is required."

        db.commit()

        return report

    try:
        # Step 1: Check application health before execution.
        before = requests.get(
            f"{SAMPLE_APP_URL}/health",
            timeout=10
        )
        before.raise_for_status()

        report["pre_execution_health"] = before.json()

        # Step 2: Execute database recovery.
        execution = requests.post(
            f"{SAMPLE_APP_URL}/admin/remediate-database",
            timeout=10
        )
        execution.raise_for_status()

        report["execution_result"] = execution.json()

        # Step 3: Verify application health after recovery.
        after = requests.get(
            f"{SAMPLE_APP_URL}/health",
            timeout=10
        )
        after.raise_for_status()

        health_data = after.json()

        report["post_execution_health"] = health_data

        recovered = (
            health_data.get("status") == "healthy"
            and health_data.get("database") == "available"
        )

        incident = db.query(Incident).filter_by(
            id=item.incident_id
        ).first()

        if recovered:

            item.execution_status = "resolved"
            item.verification_status = "passed"

            item.result = (
                "Remediation executed successfully. "
                "Application health verification passed."
            )

            if incident:
                incident.status = "resolved"

            report["verification"] = "PASSED"

        else:

            item.execution_status = "failed"
            item.verification_status = "failed"

            item.result = (
                "Remediation was executed, but "
                "health verification failed."
            )

            if incident:
                incident.status = "remediation_failed"

            report["verification"] = "FAILED"

    except Exception as error:

        logging.exception(
            "Remediation execution failed: %s",
            item.id
        )

        item.execution_status = "failed"
        item.verification_status = "failed"

        item.result = (
            f"Remediation execution failed: {str(error)}"
        )

        incident = db.query(Incident).filter_by(
            id=item.incident_id
        ).first()

        if incident:
            incident.status = "remediation_failed"

        report["execution_result"] = {
            "error": str(error)
        }

        report["verification"] = "FAILED"

    item.executed_at = datetime.utcnow()

    report["completed_at"] = item.executed_at.isoformat()
    report["execution_status"] = item.execution_status

    item.execution_report = json.dumps(report, indent=2)

    db.commit()

    return report


@router.get("/incidents")
def get_incidents():

    db = SessionLocal()

    try:
        incidents = db.query(Incident).order_by(
            Incident.id.desc()
        ).all()

        return [
            {
                "id": item.id,
                "alert_name": item.alert_name,
                "status": item.status,
                "severity": item.severity,
                "summary": item.summary,
                "description": item.description,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at else None
                )
            }
            for item in incidents
        ]

    finally:
        db.close()


@router.get("/remediations")
def get_remediations():

    db = SessionLocal()

    try:
        items = db.query(RemediationRequest).order_by(
            RemediationRequest.id.desc()
        ).all()

        return [
            {
                "id": item.id,
                "incident_id": item.incident_id,
                "action": item.action,
                "description": item.description,
                "status": item.status,
                "result": item.result,
                "execution_status": item.execution_status,
                "verification_status": item.verification_status,
                "execution_report": item.execution_report,
                "executed_at": (
                    item.executed_at.isoformat()
                    if item.executed_at else None
                ),
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at else None
                ),
                "reviewed_at": (
                    item.reviewed_at.isoformat()
                    if item.reviewed_at else None
                )
            }
            for item in items
        ]

    finally:
        db.close()


@router.get("/remediations/{remediation_id}/report")
def get_execution_report(remediation_id: int):

    db = SessionLocal()

    try:
        item = db.query(RemediationRequest).filter_by(
            id=remediation_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Remediation request not found"
            )

        if not item.execution_report:
            raise HTTPException(
                status_code=404,
                detail="Execution report not available yet"
            )

        return json.loads(item.execution_report)

    finally:
        db.close()


@router.post("/remediations/{remediation_id}/approve")
def approve_remediation(remediation_id: int):

    db = SessionLocal()

    try:
        item = db.query(RemediationRequest).filter_by(
            id=remediation_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Remediation request not found"
            )

        if item.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Request is already {item.status}"
            )

        item.status = "approved"
        item.reviewed_at = datetime.utcnow()

        db.commit()

        report = execute_approved_remediation(db, item)

        return {
            "status": "approved",
            "remediation_id": item.id,
            "execution_status": item.execution_status,
            "verification_status": item.verification_status,
            "report": report
        }

    finally:
        db.close()


@router.post("/remediations/{remediation_id}/retry")
def retry_remediation(remediation_id: int):

    db = SessionLocal()

    try:
        item = db.query(RemediationRequest).filter_by(
            id=remediation_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Remediation request not found"
            )

        if item.status != "approved":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only approved remediation requests "
                    "can be retried."
                )
            )

        if item.execution_status not in (
            "not_started",
            "failed"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Retry is allowed only when execution is "
                    "not_started or failed. Current status: "
                    f"{item.execution_status}"
                )
            )

        logging.info(
            "Retrying approved remediation %s",
            item.id
        )

        report = execute_approved_remediation(db, item)

        return {
            "status": "retry_completed",
            "remediation_id": item.id,
            "execution_status": item.execution_status,
            "verification_status": item.verification_status,
            "report": report
        }

    finally:
        db.close()


@router.post("/remediations/{remediation_id}/reject")
def reject_remediation(remediation_id: int):

    db = SessionLocal()

    try:
        item = db.query(RemediationRequest).filter_by(
            id=remediation_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Remediation request not found"
            )

        if item.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Request is already {item.status}"
            )

        item.status = "rejected"
        item.reviewed_at = datetime.utcnow()
        item.result = "Rejected by human operator."

        db.commit()

        return {
            "status": "rejected",
            "remediation_id": item.id
        }

    finally:
        db.close()
