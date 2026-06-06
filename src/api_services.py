import logging
from typing import List, Dict, Any, Optional
from .database import DatabaseManager
from .graph import get_compliance_workflow, get_langfuse_handler

logger = logging.getLogger(__name__)

# Initialize the workflow graph from the graph module
workflow = None

def _initialize_workflow():
    global workflow
    if workflow is None:
        try:
            _workflow_wrapper = get_compliance_workflow()
            workflow = _workflow_wrapper.graph
        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            workflow = None

def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    # Mock data for simulation
    mock_users = {
        "compliance_officer_sim": {"metadata": {}, "structural_roles": ["COMPLIANCE_OFFICER"]},
        "internal_auditor_sim": {"metadata": {}, "structural_roles": ["INTERNAL_AUDITOR"]},
        "compliance_head_sim": {"metadata": {}, "structural_roles": ["COMPLIANCE_HEAD"]},
    }

    try:
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
        finally:
            DatabaseManager.release_connection(conn)
    except Exception as e:
        logger.warning(f"Database error in get_user_profile, using mock: {e}")

    return mock_users.get(username)

def submit_transaction_screening(session_id: str, payload: Dict[str, Any]) -> Any:
    handler = get_langfuse_handler()
    config = {"configurable": {"thread_id": session_id}}
    if handler:
        config["callbacks"] = [handler]

    _initialize_workflow()
    try:
        if workflow is None:
            logger.error("Workflow graph is not initialized.")
            return None
        return workflow.invoke(payload, config)
    except Exception as e:
        logger.error(f"Error submitting transaction screening: {e}")
        raise

def resume_workflow_checkpoint(session_id: str, officer_approval: bool, notes: str) -> Any:
    handler = get_langfuse_handler()
    config = {"configurable": {"thread_id": session_id}}
    if handler:
        config["callbacks"] = [handler]

    _initialize_workflow()
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

    except Exception as e:
        logger.error(f"Error during workflow resume: {e}")
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

def get_session_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the current state snapshot for a given session."""
    try:
        workflow_wrapper = get_compliance_workflow()
        return workflow_wrapper.get_state(session_id)
    except Exception as e:
        logger.error(f"Error fetching state for session {session_id}: {e}")
        return None

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


def query_regulatory_knowledge(question: str) -> Dict[str, Any]:
    """FAST_RAG path: embeds the question, retrieves matching regulations from Qdrant, and uses
    the routing LLM (llama3) to produce a cited answer."""
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer
    from src.config_loader import config
    import json

    if not config:
        raise RuntimeError("Configuration not loaded.")

    try:
        encoder = SentenceTransformer("all-MiniLM-L6-v2")
        query_vector = encoder.encode(question).tolist()

        qdrant = QdrantClient(host=config.qdrant.host, port=config.qdrant.port)
        results = qdrant.query_points(
            collection_name=config.qdrant.collection_name,
            query=query_vector,
            limit=4
        )
        hits = results.points

        context_chunks = [
            f"[{h.payload['doc_id']} v{h.payload['version']} | {h.payload['jurisdiction']}]: {h.payload['text']}"
            for h in hits
        ]
        context_str = "\n\n".join(context_chunks) if context_chunks else "No matching regulations found in the knowledge base."

    except Exception as e:
        logger.warning(f"Qdrant retrieval failed, using empty context: {e}")
        context_str = "Knowledge base unavailable. Answering from general knowledge."

    try:
        llm = ChatOllama(
            base_url=config.llm.base_url,
            model=config.llm.routing_model,
            format="json",
            temperature=0
        )

        human_prompt = f"Regulatory Context:\n{context_str}\n\nUser Question: {question}"
        messages = [
            SystemMessage(content=config.llm.qa_prompt),
            HumanMessage(content=human_prompt)
        ]

        response = llm.invoke(messages)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"answer": response.content, "citations": []}

    except Exception as e:
        logger.error(f"LLM Q&A invocation failed: {e}")
        return {"answer": f"Error during Q&A: {e}", "citations": []}


def analyze_change_impact(new_regulation_text: str, jurisdiction: str) -> Dict[str, Any]:
    """Scenario 3: When a new regulation is ingested, identify which existing transaction
    types and policies are affected."""
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage
    from src.config_loader import config
    import json

    if not config:
        raise RuntimeError("Configuration not loaded.")

    query = """
        SELECT session_id, transaction_amount, currency, target_jurisdiction, metadata
        FROM compliance_sessions
        ORDER BY created_at DESC
        LIMIT 20
    """
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            recent_txns = [
                {"session_id": r[0], "amount": float(r[1]), "currency": r[2],
                 "jurisdiction": r[3], "metadata": r[4]}
                for r in rows
            ]
    finally:
        DatabaseManager.release_connection(conn)

    try:
        llm = ChatOllama(
            base_url=config.llm.base_url,
            model=config.llm.reasoning_model,
            format="json",
            temperature=0
        )

        human_prompt = (
            f"New Regulation Text:\n{new_regulation_text}\n\n"
            f"Jurisdiction: {jurisdiction}\n\n"
            f"Recent Transaction Patterns:\n{json.dumps(recent_txns, indent=2)}"
        )
        messages = [
            SystemMessage(content=config.llm.change_impact_prompt),
            HumanMessage(content=human_prompt)
        ]

        response = llm.invoke(messages)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"summary": response.content}

    except Exception as e:
        logger.error(f"Change impact analysis failed: {e}")
        return {"summary": f"Error: {e}"}


def generate_compliance_report(start_date: str, end_date: str) -> str:
    """Scenario 4: Generate a structured markdown compliance report for a time period,
    suitable for submission to an internal audit committee."""
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage
    from src.config_loader import config
    import json

    if not config:
        raise RuntimeError("Configuration not loaded.")

    query = """
        SELECT s.session_id, s.transaction_amount, s.currency,
               s.target_jurisdiction, s.status, s.metadata, s.created_at
        FROM compliance_sessions s
        WHERE s.created_at::date BETWEEN %s AND %s
        ORDER BY s.created_at DESC
    """
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            session_data = [
                {
                    "session_id": r[0], "amount": float(r[1]), "currency": r[2],
                    "jurisdiction": r[3], "status": r[4],
                    "metadata": r[5], "created_at": r[6].isoformat() if r[6] else None
                }
                for r in rows
            ]
    finally:
        DatabaseManager.release_connection(conn)

    if not session_data:
        return f"# Compliance Report\n\nNo transactions found between {start_date} and {end_date}."

    try:
        llm = ChatOllama(
            base_url=config.llm.base_url,
            model=config.llm.reasoning_model,
            temperature=0
        )

        human_prompt = (
            f"Report Period: {start_date} to {end_date}\n\n"
            f"Transaction Data ({len(session_data)} records):\n"
            f"{json.dumps(session_data, indent=2)}"
        )
        messages = [
            SystemMessage(content=config.llm.report_prompt),
            HumanMessage(content=human_prompt)
        ]

        response = llm.invoke(messages)
        return response.content

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return f"# Report Generation Error\n\n{e}"

