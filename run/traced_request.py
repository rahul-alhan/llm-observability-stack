"""Single traced request — useful for smoke-testing the observability hookup."""
from __future__ import annotations

import argparse
import json
import uuid

from agent.traced_graph import run
from instrumentation.prom_metrics import start_metrics_server


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--content", required=True)
    p.add_argument("--user-id", default="user_demo")
    p.add_argument("--prompt-version", default="moderation_v1")
    args = p.parse_args()

    start_metrics_server()
    result = run(args.content, args.user_id, str(uuid.uuid4()), args.prompt_version)
    result.pop("_trace", None)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
