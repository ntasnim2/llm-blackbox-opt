#!/usr/bin/env python3
"""SMILES validation and descriptor featurization for chemistry surrogates."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors


DESCRIPTOR_NAMES = [name for name, _ in Descriptors.descList]


def mol_from_smiles(smiles: str) -> Chem.Mol:
    """Parse and sanitize a SMILES string."""
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("SMILES must be a non-empty string")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"invalid SMILES: {smiles!r}")
    return mol


def canonicalize_smiles(smiles: str) -> str:
    """Return RDKit canonical SMILES for duplicate detection and storage."""
    return Chem.MolToSmiles(mol_from_smiles(smiles), canonical=True)


def descriptor_vector(smiles: str) -> np.ndarray:
    """Compute raw RDKit descriptor values for one SMILES string."""
    mol = mol_from_smiles(smiles)
    values = []
    for name, fn in Descriptors.descList:
        try:
            value = float(fn(mol))
        except Exception:
            value = math.nan
        if name == "Ipc" and math.isfinite(value):
            value = math.log(value + 1.0)
        values.append(value)
    return np.asarray(values, dtype=float)


def descriptor_matrix(smiles_values: Iterable[str]) -> np.ndarray:
    """Compute RDKit descriptor values for many SMILES strings."""
    rows = [descriptor_vector(smiles) for smiles in smiles_values]
    if not rows:
        return np.empty((0, len(DESCRIPTOR_NAMES)), dtype=float)
    return np.vstack(rows)


def clean_descriptor_matrix(
    features: np.ndarray,
    feature_names: list[str] | None = None,
    keep_indices: list[int] | None = None,
) -> tuple[np.ndarray, list[str], list[int]]:
    """Remove unusable descriptor columns and replace remaining non-finite values.

    During training, call without ``keep_indices`` to learn usable descriptor
    columns. During prediction, pass the saved indices so the feature layout
    exactly matches the trained model.
    """
    if feature_names is None:
        feature_names = DESCRIPTOR_NAMES

    if features.ndim != 2:
        raise ValueError("features must be a 2D array")

    if keep_indices is None:
        finite_columns = np.isfinite(features).all(axis=0)
        nonconstant_columns = np.nanstd(features, axis=0) > 0.0
        keep_mask = finite_columns & nonconstant_columns
        keep_indices = np.flatnonzero(keep_mask).astype(int).tolist()

    cleaned = features[:, keep_indices].astype(float, copy=True)
    cleaned[~np.isfinite(cleaned)] = 0.0
    cleaned_names = [feature_names[index] for index in keep_indices]
    return cleaned, cleaned_names, keep_indices

