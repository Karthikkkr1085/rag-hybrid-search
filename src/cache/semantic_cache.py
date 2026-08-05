from src.cache.cache_store import CacheStore
from src.embeddings.embedding import EmbeddingGenerator


class SemanticCache:

    def __init__(self):
        self.embedding = EmbeddingGenerator()
        self.store = CacheStore()

    def lookup(self, question: str):
        """
        Look for a semantically similar question in the cache.
        """

        embedding = self.embedding.generate_query_embedding(question)

        print("Question:", question)
        print("Embedding created.")

        result = self.store.search(embedding)

        if result:
            print(f"✅ CACHE HIT ({result['similarity']:.3f})")
            return {
                "answer": result["answer"],
                "citations": [],
                "verified": True,
                "citation_summary": {
                    "valid": 0,
                    "invalid": 0,
                    "coverage": 100,
                    "confidence_level": "High",
                },
                "retrieval_confidence": result["similarity"],
                "citation_confidence": 1.0,
                "confidence": result["similarity"],
            }

        print("❌ CACHE MISS")
        return None
