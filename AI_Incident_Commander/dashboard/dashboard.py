
import os
import json
import requests
import streamlit as st

API_URL = os.getenv("API_BASE_URL", "http://incident-api:8000")
SAMPLE_APP_URL = os.getenv(
    "SAMPLE_APP_URL",
    "http://sample-app:8001"
)

st.set_page_config(
    page_title="AI Production Incident Commander",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚨 AI Production Incident Commander")
st.caption(
    "AI-powered incident monitoring, investigation, "
    "human approval and automated recovery"
)

# -------------------------
# API FUNCTIONS
# -------------------------

def get_data(endpoint):
    try:
        response = requests.get(
            f"{API_URL}{endpoint}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        st.error(f"API connection failed: {error}")
        return None


def get_application_health():
    try:
        response = requests.get(
            f"{SAMPLE_APP_URL}/health",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {
            "status": "unreachable",
            "database": "unknown"
        }


def perform_action(endpoint, action_name):
    try:
        response = requests.post(
            f"{API_URL}{endpoint}",
            timeout=30
        )
        response.raise_for_status()
        st.success(f"{action_name} completed successfully.")
        st.rerun()
    except requests.RequestException as error:
        st.error(f"{action_name} failed: {error}")


# -------------------------
# SIDEBAR
# -------------------------

st.sidebar.title("🚨 Incident Commander")

if st.sidebar.button("🔄 Refresh Dashboard", use_container_width=True):
    st.rerun()

st.sidebar.divider()

st.sidebar.markdown("### Navigation")

page = st.sidebar.radio(
    "Select View",
    [
        "Overview",
        "Incidents",
        "Remediation Center",
        "Execution Reports"
    ]
)

st.sidebar.divider()
st.sidebar.caption("AI Production Incident Commander")


# -------------------------
# LOAD DATA
# -------------------------

incidents = get_data("/incidents")
remediations = get_data("/remediations")
health = get_application_health()

if incidents is None or remediations is None:
    st.error("Unable to load dashboard data.")
    st.stop()

incidents = sorted(
    incidents,
    key=lambda x: x["id"],
    reverse=True
)

remediations = sorted(
    remediations,
    key=lambda x: x["id"],
    reverse=True
)


# -------------------------
# METRICS
# -------------------------

pending = sum(
    item["status"] == "pending"
    for item in remediations
)

approved = sum(
    item["status"] == "approved"
    for item in remediations
)

resolved = sum(
    item.get("execution_status") == "resolved"
    for item in remediations
)

failed = sum(
    item.get("execution_status") == "failed"
    for item in remediations
)

manual = sum(
    item.get("execution_status") == "manual_required"
    for item in remediations
)


# -------------------------
# APPLICATION HEALTH
# -------------------------

st.subheader("Application Health")

health_col1, health_col2 = st.columns(2)

with health_col1:
    if health.get("status") == "healthy":
        st.success("Application: HEALTHY")
    elif health.get("status") == "unhealthy":
        st.error("Application: UNHEALTHY")
    else:
        st.warning("Application: UNREACHABLE")

with health_col2:
    if health.get("database") == "available":
        st.success("Database: AVAILABLE")
    elif health.get("database") == "unavailable":
        st.error("Database: UNAVAILABLE")
    else:
        st.warning("Database: UNKNOWN")


# -------------------------
# OVERVIEW
# -------------------------

if page == "Overview":

    st.divider()
    st.subheader("📊 System Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Incidents", len(incidents))
    col2.metric("Pending Approval", pending)
    col3.metric("Approved", approved)
    col4.metric("Resolved", resolved)
    col5.metric("Failed", failed)

    st.divider()

    st.subheader("📋 Recent Incidents")

    if not incidents:
        st.info("No incidents available.")

    for incident in incidents[:10]:

        with st.expander(
            f"Incident #{incident['id']} - "
            f"{incident['alert_name']}"
        ):

            st.write("Severity:", incident["severity"])
            st.write("Status:", incident["status"])
            st.write("Summary:", incident["summary"])
            st.write("Description:", incident["description"])
            st.write("Created:", incident["created_at"])

    st.divider()

    st.subheader("🛠️ Remediation Summary")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric("Manual Required", manual)
    summary_col2.metric("Successful Recoveries", resolved)
    summary_col3.metric("Failed Executions", failed)


# -------------------------
# INCIDENTS PAGE
# -------------------------

elif page == "Incidents":

    st.subheader("📋 Incident Monitoring")

    status_filter = st.selectbox(
        "Filter by incident status",
        ["All", "firing", "resolved", "remediation_failed"]
    )

    filtered_incidents = incidents

    if status_filter != "All":
        filtered_incidents = [
            item for item in incidents
            if item["status"] == status_filter
        ]

    st.write(f"Showing {len(filtered_incidents)} incidents")

    for incident in filtered_incidents:

        with st.expander(
            f"Incident #{incident['id']} - "
            f"{incident['alert_name']}"
        ):

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Severity:**", incident["severity"])
                st.write("**Status:**", incident["status"])

            with col2:
                st.write("**Created:**", incident["created_at"])

            st.write("**Summary:**", incident["summary"])
            st.write("**Description:**", incident["description"])


# -------------------------
# REMEDIATION CENTER
# -------------------------

elif page == "Remediation Center":

    st.subheader("🛡️ Human Approval & Remediation Center")

    if not remediations:
        st.info("No remediation requests available.")

    for item in remediations:

        with st.container(border=True):

            st.markdown(
                f"### Remediation #{item['id']} "
                f"| Incident #{item['incident_id']}"
            )

            st.write("**Recommended Action:**", item["action"])
            st.write("**Instructions:**", item["description"])

            status = item["status"]
            execution = item.get(
                "execution_status",
                "not_started"
            )
            verification = item.get(
                "verification_status",
                "not_checked"
            )

            col1, col2, col3 = st.columns(3)

            col1.write(f"**Approval:** {status}")
            col2.write(f"**Execution:** {execution}")
            col3.write(f"**Verification:** {verification}")

            if status == "pending":

                st.warning("Waiting for human approval.")

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button(
                        "✅ Approve & Execute",
                        key=f"approve_{item['id']}",
                        type="primary"
                    ):
                        perform_action(
                            f"/remediations/{item['id']}/approve",
                            "Approval and execution"
                        )

                with col_b:
                    if st.button(
                        "❌ Reject",
                        key=f"reject_{item['id']}"
                    ):
                        perform_action(
                            f"/remediations/{item['id']}/reject",
                            "Rejection"
                        )

            elif execution == "resolved":
                st.success("Recovery verified successfully.")

            elif execution == "failed":
                st.error("Remediation execution failed.")

            elif execution == "manual_required":
                st.warning("Manual investigation required.")

            elif status == "rejected":
                st.error("Remediation rejected.")

            elif status == "approved":
                st.info("Approved. Check execution status.")


# -------------------------
# EXECUTION REPORTS
# -------------------------

elif page == "Execution Reports":

    st.subheader("📄 Remediation Execution Reports")

    reports_available = [
        item for item in remediations
        if item.get("execution_report")
    ]

    if not reports_available:
        st.info("No execution reports available.")

    for item in reports_available:

        with st.expander(
            f"Remediation #{item['id']} "
            f"| Incident #{item['incident_id']}"
        ):

            st.write("**Action:**", item["action"])
            st.write("**Execution Status:**", item["execution_status"])
            st.write("**Verification:**", item["verification_status"])
            st.write("**Executed At:**", item.get("executed_at"))

            try:
                response = requests.get(
                    f"{API_URL}/remediations/"
                    f"{item['id']}/report",
                    timeout=10
                )
                response.raise_for_status()

                report = response.json()

                st.json(report)

                st.download_button(
                    "⬇️ Download JSON Report",
                    data=json.dumps(report, indent=4),
                    file_name=(
                        f"incident_{item['incident_id']}_"
                        f"remediation_{item['id']}.json"
                    ),
                    mime="application/json",
                    key=f"download_{item['id']}"
                )

            except requests.RequestException as error:
                st.error(f"Report retrieval failed: {error}")


# -------------------------
# FOOTER
# -------------------------

st.divider()

st.caption(
    "AI Production Incident Commander | "
    "Monitoring • Investigation • Human Approval • "
    "Automated Remediation • Verification"
)
