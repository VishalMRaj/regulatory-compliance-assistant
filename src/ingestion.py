import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantIngestor:
    def __init__(self, host="localhost", port=6333):
        # Initialize connection to your local Docker container
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "regulatory_compliance"

    def initialize_collection(self, vector_size=384):
        """Creates or resets the compliance collection."""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f"Collection '{self.collection_name}' initialized successfully.")

    def upsert_regulatory_chunk(self, chunk_id, vector, text, metadata):
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
    # Quick sanity check for your local Day 1 setup
    ingestor = QdrantIngestor()
    ingestor.initialize_collection(vector_size=384) # 384 matches standard local bge-small models