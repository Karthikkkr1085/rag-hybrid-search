from .database import RetrievedDocument, analytics_db

init_db = analytics_db._init_schema
record_query = analytics_db.record_query

__all__ = [
    "RetrievedDocument",
    "analytics_db",
    "init_db",
    "record_query",
]