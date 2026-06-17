#!/usr/bin/env python3
"""Configuration and validation helpers for hidden-optimum minimization."""

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

    config = {
        "dimension": int(payload["dimension"]),
        "bounds": (float(bounds_payload[0]), float(bounds_payload[1])),
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
    if config["dimension"] < 1:
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


def coerce_x(raw_x: Any) -> list[float]:
    if not isinstance(raw_x, list):
        raise ValueError('"x" must be a JSON array')
    parsed = []
    for value in raw_x:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("every coordinate must be numeric")
        parsed.append(float(value))
    return parsed


def validate_x(
    x: list[float],
    dimension: int,
    bounds: tuple[float, float],
) -> None:
    if len(x) != dimension:
        raise ValueError(f"expected {dimension} coordinates, got {len(x)}")

    lower, upper = bounds
    for index, value in enumerate(x):
        if not math.isfinite(value):
            raise ValueError(f"x[{index}] must be finite")
        if value < lower or value > upper:
            raise ValueError(f"x[{index}]={value} is outside [{lower}, {upper}]")
