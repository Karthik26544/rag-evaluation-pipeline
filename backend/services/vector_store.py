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

USE_GEMINI_EMBEDDINGS = os.getenv("USE_GEMINI_EMBEDDINGS", "false").lower() == "true"

if USE_GEMINI_EMBEDDINGS:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    EMBEDDING_DIM = 768
else:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_DIM = 384


class VectorStore:

    def __init__(self):
        if USE_GEMINI_EMBEDDINGS:
            print("Using Gemini embeddings (cloud mode)")
            self.model = None
        else:
            print("Loading local embedding model...")
            self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            print("Local embedding model loaded")

        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        if qdrant_api_key:
            self.client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=qdrant_api_key
            )
            print("Connected to Qdrant Cloud")
        else:
            self.client = QdrantClient(
                url=os.getenv("QDRANT_URL", "http://localhost:6333")
            )
            print("Connected to local Qdrant")

        self.collection_name = os.getenv("COLLECTION_NAME", "documents")
        self._ensure_collection()

def _embed(self, texts):
    if USE_GEMINI_EMBEDDINGS:
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        return embeddings
        else:
            return self.model.encode(texts, show_progress_bar=False).tolist()

def _embed_query(self, text):
    if USE_GEMINI_EMBEDDINGS:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return result['embedding']
        else:
            return self.model.encode([text])[0].tolist()

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]

        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection: {self.collection_name}")
        else:
            print(f"Collection exists: {self.collection_name}")

    def add_chunks(self, chunks: List[Dict], document_id: str) -> List[str]:
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self._embed(texts)

        points = []
        chunk_ids = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)

            points.append(PointStruct(
                id=chunk_id,
                vector=embedding,
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

    def search(self, query: str, top_k: int = 5, strategy_filter: str = None) -> List[Dict]:
        query_embedding = self._embed_query(query)

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
            query=query_embedding,
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