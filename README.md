# LLM Observability Stack — Langfuse Tracing for Agentic Pipelines

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=rahul-alhan/llm-observability-stack&branch=main&mainModule=dashboards/cohort_drilldown.py)
[![ci](https://github.com/rahul-alhan/llm-observability-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/rahul-alhan/llm-observability-stack/actions/workflows/ci.yml)

Production-grade **LLM observability** — wraps a LangGraph agent with **Langfuse** tracing and ships dashboards for token cost, p95 latency, tool-call success rate, and prompt-version A/B comparisons.

> Designed to bolt directly onto [`langgraph-agentic-pipeline`](https://github.com/rahul-alhan/langgraph-agentic-pipeline) — same graph, now fully observable.

**Try the cohort drilldown without cloning** → click **Open in Streamlit** above to deploy `dashboards/cohort_drilldown.py` to your free Streamlit Cloud account in one step.

---

## Why This Repo Exists

My [`llm-evaluation-harness`](https://github.com/rahul-alhan/llm-evaluation-harness) covers **offline** eval — RAGAS metrics, gates, prompt registry. But once a pipeline ships, the questions shift:

- Why is p95 latency 4× p50?
- Which prompt version is causing the cost spike?
- Tool X is silently failing 3% of the time — for whom?
- Is the model regressing on a *specific* user cohort?

This repo answers those with **Langfuse** for the tracing backend, **Prometheus** for the SLO-style metrics, and **Streamlit** for the cohort drilldown.

---

## Architecture

```
   user request
        │
        ▼
   ┌──────────────────┐     trace + spans     ┌──────────────────┐
   │ LangGraph agent  │ ────────────────────▶ │   Langfuse SDK   │
   │  (instrumented)  │   token usage         │  (or self-host)  │
   └──────────────────┘   tool calls          └──────────────────┘
        │  prompt version                              │
        │  user_id / session_id                        │
        ▼                                              ▼
   ┌──────────────────┐                       langfuse_export.py
   │ Prometheus expo  │                              │
   │  /metrics        │                              ▼
   └──────────────────┘                       dashboards/cohort_drilldown.py
        │                                     (Streamlit)
        ▼
   Grafana dashboards
   (latency / cost / errors / SLO burn)
```

---

## Quickstart

```bash
pip install -r requirements.txt

# Option A: Langfuse Cloud (free tier)
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com

# Option B: self-host Langfuse (docker-compose included)
docker compose -f deploy/langfuse-compose.yml up -d
export LANGFUSE_HOST=http://localhost:3000

# Run a traced request through the agent
export OPENAI_API_KEY=sk-...
python -m run.traced_request --content "Sample creator submission"

# Generate synthetic traffic for a few hundred traces
python -m run.load_simulator --n 200

# Pull traces back out for offline analysis
python -m exporters.langfuse_export --since 2026-05-01 --out reports/traces.parquet

# Launch the cohort drilldown
streamlit run dashboards/cohort_drilldown.py

# Scrape Prometheus metrics
curl http://localhost:9100/metrics | grep llm_
```

---

## Running Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

---

## What Gets Traced

For every agent run, the wrapper emits:

| Span | Captures |
|---|---|
| **Trace (root)** | `user_id`, `session_id`, `prompt_version`, `model_id`, total tokens, total cost, total latency |
| **LLM call span** | input tokens, output tokens, latency, cached?, finish reason |
| **Tool call span** | tool name, args (hashed if PII), latency, success/error, retry count |
| **Retrieval span** | query, top-k doc IDs, retrieval latency, retrieval source |
| **Guardrail span** | rule triggered, confidence band, escalation decision |

Each level adds metadata that the dashboards filter by.

---

## SLOs Tracked

| SLO | Target | Why |
|---|---|---|
| **End-to-end p95 latency** | < 4s | user-perceived latency for chat surfaces |
| **Tool-call success rate** | > 98% | failed tool calls degrade silently otherwise |
| **Cost per request** | < $0.05 | runaway prompts are the #1 cost incident |
| **Hallucination rate** | < 5% | sampled offline check on traced outputs |
| **Burn rate** | < 1× over 7d | error-budget style alerting |

`metrics/slo.py` computes burn rate against rolling windows; Prometheus alerts can be wired to PagerDuty.

---

## Prompt-Version A/B Comparison

Every trace carries a `prompt_version` attribute (sourced from the prompt registry in `llm-evaluation-harness`). The dashboard's **A/B view** lets you compare:

- Tokens per request (input + output)
- p50 / p95 latency
- Cost per request
- Tool-call success rate
- User-cohort-weighted quality (paired with offline RAGAS scores)

This is how you graduate "the new prompt feels better" into a measurable launch decision.

---

## Repository Layout

```
llm-observability-stack/
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── .env.example
├── instrumentation/
│   ├── __init__.py
│   ├── langfuse_wrapper.py       # decorators + context managers
│   ├── prom_metrics.py           # Prometheus counters/histograms
│   └── pricing.py                # token → USD lookup
├── agent/
│   └── traced_graph.py           # instrumented version of the LangGraph from the agentic-pipeline repo
├── run/
│   ├── traced_request.py         # single request
│   └── load_simulator.py         # synthetic traffic
├── exporters/
│   └── langfuse_export.py        # pull traces → parquet
├── metrics/
│   └── slo.py                    # burn-rate computations
├── dashboards/
│   └── cohort_drilldown.py       # Streamlit cohort + A/B explorer
├── deploy/
│   └── langfuse-compose.yml
└── tests/
    └── test_pricing.py
```

---

## Design Choices

| Decision | Rationale |
|---|---|
| **Langfuse over LangSmith** | Self-hostable; OSS; richer cost tracking |
| **Span-level tool tracing** | Tool failures are the #1 silent failure mode; you can't fix what you can't see |
| **Hashed args for sensitive tools** | Compliance-friendly tracing — never log raw PII |
| **Prom + Langfuse together** | Langfuse for traces / debugging; Prom for SLO alerts (different audiences, different cardinality) |
| **Sampling** | 100% trace at <1k QPS; switch to 10% + always-trace-errors at scale |

### Production notes

- **PII in traces.** Langfuse receives raw prompt + completion text. If user content contains PII, either run Langfuse self-hosted in your VPC or pre-hash sensitive segments before `record_llm_call`.

---

## License

MIT
