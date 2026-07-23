from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
from dotenv import load_dotenv

from services.auth_service import hash_password, verify_password, create_access_token
from services.auth_middleware import get_current_user

load_dotenv()

router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@router.post("/register")
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    password_hash = hash_password(req.password)
    
    cursor.execute("""
        INSERT INTO users (id, name, email, password_hash, is_admin)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, email, is_admin
    """, (user_id, req.name, req.email, password_hash, False))
    
    user = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    token = create_access_token({
        "user_id": str(user["id"]),
        "email": user["email"],
        "is_admin": user["is_admin"]
    })
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    }


@router.post("/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM users WHERE email = %s", (req.email,))
    user = cursor.fetchone()
    
    if not user or not verify_password(req.password, user["password_hash"]):
        cursor.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user["id"],))
    conn.commit()
    cursor.close()
    conn.close()
    
    token = create_access_token({
        "user_id": str(user["id"]),
        "email": user["email"],
        "is_admin": user["is_admin"]
    })
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    }


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": str(user["id"]),
        "name": user["name"],
        "email": user["email"],
        "is_admin": user["is_admin"]
    }