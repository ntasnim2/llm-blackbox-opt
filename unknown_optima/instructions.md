# Unknown-Optimum Codex Optimization Instructions

This directory mirrors the parent black-box optimization pipeline, but the
public signal is incumbent improvement rather than error to a known optimum.
The hidden objective is a weighted square utility, and candidates must satisfy
public feasibility constraints.

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
python3 query_codex_improvement.py --x '[1, 2, -3, 0.5, 4.2]'
```

Batch candidates:

```bash
python3 query_codex_improvement.py --batch '[
  {"x": [1, 2, -3, 0.5, 4.2], "rationale": "first point"},
  {"x": [2, 2, -3, 0.5, 4.2], "rationale": "coordinate probe"}
]'
```

## Public Feedback

The trace stores:

```text
x
improvement
is_new_best
feasible
constraint_values
constraint_violations
total_violation
rationale
```

It does not store the hidden objective value. The evaluator privately
recomputes objective values from previous `x` values when it needs to recover
the incumbent across separate query calls.

The public constraints are:

```text
-3 <= x_1 + 2x_2 - x_3 + 0.5x_4 - 1.5x_5 <= 3
0.8|x_1| + 1.1|x_2| + 0.7|x_3| + |x_4| + 1.2|x_5| <= 22
(x_1 - x_4)^2 + (x_2 - x_5)^2 <= 6
```

Infeasible candidates are logged with `improvement = 0.0` and cannot become the
incumbent.

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


# Adjusting Problem Setup
  For future new problems, the files you usually need to change are:

  - unknown_optima/config.json: dimensions, bounds, variable types, constraint
    coefficients/thresholds, budget, tolerance.
  - unknown_optima/private_objective.py: hidden objective.
  - unknown_optima/evaluate_toy_objective.py: only if you want the standalone
    checker to match the new problem.
  - unknown_optima/domain.py: only when adding a new constraint type, not just
    changing coefficients.
  - unknown_optima/make_codex_controller_prompt.py: only when the optimizer
    prompt needs to describe a new constraint type.

  If you only change coefficients or thresholds for the existing linear,
  absolute-budget, or pairwise-balance constraints, config.json should be
  enough.