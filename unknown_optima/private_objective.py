#!/usr/bin/env python3
"""Private objective used by the local unknown-optimum evaluator.

The optimizing Codex session should not read or import this file. The public
interface reports only incumbent improvement, not the raw objective value.
"""

from __future__ import annotations


OBJECTIVE_WEIGHTS = [1.4, 1.1, 0.9, 1.3, 1.0]


def objective(x: list[float | int]) -> float:
    """Return the weighted square utility for the private maximization problem."""
    if len(x) != len(OBJECTIVE_WEIGHTS):
        raise ValueError(f"expected {len(OBJECTIVE_WEIGHTS)} coordinates, got {len(x)}")
    return sum(weight * float(value) ** 2 for weight, value in zip(OBJECTIVE_WEIGHTS, x))
