from datetime import datetime


class AgentTools:
    """
    Tools that can be used by the Executor.
    """

    @staticmethod
    def get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def calculator(expression: str):
        try:
            return str(eval(expression))
        except Exception:
            return "Invalid expression"

    @staticmethod
    def document_statistics(contexts):
        return {
            "chunks": len(contexts),
            "documents": len(
                {c["metadata"]["source"] for c in contexts if "metadata" in c}
            ),
        }
