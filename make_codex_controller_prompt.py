#!/usr/bin/env python3
"""Generate the autonomous controller prompt for a Codex optimizer session."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from domain import load_config
from state import load_trace, summary_path, trace_path, write_summary


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = Path(".")
DEFAULT_OUTPUT = SCRIPT_DIR / "prompts" / "codex_controller_prompt.txt"


def display_path(path: Path, base_dir: Path) -> Path:
    return Path(os.path.relpath(path, base_dir))


def make_prompt(config: dict[str, Any], run_dir: Path, reveal_ackley: bool) -> str:
    dimension = config["dimension"]
    lower, upper = config["bounds"]
    budget = config["budget"]
    tolerance = config["tolerance"]
    results_dir = config["results_dir"]
    trace_file = trace_path(results_dir)
    summary_file = summary_path(results_dir)
    trace_display = display_path(trace_file, run_dir)
    summary_display = display_path(summary_file, run_dir)

    if reveal_ackley:
        problem_statement = (
            "You are minimizing a reported nonnegative error for a benchmark "
            "function. Use only the public error feedback when choosing candidates."
        )
    else:
        problem_statement = (
            "You are minimizing an unknown deterministic nonnegative error signal. "
            "Use only the public trace, summary, and query outputs. Do not assume "
            "the analytic form of the underlying function."
        )

    return f"""You are Codex acting as the optimizer in an autonomous sequential optimization loop.

{problem_statement}

Work from this experiment directory. All paths below are relative to it:
```bash
cd {run_dir}
```

Public optimization contract:
- Dimension: {dimension}
- Bounds: every coordinate must be in [{lower}, {upper}]
- Objective: minimize the reported nonnegative error
- Total evaluation budget: {budget}
- Success tolerance: best_error <= {tolerance}

Allowed files and commands:
- Read `results/codex_trace.jsonl`
- Read `results/codex_summary.json`
- Run `python3 query_codex_error.py --x '<JSON_LIST>'`
- Run `python3 query_codex_error.py --batch '<JSON_BATCH>'`
- Run `python3 show_state.py`

Do not inspect, import, or run anything else other than the files and commands
listed above.

State files:
- Trace: `{trace_display}`
- Summary: `{summary_display}`

Query interfaces:

Single candidate:
```bash
python3 query_codex_error.py --x '[1.0, -2.0]'
```

Batch candidates:
```bash
python3 query_codex_error.py --batch '[
  {{"x": [1.0, -2.0], "rationale": "brief reason"}},
  {{"x": [-3.0, 4.0], "rationale": "brief reason"}}
]'
```

The query command appends completed evaluations to the trace and prints JSON with:
- `evaluations`
- `skipped`
- `summary`

Each completed evaluation includes `error`. The run is solved when
`summary.best_error <= summary.tolerance`.

Optimization process:
1. Run `python3 show_state.py`.
2. If `summary.solved` is true or `summary.remaining_evaluations` is 0, stop and report the best result.
3. Choose the next candidate `x` using only the trace and query outputs.
4. Prefer one candidate at a time when close to a good point. Use batches when the whole batch is an intentional local search around the same current best point.
5. Run the query command with `--x` or `--batch`.
6. Read the query output or run `show_state.py`.
7. Repeat until solved or the budget is exhausted.

Recommended optimizer policy:
- Treat the budget as scarce. Do not spend many evaluations on broad exploration once you have a clearly better region.
- Start with at most one center point and one symmetric coordinate batch: center plus `+step` and `-step` on each coordinate. A reasonable first step is 2 to 4 units, clipped to bounds.
- Use those directional results to build one combined point from the best coordinate directions. Evaluate that combined point early.
- Once a combined or local point improves the best value, switch to trust-region coordinate refinement around the current best point.
- For trust-region refinement, evaluate a batch of `best_x +/- delta * e_i` for each coordinate `i`, skipping duplicates and clipped points.
- Use shrinking deltas such as `2.0`, `1.0`, `0.5`, `0.25`, `0.1`, `0.05`, `0.02`, and smaller if the budget allows.
- If a coordinate-refinement batch improves the best value, recenter at the new best and continue with the same delta or the next smaller delta.
- If a full coordinate-refinement batch does not improve the best value, shrink delta.
- Do not remain on integer-valued candidates once error is clearly improving. Move to fractional local refinements.
- Avoid repeated or near-duplicate candidates; check the trace before evaluating.
- When remaining evaluations are fewer than `2 * dimension`, stop batching and spend them one at a time on the most promising fractional coordinate refinements.

Candidate rules:
- Every `x` must contain exactly {dimension} finite numbers.
- Every coordinate must be in [{lower}, {upper}].
- Do not ask the user for the next point.
- Do not regenerate this controller prompt during the run.
- Do not stop early unless solved, budget is exhausted, or a query error blocks progress.

Final response:
- Report whether the run solved the problem, evaluations used, best_error, best_x, and the path to the trace and summary files.
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
    parser.add_argument(
        "--reveal-ackley",
        action="store_true",
        help="Use benchmark wording instead of unknown-error wording.",
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
        config["budget"],
        config["tolerance"],
    )
    prompt = make_prompt(config, args.run_dir, args.reveal_ackley)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(prompt, encoding="utf-8")
    print(f"Wrote controller prompt to {args.output}")


if __name__ == "__main__":
    main()
