import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from .config_loader import config

logger = logging.getLogger(__name__)

class IngestionError(Exception):
    """Base class for ingestion exceptions."""
    pass

class ManifestFileNotFoundError(IngestionError):
    """Raised when the manifest file is missing."""
    pass

class VectorStoreConnectionError(IngestionError):
    """Raised when connecting to Qdrant fails."""
    pass

class PayloadValidationError(IngestionError):
    """Raised when metadata validation fails."""
    pass

class RegulatoryIngestor:
    def __init__(self):
        if config is None or config.qdrant is None:
            raise IngestionError("Application configuration is missing or invalid.")

        try:
            self.client = QdrantClient(
                host=config.qdrant.host,
                port=config.qdrant.port
            )
            self.collection_name = config.qdrant.collection_name
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to initialize RegulatoryIngestor: {e}")
            raise VectorStoreConnectionError(f"Qdrant initialization failed: {e}")

    def initialize_collection(self, vector_size: int = 384):
        try:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(f"Collection '{self.collection_name}' initialized.")
        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            raise VectorStoreConnectionError(f"Could not initialize collection: {e}")

    def generate_embedding(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def load_manifest(self, manifest_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(manifest_path):
            raise ManifestFileNotFoundError(f"Manifest not found at {manifest_path}")
        
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                return data.get("documents", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse manifest JSON: {e}")
            raise PayloadValidationError(f"Invalid manifest format: {e}")

    def validate_metadata(self, metadata: Dict[str, Any]):
        required_fields = ["doc_id", "effective_start", "jurisdiction", "text"]
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                raise PayloadValidationError(f"Missing required metadata field: {field}")

    def upsert_regulatory_data(self, manifest_path: str):
        documents = self.load_manifest(manifest_path)
        points = []

        for doc in documents:
            try:
                self.validate_metadata(doc)
                vector = self.generate_embedding(doc["text"])

                payload = {
                    "text": doc["text"],
                    "doc_id": doc["doc_id"],
                    "version": doc.get("version", "1.0"),
                    "status": doc.get("status", "active"),
                    "effective_start": doc["effective_start"],
                    "effective_end": doc.get("effective_end"),
                    "jurisdiction": doc["jurisdiction"]
                }

                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload=payload
                    )
                )
            except PayloadValidationError as e:
                logger.warning(f"Skipping document due to validation error: {e}")
                continue

        if points:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Successfully upserted {len(points)} regulatory points.")
            except Exception as e:
                logger.error(f"Failed to upsert data to Qdrant: {e}")
                raise VectorStoreConnectionError(f"Upsert failed: {e}")

if __name__ == "__main__":
    try:
        ingestor = RegulatoryIngestor()
        # Use a relative path to the manifest file
        manifest_file = os.path.join("data", "manifest.json")
        ingestor.upsert_regulatory_data(manifest_file)
    except Exception as e:
        logger.error(f"Ingestion process failed: {e}")
