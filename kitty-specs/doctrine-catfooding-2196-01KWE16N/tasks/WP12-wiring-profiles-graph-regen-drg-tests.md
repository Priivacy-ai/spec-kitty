---
work_package_id: WP12
title: 'Wiring: Profiles + Single Graph Regen + DRG Tests'
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
- WP10
- WP11
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T053
- T054
- T055
- T056
- T057
phase: Phase 3 - Wiring (LC)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2082932"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/agent_profiles/built-in/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/agent_profiles/built-in/
- src/doctrine/graph.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP12 – Wiring: Profiles + Single Graph Regen + DRG Tests

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

WP12 is the sole serialized wiring WP. It owns two surfaces that no other WP may touch:

1. **`graph.yaml`**: run the SINGLE `graph.yaml` regeneration for the entire mission via `src/doctrine/drg/migration/extractor.py:generate_graph`. Verify freshness, cycle-freedom, and no worsening orphan count.
2. **`src/doctrine/agent_profiles/built-in/*.agent.yaml`**: append new directive IDs 043, 044, 045 to the `directives:` lists of the relevant agent profiles (C-002c / C-003).

**Pre-condition**: ALL conversion WPs (WP02-WP11) must be approved before WP12 starts. This ensures every artifact's inline DRG edges are in place before the single regen run.

**Acceptance gates:**
- [ ] `pytest tests/doctrine/drg/ -q` green (freshness + cycle + relations)
- [ ] `spec-kitty doctor doctrine --json` healthy for ALL mission artifacts (not just this WP's new files)
- [ ] Orphan count ≤ pre-mission baseline (NFR-003)
- [ ] `ruff` + `mypy` clean on any Python touched
- [ ] Profile `directives:` lists updated for directives 043, 044, 045

## Context & Constraints

- **C-003 (strict sole-owner)**: WP12 is the ONLY WP that may edit `agent_profiles/built-in/*.agent.yaml` files and `graph.yaml`. Any conversion WP that touched these files is a C-003 violation — investigate before proceeding.
- **PD-2 (graph.yaml regen strategy)**: `graph.yaml` is a generated file produced by `src/doctrine/drg/migration/extractor.py:generate_graph`. It is NOT hand-edited. The extractor reads inline `requires`/`suggests`/`refines` edges from all artifact YAMLs and constructs the graph. The regen here is the one and only time `graph.yaml` changes in this mission.
- **DRG generator gaps (#1755)**: known gaps exist in the DRG generator. The regen must be verified by running `tests/doctrine/drg/*` — do not assume the regen is clean. If a cycle or dangling-edge error appears, investigate and fix the offending artifact's inline edge (the artifact is the source of truth, not the graph).
- **Orphan count**: before running the regen, record the current orphan count from the DRG test output (or from `doctor doctrine --json`). After regen, confirm the count has not increased. NFR-003: this mission must not worsen the orphan count.
- **Profile `directives:` wiring**: new directives 043, 044, 045 are inert for agent sessions until referenced in the `directives:` lists of the relevant profiles. Read each profile file to understand its current directive list and append the appropriate new IDs. At minimum: any profile that governs implementation work in this repo should carry 043 and 044; any profile that governs git/workflow operations should carry 045.
- **Python files**: if any Python is touched (e.g. the extractor script to debug a regen issue), run `ruff check` and `mypy` on those files. NFR-004.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T053 – Run single graph.yaml regeneration

- **Purpose**: Produce the updated `graph.yaml` that reflects all inline DRG edges authored in WP02-WP11. This is the one and only regen for this mission.
- **Steps**:
  1. Verify all conversion WPs (WP02-WP11) are in `approved` or `done` state: `spec-kitty agent tasks status`.
  2. Record the current orphan count before regen (for comparison in T055). Run `pytest tests/doctrine/drg/ -q` and note any orphan-related output, or run `spec-kitty doctor doctrine --json` and note the orphan count.
  3. Run the regeneration using the canonical CLI (DIRECTIVE_044 — use the canonical command, do not improvise):
     ```bash
     spec-kitty doctrine regenerate-graph
     ```
     The underlying function is `generate_graph` from `src/doctrine/drg/migration/extractor.py`, but this module has no `__main__` and cannot be run directly — always invoke via the CLI. Use `spec-kitty doctrine regenerate-graph --check` for a dry-run freshness assertion (verifies the graph would change without writing) before the actual write; this is documented as the FR-009 "Composes the DRG extractor + calibrator into src/doctrine/graph.yaml" command.
  4. Verify the `graph.yaml` file has changed (it should have new nodes/edges for the mission's new artifacts).
  5. Verify `graph.yaml` is not hand-edited — it must be the output of the extractor, not manual changes.
- **Files**: `src/doctrine/graph.yaml` (regenerated — sole change in this subtask)
- **Parallel?**: No — must be first; T054 depends on this.
- **Notes**: If the CLI command fails (import error, generator gap, etc.), investigate the root cause. Do NOT hand-edit `graph.yaml` to work around a generator error — fix the generator or the artifact inline edges. The `generate_graph` function in `extractor.py` is the underlying implementation; fixing it there is the correct approach.

### Subtask T054 – Run DRG freshness, cycle, and relations tests

- **Purpose**: Verify the regenerated `graph.yaml` passes all DRG integrity tests.
- **Steps**:
  1. Run `pytest tests/doctrine/drg/ -q` — all tests must be green.
  2. If a freshness test fails: the committed `graph.yaml` does not match the regenerated output → re-run the regen (T053) and commit the result.
  3. If a cycle test fails: a circular DRG edge was introduced by one of the conversion WPs. Identify the offending artifact(s) by reading the test output; fix the inline edge in the artifact YAML (not in `graph.yaml`); re-run the regen.
  4. If a relations test fails (dangling URN, unknown artifact kind): an inline edge references a URN that doesn't resolve to an existing artifact. Find the artifact, verify its `id` field matches the URN, and fix the edge.
  5. DRG generator gaps (#1755): if the test reveals gaps in the generator (e.g. missing edge types), record the gap and work around it within the generator's capabilities — do NOT hand-edit `graph.yaml`.
- **Files**: Potentially `src/doctrine/*/built-in/*.yaml` (if inline edges need fixing — fix the artifact, not graph.yaml)
- **Parallel?**: No — must run after T053.
- **Notes**: All three test categories (freshness, cycle, relations) must be green. A single failure in any category blocks WP13 from starting.

### Subtask T055 – Verify orphan count does not worsen

- **Purpose**: Confirm NFR-003: this mission must not increase the count of orphaned DRG nodes vs. the pre-mission baseline.
- **Steps**:
  1. From the T053 pre-regen baseline record, note the orphan count.
  2. After regen (T054 green), check the orphan count in the DRG test output or `doctor doctrine --json`.
  3. If the orphan count increased: identify the new orphans (artifacts with no edges pointing to them and no edges pointing from them). If the orphan is a new artifact authored by this mission that has no referrers yet — that is expected; the charter compile (WP13) will activate it and the activation is the referrer. If the orphan is a pre-existing artifact: investigate; do NOT merge WP12 with a worsened orphan count.
  4. Record the pre-regen and post-regen orphan counts in the Activity Log.
- **Files**: No files changed — verification only.
- **Parallel?**: No — must run after T054.
- **Notes**: New artifacts authored by WP02-WP11 may appear as orphans until WP13 activates them. This is acceptable; "new artifact not yet activated" is not the same as "pre-existing artifact now disconnected."

### Subtask T056 – Wire new directives into agent profiles

- **Purpose**: Append directive IDs 043, 044, 045 to the relevant agent-profile `directives:` lists (C-002c). Without this, the new directives are inert for agent sessions.
- **Steps**:
  1. List all profile files: `ls src/doctrine/agent_profiles/built-in/*.agent.yaml`.
  2. For each profile, read its `directives:` list and `description` to understand its governance scope.
  3. Wire each directive into the EXPLICIT target profiles listed below. Do NOT leave profile selection to heuristics — the C-002c "not inert" DoD is only verifiable against this named list (reviewer will check the exact files):
     - **DIRECTIVE_043** (arch-gate / close-by-construction) → `implementer-ivan`, `python-pedro`, `architect-alphonso`, `doctrine-daphne`
     - **DIRECTIVE_044** (canonical-sources / unification) → `implementer-ivan`, `python-pedro`, `architect-alphonso`, `doctrine-daphne`
     - **DIRECTIVE_045** (PRs-only / read-intent / git-workflow) → `implementer-ivan`, `python-pedro`, and any profile that already carries directive `029` or `033`. Run the following to determine the full set:
       ```bash
       grep -l "\"029\"\|\"033\"\|'029'\|'033'" src/doctrine/agent_profiles/built-in/*.agent.yaml
       ```
       Mirror that result set for `045` — any profile that governs commit/staging/git operations and already carries 029 or 033 must also carry 045.
  4. For each relevant profile, append the directive ID(s) to its `directives:` list. Do NOT remove existing entries.
  5. Run `spec-kitty doctor doctrine --json` after edits to confirm all profiles remain valid.
- **Files**: `src/doctrine/agent_profiles/built-in/*.agent.yaml` (extend directives lists — see named profile list above)
- **Parallel?**: No — must run after T054.
- **Notes**: If a profile already carries one of the new directive IDs (unlikely but possible), do not add a duplicate. The DoD for this subtask requires naming the exact profile YAML files that were edited in the Activity Log — the reviewer will check the named list, not a vibe assessment.

### Subtask T057 – Final DoD verification

- **Purpose**: Confirm the mission-wide DoD is satisfied: all artifacts doctor-healthy, all tests green, all Python clean.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (across ALL mission artifacts, not just WP12's files).
  2. `pytest tests/doctrine/drg/ -q` → green (freshness + cycle + relations).
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. `ruff check` + `mypy` on any Python files touched in this WP (extractor, if modified).
  5. Confirm WP13 pre-conditions are met: `graph.yaml` regenerated + `tests/doctrine/drg/` green + all conversion WPs approved. Record in Activity Log.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `pytest tests/doctrine/drg/ -q` — the primary gate (freshness + cycle + relations).
- `spec-kitty doctor doctrine --json` — all artifacts mission-wide.
- `pytest tests/architectural/test_no_legacy_terminology.py -q`.
- `ruff check` + `mypy` on any Python touched.

## Risks & Mitigations

- **DRG generator gaps (#1755)**: the regeneration may not handle all inline edge types. If `pytest tests/doctrine/drg/` reveals a freshness failure after regen, check whether the generator correctly handles the edge kinds used by the new artifacts. If a generator gap is confirmed, file it as a tracking issue (reference #1755) and document a workaround — do not silently hand-edit `graph.yaml`.
- **Cycle introduced by forward references**: conversion WPs authored forward-reference edges to each other (e.g. WP07's tactic `requires` WP06's directive, WP09's 025 `suggests` WP02's ratchet tactic). These are fine as long as there is no back-edge creating a cycle. The cycle test in T054 will surface any cycle; trace the cycle back to the offending artifact YAML and remove the circular edge.
- **Profile over-wiring**: adding all three directives to all profiles indiscriminately. Read each profile's `description` field and `governance_scope` before appending. Some profiles are narrow in scope (e.g. a release-only or documentation-only profile should not carry DIRECTIVE_043 which is about AST gates). Match the directive's domain to the profile's domain.
- **Freshness failure after regen**: if the freshness test fails after regen, it means the committed `graph.yaml` does not match the generator's output. The fix is to commit the regenerated file, not to suppress the test. Run regen → commit → re-run tests.
- **Orphan worsening**: new artifacts without any referrers in `answers.yaml` or other activated artifacts may show as orphans. This is acceptable for WP12 (WP13 activates them). Pre-existing orphans that worsen indicate a regression — investigate.

## Dependency Notes

- WP12 is the serialized gate: ALL of WP02-WP11 must be `approved` before WP12 claims.
- WP12 enables WP13 — WP13 cannot start until `pytest tests/doctrine/drg/ -q` is green and `doctor doctrine --json` is healthy mission-wide.

## Review Guidance

- T053: `graph.yaml` is the output of `spec-kitty doctrine regenerate-graph` (the canonical CLI, not a direct `python` invocation of the extractor); not hand-edited.
- T054: `pytest tests/doctrine/drg/ -q` green — freshness + cycle + relations all pass.
- T055: orphan count ≤ pre-mission baseline; pre/post counts recorded in Activity Log.
- T056: directives 043/044/045 appended to the NAMED profiles (`implementer-ivan`, `python-pedro`, `architect-alphonso`, `doctrine-daphne` for 043+044; `implementer-ivan`, `python-pedro` plus grep-determined 029/033 carriers for 045). Exact profile files edited are listed in Activity Log. No existing entries removed.
- T057: `doctor doctrine --json` healthy mission-wide; terminology guard green; ruff/mypy clean.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:58:50Z – claude:sonnet:python-pedro:implementer – shell_pid=1968117 – Assigned agent via action command
- 2026-07-01T11:31:38Z – claude:sonnet:python-pedro:implementer – shell_pid=2068036 – Assigned agent via action command
- 2026-07-01T11:38:49Z – claude:sonnet:python-pedro:implementer – shell_pid=2068036 – Profiles wired; graph regenerated; DRG+compliance green; forward-refs resolved. Profiles edited: implementer-ivan (+043/044/045), python-pedro (+043/044/045), architect-alphonso (+043/044), doctrine-daphne (+043/044). DRG: 138 passed. Tactic compliance (incl. pr-agent-worktree-isolation forward-ref): 484 passed. Terminology guard: 3 passed. Doctor profile_health: healthy (18/18). Porcelain: only src/doctrine/agent_profiles/built-in/ and src/doctrine/graph.yaml changed.
- 2026-07-01T11:39:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2082932 – Started review via action command
- 2026-07-01T11:42:45Z – user – shell_pid=2082932 – WP12 met. C-003 scope: feat commit 3d2dbd3 touches ONLY 4 profiles + graph.yaml (207 insertions, 0 deletions; no directive/tactic/etc artifact edited). C-002c wiring: 043+044 -> implementer-ivan/python-pedro/architect-alphonso/doctrine-daphne; 045 -> implementer-ivan/python-pedro (no 029/033 carriers exist, so target set correct). Both context-sources.directives lists AND directive-references (name+rationale) updated -> not inert. regenerate-graph --check: FRESH/UP-TO-DATE (graph == extractor output, not hand-edited). DRG tests 138 passed; tactic_compliance 484 passed incl. test_references_resolve[pr-agent-worktree-isolation] via 045->tactic edge; terminology guard 3 passed; doctor doctrine profile_health healthy 18/18, 0 invalid. 13 new catfooding nodes present in regenerated graph (3 directives, 2 procedures, 1 styleguide, 6 tactics, 1 toolguide) with edges.
