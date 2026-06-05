import unittest
from unittest.mock import MagicMock, patch
import datetime
import psycopg2

# Mock the database before importing api_services
with patch('psycopg2.pool.ThreadedConnectionPool'):
    from src import api_services
    from src.database import DatabaseManager

class TestApiServices(unittest.TestCase):

    def setUp(self):
        # Reset the workflow placeholder for each test
        api_services.workflow = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = self.mock_conn.cursor.return_value.__enter__.return_value

        # Patch DatabaseManager to return our mock connection
        patcher = patch('src.database.DatabaseManager.get_connection', return_value=self.mock_conn)
        self.addCleanup(patcher.stop)
        patcher.start()

        patcher_release = patch('src.database.DatabaseManager.release_connection')
        self.addCleanup(patcher_release.stop)
        patcher_release.start()

    def test_get_user_profile(self):
        self.mock_cursor.fetchone.return_value = ({"key": "val"}, ["role1"])
        result = api_services.get_user_profile("testuser")

        self.assertEqual(result["metadata"], {"key": "val"})
        self.assertEqual(result["structural_roles"], ["role1"])
        self.mock_cursor.execute.assert_called_with(
            "SELECT metadata, structural_roles FROM compliance_users WHERE username = %s",
            ("testuser",)
        )

    def test_get_pending_inbox(self):
        self.mock_cursor.fetchall.return_value = [("sess1", "SUSPENDED", {"meta": "data"})]
        result = api_services.get_pending_inbox()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["session_id"], "sess1")
        self.mock_cursor.execute.assert_called_with(
            "SELECT session_id, status, metadata FROM compliance_sessions WHERE status = 'SUSPENDED'"
        )

    def test_update_session_state_success(self):
        self.mock_cursor.rowcount = 1
        result = api_services.update_session_state("sess1", "ACTIVE", "All good")

        self.assertTrue(result)
        self.mock_conn.commit.assert_called_once()

    def test_update_session_state_fail(self):
        self.mock_cursor.execute.side_effect = Exception("DB Error")
        result = api_services.update_session_state("sess1", "ACTIVE", "All good")

        self.assertFalse(result)
        self.mock_conn.rollback.assert_called_once()

    def test_get_historical_ledger(self):
        now = datetime.datetime.now()
        self.mock_cursor.fetchall.return_value = [("evt1", now, "ACTION", {"detail": "info"})]
        result = api_services.get_historical_ledger()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["timestamp"], now.isoformat())

    def test_submit_transaction_screening(self):
        payload = {"data": "test"}
        api_services.submit_transaction_screening("sess1", payload)

        api_services.workflow.invoke.assert_called_with(
            payload, {"configurable": {"thread_id": "sess1"}}
        )

    def test_resume_workflow_checkpoint(self):
        mock_state = MagicMock()
        mock_state.values = {"existing": "state"}
        api_services.workflow.get_state.return_value = mock_state

        api_services.resume_workflow_checkpoint("sess1", True, "Approved by officer")

        api_services.workflow.update_state.assert_called_with(
            {"configurable": {"thread_id": "sess1"}},
            {
                "officer_approval": True,
                "notes": "Approved by officer",
                "risk_rating": "LOW",
                "AMBIGUOUS_DATA_INPUT": False
            }
        )
        api_services.workflow.invoke.assert_called_with(
            None, {"configurable": {"thread_id": "sess1"}}
        )

    def test_resume_workflow_checkpoint_psycopg2_error(self):
        api_services.workflow.get_state.side_effect = psycopg2.Error("Postgres error")

        with self.assertRaises(psycopg2.Error):
            api_services.resume_workflow_checkpoint("sess1", True, "Approved")

if __name__ == '__main__':
    unittest.main()
