"""Prometheus counters / histograms — SLO-grade telemetry."""
from __future__ import annotations

import os
import threading

from prometheus_client import Counter, Histogram, start_http_server

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "prompt_version", "status"],
)
llm_request_latency_s = Histogram(
    "llm_request_latency_seconds",
    "End-to-end agent request latency",
    ["prompt_version"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16),
)
llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Cumulative LLM cost in USD",
    ["model", "prompt_version"],
)
llm_tool_calls_total = Counter(
    "llm_tool_calls_total",
    "Tool invocations",
    ["tool", "status"],
)

_server_started = False
_lock = threading.Lock()


def start_metrics_server(port: int | None = None) -> None:
    global _server_started
    with _lock:
        if _server_started:
            return
        start_http_server(int(port or os.getenv("PROM_METRICS_PORT", "9100")))
        _server_started = True
