#!/usr/bin/env python3
"""Train a random-forest surrogate to predict heat of formation from SMILES."""

from __future__ import annotations

import argparse
import csv
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from chem_features import (
    DESCRIPTOR_NAMES,
    canonicalize_smiles,
    clean_descriptor_matrix,
    descriptor_matrix,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = SCRIPT_DIR / "10k_data_with_ood_splits.csv"
DEFAULT_MODEL = SCRIPT_DIR / "models" / "hof_random_forest.pkl"
DEFAULT_METRICS = SCRIPT_DIR / "models" / "hof_random_forest_metrics.json"


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"no rows found in {path}")

    required = {"smiles", "hof", "hof_train", "hof_iid", "hof_ood"}
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    return rows


def rows_for_split(rows: list[dict[str, Any]], split: str) -> list[dict[str, Any]]:
    if split == "all":
        return rows
    column = {
        "train": "hof_train",
        "iid": "hof_iid",
        "ood": "hof_ood",
    }[split]
    return [row for row in rows if int(row[column]) == 1]


def featurize_rows(
    rows: list[dict[str, Any]],
    keep_indices: list[int] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str], list[int], list[str]]:
    smiles_values = [row["smiles"] for row in rows]
    canonical_smiles = [canonicalize_smiles(smiles) for smiles in smiles_values]
    raw_features = descriptor_matrix(smiles_values)
    features, feature_names, keep_indices = clean_descriptor_matrix(
        raw_features,
        DESCRIPTOR_NAMES,
        keep_indices=keep_indices,
    )
    y = np.asarray([float(row["hof"]) for row in rows], dtype=float)
    return features, y, feature_names, keep_indices, canonical_smiles


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(rmse),
        "r2": float(r2_score(y_true, y_pred)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS)
    parser.add_argument(
        "--train-scope",
        choices=["train", "all"],
        default="train",
        help=(
            "Use BOOM's HoF train split, or all 10k rows for the final "
            "surrogate after validation."
        ),
    )
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--random-state", type=int, default=0)
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Optional quick smoke-test limit before full training.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.data)
    if args.max_rows is not None:
        rows = rows[: args.max_rows]

    train_rows = rows_for_split(rows, args.train_scope)
    if not train_rows:
        raise SystemExit(f"no rows available for train scope {args.train_scope!r}")

    x_train, y_train, feature_names, keep_indices, train_smiles = featurize_rows(
        train_rows
    )

    model = RandomForestRegressor(
        n_estimators=args.n_estimators,
        max_features="sqrt",
        n_jobs=-1,
        random_state=args.random_state,
    )
    model.fit(x_train, y_train)

    metrics: dict[str, Any] = {
        "target": "hof",
        "data": str(args.data),
        "train_scope": args.train_scope,
        "n_estimators": args.n_estimators,
        "random_state": args.random_state,
        "n_features": len(feature_names),
        "n_train": len(train_rows),
        "splits": {},
    }

    for split in ["train", "iid", "ood"]:
        split_rows = rows_for_split(rows, split)
        if not split_rows:
            continue
        x_split, y_split, _, _, _ = featurize_rows(split_rows, keep_indices)
        pred = model.predict(x_split)
        metrics["splits"][split] = {
            "n": len(split_rows),
            **regression_metrics(y_split, pred),
        }

    artifact = {
        "model": model,
        "target": "hof",
        "descriptor_names": DESCRIPTOR_NAMES,
        "feature_names": feature_names,
        "keep_indices": keep_indices,
        "train_scope": args.train_scope,
        "training_smiles": train_smiles,
        "metrics": metrics,
    }

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    with args.model_out.open("wb") as f:
        pickle.dump(artifact, f)

    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    with args.metrics_out.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
        f.write("\n")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    print(f"saved model: {args.model_out}")
    print(f"saved metrics: {args.metrics_out}")


if __name__ == "__main__":
    main()
