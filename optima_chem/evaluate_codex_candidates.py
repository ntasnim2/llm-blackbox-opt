#!/usr/bin/env python3
"""Evaluate generated SMILES and append public records to the chem trace."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from domain import (
    coerce_smiles,
    load_config,
    prompt_example_canonical_smiles,
    validate_candidate_smiles,
)
from private_oracle import HofOracle
from state import (
    append_record,
    best_error_from_trace,
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
    """Accept {"smiles": "..."} or {"candidates": [{"smiles": "..."}]}."""
    if "smiles" in payload:
        return [
            {
                "smiles": coerce_smiles(payload["smiles"]),
                "rationale": payload.get("rationale", ""),
            }
        ]

    if "candidates" not in payload:
        raise ValueError('candidate JSON must contain either "smiles" or "candidates"')

    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, list):
        raise ValueError('"candidates" must be a JSON array')

    candidates = []
    for index, item in enumerate(raw_candidates):
        if not isinstance(item, dict):
            raise ValueError(f"candidate {index} must be a JSON object")
        if "smiles" not in item:
            raise ValueError(f'candidate {index} is missing "smiles"')
        candidates.append(
            {
                "smiles": coerce_smiles(item["smiles"]),
                "rationale": item.get("rationale", ""),
            }
        )
    return candidates


def candidates_from_args(args: argparse.Namespace) -> list[dict[str, Any]]:
    provided = [
        args.response is not None,
        args.smiles is not None,
        args.batch is not None,
    ]
    if sum(provided) != 1:
        raise SystemExit("provide exactly one of --response, --smiles, or --batch")

    if args.response is not None:
        return parse_candidates(read_json_maybe_fenced(args.response))
    if args.smiles is not None:
        return [{"smiles": coerce_smiles(args.smiles), "rationale": ""}]
    raw_batch = json.loads(args.batch)
    return parse_candidates({"candidates": raw_batch})


def evaluate_candidates(
    candidates: list[dict[str, Any]],
    config: dict[str, Any],
    allow_over_budget: bool,
    stop_on_converged: bool,
) -> dict[str, Any]:
    trace_file = trace_path(config["results_dir"])
    summary_file = summary_path(config["results_dir"])
    trace = load_trace(trace_file)
    oracle = HofOracle(config["primary_model_path"], config["secondary_model_path"])

    evaluations = []
    skipped = []
    best_error = best_error_from_trace(trace)
    rejected_prompt_examples = (
        prompt_example_canonical_smiles(config)
        if config["reject_prompt_examples"]
        else set()
    )
    seen_canonical = {
        record["canonical_smiles"]
        for record in trace
        if record.get("canonical_smiles")
    }

    for candidate_index, candidate in enumerate(candidates):
        summary = write_summary(
            summary_file,
            trace,
            config["target_property"],
            config["target_value"],
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

        smiles = candidate["smiles"]
        base_record: dict[str, Any] = {
            "eval_id": len(trace) + 1,
            "candidate_index": candidate_index,
            "smiles": smiles,
            "target_hof": config["target_value"],
            "rationale": candidate.get("rationale", ""),
        }
        try:
            validation = validate_candidate_smiles(smiles)
            duplicate = validation["canonical_smiles"] in seen_canonical
            rejected_prompt_example = (
                validation["canonical_smiles"] in rejected_prompt_examples
            )
            if rejected_prompt_example:
                record = {
                    **base_record,
                    **validation,
                    "valid": False,
                    "duplicate": duplicate,
                    "rejected_prompt_example": True,
                    "predicted_hof": None,
                    "secondary_predicted_hof": None,
                    "model_disagreement": None,
                    "abs_error": None,
                    "improvement": 0.0,
                    "is_new_best": False,
                    "is_initial_best": False,
                    "error": "candidate is an exact prompt example",
                }
            else:
                oracle_result = oracle.evaluate(smiles, config["target_value"])
                is_initial_best = best_error is None
                raw_improvement = (
                    0.0
                    if is_initial_best
                    else best_error - float(oracle_result["abs_error"])
                )
                improvement = max(0.0, raw_improvement)
                is_new_best = is_initial_best or raw_improvement > 0.0
                if is_new_best:
                    best_error = float(oracle_result["abs_error"])

                record = {
                    **base_record,
                    **validation,
                    **oracle_result,
                    "duplicate": duplicate,
                    "rejected_prompt_example": False,
                    "improvement": improvement,
                    "is_new_best": is_new_best,
                    "is_initial_best": is_initial_best,
                    "error": None,
                }
            seen_canonical.add(validation["canonical_smiles"])
        except ValueError as exc:
            record = {
                **base_record,
                "valid": False,
                "canonical_smiles": None,
                "num_atoms": None,
                "duplicate": False,
                "rejected_prompt_example": None,
                "predicted_hof": None,
                "secondary_predicted_hof": None,
                "model_disagreement": None,
                "abs_error": None,
                "improvement": 0.0,
                "is_new_best": False,
                "is_initial_best": False,
                "error": str(exc),
            }

        append_record(trace_file, record)
        trace.append(record)
        evaluations.append(record)

    summary = write_summary(
        summary_file,
        trace,
        config["target_property"],
        config["target_value"],
        config["budget"],
        config["tolerance"],
        config["patience"],
        config["min_evaluations"],
    )
    return {"evaluations": evaluations, "skipped": skipped, "summary": summary}


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
    parser.add_argument("--allow-over-budget", action="store_true")
    parser.add_argument("--no-stop-on-converged", action="store_true")
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
