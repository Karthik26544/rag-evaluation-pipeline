from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
from dotenv import load_dotenv

from services.auth_middleware import get_current_user, get_current_admin

load_dotenv()

router = APIRouter()


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    category: Optional[str] = "general"


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@router.post("/submit")
def submit_feedback(req: FeedbackRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    feedback_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO feedback (id, user_id, rating, comment, category)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, rating, comment, category, created_at
    """, (feedback_id, str(user["id"]), req.rating, req.comment, req.category))
    
    result = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        "success": True,
        "message": "Thank you for your feedback!",
        "feedback": dict(result)
    }


@router.get("/my-feedback")
def get_my_feedback(user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT id, rating, comment, category, created_at
        FROM feedback
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (str(user["id"]),))
    
    feedback = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"feedback": [dict(f) for f in feedback]}


@router.get("/all")
def get_all_feedback(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            f.id, f.rating, f.comment, f.category, f.created_at,
            u.name as user_name, u.email as user_email
        FROM feedback f
        LEFT JOIN users u ON f.user_id = u.id
        ORDER BY f.created_at DESC
    """)
    
    feedback = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"feedback": [dict(f) for f in feedback]}


@router.get("/stats")
def get_feedback_stats(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_feedback,
            AVG(rating) as avg_rating,
            COUNT(*) FILTER (WHERE rating = 5) as five_star,
            COUNT(*) FILTER (WHERE rating = 4) as four_star,
            COUNT(*) FILTER (WHERE rating = 3) as three_star,
            COUNT(*) FILTER (WHERE rating = 2) as two_star,
            COUNT(*) FILTER (WHERE rating = 1) as one_star
        FROM feedback
    """)
    
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return dict(stats) if stats else {}


@router.delete("/{feedback_id}")
def delete_feedback(feedback_id: str, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feedback WHERE id = %s", (feedback_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "message": "Feedback deleted"}