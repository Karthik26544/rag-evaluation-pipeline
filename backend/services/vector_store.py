from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
import uuid
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class VectorStore:

    def __init__(self):
        print("Loading embedding model... first time takes 1-2 minutes")
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        print("Embedding model loaded successfully")

        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )
        self.collection_name = os.getenv("COLLECTION_NAME", "documents")
        self._ensure_collection()

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]

        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )
            print(f"Created Qdrant collection: {self.collection_name}")
        else:
            print(f"Qdrant collection already exists: {self.collection_name}")

    def add_chunks(self, chunks: List[Dict], document_id: str) -> List[str]:
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)

        points = []
        chunk_ids = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)

            points.append(PointStruct(
                id=chunk_id,
                vector=embedding.tolist(),
                payload={
                    "document_id": document_id,
                    "content": chunk["content"],
                    "chunk_index": chunk["index"],
                    "chunking_strategy": chunk["strategy"],
                    "chunk_size": chunk["size"]
                }
            ))

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return chunk_ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        strategy_filter: str = None
    ) -> List[Dict]:
        query_embedding = self.model.encode([query])[0]

        search_filter = None
        if strategy_filter:
            search_filter = Filter(
                must=[FieldCondition(
                    key="chunking_strategy",
                    match=MatchValue(value=strategy_filter)
                )]
            )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=top_k,
            query_filter=search_filter
        )

        results = response.points

        return [
            {
                "content": r.payload["content"],
                "score": r.score,
                "document_id": r.payload["document_id"],
                "chunk_index": r.payload["chunk_index"],
                "strategy": r.payload["chunking_strategy"]
            }
            for r in results
        ]