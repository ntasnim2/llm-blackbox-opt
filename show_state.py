#!/usr/bin/env python3
"""Print the current trace and summary for the automated Codex run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domain import load_config
from state import best_record, load_trace, summary_path, trace_path, write_summary


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show automated Codex run state.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument(
        "--last",
        type=int,
        default=10,
        help="Number of most recent trace records to print.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    trace_file = trace_path(config["results_dir"])
    summary_file = summary_path(config["results_dir"])
    trace = load_trace(trace_file)

    summary = write_summary(
        summary_file,
        trace,
        config["dimension"],
        config["bounds"],
        config["budget"],
        config["tolerance"],
    )

    payload = {
        "summary": summary,
        "best_observation": best_record(trace),
        "recent_trace": trace[-args.last :],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
