from chromadb import PersistentClient


class CacheStore:
    """
    Stores and retrieves cached LLM responses.
    """

    def __init__(self):
        self.client = PersistentClient(path="cache_db")

        self.collection = self.client.get_or_create_collection(name="semantic_cache")

    def insert(
        self,
        question: str,
        embedding: list,
        answer: str,
    ):
        self.collection.add(
            ids=[question],
            embeddings=[embedding],
            documents=[answer],
            metadatas=[
                {
                    "question": question,
                }
            ],
        )

    def search(
        self,
        embedding: list,
        threshold: float = 0.80,
    ):
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=1,
        )

        if not results["documents"][0]:
            return None

        distance = results["distances"][0][0]

        # Chroma returns cosine distance.
        similarity = 1 - distance

        print(f"Similarity: {similarity:.3f}")

        if similarity < threshold:
            return None

        return {
            "question": results["metadatas"][0][0]["question"],
            "answer": results["documents"][0][0],
            "similarity": similarity,
        }
