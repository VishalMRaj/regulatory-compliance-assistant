import streamlit as st
import pandas as pd
import numpy as np
from src.api_services import get_user_profile, get_pending_inbox, get_historical_ledger

# Page configuration
st.set_page_config(
    page_title="Compliance Multi-Agent System",
    page_icon="🛡️",
    layout="wide"
)

def compliance_officer_view():
    st.header("👮 Compliance Officer Workspace")
    st.subheader("Pending Transaction Inbox")

    # In a real app, this would call get_pending_inbox()
    # For simulation, we'll show a sample if the DB isn't fully populated
    try:
        pending_sessions = get_pending_inbox()
        if pending_sessions:
            st.table(pd.DataFrame(pending_sessions))
        else:
            st.info("No pending 'SUSPENDED' sessions found.")
    except Exception as e:
        st.error(f"Error fetching inbox: {e}")
        # Mock data for UI demonstration
        mock_data = [
            {"session_id": "SESS-101", "status": "SUSPENDED", "risk_score": 0.85},
            {"session_id": "SESS-104", "status": "SUSPENDED", "risk_score": 0.92}
        ]
        st.table(pd.DataFrame(mock_data))

def internal_auditor_view():
    st.header("🕵️ Internal Audit Ledger")
    st.subheader("Historical Compliance Log")

    try:
        ledger = get_historical_ledger()
        if ledger:
            st.dataframe(pd.DataFrame(ledger), use_container_width=True)
        else:
            st.info("No historical ledger entries found.")
    except Exception as e:
        st.error(f"Error fetching ledger: {e}")
        # Mock data for UI demonstration
        mock_ledger = [
            {"event_id": "EVT-99", "timestamp": "2023-10-27 10:00:00", "action": "LOGIN", "user": "officer_jane"},
            {"event_id": "EVT-100", "timestamp": "2023-10-27 10:05:00", "action": "SCREENING_COMPLETE", "session": "SESS-101"}
        ]
        st.dataframe(pd.DataFrame(mock_ledger), use_container_width=True)

def compliance_head_view():
    st.header("📊 Compliance Executive Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Active Sessions", "42", "+5")
    col2.metric("Avg Risk Score", "0.45", "-0.02")
    col3.metric("Pending Reviews", "12", "-3")

    st.subheader("Risk Distribution Trend")
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['AML', 'KYC', 'Sanctions']
    )
    st.line_chart(chart_data)

def main():
    st.sidebar.title("🔐 Authentication")

    mock_users = {
        "officer_jane": "COMPLIANCE_OFFICER",
        "auditor_bob": "INTERNAL_AUDITOR",
        "head_alice": "COMPLIANCE_HEAD"
    }

    selected_username = st.sidebar.selectbox(
        "Simulate Authenticated User Session Profile",
        options=["Select User..."] + list(mock_users.keys())
    )

    if selected_username != "Select User...":
        with st.spinner("Loading profile..."):
            user_profile = None
            try:
                # Attempt to call backend
                user_profile = get_user_profile(selected_username)
            except Exception as e:
                st.sidebar.warning(f"Database connection unavailable (Simulation Mode). Error: {e}")

            # Fallback to mock mapping if DB call fails or returns nothing
            role = user_profile["structural_roles"][0] if user_profile else mock_users[selected_username]

            st.sidebar.success(f"Authenticated as: {selected_username}")
            st.sidebar.info(f"Role: {role}")

            # Routing logic based on role
            if role == "COMPLIANCE_OFFICER":
                compliance_officer_view()
            elif role == "INTERNAL_AUDITOR":
                internal_auditor_view()
            elif role == "COMPLIANCE_HEAD":
                compliance_head_view()
            else:
                st.warning("Unauthorized or Unknown Role")
    else:
        st.title("🛡️ Regulatory Compliance Assistant")
        st.markdown("""
        Welcome to the multi-agent compliance monitoring system.
        Please select a user profile from the sidebar to begin.
        """)

if __name__ == "__main__":
    main()
