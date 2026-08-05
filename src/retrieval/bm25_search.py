from rank_bm25 import BM25Okapi


class BM25Search:
    """
    Keyword-based search using BM25.
    """

    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.metadatas = []

    def index_documents(self, chunks):
        """
        Build the BM25 index from document chunks.
        """

        self.documents = [chunk["text"] for chunk in chunks]

        self.metadatas = [
            {
                "source": chunk["source"],
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"],
            }
            for chunk in chunks
        ]

        tokenized_documents = [document.lower().split() for document in self.documents]

        self.bm25 = BM25Okapi(tokenized_documents)

    def search(self, query: str, top_k: int = 5):
        """
        Perform keyword search.
        """

        if self.bm25 is None:
            raise ValueError(
                "BM25 index has not been created. Call index_documents() first."
            )

        tokenized_query = query.lower().split()

        scores = self.bm25.get_scores(tokenized_query)

        ranked_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results = []

        for idx in ranked_indices:
            results.append(
                {
                    "document": self.documents[idx],
                    "metadata": self.metadatas[idx],
                    "score": float(scores[idx]),
                }
            )

        return results
