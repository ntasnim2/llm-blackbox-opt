# Codex Optimization Workflow

This records the workflow used to solve the sequential optimization problem from `prompts/codex_controller_prompt.txt`.

## Objective

Minimize a deterministic nonnegative error signal in 3 dimensions, with each coordinate constrained to `[-32.0, 32.0]`. The run is successful when `best_error <= 0.01`, with a maximum budget of 100 evaluations.

## Allowed Interface

Only the public optimization interface was used:

- `python3 show_state.py`
- `python3 query_codex_error.py --x '<JSON_LIST>'`
- `python3 query_codex_error.py --batch '<JSON_BATCH>'`
- Public result state in `results/codex_trace.jsonl` and `results/codex_summary.json`

No objective internals or hidden implementation files were inspected.

## Workflow

1. Checked the initial state with `python3 show_state.py`.
2. Started with a compact exploratory batch:
   - Center point `[0, 0, 0]`
   - Symmetric coordinate probes at step size `4`
   - This identified the first promising direction, especially positive coordinate 0.
3. Built an early combined candidate from the directional signal:
   - Evaluated `[4.79, -0.31, 0.78]`
   - This improved the initial best value.
4. Switched to trust-region coordinate refinement:
   - Recentered around the current best point.
   - Evaluated `best_x +/- delta * e_i` for each coordinate.
   - Used shrinking deltas: `2.0`, `1.0`, `0.5`, `0.25`, `0.1`, `0.05`, and `0.02`.
5. When coordinate sweeps showed a bracketed local minimum, estimated improved fractional points by using the asymmetric errors from `+delta` and `-delta` probes.
6. Tested the interpolated fractional candidates one at a time once the error was close to tolerance.
7. Stopped immediately after `summary.solved` became `true`.

## Key Progression

- Initial best after the first batch: `[4.0, 0.0, 0.0]`, error about `5.97`.
- Trust-region search found a much better basin near `[3.29, -0.81, 1.78]`, error about `0.306`.
- Fractional interpolation improved the result to `[3.2944, -0.8005, 1.7172]`, error about `0.0486`.
- Further local refinement improved to `[3.29705, -0.79919, 1.70589]`, error about `0.0163`.
- Final fractional correction reached `[3.29792, -0.7992, 1.70339]`, error `0.009688498405718171`.

## Final Result

- Solved: `true`
- Evaluations used: `73`
- Remaining evaluations: `27`
- Best error: `0.009688498405718171`
- Best point: `[3.29792, -0.7992, 1.70339]`
- Trace file: `results/codex_trace.jsonl`
- Summary file: `results/codex_summary.json`

