from dataclasses import dataclass


@dataclass
class Plan:
    action: str
    query: str


class Planner:
    """
    Decide how the user's query should be handled.
    """

    def create_plan(self, query: str) -> Plan:
        q = query.lower().strip()

        # Compare
        if any(
            word in q
            for word in [
                "compare",
                "difference",
                "differences",
                "vs",
                "versus",
            ]
        ):
            return Plan("compare", query)

        # Summarize
        if any(
            word in q
            for word in [
                "summary",
                "summarize",
                "overview",
                "brief",
            ]
        ):
            return Plan("summarize", query)

        # List
        if any(
            word in q
            for word in [
                "list",
                "show all",
                "display all",
            ]
        ):
            return Plan("list", query)

        # Tool: Time
        if "time" in q:
            return Plan("tool_time", query)

        # Tool: Calculator
        if "calculate" in q:
            return Plan("tool_calculator", query)

        # Tool: Statistics
        if any(
            word in q
            for word in [
                "statistics",
                "stats",
            ]
        ):
            return Plan("tool_stats", query)

        # Document retrieval
        if any(
            word in q
            for word in [
                "policy",
                "leave",
                "attendance",
                "salary",
                "holiday",
                "working hours",
            ]
        ):
            return Plan("retrieve", query)

        # Default
        return Plan("retrieve", query)
