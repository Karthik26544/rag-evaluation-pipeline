import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class CacheService:
    
    def __init__(self):
        self.cache_ttl_hours = 24
    
    def _get_db(self):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    
    def _hash_query(self, question: str, search_type: str = "hybrid") -> str:
        """Create unique hash for question + search type combination"""
        key = f"{question.lower().strip()}::{search_type}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get(self, question: str, search_type: str = "hybrid"):
        """Try to get cached answer. Returns None if not found or expired."""
        try:
            question_hash = self._hash_query(question, search_type)
            
            conn = self._get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM query_cache 
                WHERE question_hash = %s 
                AND created_at > NOW() - INTERVAL '%s hours'
            """, (question_hash, self.cache_ttl_hours))
            
            result = cursor.fetchone()
            
            if result:
                cursor.execute("""
                    UPDATE query_cache 
                    SET hit_count = hit_count + 1,
                        last_hit_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (result["id"],))
                conn.commit()
                
                cursor.close()
                conn.close()
                
                return {
                    "answer": result["answer"],
                    "sources": result["sources"],
                    "confidence": float(result["confidence"]),
                    "search_type": result["search_type"],
                    "cached": True,
                    "hit_count": result["hit_count"] + 1
                }
            
            cursor.close()
            conn.close()
            return None
        
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, question: str, answer: str, sources: list, confidence: float, search_type: str = "hybrid"):
        """Store answer in cache"""
        try:
            question_hash = self._hash_query(question, search_type)
            
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO query_cache 
                (question_hash, question, answer, sources, confidence, search_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (question_hash) 
                DO UPDATE SET 
                    answer = EXCLUDED.answer,
                    sources = EXCLUDED.sources,
                    confidence = EXCLUDED.confidence,
                    hit_count = query_cache.hit_count + 1,
                    last_hit_at = CURRENT_TIMESTAMP
            """, (
                question_hash,
                question,
                answer,
                json.dumps(sources),
                confidence,
                search_type
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def get_stats(self):
        """Get cache statistics"""
        try:
            conn = self._get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits_per_entry
                FROM query_cache
            """)
            
            stats = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(stats) if stats else {}
        
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {}
    
    def clear_expired(self):
        """Remove expired cache entries"""
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM query_cache 
                WHERE created_at < NOW() - INTERVAL '%s hours'
            """, (self.cache_ttl_hours,))
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return deleted
        except Exception as e:
            print(f"Cache cleanup error: {e}")
            return 0