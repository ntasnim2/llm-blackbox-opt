#!/usr/bin/env python3
"""Trace and summary persistence for hidden-optimum minimization."""

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


def stagnation_count(trace: list[dict[str, Any]], tolerance: float) -> int:
    count = 0
    for record in reversed(trace):
        if record.get("is_initial_best"):
            break
        if float(record["improvement"]) <= tolerance:
            count += 1
            continue
        break
    return count


def write_summary(
    path: Path,
    trace: list[dict[str, Any]],
    dimension: int,
    bounds: tuple[float, float],
    budget: int,
    tolerance: float,
    patience: int,
    min_evaluations: int,
) -> dict[str, Any]:
    best = best_record(trace)
    stagnation = stagnation_count(trace, tolerance)
    enough_evaluations = len(trace) >= min_evaluations
    converged = best is not None and enough_evaluations and stagnation >= patience
    payload = {
        "dimension": dimension,
        "bounds": list(bounds),
        "budget": budget,
        "tolerance": tolerance,
        "patience": patience,
        "min_evaluations": min_evaluations,
        "evaluations": len(trace),
        "remaining_evaluations": max(0, budget - len(trace)),
        "converged": converged,
        "stagnation_count": stagnation,
        "last_improvement": None if not trace else float(trace[-1]["improvement"]),
        "best_x": None if best is None else best["x"],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return payload
