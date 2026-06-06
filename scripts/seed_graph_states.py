import sys
import os
import logging

# Add the project root to sys.path so we can import src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api_services import get_pending_inbox, submit_transaction_screening

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_seeder():
    logger.info("Fetching pending sessions from the database...")
    pending_sessions = get_pending_inbox()
    
    if not pending_sessions:
        logger.info("No pending sessions found.")
        return
        
    for session in pending_sessions:
        session_id = session["session_id"]
        metadata = session["metadata"]
        
        logger.info(f"Processing session: {session_id}")
        
        payload = {
            "transaction_payload": metadata,
            "session_id": session_id
        }
        
        try:
            # Submitting it to the graph will advance it until the 'human_review' interrupt
            submit_transaction_screening(session_id, payload)
            logger.info(f"Successfully created graph state for {session_id}")
        except Exception as e:
            logger.error(f"Failed to process session {session_id}: {e}")

if __name__ == "__main__":
    run_seeder()
