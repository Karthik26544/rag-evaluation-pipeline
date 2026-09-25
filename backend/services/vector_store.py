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
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

USE_GEMINI_EMBEDDINGS = os.getenv("USE_GEMINI_EMBEDDINGS", "false").lower() == "true"

if USE_GEMINI_EMBEDDINGS:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    EMBEDDING_DIM = 3072
    GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
else:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_DIM = 384


class VectorStore:

    def __init__(self):
        if USE_GEMINI_EMBEDDINGS:
            print(f"Using Gemini embeddings: {GEMINI_EMBED_MODEL} (dim {EMBEDDING_DIM})")
            self.model = None
        else:
            print("Loading local embedding model...")
            self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            print("Local embedding model loaded")

        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

        if qdrant_api_key:
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                timeout=30.0
            )
            print("Connected to Qdrant Cloud")
        else:
            self.client = QdrantClient(
                url=qdrant_url,
                timeout=30.0
            )
            print("Connected to local Qdrant")

        self.collection_name = os.getenv("COLLECTION_NAME", "documents")
        self._ensure_collection()

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Batch embeddings into chunks of 10 to speed up processing 10x"""
        if USE_GEMINI_EMBEDDINGS:
            embeddings = []
            batch_size = 10  # Batch 10 texts per API call
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        result = genai.embed_content(
                            model=GEMINI_EMBED_MODEL,
                            content=batch,
                            task_type="retrieval_document"
                        )
                        # Result['embedding'] contains a list of vectors when input is a list
                        if isinstance(result['embedding'][0], list):
                            embeddings.extend(result['embedding'])
                        else:
                            embeddings.append(result['embedding'])
                        
                        # Small delay between batches to stay within rate limits
                        time.sleep(0.5)
                        break
                        
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "quota" in error_str.lower():
                            wait_time = 20
                            print(f"Rate limit hit. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            if attempt == max_retries - 1:
                                raise Exception("Gemini rate limit exceeded. Please wait a minute and try uploading a smaller document.")
                        else:
                            if attempt == max_retries - 1:
                                raise e
                            time.sleep(2)
            
            return embeddings
        else:
            return self.model.encode(texts, show_progress_bar=False).tolist()

    def _embed_query(self, text: str) -> List[float]:
        if USE_GEMINI_EMBEDDINGS:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = genai.embed_content(
                        model=GEMINI_EMBED_MODEL,
                        content=text,
                        task_type="retrieval_query"
                    )
                    return result['embedding']
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "quota" in error_str.lower():
                        wait_time = 20
                        print(f"Query rate limit hit. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        if attempt == max_retries - 1:
                            raise Exception("Rate limit exceeded. Please wait 30 seconds and try again.")
                    else:
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(1)
        else:
            return self.model.encode([text])[0].tolist()

    def _ensure_collection(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
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
                    print(f"Created collection: {self.collection_name} (dim {EMBEDDING_DIM})")
                else:
                    print(f"Collection exists: {self.collection_name}")
                return
            except Exception as e:
                print(f"Qdrant connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

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

        # Upsert to Qdrant with connection retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                break
            except Exception as e:
                print(f"Qdrant upsert attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to save vectors to Qdrant Cloud: {e}")
                time.sleep(2)

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

        # Search Qdrant with connection retries
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    limit=top_k,
                    query_filter=search_filter
                )
                break
            except Exception as e:
                print(f"Qdrant query attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Vector search failed: {e}")
                time.sleep(1)

        results = response.points if response else []

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