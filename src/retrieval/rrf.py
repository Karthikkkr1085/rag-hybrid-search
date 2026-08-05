class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) for combining
    Vector Search and BM25 results.
    """

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(self, vector_results, bm25_results):
        """
        Fuse ranked lists using Reciprocal Rank Fusion.

        Args:
            vector_results (list): Vector search results
            bm25_results (list): BM25 search results

        Returns:
            list: Fused and ranked results
        """

        fused_scores = {}

        # ----------------------------------------
        # Vector Search Results
        # ----------------------------------------
        for rank, result in enumerate(vector_results, start=1):

            metadata = result["metadata"]

            chunk_id = metadata.get(
                "chunk_id", f"{metadata['source']}_{metadata['page']}"
            )

            if chunk_id not in fused_scores:

                fused_scores[chunk_id] = {
                    "document": result["document"],
                    "metadata": metadata,
                    "score": 0.0,
                }

            fused_scores[chunk_id]["score"] += 1 / (self.k + rank)

        # ----------------------------------------
        # BM25 Results
        # ----------------------------------------
        for rank, result in enumerate(bm25_results, start=1):

            metadata = result["metadata"]

            chunk_id = metadata.get(
                "chunk_id", f"{metadata['source']}_{metadata['page']}"
            )

            if chunk_id not in fused_scores:

                fused_scores[chunk_id] = {
                    "document": result["document"],
                    "metadata": metadata,
                    "score": 0.0,
                }

            fused_scores[chunk_id]["score"] += 1 / (self.k + rank)

        ranked_results = sorted(
            fused_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return ranked_results
