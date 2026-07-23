from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

from services.auth_service import decode_token

load_dotenv()

security = HTTPBearer(auto_error=False)


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("user_id")
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, name, email, is_admin FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return dict(user)


def get_current_admin(user: dict = Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Allows both authenticated and unauthenticated access"""
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    
    user_id = payload.get("user_id")
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, name, email, is_admin FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return dict(user) if user else None