# Hidden-Optimum Codex Optimization Instructions

This directory mirrors the original black-box optimization pipeline, but the
known optimum value is not used by the optimizer-facing interface.

The backend privately evaluates the objective. The public trace stores only:

```text
x
improvement
is_new_best
rationale
```

For minimization:

```text
improvement = max(0, previous_best_hidden_objective - hidden_objective(x))
```

The trace and summary do not contain objective values, error values, target
values, or known optimum values.

## Start Fresh

From this directory:

```bash
python3 reset_run.py
python3 make_codex_controller_prompt.py
```

The generated prompt is written to:

```text
prompts/codex_controller_prompt.txt
```

## Query Candidates

Single candidate:

```bash
python3 query_codex_improvement.py --x '[1.0, -2.0, 3.0]'
```

Batch candidates:

```bash
python3 query_codex_improvement.py --batch '[
  {"x": [1.0, -2.0, 3.0], "rationale": "first point"},
  {"x": [2.0, -2.0, 3.0], "rationale": "coordinate probe"}
]'
```

## Stopping

The run stops when either:

```text
remaining_evaluations == 0
```

or:

```text
stagnation_count >= patience
```

after at least `min_evaluations` have been used. A stagnant evaluation is one
whose improvement is less than or equal to `tolerance`.
