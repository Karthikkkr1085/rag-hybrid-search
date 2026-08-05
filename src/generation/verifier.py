import re


class Verifier:
    """
    Verifies whether the generated answer
    is supported by the retrieved context.
    """

    def __init__(self):
        pass

    def verify(
        self,
        answer: str,
        contexts: list,
    ) -> float:
        """
        Verify whether the generated answer is grounded in the retrieved context.

        Returns a confidence score between 0 and 1.
        """

        if not answer:
            return 0.0

        answer_text = answer.lower()
        context_text = " ".join(
            context["document"].lower() for context in contexts if "document" in context
        )

        answer_words = [
            word for word in re.findall(r"\b\w+\b", answer_text) if len(word) > 3
        ]

        if not answer_words:
            return 0.0

        matched_words = sum(1 for word in answer_words if word in context_text)

        return matched_words / len(answer_words)
