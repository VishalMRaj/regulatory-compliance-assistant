import logging
import psycopg2
from typing import List, Dict, Any, Optional
from .database import DatabaseManager
# Assuming workflow is defined and imported from the graph module
# from .workflow import workflow

logger = logging.getLogger(__name__)

# Placeholder for the workflow object, in a real scenario this would be imported
workflow = None

def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    query = "SELECT metadata, structural_roles FROM compliance_users WHERE username = %s"
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            if result:
                return {
                    "metadata": result[0],
                    "structural_roles": result[1]
                }
            return None
    finally:
        DatabaseManager.release_connection(conn)

def submit_transaction_screening(session_id: str, payload: Dict[str, Any]) -> Any:
    config = {"configurable": {"thread_id": session_id}}
    try:
        if workflow is None:
            logger.error("Workflow graph is not initialized.")
            return None
        return workflow.invoke(payload, config)
    except Exception as e:
        logger.error(f"Error submitting transaction screening: {e}")
        raise

def resume_workflow_checkpoint(session_id: str, officer_approval: bool, notes: str) -> Any:
    config = {"configurable": {"thread_id": session_id}}
    try:
        if workflow is None:
            logger.error("Workflow graph is not initialized.")
            return None

        # Load the existing state via thread ID
        state = workflow.get_state(config)
        if not state.values:
            logger.warning(f"No state found for thread_id: {session_id}")
            return None

        # Update graph state variables matching structural keys in agents.md
        state_updates = {
            "officer_approval": officer_approval,
            "notes": notes,
            "risk_rating": "LOW" if officer_approval else "HIGH",
            "AMBIGUOUS_DATA_INPUT": False
        }

        # Update the graph state
        workflow.update_state(config, state_updates)

        # Release the execution pause checkpoint by invoking with None input
        return workflow.invoke(None, config)

    except psycopg2.Error as e:
        logger.error(f"Postgres exception during workflow resume: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during workflow resume: {e}")
        raise

def get_pending_inbox() -> List[Dict[str, Any]]:
    query = "SELECT session_id, status, metadata FROM compliance_sessions WHERE status = 'SUSPENDED'"
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [
                {"session_id": row[0], "status": row[1], "metadata": row[2]}
                for row in rows
            ]
    finally:
        DatabaseManager.release_connection(conn)

def update_session_state(session_id: str, status: str, notes: str) -> bool:
    query = """
        UPDATE compliance_sessions
        SET status = %s, notes = %s
        WHERE session_id = %s
    """
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (status, notes, session_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating session state: {e}")
        conn.rollback()
        return False
    finally:
        DatabaseManager.release_connection(conn)

def get_historical_ledger() -> List[Dict[str, Any]]:
    query = "SELECT event_id, timestamp, action, details FROM compliance_audit_log ORDER BY timestamp DESC"
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [
                {
                    "event_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "action": row[2],
                    "details": row[3]
                }
                for row in rows
            ]
    finally:
        DatabaseManager.release_connection(conn)
