#!/usr/bin/env python3
"""Evaluate the toy mixed-integer constrained objective."""

from __future__ import annotations

import argparse
import json
import math
from typing import Any


DIMENSION = 5
INTEGER_INDICES = {0, 1, 2}
BOUNDS = (-8.0, 8.0)
OBJECTIVE_WEIGHTS = [1.4, 1.1, 0.9, 1.3, 1.0]
LINEAR_COEFFICIENTS = [1.0, 2.0, -1.0, 0.5, -1.5]
LINEAR_LOWER = -3.0
LINEAR_UPPER = 3.0
ABSOLUTE_BUDGET_COEFFICIENTS = [0.8, 1.1, 0.7, 1.0, 1.2]
ABSOLUTE_BUDGET_UPPER = 22.0
PAIRWISE_BALANCE_PAIRS = [(0, 3), (1, 4)]
PAIRWISE_BALANCE_UPPER = 6.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the 5D mixed-integer constrained toy objective."
    )
    parser.add_argument(
        "--x",
        required=True,
        help="Candidate vector as a JSON list, e.g. '[1, 2, -3, 0.5, 4.2]'.",
    )
    return parser.parse_args()


def parse_x(raw_x: str) -> list[float | int]:
    try:
        x = json.loads(raw_x)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--x must be valid JSON: {exc}") from exc

    if not isinstance(x, list):
        raise ValueError("--x must be a JSON list")
    if len(x) != DIMENSION:
        raise ValueError(f"expected {DIMENSION} coordinates, got {len(x)}")

    parsed: list[float | int] = []
    lower, upper = BOUNDS
    for index, value in enumerate(x):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"x[{index}] must be a number")
        if not math.isfinite(float(value)):
            raise ValueError(f"x[{index}] must be finite")
        if float(value) < lower or float(value) > upper:
            raise ValueError(f"x[{index}]={value} is outside [{lower}, {upper}]")
        if index in INTEGER_INDICES and not float(value).is_integer():
            one_based_index = index + 1
            raise ValueError(f"x_{one_based_index} must be an integer")
        parsed.append(int(value) if index in INTEGER_INDICES else float(value))

    return parsed


def objective(x: list[float | int]) -> float:
    return sum(weight * float(value) ** 2 for weight, value in zip(OBJECTIVE_WEIGHTS, x))


def linear_constraint_value(x: list[float | int]) -> float:
    return sum(
        coefficient * float(value)
        for coefficient, value in zip(LINEAR_COEFFICIENTS, x)
    )


def linear_constraint_violation(value: float) -> float:
    if value < LINEAR_LOWER:
        return LINEAR_LOWER - value
    if value > LINEAR_UPPER:
        return value - LINEAR_UPPER
    return 0.0


def upper_bound_violation(value: float, upper: float) -> float:
    return max(0.0, value - upper)


def absolute_budget_value(x: list[float | int]) -> float:
    return sum(
        coefficient * abs(float(value))
        for coefficient, value in zip(ABSOLUTE_BUDGET_COEFFICIENTS, x)
    )


def pairwise_balance_value(x: list[float | int]) -> float:
    return sum(
        (float(x[left_index]) - float(x[right_index])) ** 2
        for left_index, right_index in PAIRWISE_BALANCE_PAIRS
    )


def make_payload(x: list[float | int]) -> dict[str, Any]:
    linear_value = linear_constraint_value(x)
    absolute_budget_result = absolute_budget_value(x)
    pairwise_balance_result = pairwise_balance_value(x)
    constraint_values = {
        "linear": linear_value,
        "absolute_budget": absolute_budget_result,
        "pairwise_balance": pairwise_balance_result,
    }
    constraint_violations = {
        "linear": linear_constraint_violation(linear_value),
        "absolute_budget": upper_bound_violation(
            absolute_budget_result, ABSOLUTE_BUDGET_UPPER
        ),
        "pairwise_balance": upper_bound_violation(
            pairwise_balance_result, PAIRWISE_BALANCE_UPPER
        ),
    }
    total_violation = sum(constraint_violations.values())
    return {
        "x": x,
        "objective": objective(x),
        "sense": "maximize",
        "feasible": total_violation == 0.0,
        "bounds": BOUNDS,
        "linear_constraint": {
            "coefficients": LINEAR_COEFFICIENTS,
            "lower": LINEAR_LOWER,
            "upper": LINEAR_UPPER,
        },
        "absolute_budget_constraint": {
            "coefficients": ABSOLUTE_BUDGET_COEFFICIENTS,
            "upper": ABSOLUTE_BUDGET_UPPER,
        },
        "pairwise_balance_constraint": {
            "pairs": PAIRWISE_BALANCE_PAIRS,
            "upper": PAIRWISE_BALANCE_UPPER,
        },
        "constraint_values": constraint_values,
        "constraint_violations": constraint_violations,
        "total_violation": total_violation,
        "integer_variables": ["x_1", "x_2", "x_3"],
        "continuous_variables": ["x_4", "x_5"],
    }


def main() -> None:
    try:
        x = parse_x(parse_args().x)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(make_payload(x), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
