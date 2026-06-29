#!/usr/bin/env python3
"""Public query interface for chemistry optimizer sessions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument(
        "--response",
        type=Path,
        help="Path to candidate response JSON. Markdown fenced JSON is accepted.",
    )
    parser.add_argument("--smiles", help="Single candidate SMILES.")
    parser.add_argument(
        "--batch",
        help='JSON array of {"smiles": "...", "rationale": "..."} objects.',
    )
    return parser.parse_args()


def build_evaluator_command(args: argparse.Namespace) -> list[str]:
    provided = [
        args.response is not None,
        args.smiles is not None,
        args.batch is not None,
    ]
    if sum(provided) != 1:
        raise SystemExit("provide exactly one of --response, --smiles, or --batch")

    command = [
        sys.executable,
        str(SCRIPT_DIR / "evaluate_codex_candidates.py"),
        "--config",
        str(args.config),
    ]
    if args.response is not None:
        command.extend(["--response", str(args.response)])
    elif args.smiles is not None:
        command.extend(["--smiles", args.smiles])
    else:
        command.extend(["--batch", args.batch])
    return command


def public_evaluation(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "eval_id": record["eval_id"],
        "candidate_index": record["candidate_index"],
        "smiles": record["smiles"],
        "canonical_smiles": record["canonical_smiles"],
        "valid": record["valid"],
        "duplicate": record["duplicate"],
        "rejected_prompt_example": record.get("rejected_prompt_example"),
        "target_hof": record["target_hof"],
        "predicted_hof": record["predicted_hof"],
        "secondary_predicted_hof": record["secondary_predicted_hof"],
        "model_disagreement": record["model_disagreement"],
        "abs_error": record["abs_error"],
        "improvement": record["improvement"],
        "is_new_best": record["is_new_best"],
        "error": record["error"],
        "rationale": record.get("rationale", ""),
    }


def public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_property": summary["target_property"],
        "target_value": summary["target_value"],
        "budget": summary["budget"],
        "tolerance": summary["tolerance"],
        "patience": summary["patience"],
        "min_evaluations": summary["min_evaluations"],
        "evaluations": summary["evaluations"],
        "remaining_evaluations": summary["remaining_evaluations"],
        "solved": summary["solved"],
        "converged": summary["converged"],
        "stagnation_count": summary["stagnation_count"],
        "last_improvement": summary["last_improvement"],
        "best_smiles": summary["best_smiles"],
        "best_canonical_smiles": summary["best_canonical_smiles"],
        "best_predicted_hof": summary["best_predicted_hof"],
        "best_abs_error": summary["best_abs_error"],
        "best_model_disagreement": summary["best_model_disagreement"],
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
