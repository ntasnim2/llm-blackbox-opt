#!/usr/bin/env python3
"""Trace and summary persistence for chemistry optimization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def trace_path(results_dir: Path) -> Path:
    return results_dir / "codex_trace.jsonl"


def summary_path(results_dir: Path) -> Path:
    return results_dir / "codex_summary.json"


def load_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, sort_keys=True)
        f.write("\n")


def best_record(trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    best = None
    for record in trace:
        if record.get("is_new_best"):
            best = record
    return best


def best_error_from_trace(trace: list[dict[str, Any]]) -> float | None:
    best_error = None
    for record in trace:
        if not record.get("valid"):
            continue
        error = float(record["abs_error"])
        if best_error is None or error < best_error:
            best_error = error
    return best_error


def stagnation_count(trace: list[dict[str, Any]], improvement_tolerance: float) -> int:
    count = 0
    for record in reversed(trace):
        if record.get("is_initial_best"):
            break
        if float(record.get("improvement", 0.0)) <= improvement_tolerance:
            count += 1
            continue
        break
    return count


def write_summary(
    path: Path,
    trace: list[dict[str, Any]],
    target_property: str,
    target_value: float,
    budget: int,
    tolerance: float,
    patience: int,
    min_evaluations: int,
) -> dict[str, Any]:
    best = best_record(trace)
    stagnation = stagnation_count(trace, tolerance)
    solved = best is not None and float(best["abs_error"]) <= tolerance
    enough_evaluations = len(trace) >= min_evaluations
    stalled = best is not None and enough_evaluations and stagnation >= patience
    payload = {
        "target_property": target_property,
        "target_value": target_value,
        "budget": budget,
        "tolerance": tolerance,
        "patience": patience,
        "min_evaluations": min_evaluations,
        "evaluations": len(trace),
        "remaining_evaluations": max(0, budget - len(trace)),
        "solved": solved,
        "converged": solved or stalled,
        "stagnation_count": stagnation,
        "last_improvement": None if not trace else float(trace[-1]["improvement"]),
        "best_smiles": None if best is None else best["smiles"],
        "best_canonical_smiles": None if best is None else best["canonical_smiles"],
        "best_predicted_hof": None if best is None else best["predicted_hof"],
        "best_abs_error": None if best is None else best["abs_error"],
        "best_model_disagreement": None
        if best is None
        else best.get("model_disagreement"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return payload

