#!/usr/bin/env python3
"""Configuration, candidate parsing, and example selection for chem runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from chem_features import canonicalize_smiles, mol_from_smiles


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")


def resolve_path(raw_path: str, base_dir: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = base_dir / path
    return path


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = path.resolve()
    base_dir = config_path.parent
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    config = {
        "target_property": str(payload.get("target_property", "hof")).lower(),
        "target_value": float(payload["target_value"]),
        "primary_model_path": resolve_path(payload["primary_model_path"], base_dir),
        "secondary_model_path": resolve_path(
            payload["secondary_model_path"],
            base_dir,
        ),
        "data_path": resolve_path(payload["data_path"], base_dir),
        "budget": int(payload["budget"]),
        "tolerance": float(payload["tolerance"]),
        "patience": int(payload["patience"]),
        "min_evaluations": int(payload.get("min_evaluations", 0)),
        "examples_count": int(payload.get("examples_count", 20)),
        "prompt_exclusion_radius": float(
            payload.get("prompt_exclusion_radius", 25.0)
        ),
        "example_label_precision": int(payload.get("example_label_precision", 1)),
        "reject_prompt_examples": bool(payload.get("reject_prompt_examples", True)),
        "results_dir": resolve_path(payload["results_dir"], base_dir),
    }
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config["target_property"] != "hof":
        raise ValueError("only target_property='hof' is supported right now")
    if config["budget"] < 1:
        raise ValueError("budget must be >= 1")
    if config["tolerance"] < 0.0:
        raise ValueError("tolerance must be >= 0")
    if config["patience"] < 1:
        raise ValueError("patience must be >= 1")
    if config["min_evaluations"] < 0:
        raise ValueError("min_evaluations must be >= 0")
    if config["examples_count"] < 4:
        raise ValueError("examples_count must be >= 4")
    if config["prompt_exclusion_radius"] < 0.0:
        raise ValueError("prompt_exclusion_radius must be >= 0")
    if config["example_label_precision"] < 0:
        raise ValueError("example_label_precision must be >= 0")
    if not config["data_path"].exists():
        raise ValueError(f"data file does not exist: {config['data_path']}")
    if not config["primary_model_path"].exists():
        raise ValueError(
            f"primary model does not exist: {config['primary_model_path']}"
        )
    if not config["secondary_model_path"].exists():
        raise ValueError(
            f"secondary model does not exist: {config['secondary_model_path']}"
        )


def coerce_smiles(raw_smiles: Any) -> str:
    if not isinstance(raw_smiles, str):
        raise ValueError('"smiles" must be a string')
    smiles = raw_smiles.strip()
    if not smiles:
        raise ValueError('"smiles" must be non-empty')
    return smiles


def validate_candidate_smiles(smiles: str) -> dict[str, Any]:
    mol = mol_from_smiles(smiles)
    canonical = canonicalize_smiles(smiles)
    return {
        "valid": True,
        "canonical_smiles": canonical,
        "num_atoms": int(mol.GetNumAtoms()),
    }


def load_dataset_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"no rows found in {path}")
    required = {"smiles", "hof", "density"}
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    return rows


def dataset_values_for_prompt(
    rows: list[dict[str, Any]],
    target_value: float,
    count: int,
    exclusion_radius: float = 25.0,
) -> list[dict[str, Any]]:
    """Select informative examples outside a target-centered exclusion band."""
    selected: list[dict[str, Any]] = []
    seen_smiles: set[str] = set()

    def add(row: dict[str, Any], category: str) -> None:
        smiles = row["smiles"]
        if smiles in seen_smiles:
            return
        selected.append(
            {
                "category": category,
                "smiles": smiles,
                "hof": float(row["hof"]),
                "density": float(row["density"]),
                "distance_to_target": abs(float(row["hof"]) - target_value),
            }
        )
        seen_smiles.add(smiles)

    eligible = [
        row
        for row in rows
        if abs(float(row["hof"]) - target_value) >= exclusion_radius
    ]
    if len(eligible) < count:
        raise ValueError(
            "not enough rows outside prompt_exclusion_radius "
            f"{exclusion_radius:g}; found {len(eligible)}, need {count}"
        )

    below = sorted(
        [row for row in eligible if float(row["hof"]) < target_value],
        key=lambda row: float(row["hof"]),
    )
    above = sorted(
        [row for row in eligible if float(row["hof"]) > target_value],
        key=lambda row: float(row["hof"]),
    )
    rows_by_hof = sorted(eligible, key=lambda row: float(row["hof"]))

    below_count = min(len(below), max(1, round(count * 0.4)))
    above_count = min(len(above), max(1, round(count * 0.4)))
    diverse_count = count - below_count - above_count
    if diverse_count < 0:
        diverse_count = 0

    def quantile_rows(candidate_rows: list[dict[str, Any]], target_count: int):
        if target_count <= 0 or not candidate_rows:
            return []
        if target_count == 1:
            return [candidate_rows[len(candidate_rows) // 2]]
        indices = [
            round(index * (len(candidate_rows) - 1) / (target_count - 1))
            for index in range(target_count)
        ]
        return [candidate_rows[index] for index in indices]

    def add_rows(
        candidate_rows: list[dict[str, Any]],
        category: str,
    ) -> None:
        for row in candidate_rows:
            add(row, category)

    add_rows(quantile_rows(below, below_count), "below_target")
    add_rows(quantile_rows(above, above_count), "above_target")
    add_rows(quantile_rows(rows_by_hof, diverse_count), "diverse_hof")

    for row in rows_by_hof:
        if len(selected) >= count:
            break
        add(row, "diverse_fill")

    return selected[:count]


def prompt_example_canonical_smiles(config: dict[str, Any]) -> set[str]:
    rows = load_dataset_rows(config["data_path"])
    examples = dataset_values_for_prompt(
        rows,
        target_value=config["target_value"],
        count=config["examples_count"],
        exclusion_radius=config["prompt_exclusion_radius"],
    )
    return {canonicalize_smiles(example["smiles"]) for example in examples}
