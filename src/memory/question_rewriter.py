from src.generation.llm import LLM


class QuestionRewriter:
    """
    Rewrites follow-up questions into standalone questions
    using conversation history.
    """

    def __init__(self):
        self.llm = LLM()

    def rewrite(
        self,
        history: list,
        query: str,
        summary: str | None = None,
    ) -> str:
        """
        Rewrite a follow-up question into a standalone question.

        Args:
            history: Conversation history
            query: Current user question

        Returns:
            Standalone rewritten question
        """

        # No history → return original query
        if len(history) <= 1 and not summary:
            return query

        conversation = ""
        if summary:
            conversation += f"Conversation summary:\n{summary}\n\n"

        for message in history[:-1]:
            role = message["role"].capitalize()
            conversation += f"{role}: {message['content']}\n"

        prompt = f"""
You are a query rewriting assistant for a Retrieval-Augmented Generation (RAG) system.

Your task is to rewrite the latest user question into a fully standalone search query using the conversation history.

Rules:

1. Rewrite ONLY if the latest question depends on previous conversation.
2. If the latest question is already complete, return it unchanged.
3. Preserve the user's intent exactly.
4. Do NOT answer the question.
5. Do NOT add information that is not present in the conversation.
6. Preserve ALL policy IDs, document IDs, section numbers, codes, filenames, and alphanumeric identifiers exactly as written.
7. Never remove, rephrase, or modify identifiers such as:
   - CBS/POLICY/004
   - HR-001
   - LeavePolicy.pdf
   - Section 4.2
8. Replace pronouns (it, they, this, that, these, those) only when required to make the question standalone.
9. Keep the rewritten query concise and optimized for document retrieval.
10. Return ONLY the rewritten query without explanations or quotation marks.

Conversation History:
{conversation}

Latest User Question:
{query}

Standalone Query:
"""

        response = self.llm.generate(prompt)

        if isinstance(response, dict):
            rewritten_query = response.get("answer", "").strip()
        else:
            rewritten_query = str(response).strip()
        # Fallback if the LLM returns an empty response
        if not rewritten_query:
            return query

        return rewritten_query
