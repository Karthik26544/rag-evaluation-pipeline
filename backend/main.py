from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import documents, queries, evaluation

app = FastAPI(title="RAG Evaluation Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(queries.router, prefix="/api/queries", tags=["queries"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["evaluation"])

@app.get("/")
def root():
    return {"message": "RAG Pipeline API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)