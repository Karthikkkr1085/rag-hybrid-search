from src.agents.planner import Plan
from src.agents.tools import AgentTools


class Executor:

    def execute(
        self,
        plan: Plan,
        generator,
        contexts,
        settings,
        history=None,
        conversation_summary=None,
    ):

        print(f"Executing plan: {plan.action}")

        query = plan.query

        if plan.action == "summarize":
            query = f"Summarize:\n{plan.query}"

        elif plan.action == "compare":
            query = f"Compare:\n{plan.query}"

        elif plan.action == "list":
            query = f"List all relevant information:\n{plan.query}"

        elif plan.action == "tool_time":
            return {
                "answer": AgentTools.get_current_time(),
                "verified": True,
                "citations": [],
                "citation_summary": {},
                "retrieval_confidence": 1.0,
                "citation_confidence": 1.0,
                "confidence": 1.0,
            }

        elif plan.action == "tool_calculator":

            expression = plan.query.lower().replace("calculate", "").strip()

            return {
                "answer": AgentTools.calculator(expression),
                "verified": True,
                "citations": [],
                "citation_summary": {},
                "retrieval_confidence": 1.0,
                "citation_confidence": 1.0,
                "confidence": 1.0,
            }

        elif plan.action == "tool_stats":

            stats = AgentTools.document_statistics(contexts)

            return {
                "answer": (
                    f"Indexed Documents: {stats['documents']}\n"
                    f"Retrieved Chunks: {stats['chunks']}"
                ),
                "verified": True,
                "citations": [],
                "citation_summary": {},
                "retrieval_confidence": 1.0,
                "citation_confidence": 1.0,
                "confidence": 1.0,
            }

        return generator.generate(
            query=query,
            contexts=contexts,
            settings=settings,
            history=history,
            conversation_summary=conversation_summary,
        )

    def stream(
        self,
        plan: Plan,
        generator,
        contexts,
        settings,
        history=None,
        conversation_summary=None,
    ):

        print(f"Executing stream plan: {plan.action}")

        # ---------- TOOLS ----------
        if plan.action == "tool_time":
            yield {
                "type": "done",
                "answer": AgentTools.get_current_time(),
                "verified": True,
                "citations": [],
                "citation_summary": {},
                "retrieval_confidence": 1.0,
                "citation_confidence": 1.0,
                "confidence": 1.0,
            }
            return

        if plan.action == "tool_calculator":
            expression = plan.query.lower().replace("calculate", "").strip()

            yield {
                "type": "done",
                "answer": AgentTools.calculator(expression),
                "verified": True,
                "citations": [],
                "citation_summary": {},
                "retrieval_confidence": 1.0,
                "citation_confidence": 1.0,
                "confidence": 1.0,
            }
            return

        if plan.action == "tool_stats":
            stats = AgentTools.document_statistics(contexts)

            yield {
                "type": "done",
                "answer": (
                    f"Indexed Documents: {stats['documents']}\n"
                    f"Retrieved Chunks: {stats['chunks']}"
                ),
                "verified": True,
                "citations": [],
                "citation_summary": {},
                "retrieval_confidence": 1.0,
                "citation_confidence": 1.0,
                "confidence": 1.0,
            }
            return

        # ---------- NORMAL RAG ----------
        query = plan.query

        if plan.action == "summarize":
            query = f"Summarize:\n{plan.query}"

        elif plan.action == "compare":
            query = f"Compare:\n{plan.query}"

        elif plan.action == "list":
            query = f"List all relevant information:\n{plan.query}"

        yield from generator.stream(
            query=query,
            contexts=contexts,
            settings=settings,
            history=history,
            conversation_summary=conversation_summary,
        )
