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
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
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

        self.collection_name = os.getenv("COLLECTION_NAME", "documents")
        self._init_client()
        self._ensure_collection(raise_on_failure=False)

    def _init_client(self):
        """Initialize or refresh Qdrant client connection"""
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        qdrant_url = (os.getenv("QDRANT_URL") or "http://localhost:6333").strip().rstrip("/")

        parsed = urlparse(qdrant_url)
        if qdrant_api_key and not parsed.scheme:
            qdrant_url = f"https://{qdrant_url}"
            parsed = urlparse(qdrant_url)

        kwargs = {
            "url": qdrant_url,
            "timeout": 60,
            "prefer_grpc": False,
        }

        # If the URL already includes :6333, the client must not append another port.
        # https://host:6333:6333 is a common Qdrant Cloud timeout / connection failure.
        if parsed.port is not None:
            kwargs["port"] = None

        if qdrant_api_key:
            kwargs["api_key"] = qdrant_api_key
            if parsed.scheme != "http":
                kwargs["https"] = True

        self.client = QdrantClient(**kwargs)

    def _collection_vector_size(self, info) -> Optional[int]:
        vectors = getattr(getattr(info.config, "params", None), "vectors", None)
        if vectors is None:
            return None
        if hasattr(vectors, "size"):
            return vectors.size
        if isinstance(vectors, dict) and vectors:
            first = next(iter(vectors.values()))
            return getattr(first, "size", None)
        return None

    def _is_retryable_qdrant_error(self, error: Exception) -> bool:
        text = str(error).lower()
        retry_markers = (
            "timeout",
            "timed out",
            "temporarily unavailable",
            "connection",
            "connect",
            "reset",
            "broken pipe",
            "unavailable",
            "503",
            "502",
            "504",
            "429",
        )
        return any(marker in text for marker in retry_markers)

    def _is_dimension_mismatch(self, error: Exception) -> bool:
        text = str(error).lower()
        return "dimension" in text or "vector size" in text or "expected dim" in text

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if USE_GEMINI_EMBEDDINGS:
            embeddings = []
            batch_size = 10
            
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
                        if isinstance(result['embedding'][0], list):
                            embeddings.extend(result['embedding'])
                        else:
                            embeddings.append(result['embedding'])
                        break
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "quota" in error_str.lower():
                            wait_time = 15
                            print(f"Embedding rate limit hit. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            if attempt == max_retries - 1:
                                raise Exception("Rate limit reached on Gemini embeddings. Please wait 30 seconds and try again.")
                        else:
                            if attempt == max_retries - 1:
                                raise e
                            time.sleep(1)
            
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
                        time.sleep(10)
                        if attempt == max_retries - 1:
                            raise Exception("Rate limit reached. Please wait 30 seconds.")
                    else:
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(1)
        else:
            return self.model.encode([text])[0].tolist()

    def _ensure_collection(self, force_recreate: bool = False, raise_on_failure: bool = True):
        max_retries = 5
        last_error = None

        for attempt in range(max_retries):
            try:
                collections = self.client.get_collections().collections
                names = [c.name for c in collections]
                exists = self.collection_name in names

                if exists and not force_recreate:
                    info = self.client.get_collection(self.collection_name)
                    actual_dim = self._collection_vector_size(info)
                    if actual_dim is not None and actual_dim != EMBEDDING_DIM:
                        print(
                            f"Collection {self.collection_name} dim {actual_dim} "
                            f"!= embedding dim {EMBEDDING_DIM}. Recreating collection."
                        )
                        force_recreate = True
                    else:
                        print(f"Collection exists: {self.collection_name}")
                        return

                if exists and force_recreate:
                    self.client.delete_collection(self.collection_name)
                    exists = False

                if not exists:
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=EMBEDDING_DIM,
                            distance=Distance.COSINE
                        )
                    )
                    print(f"Created collection: {self.collection_name} (dim {EMBEDDING_DIM})")
                return
            except Exception as e:
                last_error = e
                print(f"Qdrant collection check attempt {attempt + 1} failed: {e}")
                self._init_client()
                time.sleep(min(2 ** attempt, 8))

        message = (
            f"Failed to connect to Qdrant. Check QDRANT_URL and QDRANT_API_KEY. Last error: {last_error}"
        )
        if raise_on_failure:
            raise Exception(message)
        print(message)

    def add_chunks(self, chunks: List[Dict], document_id: str) -> List[str]:
        self._ensure_collection()
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

        # Upsert in small batches of 10 with automatic reconnection if socket drops
        batch_size = 10
        for i in range(0, len(points), batch_size):
            batch_points = points[i:i + batch_size]
            max_retries = 5
            last_error = None

            for attempt in range(max_retries):
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=batch_points,
                        wait=True
                    )
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    print(f"Qdrant batch upsert failed (attempt {attempt + 1}/{max_retries}): {e}")
                    if self._is_dimension_mismatch(e):
                        self._init_client()
                        self._ensure_collection(force_recreate=True)
                        continue
                    if not self._is_retryable_qdrant_error(e) and attempt == 0:
                        raise Exception(f"Failed to store vectors in Qdrant: {e}")
                    self._init_client()
                    time.sleep(min(2 ** attempt, 8))

            if last_error is not None:
                raise Exception(
                    f"Failed to connect to Qdrant Cloud. Please try again. Last error: {last_error}"
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

        max_retries = 5
        response = None
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    limit=top_k,
                    query_filter=search_filter
                )
                last_error = None
                break
            except Exception as e:
                last_error = e
                print(f"Qdrant query failed (attempt {attempt + 1}/{max_retries}): {e}")
                self._init_client()
                if attempt == max_retries - 1:
                    raise Exception(f"Vector search failed. Please try again. Last error: {e}")
                time.sleep(min(2 ** attempt, 8))

        if response is None:
            raise Exception(f"Vector search failed. Please try again. Last error: {last_error}")

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