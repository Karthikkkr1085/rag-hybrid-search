from src.agents.planner import Planner

planner = Planner()

questions = [
    "What is leave policy?",
    "Summarize attendance policy",
    "Compare leave policy and attendance policy",
]

for q in questions:
    plan = planner.create_plan(q)

    print("-" * 40)
    print("Question :", q)
    print("Action   :", plan.action)
