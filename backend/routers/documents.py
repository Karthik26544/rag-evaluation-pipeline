from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from services.document_processor import DocumentProcessor
from services.vector_store import VectorStore

load_dotenv()

router = APIRouter()
processor = DocumentProcessor()
vector_store = VectorStore()

def get_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

@router.post("/upload")
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    chunking_strategy: str = Form(default="recursive")
):
    filename = file.filename
    extension = filename.split(".")[-1].lower()

    if extension not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, TXT, and MD files are supported"
        )

    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = f"{temp_dir}/{uuid.uuid4()}.{extension}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        text = processor.extract_text(temp_path, extension)

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from file"
            )

        chunks = processor.chunk_text(text, strategy=chunking_strategy)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        doc_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO documents 
            (id, filename, file_type, total_chunks, chunking_strategy, status)
            VALUES (%s, %s, %s, %s, %s, 'processing')
        """, (doc_id, filename, extension, len(chunks), chunking_strategy))

        for chunk in chunks:
            cursor.execute("""
                INSERT INTO chunks 
                (document_id, content, chunk_index, chunk_size, chunking_strategy)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                doc_id,
                chunk["content"],
                chunk["index"],
                chunk["size"],
                chunk["strategy"]
            ))

        vector_store.add_chunks(chunks, doc_id)

        cursor.execute("""
            UPDATE documents SET status = 'ready' WHERE id = %s
        """, (doc_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "document_id": doc_id,
            "filename": filename,
            "total_chunks": len(chunks),
            "chunking_strategy": chunking_strategy,
            "message": f"Document processed with {len(chunks)} chunks"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/list")
def list_documents():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT id, filename, file_type, total_chunks, 
               chunking_strategy, status, upload_time
        FROM documents
        ORDER BY upload_time DESC
    """)

    documents = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"documents": [dict(doc) for doc in documents]}


@router.delete("/{document_id}")
def delete_document(document_id: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM documents WHERE id = %s",
        (document_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True, "message": "Document deleted"}