import unittest
from unittest.mock import MagicMock, patch
import os
import json

from src.ingestion import RegulatoryIngestor, ManifestFileNotFoundError, PayloadValidationError

class TestRegulatoryIngestor(unittest.TestCase):
    @patch("src.ingestion.QdrantClient")
    @patch("src.ingestion.SentenceTransformer")
    def setUp(self, mock_transformer, mock_qdrant):
        self.mock_qdrant = mock_qdrant.return_value
        self.mock_transformer = mock_transformer.return_value
        self.ingestor = RegulatoryIngestor()

    def test_load_manifest_success(self):
        manifest_data = {
            "documents": [
                {"doc_id": "1", "text": "test", "effective_start": "2024", "jurisdiction": "US"}
            ]
        }
        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(manifest_data))):
            with patch("os.path.exists", return_value=True):
                docs = self.ingestor.load_manifest("data/manifest.json")
                self.assertEqual(len(docs), 1)
                self.assertEqual(docs[0]["doc_id"], "1")

    def test_load_manifest_not_found(self):
        with patch("os.path.exists", return_value=False):
            with self.assertRaises(ManifestFileNotFoundError):
                self.ingestor.load_manifest("missing.json")

    def test_validate_metadata_success(self):
        metadata = {"doc_id": "1", "text": "test", "effective_start": "2024", "jurisdiction": "US"}
        self.ingestor.validate_metadata(metadata) # Should not raise

    def test_validate_metadata_missing_field(self):
        metadata = {"doc_id": "1", "text": "test"}
        with self.assertRaises(PayloadValidationError):
            self.ingestor.validate_metadata(metadata)

    @patch("src.ingestion.uuid.uuid4", return_value="fixed-uuid")
    def test_upsert_regulatory_data(self, mock_uuid):
        manifest_data = {
            "documents": [
                {
                    "doc_id": "REG-1",
                    "text": "Regulatory text",
                    "effective_start": "2024-01-01",
                    "jurisdiction": "US",
                    "version": "1.1"
                }
            ]
        }

        self.mock_transformer.encode.return_value.tolist.return_value = [0.1, 0.2]

        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(manifest_data))):
            with patch("os.path.exists", return_value=True):
                self.ingestor.upsert_regulatory_data("data/manifest.json")

                self.mock_qdrant.upsert.assert_called_once()
                call_args = self.mock_qdrant.upsert.call_args
                points = call_args.kwargs["points"]
                self.assertEqual(len(points), 1)
                self.assertEqual(points[0].id, "fixed-uuid")
                self.assertEqual(points[0].payload["doc_id"], "REG-1")
                self.assertEqual(points[0].payload["jurisdiction"], "US")

if __name__ == "__main__":
    unittest.main()
