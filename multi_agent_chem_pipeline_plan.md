# Multi-Agent Chemistry Pipeline Plan

## Goal

Build a multi-agent candidate generation layer on top of the existing
`optima_chem` surrogate-oracle pipeline.

The intended setup is:

- A stronger teacher model, initially GPT/Codex.
- A weaker student model, eventually Llama.
- Both receive the same base chemistry task.
- The teacher generates a larger candidate pool.
- The student generates candidates and is later guided by teacher-neighbor
  retrieval.
- Only selected candidates are evaluated by the private HoF oracle.

The oracle evaluation trace remains the source of truth:

```text
optima_chem/results/codex_trace.jsonl
optima_chem/results/codex_summary.json
```

Agent proposal traces are separate from oracle evaluations.

## Directory Layout

Planned structure:

```text
optima_chem/
  agents/
    gpt_teacher/
      prompts/controller_prompt.txt
      traces/proposals.jsonl
      summaries/proposal_summary.json
    llama_student/
      prompts/controller_prompt.txt
      traces/proposals.jsonl
      summaries/proposal_summary.json
  consensus/
    retrieval_trace.jsonl
    selected_candidates.jsonl
  responses/
    gpt_teacher_round_1.json
    gpt_student_round_1.json
    gpt_student_round_2.json
  results/
    codex_trace.jsonl
    codex_summary.json
```

For initial testing, `llama_student` can be replaced by a second GPT/Codex
session, for example `gpt_student`.

## Scripts To Build

### `make_agent_prompts.py`

Creates separate prompts for teacher and student agents.

Teacher prompt:

- Generate a larger, diverse candidate set.
- Do not evaluate candidates.
- Output strict JSON only.

Student prompt:

- Generate a smaller candidate set from the same base task.
- Do not evaluate candidates.
- Output strict JSON only.

### `record_agent_proposals.py`

Records LLM-generated candidates without evaluating them.

Expected response shape:

```json
{
  "candidates": [
    {
      "smiles": "...",
      "rationale": "...",
      "confidence": 0.7
    }
  ]
}
```

Each proposal trace record should include:

```text
proposal_id
agent
round
smiles
canonical_smiles
valid
duplicate_within_agent
duplicate_global
rationale
confidence
timestamp
```

### `build_teacher_index.py`

Builds a searchable teacher candidate index:

```text
SMILES -> canonical SMILES -> Morgan fingerprint
```

Outputs may include:

```text
agents/gpt_teacher/index/teacher_candidates.json
agents/gpt_teacher/index/fingerprints.pkl
```

### `retrieve_teacher_neighbors.py`

For each student candidate, finds top-k teacher candidates by Morgan
fingerprint Tanimoto similarity.

Writes:

```text
consensus/retrieval_trace.jsonl
```

Each retrieval record should include:

```text
student_smiles
student_canonical_smiles
teacher_neighbors
similarity_scores
teacher_rationales
```

### `make_student_refinement_prompt.py`

Creates a second-round student prompt using:

- Student's previous candidates.
- Retrieved teacher neighbors.
- Similarity scores.
- Public oracle feedback from previous evaluated rounds, if available.
- The same target HoF task.

This implements Scheme C:

```text
student candidate -> retrieve nearby teacher candidates -> guide student refinement
```

### `select_candidates_for_evaluation.py`

Chooses candidates to actually send to the oracle.

Possible selection policy:

- Include refined student candidates.
- Include nearest teacher neighbors to strong student candidates.
- Deduplicate by canonical SMILES.
- Filter invalid SMILES.
- Prefer diversity among selected candidates.

Writes:

```text
consensus/selected_candidates_round_<N>.json
```

This file can be evaluated with:

```bash
conda run -n research python query_codex_chem.py \
  --response consensus/selected_candidates_round_<N>.json
```

### Future: `run_multi_agent_chem_loop.py`

Eventually, an API-driven coordinator can automate the whole loop:

```text
call teacher model
record teacher proposals
call student model
record student proposals
retrieve teacher neighbors
generate refinement prompt
call student again
select candidates
evaluate selected candidates
repeat
```

This will be useful after Llama access is fully configured.

## Manual Mac Workflow

For early testing, use three terminals.

### Terminal A: Teacher Agent

```bash
cd /Users/tasnim1/research-vs-code/seq_opt_auto/blackbox_codex_auto/optima_chem
codex
```

Tell it:

```text
Read agents/gpt_teacher/prompts/controller_prompt.txt and output candidates only
in the requested JSON format. Do not run evaluator commands.
```

Save its JSON output under:

```text
responses/gpt_teacher_round_1.json
```

### Terminal B: Student Agent

```bash
cd /Users/tasnim1/research-vs-code/seq_opt_auto/blackbox_codex_auto/optima_chem
codex
```

Tell it:

```text
Read agents/gpt_student/prompts/controller_prompt.txt and output candidates only
in the requested JSON format. Do not run evaluator commands.
```

Save its JSON output under:

```text
responses/gpt_student_round_1.json
```

### Terminal C: Coordinator

From:

```bash
cd /Users/tasnim1/research-vs-code/seq_opt_auto/blackbox_codex_auto/optima_chem
```

Planned command sequence:

```bash
conda run -n research python make_agent_prompts.py

conda run -n research python record_agent_proposals.py \
  --agent gpt_teacher \
  --round 1 \
  --response responses/gpt_teacher_round_1.json

conda run -n research python record_agent_proposals.py \
  --agent gpt_student \
  --round 1 \
  --response responses/gpt_student_round_1.json

conda run -n research python build_teacher_index.py \
  --agent gpt_teacher

conda run -n research python retrieve_teacher_neighbors.py \
  --student-agent gpt_student \
  --teacher-agent gpt_teacher \
  --round 1

conda run -n research python make_student_refinement_prompt.py \
  --student-agent gpt_student \
  --teacher-agent gpt_teacher \
  --round 1
```

Then paste the generated refinement prompt into the student agent terminal.

After receiving refined student candidates:

```bash
conda run -n research python record_agent_proposals.py \
  --agent gpt_student \
  --round 2 \
  --response responses/gpt_student_round_2.json

conda run -n research python select_candidates_for_evaluation.py \
  --round 2

conda run -n research python query_codex_chem.py \
  --response consensus/selected_candidates_round_2.json
```

## Experimental Arms

To measure whether teacher guidance helps, compare:

```text
1. Student alone
2. Teacher alone
3. Student guided by teacher-neighbor retrieval
4. Consensus/retrieval-selected candidates
```

Use the same target, prompt examples, budget, and oracle for all arms.

## Metrics

Track:

```text
best_abs_error after N oracle evaluations
evaluations to solve
valid SMILES rate
duplicate rate
prompt-example rejection rate
model disagreement
similarity to teacher candidates
similarity to prompt examples
```

## Notes

- LLM proposal traces are not oracle evaluations.
- The shared oracle trace is the only trace that consumes evaluation budget.
- Exact SMILES overlap between agents will be rare; use Morgan fingerprint
  Tanimoto similarity instead.
- The coordinator scripts should mediate all interaction. The teacher and
  student should not directly communicate with each other.

