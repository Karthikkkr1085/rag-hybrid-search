"""FastAPI entry point for synchronous and streaming Hybrid RAG queries."""

import hashlib
import json
import os
import time
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, Field

from src.agents.executor import Executor
from src.agents.planner import Planner
from src.analytics import (  # sqlite-backed analytics store (no new ORM)
    init_db,
    record_query,
)
from src.analytics.database import RetrievedDocument
from src.api.analytics import router as analytics_router
from src.cache.semantic_cache import SemanticCache
from src.generation.generator import Generator
from src.ingestion.build_index import build_index
from src.memory.memory import ConversationMemory
from src.memory.question_rewriter import QuestionRewriter
from src.models.request import QueryRequest, QuerySettings
from src.models.response import QueryResponse
from src.retrieval.hybrid import HybridSearch
from src.retrieval.reranker import Reranker
from src.utils.logging_config import logger

load_dotenv()
logger.info(
    "Environment loaded: GROQ_API_KEY=%s OPENAI_API_KEY=%s",
    bool(os.getenv("GROQ_API_KEY")),
    bool(os.getenv("OPENAI_API_KEY")),
)
DOCUMENTS_DIR = Path("docs").resolve()


class QuerySettings(BaseModel):
    provider: str = "groq"
    model: str | None = None
    top_k: int = Field(default=8, ge=1, le=20)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=64, le=4096)
    enable_cross_encoder: bool = True
    enable_bm25: bool = True
    enable_vector_search: bool = True
    enable_hybrid_search: bool = True
    enable_rrf: bool = True


class ProviderConnectionRequest(BaseModel):
    provider: str = "groq"
    # The API key is no longer supplied by the client. Keys are read from environment variables.
    model: str | None = None


app = FastAPI(title="Hybrid RAG API", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router)
memories: dict[str, ConversationMemory] = {}
generator = Generator()
reranker = Reranker()
semantic_cache = SemanticCache()
planner = Planner()
executor = Executor()
question_rewriter = QuestionRewriter()
# Ensure analytics DB is initialized (safe no-op on repeated calls)
init_db()

with open("data/chunks/chunks.json", encoding="utf-8") as file:
    hybrid = HybridSearch(json.load(file))


def reload_hybrid_index() -> int:
    """Recreate the in-memory BM25 index after an ingestion run."""
    global hybrid
    chunks = build_index()
    hybrid = HybridSearch(chunks)
    return len(chunks)


def get_memory(session_id: str | None) -> ConversationMemory:
    """Return browser-scoped memory; no conversation is shared between visitors."""
    key = session_id or "anonymous"
    return memories.setdefault(key, ConversationMemory(max_messages=10))


def prepare_query(
    request: QueryRequest, session_id: str | None
) -> tuple[str, list, dict, ConversationMemory, str, float, float]:
    """Prepare and run retrieval for a query.

    Returns:
        rewritten query, results (contexts), settings dict, memory object, session_id,
        retrieval_time_ms, rerank_time_ms

    Timings are measured here so the analytics layer can store retrieval and
    rerank durations without changing the retrieval/reranker internals.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    settings = (request.settings or QuerySettings()).model_dump()
    session_id = request.session_id or session_id or "anonymous"
    memory = get_memory(session_id)
    memory.add_user_message(request.question)
    rewritten = question_rewriter.rewrite(
        history=memory.get_history(),
        query=request.question,
        summary=memory.get_summary(),
    )

    # Time the retrieval (BM25/vector/hybrid) portion
    t0 = __import__("time").perf_counter()
    retrieved = hybrid.search(rewritten, settings)
    t1 = __import__("time").perf_counter()
    retrieval_time_ms = (t1 - t0) * 1000.0

    chunk_count = len(retrieved)
    logger.info("Session %s: Retrieved %s chunk(s) for query", session_id, chunk_count)
    logger.info("Session %s: Rewritten query=%s", session_id, rewritten)
    logger.info("Session %s: memory size=%s", session_id, memory.size())

    # Time the reranker if enabled
    if settings["enable_cross_encoder"]:
        t2 = __import__("time").perf_counter()
        results = reranker.rerank(rewritten, retrieved, top_k=settings["top_k"])
        t3 = __import__("time").perf_counter()
        rerank_time_ms = (t3 - t2) * 1000.0
    else:
        results = retrieved[: settings["top_k"]]
        rerank_time_ms = 0.0

    return (
        rewritten,
        results,
        settings,
        memory,
        session_id,
        retrieval_time_ms,
        rerank_time_ms,
    )


@app.get("/settings")
def get_settings():
    """Return frontend defaults without exposing credentials."""
    return QuerySettings().model_dump()


@app.post("/providers/test")
def test_provider_connection(request: ProviderConnectionRequest):
    """Check the provider using the server-side environment API key for that provider.

    The frontend must not send API keys. This endpoint uses the .env-configured key for
    the chosen provider and reports a clear error if the environment variable is missing.
    """
    try:
        return {
            "connected": True,
            **generator.llm.test_connection(request.provider, request.model),
        }
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. The provider rejected the server-side API key.",
        ) from error
    except RateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="This provider has reached its usage limit. Retry later or use another key.",
        ) from error
    except APIConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="Could not reach the provider. Check the provider service and try again.",
        ) from error
    except APIStatusError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail="The provider could not validate this connection.",
        ) from error
    except (ValueError, TypeError) as error:
        # ValueError will include the clear missing-key message we raised in _client
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/documents")
def list_documents():
    """List PDFs available to cite and view."""
    return [
        {"name": path.name, "size": path.stat().st_size}
        for path in sorted(DOCUMENTS_DIR.glob("*.pdf"))
    ]


@app.get("/documents/{filename}")
def get_document(filename: str):
    """Securely serve an indexed PDF; the frontend appends #page=N for navigation."""
    path = (DOCUMENTS_DIR / Path(filename).name).resolve()
    if (
        DOCUMENTS_DIR not in path.parents
        or path.suffix.lower() != ".pdf"
        or not path.is_file()
    ):
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@app.post("/documents/upload", status_code=201)
async def upload_documents(files: list[UploadFile] = File(...)):
    """Persist new PDFs and rebuild the retrieval indexes in the same process."""
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one PDF.")

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    duplicates: list[str] = []
    existing_hashes = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in DOCUMENTS_DIR.glob("*.pdf")
    }
    for upload in files:
        filename = Path(upload.filename or "document.pdf").name
        content = await upload.read()
        if Path(filename).suffix.lower() != ".pdf" or not content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=400, detail=f"{filename} is not a valid PDF."
            )
        digest = hashlib.sha256(content).hexdigest()
        if digest in existing_hashes:
            duplicates.append(filename)
            continue
        target = DOCUMENTS_DIR / filename
        if target.exists():
            target = DOCUMENTS_DIR / f"{target.stem}-{digest[:8]}.pdf"
        target.write_bytes(content)
        existing_hashes.add(digest)
        saved.append(target.name)

    indexed_chunks = reload_hybrid_index() if saved else 0
    return {
        "uploaded": saved,
        "duplicates": duplicates,
        "indexed_chunks": indexed_chunks,
    }


@app.post("/conversation/clear", status_code=204)
def clear_conversation(x_session_id: str | None = Header(default=None)):
    """Clear server-side follow-up context while preserving all settings and documents."""
    get_memory(x_session_id).clear()


@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest, x_session_id: str | None = Header(default=None)):
    logger.info(
        "Received /ask request provider=%s model=%s top_k=%s",
        request.settings.provider if request.settings else "groq",
        request.settings.model if request.settings else None,
        request.settings.top_k if request.settings else None,
    )
    """Backward-compatible non-streaming answer endpoint."""
    try:
        # ---------- Semantic Cache ----------
        cache_hit = semantic_cache.lookup(request.question)

        if cache_hit:
            print("✅ CACHE HIT")

            cache_hit["verified"] = True
            cache_hit["session_id"] = request.session_id or x_session_id or "anonymous"

            return QueryResponse(**cache_hit)

        # ---------- Normal RAG ----------
        (
            query,
            contexts,
            settings,
            memory,
            session_id,
            retrieval_time_ms,
            rerank_time_ms,
        ) = prepare_query(
            request,
            x_session_id,
        )

        # Time the LLM call separately so analytics can store breakdowns
        llm_start = time.perf_counter()
        plan = planner.create_plan(query)

        print("\n========== PLAN ==========")
        print(plan)
        print("==========================")

        response = executor.execute(
            plan=plan,
            generator=generator,
            contexts=contexts,
            settings=settings,
            history=memory.get_recent_history(),
            conversation_summary=memory.get_summary(),
        )
        # ---------- Save to Semantic Cache ----------
        try:
            embedding = semantic_cache.embedding.generate_query_embedding(
                request.question
            )

            semantic_cache.store.insert(
                question=request.question,
                embedding=embedding,
                answer=response["answer"],
            )

            print("💾 Saved to semantic cache")

        except Exception as e:
            print("Semantic cache insert failed:", e)
        llm_end = time.perf_counter()
        llm_time_ms = (llm_end - llm_start) * 1000.0

        total_time_ms = retrieval_time_ms + rerank_time_ms + llm_time_ms

        memory.add_assistant_message(
            response["answer"], citations=response.get("citations", [])
        )
        response["session_id"] = session_id
        response["conversation_summary"] = memory.get_summary()
        logger.info(
            "Session %s: Citation summary: %s",
            session_id,
            response.get("citation_summary"),
        )

        # Build a lightweight list of source documents for analytics
        try:
            source_docs = [
                c.get("metadata", {}).get("source")
                for c in contexts
                if isinstance(c, dict)
            ]
        except Exception:
            source_docs = None

        # Persist analytics (non-blocking best-effort). Errors should not fail the request.
        try:
            record_query(
                session_id=session_id,
                query_text=query,
                provider=settings.get("provider"),
                latency_ms=float(total_time_ms),

                success=True,
                error_message=None,

                confidence_score=response.get("confidence", 1.0),

                num_documents_retrieved=len(contexts),

                answer_length=len(response["answer"]),

                citations_verified=response.get("verified", True),

                retrieved_documents=[
                    RetrievedDocument(
                        document_id=str(i),
                        document_name=context.get("metadata", {}).get("source", "Unknown"),
                        rank=i + 1,
                        relevance_score=context.get("score"),
                    )
                    for i, context in enumerate(contexts)
                    if isinstance(context, dict)
                ],
            )
        except Exception:
            logger.exception("Failed to record analytics entry")

        return QueryResponse(**response)
    except RateLimitError as error:
        provider_name = request.settings.provider if request.settings else "groq"
        detail = (
            f"The API key for provider '{provider_name}' has reached its usage limit."
        )
        raise HTTPException(status_code=429, detail=detail) from error
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            detail="The configured API key was rejected by the provider.",
        ) from error
    except HTTPException:
        raise
    except Exception as error:
        # Attempt to record analytics for failed request
        try:
            record_query(
                session_id=(
                    request.session_id if hasattr(request, "session_id") else None
                )
                or "anonymous",
                query_text=(request.question if hasattr(request, "question") else None)
                or "",
                provider=(request.settings.provider if request.settings else None)
                or "unknown",
                success=False,
                error_message=str(error),
            )
        except Exception:
            logger.exception("Failed to record analytics for failed request")
        logger.exception("RAG request failed")
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@app.post("/ask/stream")
def ask_stream(request: QueryRequest, x_session_id: str | None = Header(default=None)):

    def events() -> Iterator[str]:
        logger.info(
            "Received /ask/stream request provider=%s model=%s top_k=%s",
            request.settings.provider if request.settings else "groq",
            request.settings.model if request.settings else None,
            request.settings.top_k if request.settings else None,
        )

        try:
            # gather retrieval + rerank timings from prepare_query
            (
                query,
                contexts,
                settings,
                memory,
                session_id,
                retrieval_time_ms,
                rerank_time_ms,
            ) = prepare_query(request, x_session_id)

            # Start LLM timer immediately before streaming begins
            llm_start = time.perf_counter()

            plan = planner.create_plan(query)

            print("\n========== PLAN ==========")
            print(plan)
            print("==========================")

            for event in executor.stream(
                plan=plan,
                generator=generator,
                contexts=contexts,
                settings=settings,
                history=memory.get_recent_history(),
                conversation_summary=memory.get_summary(),
            ):

                logger.info(
                    "Session %s: SENDING STREAM EVENT type=%s",
                    session_id,
                    event["type"],
                )

                if event["type"] == "done":
                    # LLM finished; compute timings and persist analytics
                    llm_end = time.perf_counter()
                    llm_time_ms = (llm_end - llm_start) * 1000.0
                    total_time_ms = retrieval_time_ms + rerank_time_ms + llm_time_ms

                    event["session_id"] = session_id
                    event["conversation_summary"] = memory.get_summary()
                    logger.info(
                        "Session %s: Streamed citation summary: %s",
                        session_id,
                        event.get("citation_summary"),
                    )
                    memory.add_assistant_message(
                        event["answer"], citations=event.get("citations", [])
                    )

                    # Persist analytics for the completed stream (best-effort)
                    try:
                        source_docs = [
                            c.get("metadata", {}).get("source")
                            for c in contexts
                            if isinstance(c, dict)
                        ]
                    except Exception:
                        source_docs = None
                    try:
                        record_query(
                            session_id=session_id,
                            query_text=query,
                            provider=settings.get("provider"),
                            latency_ms=float(total_time_ms),

                            success=True,
                            error_message=None,

                            confidence_score=event.get("confidence", 0.0),

                            num_documents_retrieved=len(contexts),

                            retrieved_documents=[
                                RetrievedDocument(
                                    document_id=str(i),
                                    document_name=context.get("metadata", {}).get("source", "Unknown"),
                                    rank=i + 1,
                                    relevance_score=context.get("score"),
                                )
                                for i, context in enumerate(contexts)
                                if isinstance(context, dict)
                            ],
                        )
                    except Exception:
                        logger.exception("Failed to record analytics entry for stream")

                yield (f"event: {event['type']}\n" f"data: {json.dumps(event)}\n\n")

        except Exception:
            logger.exception("Streaming RAG request failed")
            yield (
                "event: error\n"
                'data: {"detail":"Internal Server Error","status":500}\n\n'
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",  # <-- ADD THIS
            "X-Accel-Buffering": "no",
        },
    )