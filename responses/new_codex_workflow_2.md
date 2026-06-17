# Codex Optimization Workflow 2

This workflow produced the solved result:

- Best error: `2.012574116250221e-07`
- Best x: `[3.3, -0.8, 1.7]`
- Evaluations used: `83`
- Success tolerance: `best_error <= 0.01`

## Contract

- Dimension: `3`
- Bounds: each coordinate in `[-8.0, 8.0]`
- Objective: minimize the deterministic nonnegative error returned by `query_codex_error.py`
- Budget: `100` evaluations
- Use only public state and query outputs:
  - `python3 show_state.py`
  - `python3 query_codex_error.py --x '<JSON_LIST>'`
  - `python3 query_codex_error.py --batch '<JSON_BATCH>'`
  - `results/codex_trace.jsonl`
  - `results/codex_summary.json`

## Workflow

1. Start by running:

   ```bash
   python3 show_state.py
   ```

   Stop immediately if the summary is already solved or if no evaluations remain.

2. If there is no prior trace, evaluate the origin and a symmetric coordinate batch with a coarse step of `4`:

   ```text
   [0, 0, 0]
   [4, 0, 0], [-4, 0, 0]
   [0, 4, 0], [0, -4, 0]
   [0, 0, 4], [0, 0, -4]
   ```

   In this run, `[4, 0, 0]` was the best initial point.

3. Recenter on the current best point and run trust-region coordinate refinement.

   At each radius `delta`, evaluate available coordinate neighbors:

   ```text
   best_x + delta * e_i
   best_x - delta * e_i
   ```

   Skip duplicates and points outside bounds.

4. Use coarse-to-fine deltas:

   ```text
   4.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05
   ```

   If a full coordinate batch does not improve the best point, shrink `delta`.
   If a batch improves the best point, recenter and continue at the same `delta` when useful.

5. When multiple single-coordinate moves improve at the same radius, evaluate combined moves early.

   Key combined moves in this run:

   ```text
   [3, -1, 2]        from combining radius-1 improvements
   [3.5, -1, 1.5]    from combining radius-0.5 improvements
   [3.25, -0.75, 1.75]
                      from combining radius-0.25 improvements
   [3.3, -0.8, 1.7]  from combining radius-0.05 improvements
   ```

6. Once the best error became small and the search was localized, avoid broad exploration.

   Continue only with fractional local refinements and combined moves near the current best point.

7. Stop as soon as the query output reports:

   ```json
   "solved": true
   ```

   In this run, the first candidate in the final batch solved the problem:

   ```text
   x = [3.3, -0.8, 1.7]
   error = 2.012574116250221e-07
   ```

## Practical Rules

- Always check the query output summary after each evaluation or batch.
- Prefer batches only when all candidates are part of the same local search around the current best point.
- Switch to one-at-a-time evaluations if the remaining budget is low.
- Do not repeat candidates already present in the trace.
- Do not ask for user input during the optimization loop.
