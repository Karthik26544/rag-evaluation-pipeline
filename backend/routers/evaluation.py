from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

router = APIRouter()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-flash-latest")

class EvalQuestion(BaseModel):
    question: str
    ground_truth: str

class EvaluationRequest(BaseModel):
    evaluation_name: str
    questions: List[EvalQuestion]
    chunking_strategies: List[str] = ["fixed", "recursive", "sentence"]
    search_types: List[str] = ["vector", "hybrid"]

def get_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

def score_faithfulness(answer: str, context: str) -> float:
    prompt = f"""
    Score how faithful this answer is to the given context.
    Return ONLY a number between 0.0 and 1.0. Nothing else.
    1.0 = completely faithful to context
    0.0 = makes up information not in context

    Context: {context[:1000]}
    Answer: {answer[:500]}

    Score:
    """
    try:
        response = gemini_model.generate_content(prompt)
        score = float(response.text.strip())
        return min(1.0, max(0.0, score))
    except:
        return 0.5

def score_relevancy(
    question: str,
    answer: str,
    ground_truth: str
) -> float:
    prompt = f"""
    Score how relevant and correct this answer is.
    Return ONLY a number between 0.0 and 1.0. Nothing else.
    1.0 = perfectly answers the question
    0.0 = completely wrong or irrelevant

    Question: {question}
    Expected answer: {ground_truth}
    Actual answer: {answer[:500]}

    Score:
    """
    try:
        response = gemini_model.generate_content(prompt)
        score = float(response.text.strip())
        return min(1.0, max(0.0, score))
    except:
        return 0.5

@router.post("/run")
def run_evaluation(request: EvaluationRequest):
    from services.vector_store import VectorStore
    from services.hybrid_search import HybridSearch
    from services.query_processor import QueryProcessor

    vector_store = VectorStore()
    hybrid_search_service = HybridSearch()
    query_processor = QueryProcessor()

    results = []

    for strategy in request.chunking_strategies:
        for search_type in request.search_types:

            faithfulness_scores = []
            relevancy_scores = []
            latencies = []

            for eval_q in request.questions:

                if search_type == "vector":
                    chunks = vector_store.search(
                        eval_q.question,
                        top_k=5,
                        strategy_filter=strategy
                    )
                else:
                    vector_chunks = vector_store.search(
                        eval_q.question,
                        top_k=20
                    )

                    conn = get_db()
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT content, document_id, 
                               chunk_index, chunking_strategy 
                        FROM chunks 
                        WHERE chunking_strategy = %s 
                        LIMIT 5000
                    """, (strategy,))
                    all_chunks = [dict(row) for row in cursor.fetchall()]
                    cursor.close()
                    conn.close()

                    if all_chunks:
                        hybrid_search_service.build_index(all_chunks)
                        bm25_chunks = hybrid_search_service.search(
                            eval_q.question,
                            top_k=20
                        )
                        chunks = hybrid_search_service.hybrid_search(
                            vector_chunks,
                            bm25_chunks
                        )
                    else:
                        chunks = vector_chunks

                if not chunks:
                    continue

                answer, confidence, latency = query_processor.generate_answer(
                    question=eval_q.question,
                    context_chunks=chunks
                )

                latencies.append(latency)

                context_text = " ".join([c["content"] for c in chunks[:3]])
                faith = score_faithfulness(answer, context_text)
                faithfulness_scores.append(faith)

                relev = score_relevancy(
                    eval_q.question,
                    answer,
                    eval_q.ground_truth
                )
                relevancy_scores.append(relev)

                time.sleep(2)

            if not faithfulness_scores:
                continue

            avg_faith = sum(faithfulness_scores) / len(faithfulness_scores)
            avg_relev = sum(relevancy_scores) / len(relevancy_scores)
            avg_lat = int(sum(latencies) / len(latencies)) if latencies else 0

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO evaluations (
                    id, evaluation_name, chunking_strategy, 
                    search_type, faithfulness, answer_relevancy, 
                    total_questions, avg_latency_ms
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()),
                request.evaluation_name,
                strategy,
                search_type,
                avg_faith,
                avg_relev,
                len(request.questions),
                avg_lat
            ))

            conn.commit()
            cursor.close()
            conn.close()

            results.append({
                "chunking_strategy": strategy,
                "search_type": search_type,
                "faithfulness": round(avg_faith, 3),
                "answer_relevancy": round(avg_relev, 3),
                "avg_latency_ms": avg_lat,
                "questions_evaluated": len(faithfulness_scores)
            })

    best = max(
        results,
        key=lambda x: (x["faithfulness"] + x["answer_relevancy"]) / 2
    ) if results else {}

    return {
        "evaluation_name": request.evaluation_name,
        "results": results,
        "best_combination": f"{best.get('chunking_strategy')} + {best.get('search_type')}" if best else "N/A"
    }


@router.get("/history")
def get_evaluation_history():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT * FROM evaluations
        ORDER BY evaluated_at DESC
    """)

    evals = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"evaluations": [dict(e) for e in evals]}


@router.get("/dashboard")
def get_dashboard_data():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            chunking_strategy,
            search_type,
            AVG(faithfulness) as avg_faithfulness,
            AVG(answer_relevancy) as avg_relevancy,
            AVG(avg_latency_ms) as avg_latency,
            COUNT(*) as total_runs
        FROM evaluations
        GROUP BY chunking_strategy, search_type
        ORDER BY avg_faithfulness DESC
    """)
    comparison_data = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) as total FROM queries")
    query_count = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as total FROM documents")
    doc_count = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "comparison_data": [dict(d) for d in comparison_data],
        "total_queries": query_count["total"],
        "total_documents": doc_count["total"]
    }