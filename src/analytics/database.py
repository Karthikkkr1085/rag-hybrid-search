"""
src/analytics/database.py

Analytics persistence layer for the Hybrid RAG platform.

ASSUMPTION (please verify against your real code): your project already has a
SQLite database used by the RAG pipeline (conversation memory, documents,
etc.). This module does NOT open a second, unrelated database file — it opens
the SAME database file path via the `ANALYTICS_DB_PATH` setting (which you
should point at your existing SQLite file, e.g. "data/rag.db"), and adds its
own tables to it (`query_logs`, `retrieved_documents`, `analytics_sessions`).
If your existing code exposes a shared connection factory (e.g.
`src.database.get_connection()`), replace `_connect()` below with a call to
that factory so you truly have a single connection story. Everything else in
this file is independent of that detail.

This module has ZERO dependency on FastAPI — it's plain Python + sqlite3, so
it can be unit-tested and reused from scripts, background jobs, etc.
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
import statistics
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Point this at your EXISTING SQLite file. Do not create a second database.
# e.g. if your project already does `sqlite3.connect("data/rag.db")`
# somewhere, use that exact same path here.
ANALYTICS_DB_PATH = os.environ.get("ANALYTICS_DB_PATH", "data/rag.db")
print("=" * 60)
print("Analytics Database:", ANALYTICS_DB_PATH)
print("=" * 60)

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_logs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id                TEXT UNIQUE NOT NULL,
    session_id              TEXT NOT NULL,
    timestamp               TEXT NOT NULL,
    query_text              TEXT NOT NULL,
    provider                TEXT NOT NULL,
    latency_ms              REAL NOT NULL,
    confidence_score        REAL,
    success                 INTEGER NOT NULL DEFAULT 1,
    error_message           TEXT,
    num_documents_retrieved INTEGER NOT NULL DEFAULT 0,
    answer_length           INTEGER,
    citations_verified      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_query_logs_session    ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_provider   ON query_logs(provider);

CREATE TABLE IF NOT EXISTS retrieved_documents (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id           TEXT NOT NULL,
    document_id        TEXT NOT NULL,
    document_name      TEXT NOT NULL,
    rank               INTEGER NOT NULL,
    relevance_score    REAL,
    FOREIGN KEY (query_id) REFERENCES query_logs(query_id)
);

CREATE INDEX IF NOT EXISTS idx_retrieved_docs_query ON retrieved_documents(query_id);
CREATE INDEX IF NOT EXISTS idx_retrieved_docs_doc   ON retrieved_documents(document_id);

CREATE TABLE IF NOT EXISTS analytics_sessions (
    session_id     TEXT PRIMARY KEY,
    first_seen     TEXT NOT NULL,
    last_seen      TEXT NOT NULL,
    query_count    INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass
class RetrievedDocument:
    """One retrieved-document record to log alongside a query."""
    document_id: str
    document_name: str
    rank: int
    relevance_score: float | None = None


class AnalyticsDB:
    """
    Thin, dependency-free wrapper around the analytics tables.

    Usage:
        analytics_db = AnalyticsDB()          # module-level singleton, see bottom of file
        analytics_db.record_query(...)
        analytics_db.get_overview(days=7)
    """

    def __init__(self, db_path: str = ANALYTICS_DB_PATH):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_schema()

    # -- connection handling -------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # -- writes ---------------------------------------------------------------

    def record_query(
        self,
        *,
        session_id: str,
        query_text: str,
        provider: str,
        latency_ms: float,
        confidence_score: float | None = None,
        success: bool = True,
        error_message: str | None = None,
        num_documents_retrieved: int = 0,
        answer_length: int | None = None,
        citations_verified: bool | None = None,
        retrieved_documents: list[RetrievedDocument] | None = None,
        query_id: str | None = None,
        timestamp: str | None = None,
    ) -> str:
        """
        Record one completed query. Call this once, right after your RAG
        pipeline finishes (success or failure) generating a response.

        Returns the query_id (generated if not supplied).
        """
        query_id = query_id or str(uuid.uuid4())
        ts = timestamp or _utcnow_iso()
        print("=" * 60)
        print("record_query() called")
        print("Database:", self.db_path)
        print("Session:", session_id)
        print("Query:", query_text)
        print("=" * 60)
        print("=" * 60)
        print("Analytics Database:", ANALYTICS_DB_PATH)
        print("=" * 60)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO query_logs (
                    query_id,
                    session_id,
                    timestamp,
                    query_text,
                    provider,
                    latency_ms,
                    confidence_score,
                    success,
                    error_message,
                    num_documents_retrieved,
                    answer_length,
                    citations_verified
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    session_id,
                    ts,
                    query_text,
                    provider,
                    latency_ms,
                    confidence_score,
                    1 if success else 0,
                    error_message,
                    num_documents_retrieved,
                    answer_length,
                    None if citations_verified is None else (1 if citations_verified else 0),
                ),
            )

            cursor = conn.execute("SELECT COUNT(*) AS total FROM query_logs")
            print("Rows in query_logs:", cursor.fetchone()["total"])

            if retrieved_documents:
                conn.executemany(
                    """
                    INSERT INTO retrieved_documents
                        (query_id, document_id, document_name, rank, relevance_score)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (query_id, d.document_id, d.document_name, d.rank, d.relevance_score)
                        for d in retrieved_documents
                    ],
                )

            # upsert session row
            conn.execute(
                """
                INSERT INTO analytics_sessions (session_id, first_seen, last_seen, query_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    query_count = query_count + 1
                """,
                (session_id, ts, ts),
            )
            print("record_query() completed successfully")
        return query_id

    # -- reads ------------------------------------------------------------------

    def get_overview(self, days: int = 7) -> dict[str, Any]:
        since = _days_ago_iso(days)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                                   AS total_queries,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successful_queries,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failed_queries,
                    AVG(latency_ms)                            AS avg_latency_ms,
                    AVG(confidence_score)                      AS avg_confidence_score,
                    COUNT(DISTINCT session_id)                 AS total_sessions
                FROM query_logs
                WHERE timestamp >= ?
                """,
                (since,),
            ).fetchone()

            total_docs = conn.execute(
                """
                SELECT COUNT(DISTINCT rd.document_id) AS n
                FROM retrieved_documents rd
                JOIN query_logs q ON q.query_id = rd.query_id
                WHERE q.timestamp >= ?
                """,
                (since,),
            ).fetchone()["n"]

        total = row["total_queries"] or 0
        successful = row["successful_queries"] or 0
        return {
            "period_days": days,
            "total_queries": total,
            "successful_queries": successful,
            "failed_queries": row["failed_queries"] or 0,
            "success_rate": round((successful / total) * 100, 2) if total else 0.0,
            "avg_response_time_ms": round(row["avg_latency_ms"], 2) if row["avg_latency_ms"] is not None else 0.0,
            "avg_confidence_score": round(row["avg_confidence_score"], 4) if row["avg_confidence_score"] is not None else 0.0,
            "total_sessions": row["total_sessions"] or 0,
            "total_documents_referenced": total_docs or 0,
        }

    def get_provider_stats(self, days: int = 7) -> list[dict[str, Any]]:
        since = _days_ago_iso(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    provider,
                    COUNT(*)                                     AS query_count,
                    AVG(latency_ms)                              AS avg_latency_ms,
                    AVG(confidence_score)                        AS avg_confidence_score,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successful_queries
                FROM query_logs
                WHERE timestamp >= ?
                GROUP BY provider
                ORDER BY query_count DESC
                """,
                (since,),
            ).fetchall()

        result = []
        for r in rows:
            count = r["query_count"] or 0
            result.append({
                "provider": r["provider"],
                "query_count": count,
                "avg_latency_ms": round(r["avg_latency_ms"], 2) if r["avg_latency_ms"] is not None else 0.0,
                "avg_confidence_score": round(r["avg_confidence_score"], 4) if r["avg_confidence_score"] is not None else 0.0,
                "success_rate": round((r["successful_queries"] / count) * 100, 2) if count else 0.0,
            })
        return result

    def get_recent_queries(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT query_id, session_id, timestamp, query_text, provider,
                       latency_ms, confidence_score, success, error_message,
                       num_documents_retrieved
                FROM query_logs
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        return [
            {
                "query_id": r["query_id"],
                "session_id": r["session_id"],
                "timestamp": r["timestamp"],
                "query_text": r["query_text"],
                "provider": r["provider"],
                "latency_ms": r["latency_ms"],
                "confidence_score": r["confidence_score"],
                "success": bool(r["success"]),
                "error_message": r["error_message"],
                "num_documents_retrieved": r["num_documents_retrieved"],
            }
            for r in rows
        ]

    def get_top_documents(self, limit: int = 10, days: int = 30) -> list[dict[str, Any]]:
        since = _days_ago_iso(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    rd.document_id,
                    rd.document_name,
                    COUNT(*)               AS retrieval_count,
                    AVG(rd.relevance_score) AS avg_relevance_score,
                    AVG(rd.rank)             AS avg_rank
                FROM retrieved_documents rd
                JOIN query_logs q ON q.query_id = rd.query_id
                WHERE q.timestamp >= ?
                GROUP BY rd.document_id, rd.document_name
                ORDER BY retrieval_count DESC
                LIMIT ?
                """,
                (since, limit),
            ).fetchall()

        return [
            {
                "document_id": r["document_id"],
                "document_name": r["document_name"],
                "retrieval_count": r["retrieval_count"],
                "avg_relevance_score": round(r["avg_relevance_score"], 4) if r["avg_relevance_score"] is not None else 0.0,
                "avg_rank": round(r["avg_rank"], 2) if r["avg_rank"] is not None else 0.0,
            }
            for r in rows
        ]

    def get_latency_stats(self, days: int = 7) -> dict[str, Any]:
        since = _days_ago_iso(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT substr(timestamp, 1, 10) AS day, latency_ms
                FROM query_logs
                WHERE timestamp >= ?
                ORDER BY day ASC
                """,
                (since,),
            ).fetchall()

        buckets: dict[str, list[float]] = {}
        for r in rows:
            buckets.setdefault(r["day"], []).append(r["latency_ms"])

        def _percentile(values: list[float], pct: float) -> float:
            if not values:
                return 0.0
            values = sorted(values)
            k = (len(values) - 1) * pct
            f = int(k)
            c = min(f + 1, len(values) - 1)
            if f == c:
                return round(values[f], 2)
            return round(values[f] + (values[c] - values[f]) * (k - f), 2)

        daily = [
            {
                "date": day,
                "query_count": len(values),
                "avg_latency_ms": round(statistics.mean(values), 2),
                "p50_latency_ms": _percentile(values, 0.50),
                "p95_latency_ms": _percentile(values, 0.95),
                "p99_latency_ms": _percentile(values, 0.99),
            }
            for day, values in sorted(buckets.items())
        ]

        all_values = [v for values in buckets.values() for v in values]
        return {
            "daily": daily,
            "overall_avg_latency_ms": round(statistics.mean(all_values), 2) if all_values else 0.0,
            "overall_p95_latency_ms": _percentile(all_values, 0.95),
            "overall_p99_latency_ms": _percentile(all_values, 0.99),
        }

    def get_confidence_stats(self, days: int = 7) -> dict[str, Any]:
        since = _days_ago_iso(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT substr(timestamp, 1, 10) AS day, confidence_score
                FROM query_logs
                WHERE timestamp >= ? AND confidence_score IS NOT NULL
                ORDER BY day ASC
                """,
                (since,),
            ).fetchall()

        buckets: dict[str, list[float]] = {}
        all_scores: list[float] = []
        for r in rows:
            buckets.setdefault(r["day"], []).append(r["confidence_score"])
            all_scores.append(r["confidence_score"])

        daily = [
            {
                "date": day,
                "avg_confidence_score": round(statistics.mean(values), 4),
                "min_confidence_score": round(min(values), 4),
                "max_confidence_score": round(max(values), 4),
                "query_count": len(values),
            }
            for day, values in sorted(buckets.items())
        ]

        distribution = {
            "low": sum(1 for s in all_scores if s < 0.5),
            "medium": sum(1 for s in all_scores if 0.5 <= s < 0.8),
            "high": sum(1 for s in all_scores if s >= 0.8),
        }

        return {
            "daily": daily,
            "distribution": distribution,
            "overall_avg_confidence_score": round(statistics.mean(all_scores), 4) if all_scores else 0.0,
        }

    def get_session_stats(self, days: int = 7) -> dict[str, Any]:
        since = _days_ago_iso(days)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)          AS total_sessions,
                    AVG(query_count)  AS avg_queries_per_session,
                    SUM(query_count)  AS total_queries
                FROM analytics_sessions
                WHERE last_seen >= ?
                """,
                (since,),
            ).fetchone()

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sessions_today = conn.execute(
                "SELECT COUNT(*) AS n FROM analytics_sessions WHERE substr(last_seen, 1, 10) = ?",
                (today,),
            ).fetchone()["n"]

            top_sessions = conn.execute(
                """
                SELECT session_id, first_seen, last_seen, query_count
                FROM analytics_sessions
                WHERE last_seen >= ?
                ORDER BY query_count DESC
                LIMIT 5
                """,
                (since,),
            ).fetchall()

        return {
            "total_sessions": row["total_sessions"] or 0,
            "avg_queries_per_session": round(row["avg_queries_per_session"], 2) if row["avg_queries_per_session"] is not None else 0.0,
            "sessions_today": sessions_today or 0,
            "top_sessions": [
                {
                    "session_id": r["session_id"],
                    "first_seen": r["first_seen"],
                    "last_seen": r["last_seen"],
                    "query_count": r["query_count"],
                }
                for r in top_sessions
            ],
        }

    def export_queries_csv(self, days: int = 30) -> str:
        """Return recent query logs as a CSV string for the /analytics/export endpoint."""
        since = _days_ago_iso(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT query_id, session_id, timestamp, query_text, provider,
                       latency_ms, confidence_score, success, error_message,
                       num_documents_retrieved, answer_length, citations_verified
                FROM query_logs
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                """,
                (since,),
            ).fetchall()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "query_id", "session_id", "timestamp", "query_text", "provider",
            "latency_ms", "confidence_score", "success", "error_message",
            "num_documents_retrieved", "answer_length", "citations_verified",
        ])
        for r in rows:
            writer.writerow([
                r["query_id"], r["session_id"], r["timestamp"], r["query_text"],
                r["provider"], r["latency_ms"], r["confidence_score"], bool(r["success"]),
                r["error_message"], r["num_documents_retrieved"], r["answer_length"],
                None if r["citations_verified"] is None else bool(r["citations_verified"]),
            ])
        return buffer.getvalue()


# Module-level singleton — import this from src/api/analytics.py and from
# your RAG pipeline, so everyone shares one AnalyticsDB instance / connection story.
analytics_db = AnalyticsDB()
