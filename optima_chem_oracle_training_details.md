# Optima Chem Oracle Training Details

This document records how the two HoF surrogate oracles in `optima_chem` were
trained.

## Dataset

Source file:

```text
optima_chem/10k_data_with_ood_splits.csv
```

Rows:

```text
10206 molecules
```

Relevant columns:

```text
smiles
density
hof
density_score
hof_score
density_ood
density_train
density_iid
hof_ood
hof_train
hof_iid
```

Target used for both oracles:

```text
hof
```

Both final oracle artifacts were trained using the full 10k dataset, not just
the BOOM HoF train split. Because of this, reported train/IID/OOD metrics for
the final full-data models should be interpreted as in-sample diagnostics, not
held-out generalization estimates.

## Shared Feature Code

Feature and SMILES utilities live in:

```text
optima_chem/chem_features.py
optima_chem/predict_hof.py
```

The feature pipeline validates SMILES with RDKit and computes RDKit molecular
descriptors. The `Ipc` descriptor is log-transformed as:

```text
log(Ipc + 1)
```

Descriptor columns with non-finite values or zero variance during training are
removed. The retained descriptor indices are saved in the model artifact so
prediction uses the same feature layout.

## Oracle 1: Random Forest + RDKit Descriptors

Training script:

```text
optima_chem/train_hof_surrogate.py
```

Model:

```text
sklearn.ensemble.RandomForestRegressor
```

Features:

```text
RDKit molecular descriptors only
```

Default model parameters:

```text
n_estimators = 500
max_features = "sqrt"
n_jobs = -1
random_state = 0
```

Final full-data training command:

```bash
conda run -n research python3 optima_chem/train_hof_surrogate.py --train-scope all
```

Saved artifacts:

```text
optima_chem/models/hof_random_forest.pkl
optima_chem/models/hof_random_forest_metrics.json
```

Observed full-data metrics:

```json
{
  "n_features": 197,
  "n_train": 10206,
  "splits": {
    "train": {
      "mae": 5.549382965554498,
      "rmse": 7.886180978369179,
      "r2": 0.989118443551959,
      "n": 8783
    },
    "iid": {
      "mae": 5.364213472758946,
      "rmse": 7.72162175215194,
      "r2": 0.9905844754817215,
      "n": 423
    },
    "ood": {
      "mae": 14.379219056826711,
      "rmse": 20.138025740303892,
      "r2": 0.992271878636019,
      "n": 1000
    }
  }
}
```

Earlier held-out train-split run, before training on all rows:

```json
{
  "train_scope": "train",
  "n_train": 8783,
  "iid": {
    "mae": 16.173668494680058,
    "rmse": 24.232633024004063,
    "r2": 0.9072682016342889
  },
  "ood": {
    "mae": 105.50562241773542,
    "rmse": 138.97763651691685,
    "r2": 0.6319303621709047
  },
  "train": {
    "mae": 6.139880008176443,
    "rmse": 8.746704105991572,
    "r2": 0.986614135934271
  }
}
```

The random forest artifact is used as the secondary oracle in the optimization
pipeline to estimate model disagreement.

## Oracle 2: ExtraTrees + RDKit Descriptors + Morgan Fingerprints

Training script:

```text
optima_chem/train_hof_extratrees_morgan.py
```

Model:

```text
sklearn.ensemble.ExtraTreesRegressor
```

Features:

```text
RDKit molecular descriptors
Morgan fingerprint bits
```

Morgan fingerprint settings:

```text
radius = 2
n_bits = 2048
```

Default model parameters:

```text
n_estimators = 1000
max_features = "sqrt"
min_samples_leaf = 1
n_jobs = -1
random_state = 0
```

Final training command used:

```bash
conda run -n research python3 optima_chem/train_hof_extratrees_morgan.py --n-estimators 500
```

Saved artifacts:

```text
optima_chem/models/hof_extratrees_morgan.pkl
optima_chem/models/hof_extratrees_morgan_metrics.json
```

Observed full-data training metrics:

```json
{
  "model_type": "ExtraTreesRegressor",
  "feature_set": "rdkit_descriptors_plus_morgan",
  "n_estimators": 500,
  "max_features": "sqrt",
  "min_samples_leaf": 1,
  "morgan_radius": 2,
  "morgan_bits": 2048,
  "n_descriptor_features": 197,
  "n_morgan_features": 2048,
  "n_features": 2245,
  "n_train": 10206,
  "train_metrics": {
    "mae": 3.2507981781613143e-06,
    "rmse": 0.00020735844818930155,
    "r2": 0.9999999999963228
  }
}
```

This model nearly memorizes the full 10k training set. That is acceptable for
the current surrogate-oracle setup, but it should not be treated as evidence of
generalization to novel generated SMILES.

The ExtraTrees artifact is used as the primary oracle in the optimization
pipeline.

## Oracle Use In Optimization

The chemistry evaluator loads both artifacts:

```text
primary_model_path = models/hof_extratrees_morgan.pkl
secondary_model_path = models/hof_random_forest.pkl
```

For each valid candidate SMILES:

```text
primary_predicted_hof = ExtraTrees prediction
secondary_predicted_hof = Random Forest prediction
model_disagreement = abs(primary_predicted_hof - secondary_predicted_hof)
abs_error = abs(primary_predicted_hof - target_hof)
```

The optimization objective uses the primary prediction:

```text
minimize abs_error
```

The secondary model is reported as a sanity-check signal only.

## Environment

Training and verification commands were run with:

```bash
conda run -n research python ...
```

The `research` environment has the required packages:

```text
scikit-learn
rdkit
deepchem
numpy
```

The final pipeline no longer depends on BOOM package imports for training or
prediction. It loads the local CSV directly from `optima_chem`.

