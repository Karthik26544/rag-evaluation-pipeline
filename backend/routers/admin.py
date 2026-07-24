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
    
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE last_login > NOW() - INTERVAL '24 hours'")
    active_today = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM queries WHERE confidence_score > 0.7")
    high_confidence = cursor.fetchone()["total"]
    
    # Cache stats
    cache_stats = {}
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as cache_entries,
                COALESCE(SUM(hit_count), 0) as total_hits,
                COALESCE(SUM(hit_count) - COUNT(*), 0) as api_calls_saved
            FROM query_cache
        """)
        cache_stats = dict(cursor.fetchone())
    except:
        cache_stats = {"cache_entries": 0, "total_hits": 0, "api_calls_saved": 0}
    
    # Feedback stats  
    feedback_stats = {}
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_feedback,
                COALESCE(AVG(rating), 0) as avg_rating
            FROM feedback
        """)
        feedback_stats = dict(cursor.fetchone())
    except:
        feedback_stats = {"total_feedback": 0, "avg_rating": 0}
    
    total_tokens_estimate = total_queries * 500
    total_cost_estimate = round(total_tokens_estimate / 1000000 * 0.075, 4)
    
    # Estimate savings from cache
    cost_saved = round(int(cache_stats.get("api_calls_saved", 0)) * 500 / 1000000 * 0.075, 4)
    
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
        "estimated_cost_usd": total_cost_estimate,
        "cache_entries": int(cache_stats.get("cache_entries", 0)),
        "cache_hits": int(cache_stats.get("total_hits", 0)),
        "api_calls_saved": int(cache_stats.get("api_calls_saved", 0)),
        "cost_saved_usd": cost_saved,
        "total_feedback": int(feedback_stats.get("total_feedback", 0)),
        "avg_rating": round(float(feedback_stats.get("avg_rating", 0)), 1)
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
            AVG(latency_ms) as avg_latency
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
        SELECT u.name, u.email, COUNT(q.id) as query_count
        FROM users u
        LEFT JOIN queries q ON q.user_id = u.id
        GROUP BY u.id, u.name, u.email
        ORDER BY query_count DESC LIMIT 5
    """)
    top_users = cursor.fetchall()
    
    cursor.execute("""
        SELECT chunking_strategy, COUNT(*) as count
        FROM documents 
        WHERE chunking_strategy IS NOT NULL
        GROUP BY chunking_strategy
    """)
    chunking_distribution = cursor.fetchall()
    
    # Rating distribution
    rating_distribution = []
    try:
        cursor.execute("""
            SELECT rating, COUNT(*) as count 
            FROM feedback GROUP BY rating ORDER BY rating
        """)
        rating_distribution = [dict(r) for r in cursor.fetchall()]
    except:
        pass
    
    # Top cached queries
    top_cached = []
    try:
        cursor.execute("""
            SELECT question, hit_count, confidence, search_type
            FROM query_cache
            ORDER BY hit_count DESC LIMIT 10
        """)
        top_cached = [dict(r) for r in cursor.fetchall()]
    except:
        pass
    
    # Activity feed - recent events
    activity_feed = []
    try:
        cursor.execute("""
            (SELECT 'user_registered' as type, name as detail, created_at as time, email as extra
             FROM users ORDER BY created_at DESC LIMIT 5)
            UNION ALL
            (SELECT 'query_asked' as type, LEFT(question, 60) as detail, created_at as time, '' as extra
             FROM queries ORDER BY created_at DESC LIMIT 5)
            UNION ALL  
            (SELECT 'document_uploaded' as type, filename as detail, upload_time as time, chunking_strategy as extra
             FROM documents ORDER BY upload_time DESC LIMIT 5)
            ORDER BY time DESC LIMIT 15
        """)
        activity_feed = [dict(r) for r in cursor.fetchall()]
    except:
        pass
    
    cursor.close()
    conn.close()
    
    return {
        "users_growth": [{"date": str(u["date"]), "count": u["count"]} for u in users_growth],
        "queries_growth": [{"date": str(q["date"]), "count": q["count"]} for q in queries_growth],
        "search_distribution": [dict(s) for s in search_distribution],
        "chunking_distribution": [dict(c) for c in chunking_distribution],
        "top_users": [dict(u) for u in top_users],
        "rating_distribution": rating_distribution,
        "top_cached_queries": top_cached,
        "activity_feed": [{"type": a["type"], "detail": a["detail"], "time": str(a["time"]), "extra": a["extra"]} for a in activity_feed]
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
        writer.writerow([u["name"], u["email"], u["is_admin"], u["created_at"], u["last_login"] or "Never", u["doc_count"], u["query_count"]])
    
    return Response(content=output.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d')}.csv"})


@router.get("/export/queries")
def export_queries(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT u.name as user_name, u.email as user_email,
            q.question, q.answer, q.confidence_score, q.latency_ms,
            q.search_type, q.chunking_strategy, q.created_at
        FROM queries q LEFT JOIN users u ON q.user_id = u.id
        ORDER BY q.created_at DESC
    """)
    queries = cursor.fetchall()
    cursor.close()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User", "Email", "Question", "Answer", "Confidence", "Latency (ms)", "Search Type", "Chunking", "Created"])
    for q in queries:
        writer.writerow([q["user_name"] or "Anonymous", q["user_email"] or "N/A",
            q["question"][:200], (q["answer"] or "")[:500], q["confidence_score"],
            q["latency_ms"], q["search_type"], q["chunking_strategy"] or "N/A", q["created_at"]])
    
    return Response(content=output.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=queries_{datetime.now().strftime('%Y%m%d')}.csv"})


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


@router.post("/cache/clear")
def clear_cache(admin: dict = Depends(get_current_admin)):
    """Clear all cached queries"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_cache")
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))