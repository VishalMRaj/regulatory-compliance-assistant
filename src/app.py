import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

    tab1, tab2 = st.tabs(["📥 Risk Inbox & Review", "💬 Regulatory Q&A"])

    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            render_risk_inbox()
        with col2:
            render_analysis_dashboard()

    with tab2:
        render_qa_chat()

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
        del st.session_state.selected_session_id
        st.rerun()
    except Exception as e:
        logger.error(f"Validation submission failed: {e}")
        st.error("Failed to submit validation.")

def render_qa_chat():
    """FAST_RAG path: natural-language regulatory Q&A with cited answers."""
    st.subheader("💬 Regulatory Q&A")
    st.caption("Ask questions about Basel III, MiFID II, or RBI Master Directions. Answers are grounded in the regulatory knowledge base.")

    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    for entry in st.session_state.qa_history:
        st.chat_message("user").write(entry["question"])
        with st.chat_message("assistant"):
            st.write(entry["answer"])
            if entry.get("citations"):
                with st.expander("📎 Citations"):
                    for c in entry["citations"]:
                        st.markdown(f"- **{c.get('doc_id', 'N/A')}** v{c.get('version', '?')} `{c.get('jurisdiction', '?')}` — *{c.get('excerpt', '')}*")

    question = st.chat_input("Ask a regulatory question...")
    if question:
        with st.spinner("Searching knowledge base and reasoning..."):
            try:
                result = api_services.query_regulatory_knowledge(question)
                st.session_state.qa_history.append({
                    "question": question,
                    "answer": result.get("answer", "No answer returned."),
                    "citations": result.get("citations", [])
                })
                st.rerun()
            except Exception as e:
                logger.error(f"Q&A failed: {e}")
                st.error("Q&A service unavailable.")

def render_auditor_grid():
    """Renders the audit sheet data grid and impact analysis for internal auditors."""
    st.header("🔍 Internal Auditor Review")

    tab1, tab2 = st.tabs(["📊 Historical Ledger", "⚡ Regulatory Change Impact"])

    with tab1:
        col1, _ = st.columns(2)
        with col1:
            st.date_input(
                "Select Audit Period",
                value=(pd.Timestamp.now() - pd.Timedelta(days=30), pd.Timestamp.now()),
                key="audit_date_range"
            )

        st.subheader("Historical Audit Ledger")
        try:
            ledger = api_services.get_historical_ledger()
            if not ledger:
                st.info("The audit log is currently empty.")
            else:
                df = pd.DataFrame(ledger)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
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

    with tab2:
        st.subheader("⚡ Regulatory Change Impact Analysis")
        st.caption("Paste a new regulatory circular below. The system will identify which existing transaction types and policies are affected.")

        new_reg_text = st.text_area(
            "New Regulation / Circular Text",
            placeholder="Paste the new RBI circular, MiFID II amendment, or Basel update here...",
            height=150
        )
        jurisdiction = st.selectbox("Jurisdiction of New Regulation", ["IN", "EU", "US"])

        if st.button("🔍 Analyze Impact", use_container_width=True):
            if not new_reg_text.strip():
                st.warning("Please paste regulation text before analyzing.")
            else:
                with st.spinner("Analyzing impact on existing transactions..."):
                    try:
                        result = api_services.analyze_change_impact(new_reg_text, jurisdiction)
                        st.success("Impact analysis complete.")
                        st.markdown(f"**Urgency:** `{result.get('urgency', 'N/A')}`")
                        st.markdown(f"**Summary:** {result.get('summary', 'N/A')}")
                        affected = result.get('affected_transaction_types', [])
                        if affected:
                            st.markdown("**Affected Transaction Types:**")
                            for t in affected:
                                st.markdown(f"  - {t}")
                        changes = result.get('policy_changes_required', [])
                        if changes:
                            st.markdown("**Policy Changes Required:**")
                            for c in changes:
                                st.markdown(f"  - {c}")
                    except Exception as e:
                        logger.error(f"Impact analysis error: {e}")
                        st.error("Impact analysis failed.")

def render_head_dashboard():
    """Renders the analytical dashboard for the compliance head."""
    st.header("📊 Executive Compliance Dashboard")

    tab1, tab2 = st.tabs(["📈 KPI Overview", "📄 Generate Audit Report"])

    with tab1:
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Mean Process Latency", "1.4s")
        with m_col2:
            st.metric("False Positive Optimization", "94.2%")
        with m_col3:
            st.metric("Active Monitoring Sessions", "187")

        st.divider()

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.subheader("Historical Anomaly Trend Volume")
            dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
            anomaly_volume = [15, 22, 18, 25, 30, 28, 35, 42, 38, 45, 50, 48, 55, 60, 58, 65, 72, 68, 75, 80, 78, 85, 92, 88, 95, 100, 98, 105, 112, 108]
            df_trend = pd.DataFrame({"Date": dates, "Anomaly Volume": anomaly_volume})
            st.area_chart(df_trend.set_index("Date"), use_container_width=True)

        with c_col2:
            st.subheader("Risk Distribution Overview")
            risk_data = {'Risk Level': ['High', 'Medium', 'Low'], 'Count': [12, 45, 130]}
            df_risk = pd.DataFrame(risk_data)
            fig, ax = plt.subplots()
            ax.bar(df_risk['Risk Level'], df_risk['Count'], color=['#ff4b4b', '#ffa500', '#2ea043'])
            ax.set_ylabel('Number of Cases')
            st.pyplot(fig)
            plt.close(fig)

    with tab2:
        st.subheader("📄 Compliance Report Generator")
        st.caption("Generate a structured compliance report for an audit period, suitable for submission to an internal audit committee.")

        r_col1, r_col2 = st.columns(2)
        with r_col1:
            report_start = st.date_input("Report Start Date", value=pd.Timestamp.now() - pd.Timedelta(days=30))
        with r_col2:
            report_end = st.date_input("Report End Date", value=pd.Timestamp.now())

        if st.button("📄 Generate Report", use_container_width=True):
            with st.spinner("Generating compliance report via LLM..."):
                try:
                    report_md = api_services.generate_compliance_report(
                        str(report_start), str(report_end)
                    )
                    st.markdown(report_md)
                    st.download_button(
                        label="⬇️ Download Report (.md)",
                        data=report_md,
                        file_name=f"compliance_report_{report_start}_to_{report_end}.md",
                        mime="text/markdown"
                    )
                except Exception as e:
                    logger.error(f"Report generation error: {e}")
                    st.error("Report generation failed.")

if __name__ == "__main__":
    main()
