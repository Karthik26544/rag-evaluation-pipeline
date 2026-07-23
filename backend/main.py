from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from routers import documents, queries, evaluation

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="RAG Evaluation Pipeline API")

app.state.limiter = limiter

async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please wait 60 seconds and try again.",
            "message": "This demo has usage limits. Please slow down!"
        }
    )

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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