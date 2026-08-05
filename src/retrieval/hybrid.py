import os

from src.retrieval.bm25_search import BM25Search
from src.retrieval.rrf import ReciprocalRankFusion
from src.retrieval.vector_search import VectorSearch


class HybridSearch:
    """
    Hybrid Search using:
    - Vector Search
    - BM25
    - Reciprocal Rank Fusion (RRF)
    """

    def __init__(self, chunks, top_k: int | None = None):
        """Create a hybrid index with an optional result-limit override."""
        self.vector_top_k = top_k or int(os.getenv("VECTOR_TOP_K", 10))
        self.bm25_top_k = top_k or int(os.getenv("BM25_TOP_K", 10))
        self.fusion_top_k = top_k or int(os.getenv("FUSION_TOP_K", 12))

        self.vector_search = VectorSearch(top_k=self.vector_top_k)

        self.bm25_search = BM25Search()
        self.bm25_search.index_documents(chunks)

        self.rrf = ReciprocalRankFusion()

    def search(self, query, settings: dict | None = None):
        settings = settings or {}
        top_k = max(1, min(int(settings.get("top_k", self.fusion_top_k)), 20))
        use_vector = settings.get("enable_vector_search", True)
        use_bm25 = settings.get("enable_bm25", True)
        use_hybrid = settings.get("enable_hybrid_search", True)
        use_rrf = settings.get("enable_rrf", True)

        print("\n================ VECTOR SEARCH ================\n")

        vector_results = self.vector_search.search(query) if use_vector else []
        for i, doc in enumerate(vector_results, 1):

            print(
                f"{i}. "
                f"{doc['metadata']['source']} | "
                f"Page {doc['metadata']['page']}"
            )

            if "score" in doc:
                print(f"Vector Score : {doc['score']}")

            print(doc["document"][:250])
            print("-" * 80)

        print("\n================ BM25 SEARCH ================\n")

        bm25_results = (
            self.bm25_search.search(query, top_k=self.bm25_top_k) if use_bm25 else []
        )

        for i, doc in enumerate(bm25_results, 1):

            print(
                f"{i}. "
                f"{doc['metadata']['source']} | "
                f"Page {doc['metadata']['page']}"
            )

            if "score" in doc:
                print(f"BM25 Score : {doc['score']}")

            print(doc["document"][:250])
            print("-" * 80)

        if not use_hybrid:
            fused_results = vector_results if use_vector else bm25_results
        elif use_rrf:
            fused_results = self.rrf.fuse(vector_results, bm25_results)
        else:
            fused_results = vector_results + bm25_results

        print("\n================ RRF RESULTS ================\n")

        for i, doc in enumerate(fused_results, 1):

            print(
                f"{i}. "
                f"{doc['metadata']['source']} | "
                f"Page {doc['metadata']['page']}"
            )

            if "score" in doc:
                print(f"RRF Score : {doc['score']}")

            print(doc["document"][:250])
            print("-" * 80)

        return fused_results[:top_k]
