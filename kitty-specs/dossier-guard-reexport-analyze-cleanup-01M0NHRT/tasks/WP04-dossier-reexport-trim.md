---
work_package_id: WP04
title: Trim dossier CLI re-export surface (FR-005)
dependencies: []
requirement_refs:
- FR-005
- NFR-004
- C-002
planning_base_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
merge_target_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
branch_strategy: Planning artifacts for this mission were generated on fix/dossier-guard-reexport-analyze-cleanup-3676. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/dossier-guard-reexport-analyze-cleanup-3676 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dossier-guard-reexport-analyze-cleanup-01M0NHRT
base_commit: a513bcf27bc2678ab280e3462dbd9e8d14760b06
created_at: '2026-08-23T00:16:39.352551+00:00'
subtasks:
- T013
- T014
- T015
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/__init__.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/__init__.py
role: implementer
tags: []
tracker_refs: []
---

# WP04: Trim dossier CLI re-export surface (FR-005)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix GitHub issue #3677: remove the seven `spec_kitty_events` type re-exports —
`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`, and the four
`MissionDossier*Payload` types (`MissionDossierArtifactIndexedPayload`,
`MissionDossierArtifactMissingPayload`, `MissionDossierSnapshotComputedPayload`,
`MissionDossierParityDriftDetectedPayload`) — from both the `from .events import (...)`
statement and `__all__` in `src/specify_cli/dossier/__init__.py`, leaving the four `emit_*`
function re-exports (`emit_artifact_indexed`, `emit_artifact_missing`, `emit_snapshot_computed`,
`emit_parity_drift_detected`) completely untouched. The result is exactly ONE canonical import
path per type — directly from `spec_kitty_events`, the charter's declared external contract
package — instead of two, restoring the charter's single-canonical-authority governing
principle for this surface.

## Mission-wide baseline — confirm before your first commit

This mission's baseline capture command spans all five touched test files and must run once,
before the FIRST implementation commit of the WHOLE MISSION (not per-WP). WP01 (sequenced
first) owns primary responsibility for capturing it. Before your own first commit in this WP:
confirm the mission-wide baseline was already captured — check
`kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/tracer-tooling-friction.md` for an
F-0N entry recording it. If not present, run it now yourself and record the result in
`tracer-tooling-friction.md` (append, never overwrite; otherwise follow the existing entries'
format) BEFORE proceeding. The exact command:

**Concurrency note (all four WPs in this mission are `dependencies: []` / `parallel_group: 0` and
may be dispatched to genuinely concurrent worktrees):** `tracer-tooling-friction.md` is a single
shared file that is intentionally NOT listed in any WP's `owned_files`/lane `write_scope` — this
was investigated during the fix pass that added this note: adding it there would make
`_globs_overlap`'s exact-path-equality rule treat every WP pair as write-scope-overlapping, and
`compute_lanes`/`validate_ownership` would then either collapse all four independent lanes into
one or reject the manifest outright as an ownership conflict at `finalize-tasks --validate-only`
— both strictly worse than the race this note addresses, since either would destroy this
mission's intentional four-way parallelism. Because two WPs racing this check-then-act baseline
capture could both independently conclude "not present" and append competing entries, if YOU are
the WP that finds the baseline genuinely not yet captured, append it under a fresh
UTC-timestamped heading — `## F-<UTC-timestamp, e.g. 2026-08-23T00:12:04Z> — <title>` — instead of
a guessed sequential `F-0N` number, so two genuinely concurrent appends cannot collide on the same
heading even without a file lock or inter-agent coordination. Do not renumber or touch any other
WP's entry. **(Added round-2, TASKS-FRESH-003.)** The timestamp only guarantees the appended
section's *heading text* won't collide — it does NOT prevent a literal `git` merge conflict on
this shared, untracked-by-any-lane file when two WP branches that both appended to it are
combined; that conflict remains possible and expected under real concurrency. Whoever lands second
and hits it must resolve by **keeping both entries** (never discarding one) — a normal two-way
content merge on an append-only file, not a conflict requiring judgment about which append "wins."

```bash
pytest tests/architectural/test_dossier_emitter_positional_guard.py \
       tests/dossier/test_events.py \
       tests/architectural/test_no_dead_symbols.py \
       tests/specify_cli/test_analysis_report.py \
       tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q
```

**Disposition rule (restate)**: red genuinely inside issue #3284's known ~23-failures-+2-errors
set → cite #3284, file nothing. Red OUTSIDE #3284's set → file a new GitHub issue (charter §486,
binding absolutely per spec.md's corrected precedence: charter > operator standing orders >
CLAUDE.md) — not optional, not an operator-escalation candidate for this specific case.

## Context

**(a) Where this WP sits in the mission.** This WP is IC-02 in plan.md's Implementation Concern
Map — fully independent of IC-01 (dossier guard widening) and IC-03 (the other two WPs, covering
the commit-subject and path-relativization fixes). `dependencies: []` reflects that: nothing in
this WP's diff touches, or is touched by, any other WP's owned files.

**(b) §106 change-scope reconciliation.** Citing spec.md's §106 section and plan.md's own §106
table directly (restated here, not re-derived): `src/specify_cli/dossier/__init__.py` is touched
because it is "#3677's own named defect; the sole surface with the duplicate import path."
Tracker reference: #3677.

**(c) Why this is P2, not P1.** Per spec.md's User Story 3: the charter's single-canonical-
authority governing principle is violated by construction today, but the defect is inert (zero
callers use the second path) rather than actively harmful, so it is P2 relative to the two P1
stories in this mission (the dossier-guard widening and the commitlint/path-leak fix).

**(d) Grounding Correction 2 — the dead-symbol gate's self-referential loop (read this in
full before touching the file).** The mission brief attributed the dead-symbol gate's blind spot
to `src/specify_cli/dossier/events.py`'s own `from spec_kitty_events import (ArtifactIdentity,
...)` line. Tracing `_symbol_has_caller()`'s three rescue rules
(`tests/architectural/test_no_dead_symbols.py:2432-2471` — confirm this line range against the
live file) against the actual import graph shows the real mechanism is one hop further out: it is
`src/specify_cli/dossier/__init__.py`'s OWN `from .events import (ArtifactIdentity,
ContentHashRef, ...)` (confirm current line numbers — as of this WP's authoring, lines 28-40) that
populates the gate's internal `per_symbol["specify_cli.dossier.events"]` set with these seven
names. Rule 3 ("re-export via any submodule") then reads that SAME set back to "rescue"
`specify_cli.dossier.__all__`'s inclusion of those same names — a fully self-referential loop
with ZERO external caller anywhere in it. (`events.py`'s own import from `spec_kitty_events` is
unrelated to this rescue; `spec_kitty_events` is not a submodule of `specify_cli.dossier` and
never enters rule 3's candidate set.)

This means `tests/architectural/test_no_dead_symbols.py` gives ZERO signal either way about this
removal — it is currently green not because it validates the re-export is safe, but because the
self-referential loop always resolves green regardless of whether the seven names are actually
called from anywhere real. It is re-run in T013/T015 purely as an empirical confirmation per
§581 ("the gate is currently green... See the Grounding Correction... for the precise... mechanism
and why the gate will still be green — because it will have nothing to check — after their
removal"), not because it is expected to catch anything.

## Subtask T013: Capture BEFORE-state evidence (SC-003 grep, SC-004 dead-symbol gate, tests/dossier/test_events.py)

**Purpose**: establish the empirical BEFORE baseline this dead-code removal's acceptance criteria
are BEFORE/AFTER invariant checks against — not a new failing-then-passing test (see the explicit
ATDD-non-applicability statement below).

**Steps**:

(a) Run `grep -rn "from specify_cli.dossier import" src/ tests/`, filter to the seven type names
(`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`,
`MissionDossierArtifactIndexedPayload`, `MissionDossierArtifactMissingPayload`,
`MissionDossierSnapshotComputedPayload`, `MissionDossierParityDriftDetectedPayload` — confirm
these are the exact seven names in the live file before proceeding), confirm ZERO matches
(SC-003's BEFORE half).

(b) Run `pytest tests/architectural/test_no_dead_symbols.py -q`, confirm it passes (SC-004's
BEFORE half — spec.md states this was empirically re-run at spec time: 26 passed, 2026-08-22 —
re-confirm it is still green now, not stale).

(c) Run `pytest tests/dossier/test_events.py -q`, confirm it passes (this is the sole existing
test-suite consumer of the seven names, and per spec.md it already imports them directly from
`spec_kitty_events`, never via `specify_cli.dossier` — confirm this by reading the test file's
imports yourself, don't just assume it: check for a `from spec_kitty_events import (...)` line
naming the seven types, and confirm there is no `from specify_cli.dossier import` line anywhere
in the file naming any of them — the file's only `specify_cli.dossier.*` import should be `from
specify_cli.dossier.events import (emit_artifact_indexed, ...)`, the submodule directly, not the
package).

**Files**: none changed; verification only.

**Validation**: all three checks above pass/confirm as described; results recorded for
comparison against T015's AFTER state. T013 completion recorded via
`spec-kitty agent tasks mark-status T013 --status done`.

## Subtask T014: Remove the seven type re-exports from `dossier/__init__.py`

**Purpose**: implement the actual fix.

**Steps**: in `src/specify_cli/dossier/__init__.py`, remove the seven type names
(`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`,
`MissionDossierArtifactIndexedPayload`, `MissionDossierArtifactMissingPayload`,
`MissionDossierSnapshotComputedPayload`, `MissionDossierParityDriftDetectedPayload` — confirm
exact names from the live file before editing) from BOTH:

(a) the `from .events import (...)` statement, and
(b) the `__all__` list.

Leave the four `emit_*` function re-exports (`emit_artifact_indexed`, `emit_artifact_missing`,
`emit_snapshot_computed`, `emit_parity_drift_detected`) — both their import statement lines and
their `__all__` entries — completely UNTOUCHED (C-002; their real callers in
`sync/dossier_pipeline.py` and `dossier/drift_detector.py` are out of scope and must not be
modified).

Confirm `src/specify_cli/dossier/events.py` itself is NOT touched by this WP (spec.md User
Story 3 AC2 — its own `from spec_kitty_events import (...)` used to construct its own payload
objects stays exactly as-is).

Per spec.md's Key Entities section: `__all__` currently has 27 entries; after removing 7, it
should have 20 — verify this count as a sanity check.

**Files**: `src/specify_cli/dossier/__init__.py` (two edits: the import statement and `__all__`).

**Validation**: `grep -c` or manual read confirms exactly 20 entries remain in `__all__`; the
four `emit_*` names are still present in both the import statement and `__all__`; `events.py` has
zero diff (`git diff --stat -- src/specify_cli/dossier/events.py` reports nothing).

## Subtask T015: Capture AFTER-state evidence and confirm zero regressions (SC-003, SC-004 re-run)

**Purpose**: empirically confirm the removal is a true no-op for every existing caller — not
assumed, re-run.

**Steps**:

(a) Re-run `grep -rn "from specify_cli.dossier import" src/ tests/`, filtered to the seven
removed names, confirm STILL zero matches (SC-003's AFTER half — should be unchanged from T013,
since removing dead code cannot create a new caller).

(b) Re-run `pytest tests/architectural/test_no_dead_symbols.py -q`, confirm it STILL passes
(SC-004's AFTER half, NFR-004) — per Grounding Correction 2, this is expected to stay green not
because the gate validates the removal, but because the seven names are no longer declared in
`__all__` at all, so the gate has nothing to check for them.

(c) Re-run `pytest tests/dossier/test_events.py -q`, confirm it STILL passes unmodified (spec.md
User Story 3 AC3).

(d) Confirm no other test in the suite imports these seven names via `specify_cli.dossier` (the
T013 grep already covers this across `src/` and `tests/`, but re-confirm after the edit
specifically — the grep command and its zero-match result should be identical to T013's).

**Files**: none new; verification only.

**Validation**: all three re-run checks pass with identical BEFORE/AFTER results (grep zero both
times, both test suites green both times); T015 completion recorded via
`spec-kitty agent tasks mark-status T015 --status done`.

## ATDD applicability — explicit statement (why literal RED-first does NOT apply here)

This is a dead-code REMOVAL with no new observable behavior — there is no new feature or branch
to prove RED-then-GREEN against. The acceptance criteria (SC-003's zero-callers grep, SC-004's
dead-symbol-gate-stays-green check, `tests/dossier/test_events.py` staying green) are
BEFORE/AFTER invariant checks (T013 vs T015), not a new failing-then-passing test. Charter
C-011's ATDD-first discipline is honored here through the BEFORE/AFTER empirical confirmation
structure (T013→T014→T015) rather than a RED/GREEN test pair, because the change being verified
is an absence of regression, not a new capability. Do not fabricate a fake RED-first step to
force-fit the pattern — there is no code path anywhere in this WP that is expected to fail before
the change and pass after it.

## §106 change-scope reconciliation for this WP

Citing spec.md's §106 section and plan.md's own §106 table directly (restated, not re-derived):
`src/specify_cli/dossier/__init__.py` is touched because it is "#3677's own named defect; the
sole surface with the duplicate import path." Tracker reference: #3677.

## Definition of Done

- [ ] Mission-wide baseline confirmed captured — either an existing F-0N entry found in
      `tracer-tooling-friction.md`, or (if absent) captured here and recorded under a fresh
      UTC-timestamped heading per the "Mission-wide baseline" section's concurrency note, before
      your first commit.
- [ ] T013 BEFORE-state evidence captured: SC-003 grep zero matches, SC-004 dead-symbol gate
      green, `tests/dossier/test_events.py` green and confirmed to import the seven types only
      from `spec_kitty_events`, never via `specify_cli.dossier`.
- [ ] T014: the seven type names removed from both the `from .events import (...)` statement and
      `__all__` in `src/specify_cli/dossier/__init__.py`; the four `emit_*` names untouched in
      both places; `events.py` has zero diff.
- [ ] `__all__` has exactly 20 entries (27 minus 7).
- [ ] T015 AFTER-state evidence re-confirms zero regressions: SC-003 grep still zero matches,
      SC-004 dead-symbol gate still green, `tests/dossier/test_events.py` still green.
- [ ] BEFORE and AFTER results are identical across all three checks (no new failures, no new
      matches).

## Risks

Low risk, per plan.md's IC-02 entry: "verified zero external callers (SC-003); the dead-symbol
gate's self-referential blind spot (Grounding Correction 2) means it gives zero signal either way
and is re-run purely as an empirical confirmation, not because it is expected to catch anything."
The main risk is an undiscovered external (non-spec-kitty) downstream consumer package importing
these types via `specify_cli.dossier` — spec.md's Edge Cases section explicitly accepts this risk
per #3677's finding and the charter's single-canonical-authority principle taking precedence over
an unverified/unused compatibility surface.

## Reviewer Guidance

Reviewers should specifically:

- Confirm the diff touches ONLY the import statement and `__all__` in `dossier/__init__.py` — no
  other line changed.
- Confirm the four `emit_*` names (`emit_artifact_indexed`, `emit_artifact_missing`,
  `emit_snapshot_computed`, `emit_parity_drift_detected`) are present, unchanged, in both the
  import statement and `__all__`.
- Confirm `events.py` has zero diff (`git diff --stat -- src/specify_cli/dossier/events.py`).
- Independently re-run the T013/T015 BEFORE/AFTER checks themselves rather than trusting the
  WP's own report — the grep and both pytest invocations are cheap and fast to reproduce.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent claude
```
