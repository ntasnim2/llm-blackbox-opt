#!/usr/bin/env python3
"""Generate the controller prompt for chemistry optimization."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from domain import dataset_values_for_prompt, load_config, load_dataset_rows
from state import load_trace, summary_path, trace_path, write_summary


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = SCRIPT_DIR
DEFAULT_OUTPUT = SCRIPT_DIR / "prompts" / "codex_controller_prompt.txt"


def display_path(path: Path, base_dir: Path) -> Path:
    return Path(os.path.relpath(path, base_dir))


def format_examples(examples: list[dict[str, Any]], label_precision: int) -> str:
    lines = []
    for index, example in enumerate(examples, start=1):
        lines.append(
            "- "
            + json.dumps(
                {
                    "example_id": index,
                    "smiles": example["smiles"],
                    "hof": round(float(example["hof"]), label_precision),
                    "density": round(float(example["density"]), 3),
                },
                sort_keys=True,
            )
        )
    return "\n".join(lines)


def make_prompt(config: dict[str, Any], run_dir: Path) -> str:
    target_value = config["target_value"]
    budget = config["budget"]
    tolerance = config["tolerance"]
    patience = config["patience"]
    min_evaluations = config["min_evaluations"]
    results_dir = config["results_dir"]
    trace_file = trace_path(results_dir)
    summary_file = summary_path(results_dir)
    trace_display = display_path(trace_file, run_dir)
    summary_display = display_path(summary_file, run_dir)

    rows = load_dataset_rows(config["data_path"])
    examples = dataset_values_for_prompt(
        rows,
        target_value=target_value,
        count=config["examples_count"],
        exclusion_radius=config["prompt_exclusion_radius"],
    )
    examples_text = format_examples(examples, config["example_label_precision"])

    return f"""You are Codex acting as the optimizer in an autonomous sequential molecular design loop.

You are proposing SMILES strings whose predicted heat of formation (HoF) should
be as close as possible to a target value. The property evaluator is a private
surrogate oracle trained on chemistry data. You may observe only the public
feedback returned by the allowed query commands.

Work from this experiment directory. All paths below are relative to it:
```bash
cd {run_dir}
```

Public optimization contract:
- Candidate type: one valid SMILES string per candidate
- Target property: heat of formation, `hof`
- Target HoF: {target_value:g}
- Objective: minimize `abs(predicted_hof - target_hof)`
- Solved when `best_abs_error <= {tolerance:g}`
- Total evaluation budget: {budget}
- Stagnation rule: stop after {patience} consecutive evaluations with improvement <= {tolerance:g}, but not before {min_evaluations} evaluations

Public examples from the dataset:
{examples_text}

The example list is selected outside a target-centered exclusion band:
- No prompt example has `abs(hof - target_hof) < {config["prompt_exclusion_radius"]:g}`.
- Exact prompt-example molecules are not valid optimization submissions.

Allowed files and commands:
- Read `results/codex_trace.jsonl`
- Read `results/codex_summary.json`
- Run `conda run -n research python show_state.py`
- Run `conda run -n research python query_codex_chem.py --smiles '<SMILES>'`
- Run `conda run -n research python query_codex_chem.py --batch '<JSON_BATCH>'`

Do not inspect, import, or run anything else other than the files and commands
listed above. Do not inspect model artifacts or private evaluator code.

State files:
- Trace: `{trace_display}`
- Summary: `{summary_display}`

Query interfaces:

Single candidate:
```bash
conda run -n research python query_codex_chem.py --smiles 'CCO'
```

Batch candidates:
```bash
conda run -n research python query_codex_chem.py --batch '[
  {{"smiles": "CCO", "rationale": "small oxygenated baseline"}},
  {{"smiles": "c1ccccc1", "rationale": "aromatic hydrocarbon comparison"}}
]'
```

The query command appends completed evaluations to the trace and prints JSON with:
- `evaluations`
- `skipped`
- `summary`

Each completed evaluation includes:
- `valid`: whether RDKit accepted the SMILES
- `canonical_smiles`: canonicalized SMILES for duplicate checks
- `duplicate`: whether the canonical SMILES was already evaluated
- `predicted_hof`: primary surrogate prediction
- `secondary_predicted_hof`: secondary surrogate prediction for sanity checking
- `model_disagreement`: absolute difference between primary and secondary predictions
- `abs_error`: absolute error to the target HoF
- `improvement`: max(0, previous_best_abs_error - current_abs_error)
- `is_new_best`: whether the candidate became the incumbent

Optimization process:
1. Run `conda run -n research python show_state.py`.
2. If `summary.solved`, `summary.converged`, or `summary.remaining_evaluations == 0`, stop and report the best result.
3. Choose a new valid-looking SMILES using only the examples, trace, and query outputs.
4. Query one candidate at a time when refining; use batches for deliberate structural comparisons.
5. Read the query output or run `show_state.py`.
6. Repeat until solved, converged, or budget exhausted.

Recommended optimizer policy:
- Use the examples to infer rough structural patterns on both sides of {target_value:g}.
- Start with molecules inspired by the examples, then alter substituents, heteroatoms, ring count, or functional groups.
- Do not submit an exact prompt example; generate a new molecule.
- Use `predicted_hof` directionally: if it is too high, propose structures likely to lower HoF; if too low, propose structures likely to raise HoF.
- Prefer valid, simple, chemically plausible SMILES over exotic syntax.
- Avoid duplicates by checking `canonical_smiles` in the trace.
- Treat high `model_disagreement` as lower confidence; it can still be useful, but do not over-exploit it.
- Do not ask the user for the next molecule.
- Do not regenerate this controller prompt during the run.
- Do not stop early unless solved, converged, budget is exhausted, or a query error blocks progress.

Candidate rules:
- Candidate JSON objects must use the key `smiles`.
- Include a short `rationale` in batches.
- Generated SMILES must be a single molecule string parseable by RDKit.
- Do not include explanatory text inside the SMILES string.

Final response:
- Report whether the run solved or converged, evaluations used, best_smiles,
  best_predicted_hof, best_abs_error, stagnation_count, and the path to the
  trace and summary files.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
        config["target_property"],
        config["target_value"],
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
