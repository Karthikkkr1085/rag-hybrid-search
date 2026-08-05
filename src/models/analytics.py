"""
src/models/analytics.py

Pydantic response models for the analytics API (src/api/analytics.py).
Field names match the dict keys returned by src/analytics/database.py exactly,
so endpoints can do `Model(**analytics_db.get_x())` with no remapping.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /analytics/overview
# ---------------------------------------------------------------------------

class OverviewResponse(BaseModel):
    period_days: int
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float = Field(..., description="Percentage, 0-100")
    avg_response_time_ms: float
    avg_confidence_score: float = Field(..., description="0.0-1.0")
    total_sessions: int
    total_documents_referenced: int


# ---------------------------------------------------------------------------
# /analytics/providers
# ---------------------------------------------------------------------------

class ProviderStat(BaseModel):
    provider: str
    query_count: int
    avg_latency_ms: float
    avg_confidence_score: float
    success_rate: float


class ProviderStatsResponse(BaseModel):
    providers: list[ProviderStat]


# ---------------------------------------------------------------------------
# /analytics/recent
# ---------------------------------------------------------------------------

class RecentQuery(BaseModel):
    query_id: str
    session_id: str
    timestamp: str
    query_text: str
    provider: str
    latency_ms: float
    confidence_score: Optional[float] = None
    success: bool
    error_message: Optional[str] = None
    num_documents_retrieved: int


class RecentQueriesResponse(BaseModel):
    queries: list[RecentQuery]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# /analytics/documents
# ---------------------------------------------------------------------------

class TopDocument(BaseModel):
    document_id: str
    document_name: str
    retrieval_count: int
    avg_relevance_score: float
    avg_rank: float


class TopDocumentsResponse(BaseModel):
    documents: list[TopDocument]


# ---------------------------------------------------------------------------
# /analytics/performance
# ---------------------------------------------------------------------------

class DailyLatency(BaseModel):
    date: str
    query_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


class LatencyStatsResponse(BaseModel):
    daily: list[DailyLatency]
    overall_avg_latency_ms: float
    overall_p95_latency_ms: float
    overall_p99_latency_ms: float


# ---------------------------------------------------------------------------
# /analytics/confidence
# ---------------------------------------------------------------------------

class DailyConfidence(BaseModel):
    date: str
    avg_confidence_score: float
    min_confidence_score: float
    max_confidence_score: float
    query_count: int


class ConfidenceDistribution(BaseModel):
    low: int = Field(..., description="confidence < 0.5")
    medium: int = Field(..., description="0.5 <= confidence < 0.8")
    high: int = Field(..., description="confidence >= 0.8")


class ConfidenceStatsResponse(BaseModel):
    daily: list[DailyConfidence]
    distribution: ConfidenceDistribution
    overall_avg_confidence_score: float


# ---------------------------------------------------------------------------
# /analytics/sessions
# ---------------------------------------------------------------------------

class TopSession(BaseModel):
    session_id: str
    first_seen: str
    last_seen: str
    query_count: int


class SessionStatsResponse(BaseModel):
    total_sessions: int
    avg_queries_per_session: float
    sessions_today: int
    top_sessions: list[TopSession]


# ---------------------------------------------------------------------------
# Shared query params (used as FastAPI dependencies for consistent docs)
# ---------------------------------------------------------------------------

class DateRangeParams(BaseModel):
    days: int = Field(7, ge=1, le=365, description="Look-back window in days")
