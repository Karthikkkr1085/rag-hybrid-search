"""
src/api/analytics.py

FastAPI router for the Enterprise Analytics Dashboard.

Mount this in your existing src/api/main.py — see the integration snippet
at the bottom of this file's docstring (and the separate integration notes
provided alongside this file) for the exact two lines to add. This file does
not define its own FastAPI app; it only defines an APIRouter, so it plugs
into your existing app instance without any restructuring.

    from src.api.analytics import router as analytics_router
    app.include_router(analytics_router)
"""

from __future__ import annotations

import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.analytics.database import analytics_db
from src.models.analytics import (
    ConfidenceStatsResponse,
    LatencyStatsResponse,
    OverviewResponse,
    ProviderStat,
    ProviderStatsResponse,
    RecentQueriesResponse,
    RecentQuery,
    SessionStatsResponse,
    TopDocument,
    TopDocumentsResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewResponse)
def get_overview(days: int = Query(7, ge=1, le=365, description="Look-back window in days")) -> OverviewResponse:
    """High-level KPI summary: totals, success rate, avg latency/confidence, sessions."""
    try:
        data = analytics_db.get_overview(days=days)
        return OverviewResponse(**data)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to compute overview: {exc}") from exc


@router.get("/providers", response_model=ProviderStatsResponse)
def get_providers(days: int = Query(7, ge=1, le=365)) -> ProviderStatsResponse:
    """Per-provider (LLM/agent) breakdown: volume, latency, confidence, success rate."""
    try:
        rows = analytics_db.get_provider_stats(days=days)
        return ProviderStatsResponse(providers=[ProviderStat(**r) for r in rows])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute provider stats: {exc}") from exc


@router.get("/recent", response_model=RecentQueriesResponse)
def get_recent(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> RecentQueriesResponse:
    """Most recent queries, newest first, for the live activity table."""
    try:
        rows = analytics_db.get_recent_queries(limit=limit, offset=offset)
        return RecentQueriesResponse(
            queries=[RecentQuery(**r) for r in rows],
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent queries: {exc}") from exc


@router.get("/documents", response_model=TopDocumentsResponse)
def get_top_documents(
    limit: int = Query(10, ge=1, le=100),
    days: int = Query(30, ge=1, le=365),
) -> TopDocumentsResponse:
    """Most frequently retrieved source documents, with average relevance/rank."""
    try:
        rows = analytics_db.get_top_documents(limit=limit, days=days)
        return TopDocumentsResponse(documents=[TopDocument(**r) for r in rows])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch top documents: {exc}") from exc


@router.get("/performance", response_model=LatencyStatsResponse)
def get_performance(days: int = Query(7, ge=1, le=365)) -> LatencyStatsResponse:
    """Daily latency time series plus overall p50/p95/p99 response-time stats."""
    try:
        data = analytics_db.get_latency_stats(days=days)
        return LatencyStatsResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute latency stats: {exc}") from exc


@router.get("/confidence", response_model=ConfidenceStatsResponse)
def get_confidence(days: int = Query(7, ge=1, le=365)) -> ConfidenceStatsResponse:
    """Daily confidence-score trend plus a low/medium/high distribution."""
    try:
        data = analytics_db.get_confidence_stats(days=days)
        return ConfidenceStatsResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute confidence stats: {exc}") from exc


@router.get("/sessions", response_model=SessionStatsResponse)
def get_sessions(days: int = Query(7, ge=1, le=365)) -> SessionStatsResponse:
    """Session-level aggregates: total sessions, avg queries/session, top sessions."""
    try:
        data = analytics_db.get_session_stats(days=days)
        return SessionStatsResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute session stats: {exc}") from exc


@router.get("/export")
def export_queries(days: int = Query(30, ge=1, le=365)) -> StreamingResponse:
    """Download recent query logs as CSV (used by the dashboard's Export button)."""
    try:
        csv_text = analytics_db.export_queries_csv(days=days)
        buffer = io.BytesIO(csv_text.encode("utf-8"))
        filename = f"analytics_export_{days}d.csv"
        return StreamingResponse(
            buffer,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to export queries: {exc}") from exc
