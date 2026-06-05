import logging
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from src.database import get_db_manager

logger = logging.getLogger(__name__)

class WorkflowError(Exception):
    """Base exception for workflow operations."""
    pass

class WorkflowPersistenceError(WorkflowError):
    """Raised when state persistence fails."""
    pass

class ComplianceGraphState(Dict[str, Any]):
    """Standard state for the compliance workflow."""
    pass

class ComplianceWorkflow:
    def __init__(self):
        self.db_manager = get_db_manager()
        self.workflow = self._initialize_workflow()
        self._compiled_graph = None

    def _initialize_workflow(self) -> StateGraph:
        builder = StateGraph(ComplianceGraphState)
        builder.add_node("start", lambda state: state)
        builder.set_entry_point("start")
        builder.set_finish_point("start")
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
            return self.workflow.compile(checkpointer=checkpointer)
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

    def resume_workflow(self, thread_id: str, inputs: Optional[Dict[str, Any]] = None):
        """Resumes or starts a workflow execution for a given thread_id."""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            return self.graph.invoke(inputs, config=config)
        except Exception as e:
            logger.error(f"Error resuming workflow for thread {thread_id}: {e}")
            raise WorkflowError(f"Execution failed: {e}")

# Global instance for the workflow
_workflow_instance = None

def get_compliance_workflow() -> ComplianceWorkflow:
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = ComplianceWorkflow()
    return _workflow_instance
