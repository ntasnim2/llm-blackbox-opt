#!/usr/bin/env python3
"""Configuration and validation helpers for unknown-optimum optimization."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = path.resolve()
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    bounds_payload = payload["bounds"]
    results_dir = Path(payload["results_dir"])
    if not results_dir.is_absolute():
        results_dir = config_path.parent / results_dir

    integer_indices = [int(index) for index in payload.get("integer_indices", [])]
    linear_constraint_payload = payload["linear_constraint"]
    absolute_budget_payload = payload["absolute_budget_constraint"]
    pairwise_balance_payload = payload["pairwise_balance_constraint"]
    config = {
        "dimension": int(payload["dimension"]),
        "bounds": (float(bounds_payload[0]), float(bounds_payload[1])),
        "integer_indices": integer_indices,
        "objective_weights": [
            float(value) for value in payload.get("objective_weights", [])
        ],
        "linear_constraint": {
            "coefficients": [
                float(value) for value in linear_constraint_payload["coefficients"]
            ],
            "lower": float(linear_constraint_payload["lower"]),
            "upper": float(linear_constraint_payload["upper"]),
        },
        "absolute_budget_constraint": {
            "coefficients": [
                float(value) for value in absolute_budget_payload["coefficients"]
            ],
            "upper": float(absolute_budget_payload["upper"]),
        },
        "pairwise_balance_constraint": {
            "pairs": [
                [int(pair[0]), int(pair[1])] for pair in pairwise_balance_payload["pairs"]
            ],
            "upper": float(pairwise_balance_payload["upper"]),
        },
        "budget": int(payload["budget"]),
        "tolerance": float(payload["tolerance"]),
        "patience": int(payload["patience"]),
        "min_evaluations": int(payload.get("min_evaluations", 0)),
        "results_dir": results_dir,
    }
    validate_domain(config)
    return config


def validate_domain(config: dict[str, Any]) -> None:
    lower, upper = config["bounds"]
    dimension = config["dimension"]
    if dimension < 1:
        raise ValueError("dimension must be >= 1")
    if lower >= upper:
        raise ValueError("lower bound must be less than upper bound")
    if config["budget"] < 1:
        raise ValueError("budget must be >= 1")
    if config["tolerance"] < 0.0:
        raise ValueError("tolerance must be >= 0")
    if config["patience"] < 1:
        raise ValueError("patience must be >= 1")
    if config["min_evaluations"] < 0:
        raise ValueError("min_evaluations must be >= 0")
    if len(config["objective_weights"]) != dimension:
        raise ValueError("objective_weights must match dimension")
    linear_constraint = config["linear_constraint"]
    if len(linear_constraint["coefficients"]) != dimension:
        raise ValueError("linear constraint coefficients must match dimension")
    if linear_constraint["lower"] > linear_constraint["upper"]:
        raise ValueError("linear constraint lower must be <= upper")
    absolute_budget = config["absolute_budget_constraint"]
    if len(absolute_budget["coefficients"]) != dimension:
        raise ValueError("absolute budget coefficients must match dimension")
    if absolute_budget["upper"] < 0:
        raise ValueError("absolute budget upper must be >= 0")
    pairwise_balance = config["pairwise_balance_constraint"]
    if pairwise_balance["upper"] < 0:
        raise ValueError("pairwise balance upper must be >= 0")
    for pair in pairwise_balance["pairs"]:
        if len(pair) != 2:
            raise ValueError("pairwise balance pairs must have length 2")
        for index in pair:
            if index < 0 or index >= dimension:
                raise ValueError(
                    f"pairwise balance index {index} is outside dimension {dimension}"
                )
    for index in config["integer_indices"]:
        if index < 0 or index >= dimension:
            raise ValueError(f"integer index {index} is outside dimension {dimension}")


def coerce_x(raw_x: Any) -> list[float | int]:
    if not isinstance(raw_x, list):
        raise ValueError('"x" must be a JSON array')
    parsed: list[float | int] = []
    for value in raw_x:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("every coordinate must be numeric")
        parsed.append(value)
    return parsed


def validate_x(
    x: list[float | int],
    dimension: int,
    bounds: tuple[float, float],
    integer_indices: list[int],
) -> list[float | int]:
    if len(x) != dimension:
        raise ValueError(f"expected {dimension} coordinates, got {len(x)}")

    lower, upper = bounds
    integer_index_set = set(integer_indices)
    validated: list[float | int] = []
    for index, value in enumerate(x):
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"x[{index}] must be finite")
        if numeric_value < lower or numeric_value > upper:
            raise ValueError(f"x[{index}]={numeric_value} is outside [{lower}, {upper}]")
        if index in integer_index_set:
            if not numeric_value.is_integer():
                raise ValueError(f"x_{index + 1} must be an integer")
            validated.append(int(numeric_value))
        else:
            validated.append(numeric_value)
    return validated


def linear_constraint_value(
    x: list[float | int], coefficients: list[float]
) -> float:
    return sum(coefficient * float(value) for coefficient, value in zip(coefficients, x))


def linear_constraint_violation(
    value: float,
    lower: float,
    upper: float,
) -> float:
    if value < lower:
        return lower - value
    if value > upper:
        return value - upper
    return 0.0


def upper_bound_violation(value: float, upper: float) -> float:
    return max(0.0, value - upper)


def absolute_budget_value(
    x: list[float | int], coefficients: list[float]
) -> float:
    return sum(
        coefficient * abs(float(value))
        for coefficient, value in zip(coefficients, x)
    )


def pairwise_balance_value(
    x: list[float | int], pairs: list[list[int]]
) -> float:
    return sum(
        (float(x[left_index]) - float(x[right_index])) ** 2
        for left_index, right_index in pairs
    )


def evaluate_constraints(
    x: list[float | int],
    config: dict[str, Any],
) -> dict[str, Any]:
    linear_constraint = config["linear_constraint"]
    linear_value = linear_constraint_value(x, linear_constraint["coefficients"])
    linear_violation = linear_constraint_violation(
        linear_value,
        linear_constraint["lower"],
        linear_constraint["upper"],
    )

    absolute_budget = config["absolute_budget_constraint"]
    absolute_budget_result = absolute_budget_value(
        x, absolute_budget["coefficients"]
    )
    absolute_budget_violation = upper_bound_violation(
        absolute_budget_result,
        absolute_budget["upper"],
    )

    pairwise_balance = config["pairwise_balance_constraint"]
    pairwise_balance_result = pairwise_balance_value(
        x, pairwise_balance["pairs"]
    )
    pairwise_balance_violation = upper_bound_violation(
        pairwise_balance_result,
        pairwise_balance["upper"],
    )

    violations = {
        "linear": linear_violation,
        "absolute_budget": absolute_budget_violation,
        "pairwise_balance": pairwise_balance_violation,
    }
    total_violation = sum(violations.values())
    return {
        "feasible": total_violation == 0.0,
        "constraint_values": {
            "linear": linear_value,
            "absolute_budget": absolute_budget_result,
            "pairwise_balance": pairwise_balance_result,
        },
        "constraint_violations": violations,
        "total_violation": total_violation,
    }
