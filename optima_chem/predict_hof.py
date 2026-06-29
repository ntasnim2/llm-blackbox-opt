#!/usr/bin/env python3
"""Predict heat of formation for one SMILES string using a saved surrogate."""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator

from chem_features import clean_descriptor_matrix, descriptor_matrix, mol_from_smiles


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = SCRIPT_DIR / "models" / "hof_extratrees_morgan.pkl"


def morgan_matrix(smiles_values: list[str], radius: int, n_bits: int) -> np.ndarray:
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=radius,
        fpSize=n_bits,
    )
    features = np.zeros((len(smiles_values), n_bits), dtype=np.float32)
    for row_index, smiles in enumerate(smiles_values):
        mol = mol_from_smiles(smiles)
        fingerprint = generator.GetFingerprint(mol)
        DataStructs.ConvertToNumpyArray(fingerprint, features[row_index])
    return features


def featurize_for_artifact(smiles: str, artifact: dict) -> np.ndarray:
    raw_features = descriptor_matrix([smiles])
    descriptor_features, _, _ = clean_descriptor_matrix(
        raw_features,
        artifact["descriptor_names"],
        keep_indices=artifact["keep_indices"],
    )
    if artifact.get("feature_set") != "rdkit_descriptors_plus_morgan":
        return descriptor_features

    morgan_features = morgan_matrix(
        [smiles],
        radius=int(artifact["morgan_radius"]),
        n_bits=int(artifact["morgan_bits"]),
    )
    return np.hstack([descriptor_features, morgan_features])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--smiles", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.model.open("rb") as f:
        artifact = pickle.load(f)

    features = featurize_for_artifact(args.smiles, artifact)
    prediction = float(artifact["model"].predict(features)[0])
    print(
        json.dumps(
            {
                "smiles": args.smiles,
                "target": artifact["target"],
                "predicted_hof": prediction,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
