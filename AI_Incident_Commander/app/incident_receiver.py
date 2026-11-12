import json
import logging

from fastapi import APIRouter, HTTPException

from app.database import SessionLocal, Incident, init_db
from app.ai_investigator import investigate_incident
from app.remediation import create_remediation_for_incident

router = APIRouter()

init_db()


@router.post("/webhook/incident")
async def receive_incident(data: dict):

    db = SessionLocal()

    saved_incidents = []
    updated_incidents = []
    investigations = []
    remediation_requests = []

    try:
        alerts = data.get("alerts", []) or [data]

        for alert in alerts:

            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})

            alert_status = alert.get(
                "status",
                data.get("status", "unknown")
            )

            fingerprint = alert.get("fingerprint")

            # Handle resolved alerts.
            if alert_status == "resolved":

                existing_incident = None

                if fingerprint:
                    existing_incident = (
                        db.query(Incident)
                        .filter(
                            Incident.raw_payload.like(
                                f'%"fingerprint": "{fingerprint}"%'
                            )
                        )
                        .order_by(Incident.id.desc())
                        .first()
                    )

                if existing_incident:

                    existing_incident.status = "resolved"

                    existing_incident.raw_payload = json.dumps(alert)

                    updated_incidents.append(
                        existing_incident.id
                    )

                else:

                    # Store unmatched resolved alerts for audit.
                    incident = Incident(
                        alert_name=labels.get(
                            "alertname",
                            "Unknown Alert"
                        ),
                        status="resolved",
                        severity=labels.get("severity", "unknown"),
                        summary=annotations.get("summary", ""),
                        description=annotations.get("description", ""),
                        raw_payload=json.dumps(alert)
                    )

                    db.add(incident)
                    db.flush()

                    saved_incidents.append(incident.id)

                # Never create remediation for resolved alerts.
                continue

            # Handle firing alerts.
            incident = Incident(
                alert_name=labels.get(
                    "alertname",
                    "Unknown Alert"
                ),
                status=alert_status,
                severity=labels.get("severity", "unknown"),
                summary=annotations.get("summary", ""),
                description=annotations.get("description", ""),
                raw_payload=json.dumps(alert)
            )

            db.add(incident)
            db.flush()

            saved_incidents.append(incident.id)

        db.commit()

    except Exception as e:

        db.rollback()

        logging.exception("Incident storage failed")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

    # Investigate and create remediation only for new firing incidents.
    for incident_id in saved_incidents:

        try:
            incident_result = investigate_incident(incident_id)

            investigations.append(incident_result)

            # Do not create remediation for resolved incidents.
            db = SessionLocal()

            try:
                incident = db.query(Incident).filter_by(
                    id=incident_id
                ).first()

                if not incident or incident.status != "firing":
                    continue

            finally:
                db.close()

            remediation_id = create_remediation_for_incident(
                incident_id
            )

            remediation_requests.append({
                "incident_id": incident_id,
                "remediation_id": remediation_id,
                "status": "pending"
            })

        except Exception as e:

            logging.exception(
                "Incident processing failed for %s",
                incident_id
            )

            investigations.append({
                "incident_id": incident_id,
                "status": "investigation_failed",
                "error": str(e)
            })

    return {
        "status": "received",
        "saved_incident_ids": saved_incidents,
        "updated_incident_ids": updated_incidents,
        "investigations": investigations,
        "remediation_requests": remediation_requests
    }