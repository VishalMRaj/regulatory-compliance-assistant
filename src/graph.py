import logging
import os
from typing import Dict, Any, Optional

import psycopg
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from src.database import get_db_manager
import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from src.config_loader import config


logger = logging.getLogger(__name__)

class WorkflowError(Exception):
    """Base exception for workflow operations."""
    pass

class WorkflowPersistenceError(WorkflowError):
    """Raised when state persistence fails."""
    pass

from typing import Dict, Any, Optional, TypedDict

class ComplianceGraphState(TypedDict, total=False):
    """Standard state for the compliance workflow."""
    transaction_payload: Dict[str, Any]
    risk_rating: str
    notes: str
    officer_approval: str
    ambiguous_data_input: bool
    context_retrieved: bool
    session_id: str

def retrieve_context(state: ComplianceGraphState) -> ComplianceGraphState:
    """Simulates fetching regulatory context from Qdrant."""
    logger.info("Node: retrieve_context executed.")
    return {"context_retrieved": True}

def analyze_compliance(state: ComplianceGraphState) -> ComplianceGraphState:
    """Uses LLM to evaluate the payload."""
    logger.info("Node: analyze_compliance executed.")
    payload = state.get("transaction_payload", {})
    
    if not config or not config.llm:
        logger.error("LLM configuration is missing.")
        return {"risk_rating": "HIGH", "notes": "System Error: Missing LLM config."}

    try:
        # Initialize the ChatOllama model
        llm = ChatOllama(
            base_url=config.llm.base_url,
            model=config.llm.reasoning_model,
            format="json", # Instruct ollama to return valid JSON
            temperature=0
        )
        
        system_prompt = config.llm.system_prompt
        human_prompt = f"Transaction Payload: {json.dumps(payload)}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = llm.invoke(messages)
        
        # Parse the JSON response
        try:
            result = json.loads(response.content)
            risk_rating = result.get("risk_rating", "HIGH")
            notes = result.get("notes", "No notes provided by LLM.")
        except json.JSONDecodeError:
            logger.error(f"LLM did not return valid JSON: {response.content}")
            risk_rating = "HIGH"
            notes = f"LLM parsing error. Raw output: {response.content}"
            
        return {"risk_rating": risk_rating, "notes": notes}

    except Exception as e:
        logger.error(f"Error invoking LLM: {e}")
        return {"risk_rating": "HIGH", "notes": f"LLM Invocation Error: {e}"}

def human_review(state: ComplianceGraphState) -> ComplianceGraphState:
    """Breakpoint node for human intervention."""
    logger.info("Node: human_review executed (Human provided input).")
    # State update should come from the human via resume_workflow(inputs={...})
    return {}

def log_audit(state: ComplianceGraphState) -> ComplianceGraphState:
    """Simulates syncing final decision to Langfuse/Audit Log."""
    logger.info("Node: log_audit executed.")
    return {}

class ComplianceWorkflow:
    def __init__(self):
        self.db_manager = get_db_manager()
        self.workflow = self._initialize_workflow()
        self._compiled_graph = None

    def _initialize_workflow(self) -> StateGraph:
        builder = StateGraph(ComplianceGraphState)
        
        builder.add_node("retrieve_context", retrieve_context)
        builder.add_node("analyze_compliance", analyze_compliance)
        builder.add_node("human_review", human_review)
        builder.add_node("log_audit", log_audit)
        
        builder.set_entry_point("retrieve_context")
        builder.add_edge("retrieve_context", "analyze_compliance")
        builder.add_edge("analyze_compliance", "human_review")
        builder.add_edge("human_review", "log_audit")
        builder.set_finish_point("log_audit")
        
        return builder

    @property
    def graph(self):
        if self._compiled_graph is None:
            self._compiled_graph = self._compile()
        return self._compiled_graph

    def _compile(self):
        try:
            checkpointer = PostgresSaver(self.db_manager.pool)
            # Ensure tables exist for checkpoints once during compilation
            checkpointer.setup()
            return self.workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])
        except Exception as e:
            logger.error(f"Failed to compile graph with persistence: {e}")
            raise WorkflowPersistenceError(f"Compilation failed: {e}")


    def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Reads the current state snapshot for a given thread_id."""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state_snapshot = self.graph.get_state(config)
            return state_snapshot.values if state_snapshot else None
        except Exception as e:
            logger.error(f"Error reading state for thread {thread_id}: {e}")
            raise WorkflowPersistenceError(f"Read failed: {e}")

    def resume_workflow(self, thread_id: str, inputs: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        """Resumes or starts a workflow execution for a given thread_id."""
        full_config = {"configurable": {"thread_id": thread_id}}
        if config:
            full_config.update(config)

        try:
            return self.graph.invoke(inputs, config=full_config)
        except Exception as e:
            logger.error(f"Error resuming workflow for thread {thread_id}: {e}")
            raise WorkflowError(f"Execution failed: {e}")

# Global singleton for Langfuse CallbackHandler
_langfuse_handler = None

def get_langfuse_handler():
    global _langfuse_handler
    if _langfuse_handler is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"))

        if public_key and secret_key:
            _langfuse_handler = CallbackHandler(
                public_key=public_key,
                secret_key=secret_key,
                host=host
            )
            logger.info("Langfuse CallbackHandler initialized.")
        else:
            logger.warning("Langfuse credentials missing; observability disabled.")
    return _langfuse_handler

# Global instance for the workflow
_workflow_instance = None

def get_compliance_workflow() -> ComplianceWorkflow:
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = ComplianceWorkflow()
    return _workflow_instance
