#!/usr/bin/env python3
"""Print current chemistry optimization state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domain import load_config
from state import best_record, load_trace, summary_path, trace_path, write_summary


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument("--last", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    trace = load_trace(trace_path(config["results_dir"]))
    summary = write_summary(
        summary_path(config["results_dir"]),
        trace,
        config["target_property"],
        config["target_value"],
        config["budget"],
        config["tolerance"],
        config["patience"],
        config["min_evaluations"],
    )
    payload = {
        "summary": summary,
        "best_observation": best_record(trace),
        "recent_trace": trace[-args.last :],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

