from src.evaluation.logger import EvaluationLogger
from src.evaluation.metrics import Metrics


class Evaluator:
    """
    Evaluates the RAG pipeline by collecting runtime
    and response statistics.
    """

    def __init__(self):
        self.metrics = Metrics()
        self.logger = EvaluationLogger()

    def evaluate(
        self,
        retrieved_docs: list,
        reranked_docs: list,
        answer: str,
        retrieval_time_ms: float,
        generation_time_ms: float,
    ) -> dict:
        """
        Build evaluation metrics for a response.
        """

        retrieval_stats = self.metrics.retrieval_stats(
            retrieved_docs,
            reranked_docs,
        )

        answer_stats = self.metrics.answer_stats(answer)

        result = {
            **retrieval_stats,
            **answer_stats,
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "generation_time_ms": round(generation_time_ms, 2),
            "total_time_ms": round(
                retrieval_time_ms + generation_time_ms,
                2,
            ),

            "confidence_score": round(
                min(
                    1.0,
                    len(reranked_docs) / 5
                ),
                2,
            ),
        }
        self.logger.log(result)

        return result
