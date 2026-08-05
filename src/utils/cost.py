# Cost per 1M tokens (update whenever providers change pricing)
MODEL_PRICING = {
    "llama-3.3-70b-versatile": {
        "input": 0.59,
        "output": 0.79,
    },
    "gpt-4.1-mini": {
        "input": 0.40,
        "output": 1.60,
    },
    "gemini-2.5-flash": {
        "input": 0.30,
        "output": 2.50,
    },
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict:
    pricing = MODEL_PRICING.get(model)

    if pricing is None:
        return {
            "estimated_usd": None,
            "currency": "USD",
        }

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    total = input_cost + output_cost

    return {
        "estimated_usd": round(total, 8),
        "currency": "USD",
    }


if __name__ == "__main__":
    result = estimate_cost(
        model="llama-3.3-70b-versatile",
        prompt_tokens=1409,
        completion_tokens=129,
    )

    print(result)
