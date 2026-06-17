#!/usr/bin/env python3
"""Trace and summary persistence for automated Codex-driven optimization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def trace_path(results_dir: Path) -> Path:
    return results_dir / "codex_trace.jsonl"


def summary_path(results_dir: Path) -> Path:
    return results_dir / "codex_summary.json"


def ensure_results_dir(results_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)


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
    if not trace:
        return None
    return min(trace, key=lambda record: float(record["error"]))


def write_summary(
    path: Path,
    trace: list[dict[str, Any]],
    dimension: int,
    bounds: tuple[float, float],
    budget: int,
    tolerance: float,
) -> dict[str, Any]:
    best = best_record(trace)
    best_error = None if best is None else float(best["error"])
    solved = best_error is not None and best_error <= tolerance
    payload = {
        "dimension": dimension,
        "bounds": list(bounds),
        "budget": budget,
        "tolerance": tolerance,
        "evaluations": len(trace),
        "remaining_evaluations": max(0, budget - len(trace)),
        "solved": solved,
        "best_error": best_error,
        "best_x": None if best is None else best["x"],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return payload
