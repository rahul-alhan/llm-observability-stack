"""Token → USD lookup. Keep updated with provider pricing."""
from __future__ import annotations

# Per-1M-token pricing (USD). Update when providers change rates.
PRICING_PER_M = {
    "gpt-4o":          {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":     {"input": 0.15, "output": 0.60},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku":  {"input": 0.80, "output": 4.00},
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICING_PER_M:
        return 0.0
    p = PRICING_PER_M[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
