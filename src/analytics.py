"""Analytics persistence helper for the Hybrid RAG API.

This module implements a minimal, dependency-free SQLite-backed analytics store using
Python's builtin sqlite3 module. It intentionally avoids introducing any ORM so it
integrates cleanly with the existing project.

Table schema (analytics):
- id INTEGER PRIMARY KEY AUTOINCREMENT
- session_id TEXT NULL -- kept for future auth/workspace compatibility
- query TEXT NOT NULL
- provider TEXT NULL
- model TEXT NULL
- retrieval_time_ms REAL NULL
- rerank_time_ms REAL NULL
- llm_time_ms REAL NULL
- total_time_ms REAL NULL
- input_tokens INTEGER NULL
- output_tokens INTEGER NULL
- total_tokens INTEGER NULL
- retrieved_chunks INTEGER NULL
- source_documents TEXT NULL -- JSON-encoded list
- success INTEGER NOT NULL DEFAULT 1
- error_message TEXT NULL
- created_at TEXT DEFAULT (datetime('now'))

Indexes:
- idx_analytics_provider(provider)
- idx_analytics_model(model)
- idx_analytics_created_at(created_at)

Usage:
- call init_db() at startup (module will lazily create DB on first use)
- call record_query(...) to persist one analytics row

The module is concurrency-conscious: it uses a short-lived sqlite3 connection per
operation and relies on WAL mode for reasonable concurrency in production.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Iterable
from typing import Any

# Location for analytics DB relative to project root. Matches project's data/ layout.
DB_DIR = os.path.join(os.getcwd(), "data", "analytics")
DB_PATH = os.path.join(DB_DIR, "analytics.db")

# DDL for table and indexes. Kept simple and explicit so this module is self-contained.
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    query TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    retrieval_time_ms REAL,
    rerank_time_ms REAL,
    llm_time_ms REAL,
    total_time_ms REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    retrieved_chunks INTEGER,
    source_documents TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

_CREATE_INDEXES_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_analytics_provider ON analytics(provider);",
    "CREATE INDEX IF NOT EXISTS idx_analytics_model ON analytics(model);",
    "CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics(created_at);",
)

# Simple lock to serialize DB initialization so multiple threads/startup tasks don't race.
_init_lock = threading.Lock()
_initialized = False


def _ensure_db_dir_exists() -> None:
    os.makedirs(DB_DIR, exist_ok=True)


def init_db() -> None:
    """Initialize the analytics database and indexes.

    Safe to call multiple times; initialization is idempotent.
    """
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        _ensure_db_dir_exists()
        # Use a short-lived connection for setup
        conn = sqlite3.connect(DB_PATH)
        try:
            # Use WAL for improved concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(_CREATE_TABLE_SQL)
            for idx_sql in _CREATE_INDEXES_SQL:
                conn.execute(idx_sql)
            conn.commit()
            _initialized = True
        finally:
            conn.close()


def _connect() -> sqlite3.Connection:
    """Connect to the analytics DB, ensuring initialization.

    Returns a sqlite3.Connection (caller is responsible for closing it).
    """
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    return conn


def record_query(
    *,
    session_id: str | None,
    query: str,
    provider: str | None = None,
    model: str | None = None,
    retrieval_time_ms: float | None = None,
    rerank_time_ms: float | None = None,
    llm_time_ms: float | None = None,
    total_time_ms: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    retrieved_chunks: int | None = None,
    source_documents: Iterable[Any] | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> int:
    """Persist a single analytics row.

    All timing/token fields are optional because the existing codebase does not
    yet calculate every metric. This function accepts the listed named arguments
    and stores a single row. Returns the inserted row id.
    """
    src_docs_json = None
    if source_documents is not None:
        try:
            src_docs_json = json.dumps(list(source_documents), ensure_ascii=False)
        except Exception:
            # Fallback: coerce to str
            src_docs_json = json.dumps(
                [str(x) for x in source_documents], ensure_ascii=False
            )

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analytics (
                session_id, query, provider, model, retrieval_time_ms, rerank_time_ms,
                llm_time_ms, total_time_ms, input_tokens, output_tokens, total_tokens,
                retrieved_chunks, source_documents, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                query,
                provider,
                model,
                retrieval_time_ms,
                rerank_time_ms,
                llm_time_ms,
                total_time_ms,
                input_tokens,
                output_tokens,
                total_tokens,
                retrieved_chunks,
                src_docs_json,
                1 if success else 0,
                error_message,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# Provide a convenience wrapper to record minimal data quickly.
def record_simple(
    query: str,
    session_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    retrieved_chunks: int | None = None,
    source_documents: list[Any] | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> int:
    """Helper that records a minimal analytics entry.

    Useful for quick instrumentation where timing/token metrics are not yet available.
    """
    return record_query(
        session_id=session_id,
        query=query,
        provider=provider,
        model=model,
        retrieved_chunks=retrieved_chunks,
        source_documents=source_documents,
        success=success,
        error_message=error_message,
    )
