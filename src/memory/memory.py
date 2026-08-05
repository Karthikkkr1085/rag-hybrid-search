from collections import deque
from datetime import datetime
from typing import Any

from src.memory.summarizer import MemorySummarizer
from src.utils.logging_config import logger


class ConversationMemory:
    """
    Stores conversation history and a rolling summary for a chat session.
    """

    def __init__(self, max_messages: int = 12, max_tokens: int = 800):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.history = deque()
        self.summary = ""
        self.total_tokens = 0
        self.summarizer = MemorySummarizer()

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _count_tokens(self, text: str) -> int:
        return max(1, len(text.strip().split()))

    def _append(
        self, role: str, content: str, citations: list[dict[str, Any]] | None = None
    ) -> None:
        timestamp = self._now()
        tokens = self._count_tokens(content)
        self.history.append(
            {
                "role": role,
                "content": content,
                "citations": citations or [],
                "timestamp": timestamp,
                "tokens": tokens,
            }
        )
        self.total_tokens += tokens
        self._compact_history()

    def add_user_message(self, message: str) -> None:
        """
        Add a user message to memory.
        """
        self._append("user", message)

    def add_assistant_message(
        self, message: str, citations: list[dict[str, Any]] | None = None
    ) -> None:
        """
        Add an assistant message and its citations to memory.
        """
        self._append("assistant", message, citations=citations)

    def get_history(self) -> list[dict[str, Any]]:
        """
        Return the full retained conversation history.
        """
        return list(self.history)

    def get_recent_history(self, max_entries: int = 6) -> list[dict[str, Any]]:
        """
        Return the most recent history entries for prompt construction.
        """
        return list(self.history)[-max_entries:]

    def get_summary(self) -> str:
        """
        Return the current conversation summary.
        """
        return self.summary

    def clear(self) -> None:
        """
        Clear the conversation history and summary.
        """
        self.history.clear()
        self.summary = ""
        self.total_tokens = 0

    def is_empty(self) -> bool:
        """
        Check if memory is empty.
        """
        return len(self.history) == 0

    def _compact_history(self) -> None:
        """
        Trim old history and summarize removed turns when memory limits are exceeded.
        """
        if (
            len(self.history) <= self.max_messages
            and self.total_tokens <= self.max_tokens
        ):
            return

        removed: list[dict[str, Any]] = []
        while self.history and (
            len(self.history) > self.max_messages or self.total_tokens > self.max_tokens
        ):
            oldest = self.history.popleft()
            removed.append(oldest)
            self.total_tokens -= oldest["tokens"]

        if removed:
            logger.info(
                "Memory compacting %s old messages; summary size before=%s tokens",
                len(removed),
                len(self.summary.split()),
            )
            self.summary = self.summarizer.summarize(self.summary, removed)
            logger.info(
                "Memory summary updated; new length=%s tokens",
                len(self.summary.split()),
            )

    def size(self) -> dict[str, int]:
        """
        Return current memory statistics.
        """
        return {
            "messages": len(self.history),
            "tokens": self.total_tokens,
            "summary_tokens": len(self.summary.split()),
        }
