from sentence_transformers import SentenceTransformer

from src.vectordb.chroma_store import ChromaStore


class VectorSearch:
    """
    Semantic search using ChromaDB.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
    ):
        self.top_k = top_k
        self.embedder = SentenceTransformer(embedding_model)

        self.store = ChromaStore()
        self.collection = self.store.collection

    def search(self, query: str):
        """
        Perform semantic vector search.

        Args:
            query (str): User question.

        Returns:
            list: List of retrieved documents.
        """

        # Generate query embedding
        query_embedding = self.embedder.encode(query, convert_to_numpy=True).tolist()

        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        formatted_results = []

        for document, metadata, distance in zip(documents, metadatas, distances):
            formatted_results.append(
                {"document": document, "metadata": metadata, "score": float(distance)}
            )

        return formatted_results
