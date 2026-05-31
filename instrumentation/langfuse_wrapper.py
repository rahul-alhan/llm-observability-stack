"""Langfuse tracing decorators + context managers."""
from __future__ import annotations

import functools
import hashlib
import os
import time
from contextlib import contextmanager
from typing import Any

from langfuse import Langfuse

from .pricing import cost_usd
from .prom_metrics import (
    llm_cost_usd_total,
    llm_request_latency_s,
    llm_requests_total,
    llm_tool_calls_total,
)

_lf = None


def _client() -> Langfuse:
    global _lf
    if _lf is None:
        _lf = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    return _lf


def _hash_pii(args: dict, fields: tuple[str, ...]) -> dict:
    safe = {}
    for k, v in (args or {}).items():
        if k in fields and isinstance(v, str):
            safe[k] = "sha256:" + hashlib.sha256(v.encode()).hexdigest()[:16]
        else:
            safe[k] = v
    return safe


@contextmanager
def trace_agent_run(user_id: str, session_id: str, prompt_version: str, model: str):
    trace = _client().trace(
        user_id=user_id,
        session_id=session_id,
        metadata={"prompt_version": prompt_version, "model": model},
    )
    start = time.time()
    status = "ok"
    try:
        yield trace
    except Exception:
        status = "error"
        raise
    finally:
        latency = time.time() - start
        llm_request_latency_s.labels(prompt_version=prompt_version).observe(latency)
        llm_requests_total.labels(model=model, prompt_version=prompt_version, status=status).inc()


def record_llm_call(trace, *, model: str, prompt_version: str, prompt: str, completion: str,
                    input_tokens: int, output_tokens: int, latency_s: float, cached: bool = False):
    usd = cost_usd(model, input_tokens, output_tokens)
    llm_cost_usd_total.labels(model=model, prompt_version=prompt_version).inc(usd)
    trace.generation(
        name="llm_call",
        model=model,
        input=prompt,
        output=completion,
        usage={
            "input": input_tokens,
            "output": output_tokens,
            "total_cost": usd,
            "unit": "TOKENS",
        },
        metadata={"prompt_version": prompt_version, "latency_s": latency_s, "cached": cached},
    )


def traced_tool(name: str, sensitive_arg_fields: tuple[str, ...] = ()):
    """Decorator that records tool invocations as spans on the active trace."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            trace = kwargs.pop("_trace", None)
            t0 = time.time()
            status = "ok"
            err = None
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as exc:
                status = "error"
                err = repr(exc)
                raise
            finally:
                llm_tool_calls_total.labels(tool=name, status=status).inc()
                if trace is not None:
                    trace.span(
                        name=f"tool:{name}",
                        input=_hash_pii(kwargs, sensitive_arg_fields),
                        metadata={"latency_s": time.time() - t0, "status": status, "error": err},
                    )
        return wrapper
    return deco
