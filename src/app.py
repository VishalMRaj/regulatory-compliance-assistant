import streamlit as st
import logging
import pandas as pd
import matplotlib.pyplot as plt
from src import api_services

# Initialize logger
logger = logging.getLogger(__name__)

def get_user_session_role(username: str) -> str:
    """Simulates role capturing from the database configuration."""
    try:
        profile = api_services.get_user_profile(username)
        if profile:
            roles = profile.get("structural_roles", ["GUEST"])
            if isinstance(roles, list) and len(roles) > 0:
                return roles[0]
            elif isinstance(roles, str):
                return roles
    except Exception as e:
        logger.warning(f"Database profile lookup failed, using simulation fallback: {e}")

    simulation_map = {
        "compliance_officer_sim": "COMPLIANCE_OFFICER",
        "internal_auditor_sim": "INTERNAL_AUDITOR",
        "compliance_head_sim": "COMPLIANCE_HEAD"
    }
    return simulation_map.get(username, "GUEST")

def main():
    st.set_page_config(page_title="Compliance AI Assistant", layout="wide")
    st.title("🛡️ Compliance AI Assistant")

    st.sidebar.title("Authentication")
    user_options = [
        "compliance_officer_sim",
        "internal_auditor_sim",
        "compliance_head_sim"
    ]

    selected_user = st.sidebar.selectbox(
        "Simulate Authenticated User Session Profile",
        options=user_options
    )

    role = get_user_session_role(selected_user)
    st.sidebar.info(f"Authenticated as: {role}")

    if role == "COMPLIANCE_OFFICER":
        render_officer_workspace()
    elif role == "INTERNAL_AUDITOR":
        render_auditor_grid()
    elif role == "COMPLIANCE_HEAD":
        render_head_dashboard()
    else:
        st.warning("Unauthorized access. Please select a valid profile.")

def render_officer_workspace():
    """Renders the specialized workspace view for compliance officers."""
    st.header("📋 Compliance Officer Workspace")

    col1, col2 = st.columns([1, 2])

    with col1:
        render_risk_inbox()

    with col2:
        render_analysis_dashboard()

def render_risk_inbox():
    """Renders the 'Pending Risk Inbox' list layout."""
    st.subheader("Pending Risk Inbox")

    try:
        pending_inbox = api_services.get_pending_inbox()
        if not pending_inbox:
            st.info("No pending screenings.")
            return

        for item in pending_inbox:
            sess_id = item.get("session_id")
            metadata = item.get("metadata", {})
            amount = metadata.get("amount", "N/A")

            # Transaction ID card selection
            if st.button(f"🆔 {sess_id}\n\nAmt: ${amount}", key=f"btn_{sess_id}"):
                st.session_state.selected_session_id = sess_id
                st.rerun()

    except Exception as e:
        logger.error(f"Failed to load pending inbox: {e}")
        st.error("Error loading inbox.")

def render_analysis_dashboard():
    """Renders the chat-style analysis dashboard and validation interface."""
    selected_id = st.session_state.get("selected_session_id")
    if not selected_id:
        st.info("Select a transaction from the inbox to begin analysis.")
        return

    st.subheader(f"Analysis: {selected_id}")

    state = api_services.get_session_state(selected_id)
    if not state:
        st.warning("Could not retrieve active graph state.")
        return

    # Chat-style display for analysis conclusions
    st.markdown("### 🤖 Reasoning Model Analysis")
    notes = state.get("notes", "No analysis notes available.")
    risk = state.get("risk_rating", "PENDING")

    st.chat_message("assistant").write(f"**Current Risk Rating:** {risk}")
    st.chat_message("assistant").write(notes)

    # Validation Interface
    st.divider()
    val_notes = st.text_area("Compliance Validation Notes", placeholder="Enter your justification here...")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("✅ Approve and Clear", use_container_width=True):
            handle_validation(selected_id, True, val_notes)
    with btn_col2:
        if st.button("🚩 Flag and Defend", use_container_width=True):
            handle_validation(selected_id, False, val_notes)

def handle_validation(session_id: str, approved: bool, notes: str):
    """Handles the submission of compliance validation."""
    try:
        api_services.resume_workflow_checkpoint(session_id, approved, notes)
        st.success(f"Session {session_id} {'approved' if approved else 'flagged'} successfully.")
        # Clear selection after action
        del st.session_state.selected_session_id
        st.rerun()
    except Exception as e:
        logger.error(f"Validation submission failed: {e}")
        st.error("Failed to submit validation.")

def render_auditor_grid():
    """Renders the audit sheet data grid for internal auditors."""
    st.header("🔍 Internal Auditor Review")

    # Date-range search selector
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.date_input(
            "Select Audit Period",
            value=(pd.Timestamp.now() - pd.Timedelta(days=30), pd.Timestamp.now()),
            key="audit_date_range"
        )

    st.subheader("Historical Audit Ledger")

    try:
        ledger = api_services.get_historical_ledger()
        if not ledger:
            st.info("The audit log is currently empty.")
            return

        df = pd.DataFrame(ledger)
        if df.empty:
            st.info("The audit log is currently empty.")
            return

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Apply date filtering if range is selected
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)]

        # Add operational audit trace links
        df['Launch Operational Audit Trace'] = "http://localhost:3000"

        st.dataframe(
            df,
            column_config={
                "Launch Operational Audit Trace": st.column_config.LinkColumn(
                    "Operational Audit Trace",
                    help="Deep-link to Langfuse operational trace",
                    validate=r"^http://localhost:3000.*",
                    display_text="Launch Trace"
                )
            },
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        logger.error(f"Failed to load audit ledger: {e}")
        st.error("Error loading historical ledger.")

def render_head_dashboard():
    """Renders the analytical dashboard for the compliance head."""
    st.header("📊 Executive Compliance Dashboard")

    # Metric Overview Cards
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Mean Process Latency", "1.4s")
    with m_col2:
        st.metric("False Positive Optimization", "94.2%")
    with m_col3:
        st.metric("Active Monitoring Sessions", "187")

    st.divider()

    # Layout for charts
    c_col1, c_col2 = st.columns(2)

    with c_col1:
        st.subheader("Historical Anomaly Trend Volume")
        # Mock time-series data preparation
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        anomaly_volume = [15, 22, 18, 25, 30, 28, 35, 42, 38, 45, 50, 48, 55, 60, 58, 65, 72, 68, 75, 80, 78, 85, 92, 88, 95, 100, 98, 105, 112, 108]
        df_trend = pd.DataFrame({"Date": dates, "Anomaly Volume": anomaly_volume})
        st.area_chart(df_trend.set_index("Date"), use_container_width=True)

    with c_col2:
        st.subheader("Risk Distribution Overview")
        risk_data = {
            'Risk Level': ['High', 'Medium', 'Low'],
            'Count': [12, 45, 130]
        }
        df_risk = pd.DataFrame(risk_data)
        fig, ax = plt.subplots()
        ax.bar(df_risk['Risk Level'], df_risk['Count'], color=['#ff4b4b', '#ffa500', '#2ea043'])
        ax.set_ylabel('Number of Cases')
        st.pyplot(fig)
        plt.close(fig)

if __name__ == "__main__":
    main()
