# Chemistry Codex Optimization Instructions

This directory contains a chemistry variant of the black-box sequential
optimization pipeline. The optimizer proposes SMILES strings and receives
public feedback from private HoF surrogate models.

## Start Fresh

From this directory:

```bash
conda run -n research python reset_run.py
conda run -n research python make_codex_controller_prompt.py
```

The generated prompt is written to:

```text
prompts/codex_controller_prompt.txt
```

## Query Candidates

Single candidate:

```bash
conda run -n research python query_codex_chem.py --smiles 'CCO'
```

Batch candidates:

```bash
conda run -n research python query_codex_chem.py --batch '[
  {"smiles": "CCO", "rationale": "small oxygenated baseline"},
  {"smiles": "c1ccccc1", "rationale": "aromatic hydrocarbon comparison"}
]'
```

## Public Feedback

The trace stores SMILES validity, canonical SMILES, predicted HoF, secondary
prediction, model disagreement, absolute target error, incumbent improvement,
and best-incumbent flags. The model artifacts and evaluator implementation are
private to the benchmark controller.

