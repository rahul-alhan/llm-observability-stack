"""Pull traces back out of Langfuse → flat parquet for offline analysis."""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from langfuse import Langfuse


def export(since: str, out_path: str, page_size: int = 100):
    lf = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
    from_ts = datetime.fromisoformat(since)
    rows = []
    page = 1
    while True:
        resp = lf.fetch_traces(from_timestamp=from_ts, limit=page_size, page=page)
        if not resp.data:
            break
        for t in resp.data:
            meta = t.metadata or {}
            rows.append({
                "trace_id": t.id,
                "user_id": t.user_id,
                "session_id": t.session_id,
                "timestamp": t.timestamp,
                "prompt_version": meta.get("prompt_version"),
                "model": meta.get("model"),
                "total_tokens": (t.usage or {}).get("total"),
                "total_cost": t.total_cost,
                "latency_ms": t.latency,
            })
        if len(resp.data) < page_size:
            break
        page += 1

    df = pd.DataFrame(rows)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"Exported {len(df):,} traces → {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True, help="ISO date, e.g. 2026-05-01")
    p.add_argument("--out", default="reports/traces.parquet")
    args = p.parse_args()
    export(args.since, args.out)


if __name__ == "__main__":
    main()
