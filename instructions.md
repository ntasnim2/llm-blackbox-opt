# Automated Codex Black-Box Optimization Instructions

This pipeline lets a fresh Codex session act as the sequential optimizer. Codex receives one controller prompt, then uses the evaluator and output files until the problem is solved or the evaluation budget is exhausted.

## Files

```text
config.json
make_codex_controller_prompt.py
query_codex_error.py
evaluate_codex_candidates.py
show_state.py
reset_run.py
prompts/codex_controller_prompt.txt
results/codex_trace.jsonl
results/codex_summary.json
```

## Start Fresh

From the experiment directory:

```bash
cd <experiment-directory>
```

Reset the run:

```bash
python3 reset_run.py
```

Generate the autonomous controller prompt:

```bash
python3 make_codex_controller_prompt.py
```

The prompt is written to:

```text
prompts/codex_controller_prompt.txt
```

## Run with Codex

Open a fresh Codex session and provide only the contents of:

```text
prompts/codex_controller_prompt.txt
```

The prompt tells Codex to:

1. Inspect the current state with `show_state.py`.
2. Choose the next candidate `x`.
3. Evaluate it with `query_codex_error.py`.
4. Read the updated summary.
5. Continue until solved or budget exhausted.

The generated controller prompt includes an optimizer policy:

- Use only a small initial exploration batch.
- Build a combined candidate from promising coordinate directions early.
- Switch quickly to trust-region coordinate refinement around the current best point.
- Shrink local step sizes, for example `2.0`, `1.0`, `0.5`, `0.25`, `0.1`, `0.05`, `0.02`.
- Avoid staying on integer-valued candidates once a promising basin is found.
- Avoid repeated or near-duplicate candidates.

## Evaluator Commands

Single candidate:

```bash
python3 query_codex_error.py --x '[1.0, -2.0]'
```

Batch candidates:

```bash
python3 query_codex_error.py --batch '[
  {"x": [1.0, -2.0], "rationale": "brief reason"},
  {"x": [-3.0, 4.0], "rationale": "brief reason"}
]'
```

Response file:

```bash
python3 query_codex_error.py \
  --response responses/response_001.json
```

The response file can contain either:

```json
{
  "x": [1.0, -2.0],
  "rationale": "single point"
}
```

or:

```json
{
  "candidates": [
    {"x": [1.0, -2.0], "rationale": "first point"},
    {"x": [-3.0, 4.0], "rationale": "second point"}
  ]
}
```

## Check State

```bash
python3 show_state.py
```

This prints:

```text
summary
best_observation
recent_trace
```

## Outputs

`results_dir` in `config.json` is resolved relative to the directory containing
that config file. With the default config, each copied experiment directory keeps
its own outputs under `results/`.

The trace is stored at:

```text
results/codex_trace.jsonl
```

The summary is stored at:

```text
results/codex_summary.json
```

The public trace stores only the reported error for each evaluated candidate.
The public summary stores `best_error`, not the raw objective value. A run is
solved when:

```text
best_error <= tolerance
```

The private evaluator may compute that error from private quantities, but the
optimizer only sees the error signal.

Stop when `codex_summary.json` reports:

```json
"solved": true
```

or when:

```json
"remaining_evaluations": 0
```

## Black-Box Rule

For a clean black-box test, the optimizing Codex session should use only the
files and commands listed in the generated controller prompt. The prompt does
not expose the internal evaluator or the private objective implementation.

## Benchmarking Optimizer Quality

Solving a 3D shifted Ackley run in 46 evaluations is a useful proof of concept, but it is not enough by itself to claim the optimizer is generally strong.

For Codex as a black-box reasoning optimizer, this is a meaningful success:

- It found the hidden optimum.
- It adapted from trace feedback.
- It reached numerical zero within a finite budget.
- It did this without using the private objective implementation.

For a standard numerical optimizer, 46 evaluations in 3D is not necessarily exceptional. Classical optimizers such as Powell, Nelder-Mead, CMA-ES, Bayesian optimization, or even well-designed coordinate search may perform competitively on smooth deterministic low-dimensional problems.

To judge optimizer quality, compare Codex against baselines under the same objective, bounds, budget, tolerance, and shift settings.

Recommended baselines:

```text
random search
grid or coordinate search
Nelder-Mead
Powell
CMA-ES
Bayesian optimization
Codex-driven optimizer
```

Recommended test variations:

```text
dimension: 2, 3, 5, 10
shift vectors: multiple random seeds
budget: 25, 50, 100
tolerance: 1e-3, 1e-6
bounds: [-5, 5] and [-32.768, 32.768]
```

Recommended metrics:

```text
best_y after N evaluations
evaluations to reach y <= 1e-3
evaluations to reach y <= 1e-6
success rate across random shifts
median evaluations to success
mean evaluations to success
```

A good conclusion should be based on repeated runs across several shifts and dimensions, not one successful run. The current result shows the pipeline works and that Codex can act as a sequential optimizer, but optimizer quality should be measured against simple numerical baselines.



## NOTES

1. If you are private separately (cannot give it range or any other detail), we have to create a "proxy private" function. Codex cannot evaluate the proxy private function. What can you give as "signal" from the private function that can help solve the problem. E.g. give it the error value. 

2. Do evaluation manually. 

3. Come up with a functional distance measure for our chemistry setting. As we increase the distance, does codex still help?

4. Check functions other than Ackley. Such as the non-linear setup from molecular.

5. Let codex select the "next candidate" and optimize its prompt. How do we optimize the prompt so that it reaches the desired conclusion faster? What are the most informative trace to give?



## Implementation notes

  One caveat: this is interface-level protection. If a Codex session
  has unrestricted filesystem access and ignores the prompt, it
  could still inspect other files. The prompt and public files now
  enforce the intended protocol, but true enforcement would require
  filesystem sandboxing or moving private files outside Codex’s
  readable workspace.