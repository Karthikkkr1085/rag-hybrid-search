import re
from difflib import SequenceMatcher


class ContextDeduplicator:
    """
    Removes duplicate and near-duplicate retrieved chunks.
    """

    def __init__(self, similarity_threshold: float = 0.90):
        self.similarity_threshold = similarity_threshold

    def _normalize(self, text: str) -> str:
        """
        Normalize text before similarity comparison.
        """
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def deduplicate(self, contexts: list[dict]) -> list[dict]:
        """
        Remove duplicate or highly similar chunks while
        preserving reranker order.
        """
        unique = []

        for context in contexts:
            current_text = self._normalize(context["document"])

            is_duplicate = False

            for kept in unique:
                kept_text = self._normalize(kept["document"])

                similarity = SequenceMatcher(
                    None,
                    current_text,
                    kept_text,
                ).ratio()

                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(context)

        print(f"\nDeduplicator: {len(contexts)} → {len(unique)} chunks")

        return unique
