from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import json
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.vector_store import VectorStore
from services.hybrid_search import HybridSearch
from services.query_processor import QueryProcessor
from services.reranker import Reranker
from services.cache_service import CacheService
from services.auth_service import decode_token
from services.auth_middleware import get_current_user

load_dotenv()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer(auto_error=False)

vector_store = VectorStore()
hybrid_search = HybridSearch()
query_processor = QueryProcessor()
reranker = Reranker()
cache_service = CacheService()


class QueryRequest(BaseModel):
    question: str
    search_type: str = "hybrid"
    chunking_strategy: Optional[str] = None
    use_query_rewriting: bool = True
    use_reranker: bool = True
    use_cache: bool = True
    top_k: int = 5


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def get_user_id_from_request(request: Request):
    """Extract user_id from token if present, return None otherwise"""
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        if payload:
            return payload.get("user_id")
    except:
        pass
    return None


@router.post("/ask")
@limiter.limit("10/minute")
def ask_question(request: Request, req: QueryRequest):
    original_question = req.question
    user_id = get_user_id_from_request(request)

    if req.use_cache:
        cached = cache_service.get(original_question, req.search_type)
        if cached:
            _save_query_to_db(
                user_id=user_id,
                original_question=original_question,
                rewritten_question=original_question,
                answer=cached["answer"],
                sources=cached["sources"] if isinstance(cached["sources"], list) else [],
                search_type=req.search_type,
                chunking_strategy=req.chunking_strategy,
                latency_ms=50,
                confidence=cached["confidence"]
            )
            return {
                "answer": cached["answer"],
                "sources": cached["sources"] if isinstance(cached["sources"], list) else [],
                "confidence": cached["confidence"],
                "rewritten_question": None,
                "latency_ms": 50,
                "search_type": req.search_type,
                "chunks_found": len(cached["sources"]) if isinstance(cached["sources"], list) else 0,
                "reranked": False,
                "cached": True,
                "cache_hit_count": cached.get("hit_count", 1)
            }

    question = original_question
    if req.use_query_rewriting:
        question = query_processor.rewrite_query(original_question)

    initial_top_k = 20 if req.use_reranker else req.top_k

    if req.search_type == "vector":
        results = vector_store.search(question, top_k=initial_top_k, strategy_filter=req.chunking_strategy)

    elif req.search_type == "bm25":
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT content, document_id, chunk_index, chunking_strategy FROM chunks LIMIT 10000")
        all_chunks = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        hybrid_search.build_index(all_chunks)
        results = hybrid_search.search(question, top_k=initial_top_k)

    elif req.search_type == "hybrid":
        vector_results = vector_store.search(question, top_k=20, strategy_filter=req.chunking_strategy)
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT content, document_id, chunk_index, chunking_strategy FROM chunks LIMIT 10000")
        all_chunks = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        hybrid_search.build_index(all_chunks)
        bm25_results = hybrid_search.search(question, top_k=20)
        results = hybrid_search.hybrid_search(vector_results, bm25_results)
    else:
        raise HTTPException(status_code=400, detail="Invalid search_type")

    if not results:
        return {
            "answer": "No relevant documents found. Please upload documents first.",
            "sources": [], "confidence": 0.0, "rewritten_question": question,
            "latency_ms": 0, "search_type": req.search_type, "chunks_found": 0,
            "reranked": False, "cached": False
        }

    reranked_flag = False
    if req.use_reranker and len(results) > req.top_k:
        results = reranker.rerank(question, results, top_k=req.top_k)
        reranked_flag = reranker.enabled

    results = results[:req.top_k]

    answer, confidence, latency = query_processor.generate_answer(
        question=question, context_chunks=results, original_question=original_question
    )

    sources = [
        {
            "content": r["content"][:200],
            "document_id": r.get("document_id", ""),
            "score": r.get("rerank_score", r.get("score", r.get("final_score", 0)))
        }
        for r in results[:5]
    ]

    if req.use_cache and confidence > 0.5:
        cache_service.set(
            question=original_question, answer=answer, sources=sources,
            confidence=confidence, search_type=req.search_type
        )

    _save_query_to_db(
        user_id=user_id,
        original_question=original_question,
        rewritten_question=question,
        answer=answer,
        sources=sources,
        search_type=req.search_type,
        chunking_strategy=req.chunking_strategy,
        latency_ms=latency,
        confidence=confidence
    )

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "rewritten_question": question if req.use_query_rewriting else None,
        "latency_ms": latency,
        "search_type": req.search_type,
        "chunks_found": len(results),
        "reranked": reranked_flag,
        "cached": False
    }


def _save_query_to_db(user_id, original_question, rewritten_question, answer, sources, search_type, chunking_strategy, latency_ms, confidence):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO queries 
            (id, user_id, question, rewritten_question, answer, sources, 
             search_type, chunking_strategy, latency_ms, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()), user_id, original_question, rewritten_question,
            answer, json.dumps(sources), search_type, chunking_strategy,
            latency_ms, confidence
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Save query error: {e}")


@router.get("/history")
def get_query_history():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, question, answer, confidence_score, 
               latency_ms, search_type, created_at
        FROM queries ORDER BY created_at DESC LIMIT 50
    """)
    queries = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"queries": [dict(q) for q in queries]}


@router.get("/my-history")
def get_my_history(user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, question, answer, confidence_score, 
               latency_ms, search_type, sources, created_at
        FROM queries WHERE user_id = %s
        ORDER BY created_at DESC LIMIT 100
    """, (str(user["id"]),))
    queries = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"queries": [dict(q) for q in queries]}


@router.delete("/my-history/{query_id}")
def delete_my_query(query_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM queries WHERE id = %s AND user_id = %s", (query_id, str(user["id"])))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}