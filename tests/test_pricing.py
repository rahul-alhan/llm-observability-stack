"""Smoke tests for pricing + SLO logic — no network."""
from __future__ import annotations

import pandas as pd

from instrumentation.pricing import cost_usd
from metrics.slo import SLO_TARGETS, slo_report


def test_pricing_known_model():
    # 1M tokens of input at $0.15/M = $0.15
    assert abs(cost_usd("gpt-4o-mini", 1_000_000, 0) - 0.15) < 1e-9


def test_pricing_unknown_returns_zero():
    assert cost_usd("nonexistent-model", 1000, 1000) == 0.0


def test_slo_violation_detection():
    df = pd.DataFrame({
        "latency_ms": [100, 200, 300, 5000, 10000],
        "total_cost": [0.01, 0.02, 0.5, 0.5, 0.5],
        "trace_id": [1, 2, 3, 4, 5],
    })
    r = slo_report(df)
    assert r["violations"]["latency"] is True
    assert r["violations"]["cost"] is True
    assert r["targets"] == SLO_TARGETS
