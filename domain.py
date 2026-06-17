#!/usr/bin/env python3
"""Public configuration and validation helpers for Codex-driven optimization."""

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
        "target_y": float(payload.get("target_y", 0.0)),
        "tolerance": float(payload["tolerance"]),
        "results_dir": results_dir,
    }
    validate_domain(
        config["dimension"],
        config["bounds"],
        config["budget"],
        config["target_y"],
        config["tolerance"],
    )
    return config


def validate_domain(
    dimension: int,
    bounds: tuple[float, float],
    budget: int,
    target_y: float,
    tolerance: float,
) -> None:
    lower, upper = bounds
    if dimension < 1:
        raise ValueError("dimension must be >= 1")
    if lower >= upper:
        raise ValueError("lower bound must be less than upper bound")
    if budget < 1:
        raise ValueError("budget must be >= 1")
    if not math.isfinite(target_y):
        raise ValueError("target_y must be finite")
    if tolerance < 0.0:
        raise ValueError("tolerance must be >= 0")


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
