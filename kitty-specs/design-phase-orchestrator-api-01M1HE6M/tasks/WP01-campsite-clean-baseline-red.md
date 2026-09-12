---
work_package_id: WP01
title: Campsite-clean + baseline-red snapshot
dependencies: []
requirement_refs:
- NFR-003
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-design-phase-orchestrator-api-01M1HE6M
base_commit: 7a996ce7b78df18df59375982d4494e13ac280fc
created_at: '2026-09-02T20:17:09.475814+00:00'
subtasks:
- T001
- T002
- T003
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/next_cmd.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/next_cmd.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Campsite-clean + baseline-red snapshot

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Before any functional WP starts: (1) baseline the mission's targeted test
directories against the pre-mission commit so later WPs can distinguish
issue #3284's ~23 known-red tests from anything this mission introduces
(NFR-003), and (2) fold the one domain-matched debt item plan.md's
campsite-clean pass already found in the files this mission is about to
touch (charter Standing Order #2 / `DIRECTIVE_025`). This WP must land
first — every other WP depends on it.

## Context

This is the mission's opening, behaviour-preserving WP — no functional
verb work happens here. Two independent, mechanically distinct
deliverables, both plan-time-scoped in `plan.md`:

- **Baseline-red snapshot** (plan.md § (f)): `main` carries ~23 known-red
  tests tracked as issue #3284, plus a shared test-venv lock that can time
  out under concurrency (issue #3283). Snapshot the mission's own targeted
  test directories against the pre-mission commit on
  `feat/design-phase-orchestrator-api-3837` (this mission's
  `planning_base_branch`, since the mission topology is `single_branch` —
  plan.md § (h)) so every later WP can cite "was this red already, or did
  I introduce it."
- **Campsite-clean** (plan.md § (g)): a quick pass at plan time found
  exactly ONE domain-matched debt item directly inside one of the three
  functions FR-014 (WP02) is about to promote to public, module-level
  surface: `_pair_previous_lifecycle_record` (`next_cmd.py:333-429`)
  contains an un-investigated `# type: ignore[arg-type]` suppression at
  `next_cmd.py:425`, on the `phase=phase` argument passed into
  `write_paired_completion(...)`. The other two functions WP02 extracts
  (`_emit_mission_next_invoked` at `next_cmd.py:863`,
  `_write_issuance_lifecycle_record` at `next_cmd.py:430`) are already
  clean — do not invent filler cleanup there. The module-level size of
  `next_cmd.py` itself (900+ lines) is a pre-existing characteristic not
  localized to the three extracted functions — explicitly NOT folded in
  here (would violate Locality of Change / turn this WP into a grab-bag).

**Why this WP must land first**: every other WP's ATDD RED test is
verified against the state THIS WP leaves behind. WP02 promotes
`_pair_previous_lifecycle_record` to a public module (`next_invocation_lifecycle.py`)
immediately after this WP — the suppression must be resolved or justified
BEFORE it becomes public API, not carried forward silently.

## Subtask T001: Baseline-red snapshot

**Purpose**: Establish which tests are already red on `main`/this mission's
pre-change commit, so WP02–WP09 can each state "N pre-existing reds
observed, 0 introduced" instead of re-deriving issue #3284 from scratch.

**Steps**:
1. Confirm the current commit is the mission's pre-change baseline (no
   functional edits yet on this branch beyond planning artifacts).
2. Run each targeted directory named in plan.md § (e) Gate Set item 3,
   recording full pass/fail/error counts and the individual failing test
   node ids:
   - `pytest tests/specify_cli/orchestrator_api/ -v`
   - `pytest tests/specify_cli/cli/commands/test_next_answer_effective_root.py tests/specify_cli/cli/commands/test_next_fail_closed.py tests/specify_cli/cli/commands/test_next_owned_commit_guard.py tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py -v`
   - `pytest tests/architectural/test_shared_package_boundary.py tests/architectural/test_runtime_charter_doctrine_boundary.py -v`
3. Cross-reference each failing node id against issue #3284 (`gh issue view 3284`).
   Do NOT open a new issue for anything that matches — NFR-003 is explicit
   that #3284's pre-existing reds are not this mission's concern to fix.
   Any failure that does NOT obviously match #3284's known set must be
   reported per the charter's "Pre-existing Failure Reporting Rule" (open a
   GitHub issue with the command run, the failure summary, and why it's
   believed pre-existing) BEFORE treating it as baseline context.
4. Record the full snapshot (counts + node ids + #3284 cross-reference) in
   `kitty-specs/design-phase-orchestrator-api-01M1HE6M/tracer-tooling-friction.md`
   (append, do not overwrite the existing entries) so it is durably
   available to every later WP's reviewer.

**Files**: `kitty-specs/design-phase-orchestrator-api-01M1HE6M/tracer-tooling-friction.md` (append only — this is a planning artifact, not `owned_files`-tracked code).

**Validation**: The tracer file entry lists exact counts and node ids, not
just "some tests are red" — a later WP's reviewer must be able to diff
their own local run against this snapshot without re-running #3284's
investigation.

## Subtask T002: Resolve or justify the `next_cmd.py:425` type suppression

**Purpose**: `_pair_previous_lifecycle_record` becomes a public,
module-level function in WP02 (`next_invocation_lifecycle.py`). A bare,
un-investigated `# type: ignore[arg-type]` is not acceptable on surface
that's about to be promoted to a shared contract — resolve it now, while
the function is still private and low-risk to touch.

**Steps**:
1. Read `next_cmd.py:333-429` and `write_paired_completion`'s signature in
   `src/specify_cli/invocation/lifecycle.py` to see the exact declared type
   of its `phase` parameter vs. the local `phase: str` this function
   computes (`next_cmd.py:414-419`: `phase: str = "completed"` or
   `phase = "failed"`).
2. **Preferred fix**: if `write_paired_completion`'s `phase` parameter is a
   `Literal["completed", "failed"]` (or similar narrow type) and the local
   `phase` variable can be narrowed to match (e.g. via a `Literal` type
   annotation on the local variable, or restructuring the two branches to
   each pass a literal directly), do that and delete the
   `# type: ignore[arg-type]` comment entirely. Run `mypy --strict` on
   `next_cmd.py` to confirm the suppression is genuinely no longer needed.
3. **Fallback** (only if genuine narrowing is non-trivial — e.g. the
   parameter's declared type is intentionally broader for reasons outside
   this WP's scope): keep the suppression but replace the bare comment with
   an inline justification per this repo's `CLAUDE.md` code-style rule
   ("narrowly-scoped, individually-justified suppressions... must carry an
   inline rationale"), e.g.
   `# type: ignore[arg-type]  # write_paired_completion's phase param is
   typed <X>; narrowing this local requires <reason>, tracked as a
   pre-existing characteristic, not this WP's scope to fix`.
4. State explicitly in this WP's own commit message and in
   `tracer-design-decisions.md` which of the two (narrow vs. justify) was
   chosen and why — carrying the suppression forward silently is not
   acceptable now that the function becomes public surface (per plan.md
   § (g)'s explicit instruction).
5. If your own closer read (more time than the plan-phase pass) finds any
   further genuine, narrowly-scoped debt item directly inside one of the
   three functions' bodies, fold it in with a one-line rationale — do not
   invent filler cleanup to pad this WP.

**Files**: `src/specify_cli/cli/commands/next_cmd.py` (~1-5 line change).

**Validation**: `mypy --strict src/specify_cli/cli/commands/next_cmd.py`
passes; if the suppression was kept, it now carries a rationale comment
inline, not a bare `# type: ignore[arg-type]`.

## Subtask T003: Record findings

**Purpose**: Close the loop — this WP's findings must be visible to WP02
(which immediately builds on this file) and to the mission's later review
squad without re-deriving them.

**Steps**:
1. Append a dated entry to `tracer-design-decisions.md` naming: (a) the
   T002 resolution (narrow vs. justify, with the concrete reasoning), and
   (b) confirmation that `orchestrator_api/commands.py` and `envelope.py`
   were spot-checked and found already `ruff`/`mypy`-clean in the functions
   WP03–WP08 will extend (per plan.md § (g)'s own spot-check — re-confirm
   it still holds at WP01's actual run time, since time has passed since
   the plan was written).
2. If the re-confirmation in (b) finds the spot-check no longer holds
   (e.g. an intervening commit introduced a suppression), report that
   explicitly as a new finding — do not silently update WP03–WP08's scope
   without flagging it to the orchestrator.

**Files**: `kitty-specs/design-phase-orchestrator-api-01M1HE6M/tracer-design-decisions.md` (append).

## ATDD Note (this WP is the one exception to the RED-test pattern)

This WP is explicitly **behaviour-preserving, no functional test to drive**:
T001 is a diagnostic run (not a code change), and T002's fix is a type-only
change with no behavioural surface (the existing runtime tests already
cover `_pair_previous_lifecycle_record`'s behavior; `mypy --strict` is the
"test" that must go from failing-suppression-masked to genuinely clean).
Per plan.md § (h), every WP lands as at minimum a RED-then-GREEN commit
pair; for WP01 that pair is: commit 1 = the baseline-red snapshot recorded
in the tracer file (a diagnostic artifact, not a test), commit 2 = the
T002 fix + `tracer-design-decisions.md` entry. There is no new pytest test
authored by this WP — do not invent one to force-fit the ATDD pattern
where the work genuinely has no new behavior to pin (this would itself be
the "vacuous test" anti-pattern the charter warns against).

## Write-Scope / Adjacent Open PRs

`src/specify_cli/cli/commands/next_cmd.py` is not touched by any of the
three adjacent open PRs named in this mission's tasks-authoring brief
(#3842, #3826, #3836) — no rebase-risk note applies to WP01's own file.
WP02 (which depends on this WP and touches the same file) carries the
`next_cmd.py`-related chokepoint note.

## Definition of Done

- [ ] Baseline-red snapshot recorded in `tracer-tooling-friction.md` with
      exact counts + node ids for all targeted directories, cross-referenced
      against issue #3284.
- [ ] Any non-#3284-matching failure reported as its own GitHub issue per
      the charter's Pre-existing Failure Reporting Rule, BEFORE being
      treated as baseline.
- [ ] `next_cmd.py:425`'s type suppression resolved (narrowed) or justified
      (inline rationale comment) — never carried forward silently.
- [ ] `mypy --strict src/specify_cli/cli/commands/next_cmd.py` passes.
- [ ] `tracer-design-decisions.md` records the T002 resolution and the
      re-confirmed spot-check of `commands.py`/`envelope.py`.
- [ ] Two commits: baseline-snapshot commit, then the T002 fix commit.

Run: `spec-kitty agent action implement WP01 --agent <name>`

## Risks

- **Baseline drift**: if other work has landed on `main`/this branch
  between plan-time and WP01's actual run, the ~23-red-test count from
  plan.md § (f) may be stale. Re-verify against issue #3284's CURRENT state
  (`gh issue view 3284`), don't trust the plan's cited number blindly.
- **Suppression narrowing risk**: an overly-aggressive narrowing of
  `phase`'s type could silently change `write_paired_completion`'s runtime
  behavior if the two are not actually type-compatible today. Run the
  existing lifecycle-record test surface
  (`tests/specify_cli/cli/commands/test_next_*.py`) after the T002 change,
  not just `mypy`, to confirm no behavioural regression.

## Reviewer Guidance

- Confirm the baseline-red snapshot is a REAL run output (exact counts,
  real node ids), not an assertion "matches plan.md's ~23."
- Confirm T002's resolution is genuinely one of narrow-fix or
  justify-with-rationale — a bare `# type: ignore[arg-type]` surviving
  unchanged is a WP01 rejection.
- Confirm no drive-by refactor beyond the T002 scope landed in
  `next_cmd.py` (Locality of Change — this WP is deliberately narrow).
