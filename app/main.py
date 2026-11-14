import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from .core import MAX_BYTES, DocumentService, SemanticEmbedder, generate_with_ollama


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: Optional[List[str]] = Field(default=None, max_length=100)
    top_k: int = Field(default=4, ge=1, le=10)
    min_score: float = Field(default=0.30, ge=0, le=1)
    generate: bool = False

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Question cannot be blank.")
        return value.strip()


def create_app(database=None, embedder=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = DocumentService(
            Path(database or os.environ.get("RAG_DATABASE", "data/documents.sqlite3")),
            embedder if embedder is not None else SemanticEmbedder(),
        )
        yield

    app = FastAPI(title="Document Assistant", version="0.1.0", lifespan=lifespan,
                  description="Single-user local prototype. Semantic retrieval with optional local Ollama generation.")

    @app.get('/', include_in_schema=False)
    def index():
        from fastapi.responses import RedirectResponse
        return RedirectResponse('/docs')

    @app.get("/health")
    def health():
        return {"status": "ready", "embedding_model": app.state.service.embedder.name,
                "generation_configured": bool(os.environ.get("OLLAMA_MODEL"))}

    @app.post("/documents", status_code=201)
    async def upload(file: UploadFile = File(...)):
        from starlette.concurrency import run_in_threadpool

        try:
            content = await file.read(MAX_BYTES + 1)
            return await run_in_threadpool(app.state.service.ingest, file.filename or "document.txt", content)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            await file.close()

    @app.get("/documents")
    def list_documents():
        return app.state.service.documents()

    @app.delete("/documents/{document_id}")
    def delete_document(document_id: str):
        if not app.state.service.delete(document_id):
            raise HTTPException(404, "Document not found.")
        return {"deleted": document_id}

    @app.post("/questions")
    def ask(body: Question):
        sources = app.state.service.retrieve(body.question, body.document_ids, body.top_k, body.min_score)
        if not sources:
            return {"mode": "insufficient_evidence", "answer": "No passages met the retrieval threshold. Try another question or document.",
                    "citations": [], "sources": []}
        if not body.generate:
            return {"mode": "retrieval_only", "answer": None, "citations": [], "sources": sources,
                    "message": "These are retrieved passages, not an LLM-generated answer. Set generate=true after configuring Ollama."}
        model = os.environ.get("OLLAMA_MODEL")
        if not model:
            raise HTTPException(503, "Generation is not configured. Set OLLAMA_MODEL or use generate=false.")
        try:
            result = generate_with_ollama(body.question, sources, model, os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(502, "Local model failed or returned invalid output. Retrieved documents are unchanged.") from exc
        return dict(result, mode="generated" if result["citations"] else "insufficient_evidence", sources=sources)

    return app


app = create_app()
