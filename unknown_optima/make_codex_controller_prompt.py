#!/usr/bin/env python3
"""Generate the controller prompt for an unknown-optimum Codex session."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from domain import load_config
from state import load_trace, summary_path, trace_path, write_summary


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = SCRIPT_DIR
DEFAULT_OUTPUT = SCRIPT_DIR / "prompts" / "codex_controller_prompt.txt"


def display_path(path: Path, base_dir: Path) -> Path:
    return Path(os.path.relpath(path, base_dir))


def variable_list(indices: list[int]) -> str:
    return ", ".join(f"x_{index + 1}" for index in indices)


def signed_linear_expression(coefficients: list[float]) -> str:
    terms = []
    for index, coefficient in enumerate(coefficients):
        variable = f"x_{index + 1}"
        if index == 0:
            terms.append(f"{coefficient:g}{variable}")
        elif coefficient < 0:
            terms.append(f"- {abs(coefficient):g}{variable}")
        else:
            terms.append(f"+ {coefficient:g}{variable}")
    return " ".join(terms)


def absolute_budget_expression(coefficients: list[float]) -> str:
    return " + ".join(
        f"{coefficient:g}|x_{index + 1}|"
        for index, coefficient in enumerate(coefficients)
    )


def pairwise_balance_expression(pairs: list[list[int]]) -> str:
    return " + ".join(
        f"(x_{left_index + 1} - x_{right_index + 1})^2"
        for left_index, right_index in pairs
    )


def make_prompt(config: dict[str, Any], run_dir: Path) -> str:
    dimension = config["dimension"]
    lower, upper = config["bounds"]
    budget = config["budget"]
    tolerance = config["tolerance"]
    patience = config["patience"]
    min_evaluations = config["min_evaluations"]
    integer_indices = config["integer_indices"]
    continuous_indices = [
        index for index in range(dimension) if index not in set(integer_indices)
    ]
    linear_constraint = config["linear_constraint"]
    linear_expression = signed_linear_expression(linear_constraint["coefficients"])
    absolute_budget = config["absolute_budget_constraint"]
    absolute_budget_expr = absolute_budget_expression(absolute_budget["coefficients"])
    pairwise_balance = config["pairwise_balance_constraint"]
    pairwise_balance_expr = pairwise_balance_expression(pairwise_balance["pairs"])
    results_dir = config["results_dir"]
    trace_file = trace_path(results_dir)
    summary_file = summary_path(results_dir)
    trace_display = display_path(trace_file, run_dir)
    summary_display = display_path(summary_file, run_dir)

    integer_variables = variable_list(integer_indices)
    continuous_variables = variable_list(continuous_indices)

    return f"""You are Codex acting as the optimizer in an autonomous sequential optimization loop.

You are maximizing an unknown deterministic objective. You do not observe the
objective value. You only observe whether a candidate improves the best value
seen so far, and by how much it improves that incumbent.

Work from this experiment directory. All paths below are relative to it:
```bash
cd {run_dir}
```

Public optimization contract:
- Dimension: {dimension}
- Bounds: every coordinate must be in [{lower}, {upper}]
- Mixed variables: {integer_variables} are integers; {continuous_variables} are continuous
- Public linear constraint: {linear_constraint["lower"]:g} <= {linear_expression} <= {linear_constraint["upper"]:g}
- Public absolute-budget constraint: {absolute_budget_expr} <= {absolute_budget["upper"]:g}
- Public pairwise-balance constraint: {pairwise_balance_expr} <= {pairwise_balance["upper"]:g}
- Objective: maximize the hidden objective using only reported incumbent improvements
- Total evaluation budget: {budget}
- Convergence rule: stop after {patience} consecutive evaluations with improvement <= {tolerance}, but not before {min_evaluations} evaluations

Allowed files and commands:
- Read `results/codex_trace.jsonl`
- Read `results/codex_summary.json`
- Run `python3 query_codex_improvement.py --x '<JSON_LIST>'`
- Run `python3 query_codex_improvement.py --batch '<JSON_BATCH>'`
- Run `python3 show_state.py`

Do not inspect, import, or run anything else other than the files and commands
listed above.

State files:
- Trace: `{trace_display}`
- Summary: `{summary_display}`

Query interfaces:

Single candidate:
```bash
python3 query_codex_improvement.py --x '[1, -2, 3, 0.5, -4.2]'
```

Batch candidates:
```bash
python3 query_codex_improvement.py --batch '[
  {{"x": [1, -2, 3, 0.5, -4.2], "rationale": "brief reason"}},
  {{"x": [2, -2, 3, 0.5, -4.2], "rationale": "brief reason"}}
]'
```

The query command appends completed evaluations to the trace and prints JSON with:
- `evaluations`
- `skipped`
- `summary`

Each completed evaluation includes:
- `improvement`: max(0, hidden_objective(x) - previous_best_hidden_objective)
- `is_new_best`: whether the candidate became the incumbent
- `feasible`: whether the candidate satisfies the public constraints and bounds
- `constraint_values`: values of the public constraints
- `constraint_violations`: per-constraint violation amounts
- `total_violation`: sum of public constraint violations

The public trace and summary do not reveal hidden objective values.

Optimization process:
1. Run `python3 show_state.py`.
2. If `summary.converged` is true or `summary.remaining_evaluations` is 0, stop and report the best result.
3. Choose the next candidate `x` using only the trace and query outputs.
4. Prefer one candidate at a time when close to a good point. Use batches when the whole batch is an intentional local search around the same current best point.
5. Run the query command with `--x` or `--batch`.
6. Read the query output or run `show_state.py`.
7. Repeat until converged or the budget is exhausted.

Recommended optimizer policy:
- Treat `improvement > 0` as the only direct evidence that a candidate improved the incumbent.
- Infeasible candidates cannot become the incumbent; use `total_violation` to move back toward feasibility.
- Since non-improving candidates all report `improvement = 0`, use structured local experiments around the current `best_x`.
- Start with a small center point and coordinate probes in positive and negative directions.
- Use reported improvements to infer useful coordinate directions.
- Once a point improves the incumbent, recenter local search around `summary.best_x`.
- For integer variables, use integer step sizes. For continuous variables, use fractional refinements.
- If a full local refinement batch does not improve the incumbent, shrink the step size or try a different structured direction.
- Avoid repeated candidates; check the trace before evaluating.
- When remaining evaluations are low, stop batching and spend them one at a time on the most promising refinements.

Candidate rules:
- Every `x` must contain exactly {dimension} finite numbers.
- Every coordinate must be in [{lower}, {upper}].
- The public linear constraint must satisfy {linear_constraint["lower"]:g} <= {linear_expression} <= {linear_constraint["upper"]:g}.
- The public absolute-budget constraint must satisfy {absolute_budget_expr} <= {absolute_budget["upper"]:g}.
- The public pairwise-balance constraint must satisfy {pairwise_balance_expr} <= {pairwise_balance["upper"]:g}.
- {integer_variables} must be integers.
- {continuous_variables} may be real numbers.
- Do not ask the user for the next point.
- Do not regenerate this controller prompt during the run.
- Do not stop early unless converged, budget is exhausted, or a query error blocks progress.

Final response:
- Report whether the run converged, evaluations used, best_x, stagnation_count, and the path to the trace and summary files.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an autonomous Codex prompt.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--run-dir",
        "--repo-root",
        type=Path,
        default=DEFAULT_RUN_DIR,
        dest="run_dir",
        help="Experiment directory to place in the generated prompt.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    trace = load_trace(trace_path(config["results_dir"]))
    write_summary(
        summary_path(config["results_dir"]),
        trace,
        config["dimension"],
        config["bounds"],
        config["integer_indices"],
        config["linear_constraint"],
        config["absolute_budget_constraint"],
        config["pairwise_balance_constraint"],
        config["budget"],
        config["tolerance"],
        config["patience"],
        config["min_evaluations"],
    )
    prompt = make_prompt(config, args.run_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(prompt, encoding="utf-8")
    print(f"Wrote controller prompt to {args.output}")


if __name__ == "__main__":
    main()
