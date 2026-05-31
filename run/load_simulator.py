"""Generate synthetic traffic for dashboards / load testing."""
from __future__ import annotations

import argparse
import random
import uuid

from agent.traced_graph import run
from instrumentation.prom_metrics import start_metrics_server

SAMPLES = [
    "Short story about a detective in 1920s Berlin.",
    "Promotional copy that mimics a registered brand.",
    "Direct copy of copyrighted lyrics.",
    "Generic review of a product.",
    "Aggressive language targeting another user.",
]
PROMPT_VERSIONS = ["moderation_v1", "moderation_v2_candidate"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--users", type=int, default=20)
    args = p.parse_args()

    start_metrics_server()
    user_ids = [f"user_{i:03d}" for i in range(args.users)]
    for i in range(args.n):
        run(
            content=random.choice(SAMPLES),
            user_id=random.choice(user_ids),
            session_id=str(uuid.uuid4()),
            prompt_version=random.choice(PROMPT_VERSIONS),
        )
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{args.n} ...")
    print("Done — check Langfuse + Grafana.")


if __name__ == "__main__":
    main()
