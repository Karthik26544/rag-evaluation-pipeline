from fastapi import APIRouter, Depends, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import os
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
        "avg_confidence": round(float(avg_confidence), 2)
    }


@router.get("/users")
def get_all_users(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            u.id, u.name, u.email, u.is_admin, u.created_at, u.last_login,
            (SELECT COUNT(*) FROM documents WHERE user_id = u.id) as doc_count,
            (SELECT COUNT(*) FROM queries WHERE user_id = u.id) as query_count
        FROM users u
        ORDER BY u.created_at DESC
    """)
    
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"users": [dict(u) for u in users]}


@router.get("/queries/recent")
def get_recent_queries(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            q.id, q.question, q.answer, q.confidence_score, q.latency_ms,
            q.search_type, q.created_at,
            u.name as user_name, u.email as user_email
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        ORDER BY q.created_at DESC
        LIMIT 50
    """)
    
    queries = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"queries": [dict(q) for q in queries]}


@router.get("/analytics/growth")
def get_growth_analytics(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
        FROM users
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    users_growth = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
        FROM queries
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    queries_growth = cursor.fetchall()
    
    cursor.execute("""
        SELECT search_type, COUNT(*) as count
        FROM queries
        GROUP BY search_type
    """)
    search_distribution = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "users_growth": [{"date": str(u["date"]), "count": u["count"]} for u in users_growth],
        "queries_growth": [{"date": str(q["date"]), "count": q["count"]} for q in queries_growth],
        "search_distribution": [dict(s) for s in search_distribution]
    }


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