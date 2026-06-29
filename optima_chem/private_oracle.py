#!/usr/bin/env python3
"""Private surrogate oracle for chemistry optimization.

The optimizer-facing session should not inspect this file. Public commands
expose only controlled prediction and error feedback.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np

from predict_hof import featurize_for_artifact


def load_artifact(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        artifact = pickle.load(f)
    if artifact.get("target") != "hof":
        raise ValueError(f"model {path} does not target HoF")
    return artifact


def predict_hof(smiles: str, artifact: dict[str, Any]) -> float:
    features = featurize_for_artifact(smiles, artifact)
    return float(np.asarray(artifact["model"].predict(features))[0])


class HofOracle:
    def __init__(self, primary_model_path: Path, secondary_model_path: Path):
        self.primary_artifact = load_artifact(primary_model_path)
        self.secondary_artifact = load_artifact(secondary_model_path)

    def evaluate(self, smiles: str, target_hof: float) -> dict[str, float]:
        primary = predict_hof(smiles, self.primary_artifact)
        secondary = predict_hof(smiles, self.secondary_artifact)
        return {
            "predicted_hof": primary,
            "secondary_predicted_hof": secondary,
            "model_disagreement": abs(primary - secondary),
            "abs_error": abs(primary - target_hof),
        }

