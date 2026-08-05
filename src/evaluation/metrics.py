import time


class Metrics:
    """
    Utility class for tracking RAG evaluation metrics.
    """

    def __init__(self):
        self.start_time = None

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        if self.start_time is None:
            return 0

        return round((time.perf_counter() - self.start_time) * 1000, 2)

    @staticmethod
    def retrieval_stats(retrieved_docs, reranked_docs):
        return {
            "retrieved_documents": len(retrieved_docs),
            "reranked_documents": len(reranked_docs),
        }

    @staticmethod
    def answer_stats(answer):
        return {
            "answer_length": len(answer),
            "word_count": len(answer.split()),
        }
