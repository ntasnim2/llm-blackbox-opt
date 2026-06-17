# Codex Optimization Workflow

This file records the workflow used for the black-box optimization run executed from `prompts/codex_controller_prompt.txt`.

## Contract

- Dimension: 3
- Bounds: each coordinate in `[-32.0, 32.0]`
- Objective: minimize scalar `y = f(x)`
- Evaluation budget: 50
- Target objective value: `5.0`
- Success tolerance: `abs(best_y - target_y) <= 0.001`

## Allowed Inputs And Commands

The run used only the public optimization interface:

- `python3 show_state.py`
- `python3 evaluate_codex_candidates.py --x '<JSON_LIST>'`
- `python3 evaluate_codex_candidates.py --batch '<JSON_BATCH>'`
- `config.json`
- `results/codex_trace.jsonl`
- `results/codex_summary.json`

The private objective implementation was not inspected.

## Workflow

1. Checked the initial state with `python3 show_state.py`.
2. Started with a center point and symmetric coordinate probes at step size `4`:
   - `[0, 0, 0]`
   - `[4, 0, 0]`, `[-4, 0, 0]`
   - `[0, 4, 0]`, `[0, -4, 0]`
   - `[0, 0, 4]`, `[0, 0, -4]`
3. Recentered around the best initial point, `[4, 0, 0]`, and ran trust-region coordinate probes.
4. Shrunk the trust-region step from `4` to `2` after no improvement.
5. Found an improved point at `[4, 0, 2]`, then continued coordinate refinement around the current best.
6. Shrunk to step size `1` and refined through:
   - `[4, -1, 2]`
   - `[3, -1, 2]`
7. Moved off integer-valued candidates with fractional step size `0.5`.
8. Tested combined fractional moves based on the best single-coordinate directions.
9. Found an improved combined point at `[3.5, -1.0, 1.5]`.
10. Used the last evaluations for line/refinement guesses near the target basin:
    - `[3.375, -0.875, 1.625]`
    - `[3.25, -0.75, 1.75]`
    - `[3.125, -0.625, 1.875]`
    - `[3.3, -0.8, 1.7]`

## Result

The final evaluation solved the problem:

- Evaluations used: `50`
- Best objective: `5.0`
- Objective gap: `0.0`
- Best point: `[3.3, -0.8, 1.7]`
- Trace: `results/codex_trace.jsonl`
- Summary: `results/codex_summary.json`

