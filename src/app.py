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
            return profile.get("structural_roles", ["GUEST"])[0]
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
    st.subheader("Pending Transaction Screenings")

    try:
        pending_inbox = api_services.get_pending_inbox()
        if pending_inbox:
            st.table(pd.DataFrame(pending_inbox))
        else:
            st.info("No pending screenings at this time.")
    except Exception as e:
        logger.error(f"Failed to load pending inbox: {e}")
        st.error("Error loading task inbox.")

def render_auditor_grid():
    """Renders the audit sheet data grid for internal auditors."""
    st.header("🔍 Internal Auditor Review")
    st.subheader("Historical Audit Ledger")

    try:
        ledger = api_services.get_historical_ledger()
        if ledger:
            st.dataframe(pd.DataFrame(ledger), use_container_width=True)
        else:
            st.info("The audit log is currently empty.")
    except Exception as e:
        logger.error(f"Failed to load audit ledger: {e}")
        st.error("Error loading historical ledger.")

def render_head_dashboard():
    """Renders the visualization dashboard for the compliance head."""
    st.header("📊 Executive Compliance Dashboard")

    # Mock data preparation
    risk_data = {
        'Risk Level': ['High', 'Medium', 'Low'],
        'Count': [12, 45, 130]
    }
    df_risk = pd.DataFrame(risk_data)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Level Distribution")
        fig, ax = plt.subplots()
        ax.bar(df_risk['Risk Level'], df_risk['Count'], color=['#ff4b4b', '#ffa500', '#2ea043'])
        ax.set_ylabel('Number of Cases')
        st.pyplot(fig)

    with col2:
        st.subheader("Summary Metrics")
        st.metric("Active Sessions", 187)
        st.metric("Avg Resolution Time", "1.4h")

if __name__ == "__main__":
    main()
