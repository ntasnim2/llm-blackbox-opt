#!/usr/bin/env python3
"""Public improvement-query interface for hidden-optimum minimization."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate candidates through the public improvement-only interface."
    )
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument(
        "--response",
        type=Path,
        help="Path to candidate response JSON. Markdown fenced JSON is accepted.",
    )
    parser.add_argument("--x", help="Single candidate vector as a JSON list.")
    parser.add_argument(
        "--batch",
        help=(
            "Batch as JSON: either [[x1], [x2]] or "
            '[{"x": [..], "rationale": "..."}, ...].'
        ),
    )
    return parser.parse_args()


def build_evaluator_command(args: argparse.Namespace) -> list[str]:
    provided = [args.response is not None, args.x is not None, args.batch is not None]
    if sum(provided) != 1:
        raise SystemExit("provide exactly one of --response, --x, or --batch")

    command = [
        sys.executable,
        str(SCRIPT_DIR / "evaluate_codex_candidates.py"),
        "--config",
        str(args.config),
    ]
    if args.response is not None:
        command.extend(["--response", str(args.response)])
    elif args.x is not None:
        command.extend(["--x", args.x])
    else:
        command.extend(["--batch", args.batch])
    return command


def public_evaluation(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "eval_id": record["eval_id"],
        "candidate_index": record["candidate_index"],
        "x": record["x"],
        "improvement": record["improvement"],
        "is_new_best": record["is_new_best"],
        "rationale": record.get("rationale", ""),
    }


def public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "dimension": summary["dimension"],
        "bounds": summary["bounds"],
        "budget": summary["budget"],
        "tolerance": summary["tolerance"],
        "patience": summary["patience"],
        "min_evaluations": summary["min_evaluations"],
        "evaluations": summary["evaluations"],
        "remaining_evaluations": summary["remaining_evaluations"],
        "converged": summary["converged"],
        "stagnation_count": summary["stagnation_count"],
        "last_improvement": summary["last_improvement"],
        "best_x": summary["best_x"],
    }


def make_public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluations": [
            public_evaluation(record) for record in payload.get("evaluations", [])
        ],
        "skipped": payload.get("skipped", []),
        "summary": public_summary(payload["summary"]),
    }


def main() -> None:
    args = parse_args()
    result = subprocess.run(
        build_evaluator_command(args),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)

    payload = json.loads(result.stdout)
    print(json.dumps(make_public_payload(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
