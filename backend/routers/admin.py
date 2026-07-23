from fastapi import APIRouter, Depends, HTTPException, Response
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import io
import csv
from datetime import datetime
from dotenv import load_dotenv

from services.auth_middleware import get_current_admin

load_dotenv()

router = APIRouter()


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@router.get("/stats")
def get_platform_stats(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM documents")
    total_documents = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM queries")
    total_queries = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM evaluations")
    total_evaluations = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE created_at > NOW() - INTERVAL '7 days'")
    new_users_week = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM queries WHERE created_at > NOW() - INTERVAL '24 hours'")
    queries_today = cursor.fetchone()["total"]
    
    cursor.execute("SELECT AVG(latency_ms) as avg FROM queries WHERE latency_ms > 0")
    avg_latency = cursor.fetchone()["avg"] or 0
    
    cursor.execute("SELECT AVG(confidence_score) as avg FROM queries WHERE confidence_score > 0")
    avg_confidence = cursor.fetchone()["avg"] or 0
    
    cursor.execute("""
        SELECT COUNT(*) as total FROM users 
        WHERE last_login > NOW() - INTERVAL '24 hours'
    """)
    active_today = cursor.fetchone()["total"]
    
    cursor.execute("""
        SELECT COUNT(*) as total FROM queries 
        WHERE confidence_score > 0.7
    """)
    high_confidence = cursor.fetchone()["total"]
    
    total_tokens_estimate = total_queries * 500
    total_cost_estimate = round(total_tokens_estimate / 1000000 * 0.075, 4)
    
    cursor.close()
    conn.close()
    
    return {
        "total_users": total_users,
        "total_documents": total_documents,
        "total_queries": total_queries,
        "total_evaluations": total_evaluations,
        "new_users_week": new_users_week,
        "queries_today": queries_today,
        "avg_latency_ms": int(avg_latency),
        "avg_confidence": round(float(avg_confidence), 2),
        "active_today": active_today,
        "high_confidence_queries": high_confidence,
        "estimated_tokens_used": total_tokens_estimate,
        "estimated_cost_usd": total_cost_estimate
    }


@router.get("/users")
def get_all_users(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            u.id, u.name, u.email, u.is_admin, u.created_at, u.last_login,
            (SELECT COUNT(*) FROM documents WHERE user_id = u.id) as doc_count,
            (SELECT COUNT(*) FROM queries WHERE user_id = u.id) as query_count,
            (SELECT AVG(confidence_score) FROM queries WHERE user_id = u.id AND confidence_score > 0) as avg_confidence,
            (SELECT AVG(latency_ms) FROM queries WHERE user_id = u.id AND latency_ms > 0) as avg_latency,
            (SELECT MAX(created_at) FROM queries WHERE user_id = u.id) as last_activity
        FROM users u
        ORDER BY u.created_at DESC
    """)
    
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"users": [dict(u) for u in users]}


@router.get("/users/{user_id}/details")
def get_user_details(user_id: str, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    cursor.execute("""
        SELECT id, filename, file_type, total_chunks, chunking_strategy, upload_time
        FROM documents WHERE user_id = %s ORDER BY upload_time DESC
    """, (user_id,))
    documents = cursor.fetchall()
    
    cursor.execute("""
        SELECT id, question, answer, confidence_score, latency_ms, search_type, created_at
        FROM queries WHERE user_id = %s ORDER BY created_at DESC LIMIT 50
    """, (user_id,))
    queries = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_queries,
            AVG(confidence_score) as avg_confidence,
            AVG(latency_ms) as avg_latency,
            SUM(CASE WHEN confidence_score > 0.7 THEN 1 ELSE 0 END) as high_confidence_count,
            SUM(CASE WHEN search_type = 'hybrid' THEN 1 ELSE 0 END) as hybrid_count,
            SUM(CASE WHEN search_type = 'vector' THEN 1 ELSE 0 END) as vector_count,
            SUM(CASE WHEN search_type = 'bm25' THEN 1 ELSE 0 END) as bm25_count
        FROM queries WHERE user_id = %s
    """, (user_id,))
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    user_dict = dict(user)
    user_dict.pop("password_hash", None)
    
    return {
        "user": user_dict,
        "documents": [dict(d) for d in documents],
        "queries": [dict(q) for q in queries],
        "stats": dict(stats) if stats else {}
    }


@router.get("/queries/recent")
def get_recent_queries(admin: dict = Depends(get_current_admin), limit: int = 100):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            q.id, q.question, q.answer, q.confidence_score, q.latency_ms,
            q.search_type, q.chunking_strategy, q.created_at,
            u.name as user_name, u.email as user_email
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        ORDER BY q.created_at DESC
        LIMIT %s
    """, (limit,))
    
    queries = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"queries": [dict(q) for q in queries]}


@router.get("/analytics/growth")
def get_growth_analytics(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM users WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at) ORDER BY date
    """)
    users_growth = cursor.fetchall()
    
    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM queries WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at) ORDER BY date
    """)
    queries_growth = cursor.fetchall()
    
    cursor.execute("""
        SELECT search_type, COUNT(*) as count
        FROM queries GROUP BY search_type
    """)
    search_distribution = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            u.name, u.email,
            COUNT(q.id) as query_count
        FROM users u
        LEFT JOIN queries q ON q.user_id = u.id
        GROUP BY u.id, u.name, u.email
        ORDER BY query_count DESC
        LIMIT 5
    """)
    top_users = cursor.fetchall()
    
    cursor.execute("""
        SELECT chunking_strategy, COUNT(*) as count
        FROM documents 
        WHERE chunking_strategy IS NOT NULL
        GROUP BY chunking_strategy
    """)
    chunking_distribution = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "users_growth": [{"date": str(u["date"]), "count": u["count"]} for u in users_growth],
        "queries_growth": [{"date": str(q["date"]), "count": q["count"]} for q in queries_growth],
        "search_distribution": [dict(s) for s in search_distribution],
        "chunking_distribution": [dict(c) for c in chunking_distribution],
        "top_users": [dict(u) for u in top_users]
    }


@router.get("/export/users")
def export_users(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            u.name, u.email, u.is_admin, u.created_at, u.last_login,
            (SELECT COUNT(*) FROM documents WHERE user_id = u.id) as doc_count,
            (SELECT COUNT(*) FROM queries WHERE user_id = u.id) as query_count
        FROM users u ORDER BY u.created_at DESC
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Admin", "Created", "Last Login", "Documents", "Queries"])
    
    for u in users:
        writer.writerow([
            u["name"], u["email"], u["is_admin"],
            u["created_at"], u["last_login"] or "Never",
            u["doc_count"], u["query_count"]
        ])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@router.get("/export/queries")
def export_queries(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            u.name as user_name, u.email as user_email,
            q.question, q.answer, q.confidence_score, q.latency_ms,
            q.search_type, q.chunking_strategy, q.created_at
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        ORDER BY q.created_at DESC
    """)
    queries = cursor.fetchall()
    cursor.close()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User", "Email", "Question", "Answer", "Confidence", "Latency (ms)", "Search Type", "Chunking", "Created"])
    
    for q in queries:
        writer.writerow([
            q["user_name"] or "Anonymous",
            q["user_email"] or "N/A",
            q["question"][:200],
            (q["answer"] or "")[:500],
            q["confidence_score"],
            q["latency_ms"],
            q["search_type"],
            q["chunking_strategy"] or "N/A",
            q["created_at"]
        ])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=queries_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin: dict = Depends(get_current_admin)):
    if str(admin["id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"success": True, "message": "User deleted"}


@router.post("/users/{user_id}/toggle-admin")
def toggle_admin(user_id: str, admin: dict = Depends(get_current_admin)):
    if str(admin["id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own admin status")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = NOT is_admin WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"success": True, "message": "Admin status toggled"}