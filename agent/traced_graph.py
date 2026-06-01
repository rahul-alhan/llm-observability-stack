"""Minimal LangGraph with full Langfuse + Prometheus tracing.

This is a stripped, instrumented mirror of the moderation graph from
the `langgraph-agentic-pipeline` repo.
"""
from __future__ import annotations

import random
import time
from typing import Annotated, TypedDict
from operator import add

from langgraph.graph import END, START, StateGraph

from instrumentation.langfuse_wrapper import (
    record_llm_call,
    trace_agent_run,
    traced_tool,
)


class State(TypedDict, total=False):
    content: str
    user_id: str
    session_id: str
    prompt_version: str
    retrieved: list[dict]
    classification: str
    confidence: float
    final_decision: str
    audit_log: Annotated[list[dict], add]
    _trace: object  # opaque Langfuse trace handle


# ----- tools -----

@traced_tool("policy_search", sensitive_arg_fields=("query",))
def policy_search(query: str):
    time.sleep(random.uniform(0.05, 0.2))
    return [{"id": "POL-001", "score": 0.92}]


@traced_tool("ip_scan", sensitive_arg_fields=("content",))
def ip_scan(content: str):
    time.sleep(random.uniform(0.05, 0.15))
    return {"trademark_hit": False, "similarity": 0.42}


# ----- nodes -----

def retriever(state: State) -> State:
    trace = state.get("_trace")
    pol = policy_search(query=state["content"][:200], _trace=trace)
    ip = ip_scan(content=state["content"], _trace=trace)
    return {"retrieved": [{"policy": pol, "ip": ip}], "audit_log": [{"node": "retriever"}]}


def analyzer(state: State) -> State:
    trace = state.get("_trace")
    t0 = time.time()
    # Mock an LLM call; in production this is the actual provider call
    prompt = f"Classify: {state['content']}"
    completion = random.choice(["APPROVE", "REJECT", "ESCALATE"])
    input_tokens = max(20, len(prompt) // 4)
    output_tokens = 4
    latency_s = time.time() - t0 + random.uniform(0.3, 0.9)

    if trace is not None:
        record_llm_call(
            trace,
            model="gpt-4o-mini",
            prompt_version=state["prompt_version"],
            prompt=prompt,
            completion=completion,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_s=latency_s,
        )

    confidence = random.uniform(0.55, 0.99)
    return {
        "classification": completion,
        "confidence": confidence,
        "audit_log": [{"node": "analyzer", "label": completion, "confidence": confidence}],
    }


def finalize(state: State) -> State:
    final = state["classification"] if state["confidence"] >= 0.7 else "ESCALATE"
    return {"final_decision": final, "audit_log": [{"node": "finalize", "decision": final}]}


# ----- graph -----

def build_traced_graph():
    g = StateGraph(State)
    g.add_node("retriever", retriever)
    g.add_node("analyzer", analyzer)
    g.add_node("finalize", finalize)
    g.add_edge(START, "retriever")
    g.add_edge("retriever", "analyzer")
    g.add_edge("analyzer", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


def run(content: str, user_id: str, session_id: str, prompt_version: str = "moderation_v1") -> dict:
    model = "gpt-4o-mini"
    graph = build_traced_graph()
    with trace_agent_run(user_id, session_id, prompt_version, model) as trace:
        initial = {
            "content": content,
            "user_id": user_id,
            "session_id": session_id,
            "prompt_version": prompt_version,
            "audit_log": [],
            "_trace": trace,
        }
        return graph.invoke(initial)
