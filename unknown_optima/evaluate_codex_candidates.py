#!/usr/bin/env python3
"""Evaluate candidates and append public improvement records to the trace."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from domain import (
    coerce_x,
    evaluate_constraints,
    load_config,
    validate_x,
)
from private_objective import objective
from state import (
    append_record,
    load_trace,
    summary_path,
    trace_path,
    write_summary,
)


SCRIPT_DIR = Path(__file__).resolve().parent


def read_json_maybe_fenced(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("candidate response must be a JSON object")
    return payload


def parse_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Accept {"x": [...]} or {"candidates": [{"x": [...]}, ...]}."""
    if "x" in payload:
        return [{"x": coerce_x(payload["x"]), "rationale": payload.get("rationale", "")}]

    if "candidates" not in payload:
        raise ValueError('candidate JSON must contain either "x" or "candidates"')

    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, list):
        raise ValueError('"candidates" must be a JSON array')

    candidates = []
    for index, item in enumerate(raw_candidates):
        if isinstance(item, dict):
            if "x" not in item:
                raise ValueError(f'candidate {index} is missing "x"')
            candidates.append(
                {
                    "x": coerce_x(item["x"]),
                    "rationale": item.get("rationale", ""),
                }
            )
        else:
            candidates.append({"x": coerce_x(item), "rationale": ""})
    return candidates


def candidates_from_args(args: argparse.Namespace) -> list[dict[str, Any]]:
    provided = [args.response is not None, args.x is not None, args.batch is not None]
    if sum(provided) != 1:
        raise SystemExit("provide exactly one of --response, --x, or --batch")

    if args.response is not None:
        return parse_candidates(read_json_maybe_fenced(args.response))

    if args.x is not None:
        return [{"x": coerce_x(json.loads(args.x)), "rationale": ""}]

    raw_batch = json.loads(args.batch)
    if not isinstance(raw_batch, list):
        raise ValueError("--batch must be a JSON array")
    if raw_batch and all(isinstance(value, (int, float)) for value in raw_batch):
        raise ValueError("--batch must contain multiple x arrays or candidate objects")
    return parse_candidates({"candidates": raw_batch})


def best_objective_from_trace(trace: list[dict[str, Any]]) -> float | None:
    best_objective = None
    for record in trace:
        if not record.get("feasible", True):
            continue
        value = objective(record["x"])
        if best_objective is None or value > best_objective:
            best_objective = value
    return best_objective


def evaluate_candidates(
    candidates: list[dict[str, Any]],
    config: dict[str, Any],
    allow_over_budget: bool,
    stop_on_converged: bool,
) -> dict[str, Any]:
    trace_file = trace_path(config["results_dir"])
    summary_file = summary_path(config["results_dir"])
    trace = load_trace(trace_file)

    evaluations = []
    skipped = []
    best_objective = best_objective_from_trace(trace)

    for candidate_index, candidate in enumerate(candidates):
        summary = write_summary(
            summary_file,
            trace,
            config["dimension"],
            config["bounds"],
            config["integer_indices"],
            config["linear_constraint"],
            config["absolute_budget_constraint"],
            config["pairwise_balance_constraint"],
            config["budget"],
            config["tolerance"],
            config["patience"],
            config["min_evaluations"],
        )
        if stop_on_converged and summary["converged"]:
            skipped.append(
                {
                    "candidate_index": candidate_index,
                    "reason": "already converged before this candidate",
                }
            )
            break

        if len(trace) >= config["budget"] and not allow_over_budget:
            skipped.append(
                {
                    "candidate_index": candidate_index,
                    "reason": "budget exhausted",
                }
            )
            break

        x = validate_x(
            candidate["x"],
            config["dimension"],
            config["bounds"],
            config["integer_indices"],
        )

        constraint_result = evaluate_constraints(x, config)
        feasible = constraint_result["feasible"]

        is_initial_best = feasible and best_objective is None
        if feasible:
            y = objective(x)
            raw_improvement = 0.0 if is_initial_best else y - best_objective
            improvement = max(0.0, raw_improvement)
            is_new_best = is_initial_best or raw_improvement > 0.0
        else:
            improvement = 0.0
            is_new_best = False
        if is_new_best:
            best_objective = y

        record = {
            "eval_id": len(trace) + 1,
            "candidate_index": candidate_index,
            "x": x,
            "improvement": improvement,
            "is_new_best": is_new_best,
            "is_initial_best": is_initial_best,
            "feasible": feasible,
            "constraint_values": constraint_result["constraint_values"],
            "constraint_violations": constraint_result["constraint_violations"],
            "total_violation": constraint_result["total_violation"],
            "rationale": candidate.get("rationale", ""),
        }
        append_record(trace_file, record)
        trace.append(record)
        evaluations.append(record)

    summary = write_summary(
        summary_file,
        trace,
        config["dimension"],
        config["bounds"],
        config["integer_indices"],
        config["linear_constraint"],
        config["absolute_budget_constraint"],
        config["pairwise_balance_constraint"],
        config["budget"],
        config["tolerance"],
        config["patience"],
        config["min_evaluations"],
    )
    return {"evaluations": evaluations, "skipped": skipped, "summary": summary}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate and log one or more Codex candidates."
    )
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument(
        "--response",
        type=Path,
        help="Path to Codex response JSON. Markdown fenced JSON is accepted.",
    )
    parser.add_argument("--x", help="Single candidate vector as a JSON list.")
    parser.add_argument(
        "--batch",
        help=(
            "Batch as JSON: either [[x1], [x2]] or "
            '[{"x": [..], "rationale": "..."}, ...].'
        ),
    )
    parser.add_argument(
        "--allow-over-budget",
        action="store_true",
        help="Append evaluations even if the configured budget is exhausted.",
    )
    parser.add_argument(
        "--no-stop-on-converged",
        action="store_true",
        help="Continue through a batch even after the stagnation rule triggers.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        config = load_config(args.config)
        candidates = candidates_from_args(args)
        result = evaluate_candidates(
            candidates,
            config,
            allow_over_budget=args.allow_over_budget,
            stop_on_converged=not args.no_stop_on_converged,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
