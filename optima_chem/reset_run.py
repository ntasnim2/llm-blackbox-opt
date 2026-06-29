#!/usr/bin/env python3
"""Clear chemistry optimization trace and summary."""

from __future__ import annotations

import argparse
from pathlib import Path

from domain import load_config
from state import summary_path, trace_path


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    trace_file = trace_path(config["results_dir"])
    summary_file = summary_path(config["results_dir"])
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    trace_file.write_text("", encoding="utf-8")
    if summary_file.exists():
        summary_file.unlink()
    print(f"Reset {trace_file}")


if __name__ == "__main__":
    main()

