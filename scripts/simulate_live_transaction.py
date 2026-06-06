import sys
import os
import logging
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api_services import submit_transaction_screening
from src.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRANSACTIONS = [
    {
        "session_id": "TXN-LIVE-001",
        "amount": 5500000.00,
        "currency": "USD",
        "target_jurisdiction": "Sanctioned-Zone-X",
        "sender": "Global Corp LLC",
        "receiver": "Shell Holdings Inc.",
        "notes": "Urgent transfer for consulting fees.",
        "initiated_by": "USR-001",
    },
    {
        "session_id": "TXN-LIVE-002",
        "amount": 12000000.00,
        "currency": "USD",
        "target_jurisdiction": "High-Risk-A",
        "sender": "FinCo International",
        "receiver": "Anonymous Trust Ltd.",
        "notes": "Real estate acquisition — offshore entity.",
        "initiated_by": "USR-001",
    },
    {
        "session_id": "TXN-LIVE-003",
        "amount": 850000.00,
        "currency": "EUR",
        "target_jurisdiction": "EU",
        "sender": "Apex Asset Management",
        "receiver": "Deutsche Investments GmbH",
        "notes": "Cross-border bond settlement under MiFID II.",
        "initiated_by": "USR-001",
    },
    {
        "session_id": "TXN-LIVE-004",
        "amount": 3200000.00,
        "currency": "INR",
        "target_jurisdiction": "IN",
        "sender": "Mumbai Trading House",
        "receiver": "Foreign Brokerage Pvt Ltd.",
        "notes": "Equity remittance — RBI LRS scheme.",
        "initiated_by": "USR-001",
    },
    {
        "session_id": "TXN-LIVE-005",
        "amount": 9750000.00,
        "currency": "USD",
        "target_jurisdiction": "High-Risk-B",
        "sender": "Pacific Capital Corp",
        "receiver": "Unknown Beneficiary",
        "notes": "Trade finance — no underlying contract attached.",
        "initiated_by": "USR-001",
    },
]


def inject_transaction(txn: dict):
    session_id = txn["session_id"]
    payload = {k: v for k, v in txn.items() if k not in ("session_id", "initiated_by")}

    query = """
        INSERT INTO compliance_sessions
        (session_id, initiated_by, transaction_amount, currency, target_jurisdiction, status, metadata)
        VALUES (%s, %s, %s, %s, %s, 'SUSPENDED', %s)
        ON CONFLICT (session_id) DO NOTHING
    """
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (
                session_id,
                txn["initiated_by"],
                txn["amount"],
                txn["currency"],
                txn["target_jurisdiction"],
                json.dumps(payload),
            ))
            if not conn.autocommit:
                conn.commit()
        logger.info(f"DB record created: {session_id}")
    except Exception as e:
        logger.error(f"DB insert failed for {session_id}: {e}")
        return
    finally:
        DatabaseManager.release_connection(conn)

    logger.info(f"Running LangGraph for {session_id} — sending to DeepSeek via Ollama...")
    graph_payload = {"transaction_payload": payload, "session_id": session_id}
    try:
        submit_transaction_screening(session_id, graph_payload)
        logger.info(f"Checkpoint saved. {session_id} is now visible in Streamlit UI.")
    except Exception as e:
        logger.error(f"LangGraph error for {session_id}: {e}")


def run():
    logger.info(f"Seeding {len(TRANSACTIONS)} live transactions...")
    for txn in TRANSACTIONS:
        inject_transaction(txn)
    logger.info("All transactions processed. Reload the Streamlit UI to see them.")


if __name__ == "__main__":
    run()
