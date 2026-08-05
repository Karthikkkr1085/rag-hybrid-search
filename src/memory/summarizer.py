from collections.abc import Iterable

from src.generation.llm import LLM


class MemorySummarizer:
    """
    Summarizes older conversation turns for short-term memory retention.
    """

    def __init__(self):
        self.llm = LLM()

    def summarize(self, existing_summary: str, removed_messages: Iterable[dict]) -> str:
        removed_text = "\n".join(
            f"{message['role'].capitalize()}: {message['content']}"
            for message in removed_messages
        ).strip()

        if not removed_text:
            return existing_summary or ""

        prompt = f"""
You are a memory summarization assistant for a conversational retrieval application.

Your task is to condense older conversation turns into a short summary that preserves:
- important facts and policy details,
- user preferences and instructions,
- cited documents and referenced pages,
- the meaning of the conversation.

Do not invent new facts.
Do not repeat the same details verbatim unless they are essential.
Do not include the latest user question or assistant response; summarize only the older removed turns.

Existing summary:
{existing_summary or 'None'}

Removed conversation:
{removed_text}

Return a concise summary that can be used to maintain context for follow-up questions.
"""

        summary = self.llm.generate(prompt).strip()
        if not summary:
            return existing_summary or ""
        return summary
