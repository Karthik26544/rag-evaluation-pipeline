from fastapi import APIRouter, HTTPException, Request
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

load_dotenv()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

vector_store = VectorStore()
hybrid_search = HybridSearch()
query_processor = QueryProcessor()
reranker = Reranker()

class QueryRequest(BaseModel):
    question: str
    search_type: str = "hybrid"
    chunking_strategy: Optional[str] = None
    use_query_rewriting: bool = True
    use_reranker: bool = True
    top_k: int = 5

def get_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

@router.post("/ask")
@limiter.limit("10/minute")
def ask_question(request: Request, req: QueryRequest):
    original_question = req.question
    question = original_question

    if req.use_query_rewriting:
        question = query_processor.rewrite_query(original_question)

    initial_top_k = 20 if req.use_reranker else req.top_k

    if req.search_type == "vector":
        results = vector_store.search(
            question,
            top_k=initial_top_k,
            strategy_filter=req.chunking_strategy
        )

    elif req.search_type == "bm25":
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT content, document_id, chunk_index, chunking_strategy 
            FROM chunks LIMIT 10000
        """)
        all_chunks = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        hybrid_search.build_index(all_chunks)
        results = hybrid_search.search(question, top_k=initial_top_k)

    elif req.search_type == "hybrid":
        vector_results = vector_store.search(
            question,
            top_k=20,
            strategy_filter=req.chunking_strategy
        )

        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT content, document_id, chunk_index, chunking_strategy 
            FROM chunks LIMIT 10000
        """)
        all_chunks = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        hybrid_search.build_index(all_chunks)
        bm25_results = hybrid_search.search(question, top_k=20)
        results = hybrid_search.hybrid_search(vector_results, bm25_results)

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid search_type. Use vector, bm25, or hybrid"
        )

    if not results:
        return {
            "answer": "No relevant documents found. Please upload documents first.",
            "sources": [],
            "confidence": 0.0,
            "rewritten_question": question,
            "latency_ms": 0,
            "search_type": req.search_type,
            "chunks_found": 0,
            "reranked": False
        }

    reranked_flag = False
    if req.use_reranker and len(results) > req.top_k:
        results = reranker.rerank(question, results, top_k=req.top_k)
        reranked_flag = reranker.enabled

    results = results[:req.top_k]

    answer, confidence, latency = query_processor.generate_answer(
        question=question,
        context_chunks=results,
        original_question=original_question
    )

    sources = [
        {
            "content": r["content"][:200],
            "document_id": r.get("document_id", ""),
            "score": r.get("rerank_score", r.get("score", r.get("final_score", 0)))
        }
        for r in results[:5]
    ]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO queries 
        (id, question, rewritten_question, answer, sources, 
         search_type, chunking_strategy, latency_ms, confidence_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        str(uuid.uuid4()),
        original_question,
        question,
        answer,
        json.dumps(sources),
        req.search_type,
        req.chunking_strategy,
        latency,
        confidence
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "rewritten_question": question if req.use_query_rewriting else None,
        "latency_ms": latency,
        "search_type": req.search_type,
        "chunks_found": len(results),
        "reranked": reranked_flag
    }


@router.get("/history")
def get_query_history():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT id, question, answer, confidence_score, 
               latency_ms, search_type, created_at
        FROM queries
        ORDER BY created_at DESC
        LIMIT 50
    """)

    queries = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"queries": [dict(q) for q in queries]}