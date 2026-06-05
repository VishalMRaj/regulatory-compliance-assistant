import logging
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

class QdrantIngestor:
    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "regulatory_compliance"

    def initialize_collection(self, vector_size: int = 384) -> None:
        """Creates or resets the compliance collection."""
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Collection '{self.collection_name}' initialized successfully.")

    def upsert_regulatory_chunk(
        self, 
        chunk_id: int, 
        vector: List[float], 
        text: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """Upserts a chunk with strict audit and version metadata payload."""
        payload = {
            "text": text,
            "doc_id": metadata.get("doc_id"),
            "version": metadata.get("version", "1.0"),
            "status": metadata.get("status", "active"),
            "effective_start": metadata.get("effective_start"),
            "effective_end": metadata.get("effective_end"),
            "jurisdiction": metadata.get("jurisdiction")
        }
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=chunk_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingestor = QdrantIngestor()
    ingestor.initialize_collection(vector_size=384)