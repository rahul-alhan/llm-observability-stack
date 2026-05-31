"""SLO burn-rate computations against an exported trace parquet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

SLO_TARGETS = {
    "p95_latency_ms": 4000,
    "tool_success_rate": 0.98,
    "cost_per_request_usd": 0.05,
}


def slo_report(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"empty": True}
    p95 = float(df["latency_ms"].quantile(0.95))
    avg_cost = float(df["total_cost"].mean())
    report = {
        "n_traces": len(df),
        "p95_latency_ms": p95,
        "avg_cost_usd": avg_cost,
        "violations": {
            "latency": p95 > SLO_TARGETS["p95_latency_ms"],
            "cost":    avg_cost > SLO_TARGETS["cost_per_request_usd"],
        },
        "targets": SLO_TARGETS,
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--traces", required=True)
    p.add_argument("--out", default="reports/slo.json")
    args = p.parse_args()

    df = pd.read_parquet(args.traces)
    r = slo_report(df)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(r, indent=2, default=str))
    print(json.dumps(r, indent=2, default=str))


if __name__ == "__main__":
    main()
