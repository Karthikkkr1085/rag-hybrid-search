import math
import re

from sentence_transformers import CrossEncoder

from src.retrieval.deduplicator import ContextDeduplicator


class Reranker:
    """
    CrossEncoder reranker.
    Re-ranks retrieved documents based on query relevance.

    The CrossEncoder model is lazy-loaded so that FastAPI
    does not load the model during application startup.
    """

    def __init__(self, model_name="BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None
        self.deduplicator = ContextDeduplicator()

    def _get_model(self):
        """
        Load the CrossEncoder only when reranking is actually required.
        """

        if self.model is None:
            print(f"Loading CrossEncoder model: {self.model_name}")

            self.model = CrossEncoder(
                self.model_name,
                device="cpu",
            )

            print("CrossEncoder model loaded.")

        return self.model

    def rerank(self, query: str, results: list, top_k: int = 8):
        """
        Rerank retrieved documents.
        """

        if not results:
            return []

        model = self._get_model()

        pairs = [(query, result["document"]) for result in results]

        scores = model.predict(pairs)

        print("Raw CrossEncoder scores:", scores)

        for result, score in zip(results, scores):
            normalized_score = 1.0 / (1.0 + math.exp(-float(score)))
            result["rerank_score"] = normalized_score
            print("Normalized score:", normalized_score)
            
        reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)

        print("\n========== CROSS ENCODER SCORES ==========\n")

        for i, doc in enumerate(reranked, 1):
            print(
                f"{i}. "
                f"{doc['metadata']['source']} "
                f"(Page {doc['metadata']['page']}) "
                f"Score={doc['rerank_score']:.4f}"
            )

        best_score = reranked[0]["rerank_score"]

        query_lower = query.lower()

        summary_keywords = ["explain", "summary", "summarize", "overview", "describe"]

        if any(keyword in query_lower for keyword in summary_keywords):
            threshold = best_score * 0.65
            top_k = min(top_k, 6)
        else:
            threshold = best_score * 0.55
            top_k = min(top_k, 8)

        print(f"\nThreshold: {threshold:.4f}")

        for doc in reranked:
            print(
                doc["metadata"]["source"], doc["metadata"]["page"], doc["rerank_score"]
            )

        # ---------------------------------------------------------
        # Detect document/policy identifier queries
        # Example: CBS/POLICY/004
        # ---------------------------------------------------------
        doc_id_pattern = r"[A-Za-z]+/[A-Za-z]+/\d+"
        is_document_query = bool(re.search(doc_id_pattern, query))

        # ---------------------------------------------------------
        # Filter documents
        # ---------------------------------------------------------
        if is_document_query:

            top_source = reranked[0]["metadata"]["source"]

            # Keep every retrieved chunk that belongs to the selected document.
            filtered = [
                doc for doc in results if doc["metadata"]["source"] == top_source
            ]
        else:
            filtered = [doc for doc in reranked if doc["rerank_score"] >= threshold]

        # ---------------------------------------------------------
        # Always include Page 1 of the same document
        # ---------------------------------------------------------
        if is_document_query:

            top_source = reranked[0]["metadata"]["source"]

            page1 = next(
                (
                    doc
                    for doc in reranked
                    if (
                        doc["metadata"]["source"] == top_source
                        and doc["metadata"]["page"] == 1
                    )
                ),
                None,
            )

            if page1 and page1 not in filtered:
                filtered.insert(0, page1)

        # ---------------------------------------------------------
        # Ensure at least 3 chunks
        # ---------------------------------------------------------
        if len(filtered) < 3 and not is_document_query:
            filtered = reranked[:3]

        print("\n========== FILTERED DOCUMENTS ==========\n")

        for i, doc in enumerate(filtered, 1):
            print(
                f"{i}. "
                f"{doc['metadata']['source']} "
                f"(Page {doc['metadata']['page']}) "
                f"Score={doc['rerank_score']:.4f}"
            )

        if is_document_query:
            # Remove exact duplicate chunks and preserve document order.
            seen = set()
            unique = []
            for doc in filtered:
                key = (doc["metadata"]["page"], doc["document"])
                if key not in seen:
                    seen.add(key)
                    unique.append(doc)

            unique = self.deduplicator.deduplicate(unique)

            return sorted(
                unique,
                key=lambda doc: (
                    int(doc["metadata"]["page"]),
                    len(doc["document"]),
                ),
            )

        filtered = self.deduplicator.deduplicate(filtered)

        return filtered[:top_k]
