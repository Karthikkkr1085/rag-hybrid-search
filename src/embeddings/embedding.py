from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    Generates embeddings for text chunks using Sentence Transformers.
    """

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def generate_embeddings(self, chunks):
        """
        Generate embeddings for each chunk.

        Args:
            chunks (list): List of chunk dictionaries.

        Returns:
            list: Updated chunks with embeddings.
        """

        texts = [chunk["text"] for chunk in chunks]

        embeddings = self.model.encode(
            texts, convert_to_numpy=True, show_progress_bar=True
        )

        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding.tolist()

        return chunks

    def generate_query_embedding(self, query: str):
        """
        Generate an embedding for a single query.

        Args:
            query (str): User question.

        Returns:
            list: Query embedding.
        """
        embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embedding.tolist()
