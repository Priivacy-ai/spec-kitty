---
work_package_id: WP06
title: Orphan-lint fix + cascade exclusion regression
dependencies:
- WP01
- WP02
requirement_refs:
- FR-008
- FR-013
- NFR-003
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
phase: Phase 3 - Checkup surface
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "99017"
shell_pid_created_at: "1784646636.283409"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/lint/checks/orphan.py
create_intent:
- tests/charter/test_tension_cascade_exclusion.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/charter_runtime/lint/checks/orphan.py
- tests/specify_cli/charter_lint/checks/test_orphan.py
- tests/charter/test_cascade.py
- tests/charter/test_tension_cascade_exclusion.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Orphan-lint fix + cascade exclusion regression

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/specify_cli/charter_runtime/lint/checks/orphan.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## Objectives & Success Criteria

Two independent fixes bundled because both are "checkup surface" concerns with no shared code:

Done means:
- `charter lint`'s `orphaned_directive` findings equal **exactly** `{DIRECTIVE_035, DIRECTIVE_039}` — count == 2, zero false positives (FR-008, closes #2737).
- A regression test proves `{IN_TENSION_WITH, RECONCILES_TENSION, REJECTS}` stay absent from `cascade.REFERENCE_RELATIONS` (FR-013).
- A regression test proves activating one side of a tension never auto-activates the other, and activating a reconciler never activates the pair it reconciles (INV-003).

## Context & Constraints

- **Verified fact, do not "fix" this**: `src/charter/cascade.py::REFERENCE_RELATIONS` is `frozenset({Relation.REQUIRES, Relation.SUGGESTS, Relation.REFINES})` today. The three new relations achieve exclusion **by never being added to this set** — there is no code change required for T032, only a test that proves the omission holds and stays held. Do not add a denylist check to `cascade.py`; that would reintroduce the per-kind branching the engine's design (C-003) deliberately avoids.
- `src/specify_cli/charter_runtime/lint/checks/orphan.py` (verified): `_ORPHAN_RULES` maps `"directive": ("directive", {"governs"})` and `"adr": ("adr", {"supersedes", "references"})`. Neither `"governs"` nor `"supersedes"` is a member of the `Relation` enum (confirmed by reading `src/doctrine/drg/models.py`'s `Relation` class) — these are phantom expected-inbound-relations that can never actually be satisfied, which is exactly why every built-in directive with no OTHER inbound relation gets flagged.
- This WP depends on WP01 (relations must exist to assert their absence) and WP02 (INV-003's test needs the real tension/reconciler edges to exist).

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP06 --agent <name>` (depends on WP01, WP02).

## Subtasks & Detailed Guidance

### Subtask T030 – Remove the phantom orphan-lint branches

- **Purpose**: FR-008 — stop flagging every built-in directive as orphaned due to an unsatisfiable expected relation.
- **Steps**:
  1. In `src/specify_cli/charter_runtime/lint/checks/orphan.py`, remove the `"directive": ("directive", {"governs"})` entry from `_ORPHAN_RULES`.
  2. Remove the `"adr": ("adr", {"supersedes", "references"})` entry too — spec.md FR-008 names both the `governs` (directive) and `supersedes` (adr) branches as phantom; confirm whether `"references"` in that same tuple is a real relation (it may be — check the `Relation` enum) before deciding whether to drop the whole `"adr"` entry or just the `supersedes` half. If `"references"` turns out to be real and load-bearing, keep the `"adr"` rule but narrow it to `{"references"}` only — do not blanket-delete a rule that partially still applies.
  3. Update the module docstring (lines ~9-10 as of plan time) that documents the expected-inbound-relation mapping — remove the `governs`/`supersedes` lines from the docstring too, per FR-008's explicit mention of "module docstring references."
  4. Confirm this does **not** yield 0 findings (deleting the directive branch outright yielding 0 findings is explicitly NOT acceptable per spec.md FR-008) — the two genuinely-orphaned directives (`DIRECTIVE_035`, `DIRECTIVE_039`, which have zero incoming edges of any kind) must still be flagged after your change.
- **Files**: `src/specify_cli/charter_runtime/lint/checks/orphan.py`
- **Parallel?**: Yes, relative to T032/T033 (different files).

### Subtask T031 – Orphan-lint exact-set test

- **Purpose**: NFR-003 — "the orphan set is exact, not just bounded... NOT merely `≤ 2` (which 0 would satisfy by deleting the rule)."
- **Steps**: Extend `tests/specify_cli/charter_lint/checks/test_orphan.py` with an assertion that running the orphan check against the built-in layer produces a finding set **equal to** `{"DIRECTIVE_035", "DIRECTIVE_039"}` (exact set equality, not `<=`, not `len() <= 2`) — and that neither directive referenced via `scope`/`requires`/`suggests` (or any other real relation) appears.
- **Files**: `tests/specify_cli/charter_lint/checks/test_orphan.py`
- **Parallel?**: Yes, relative to T032/T033.
- **Notes**: Write this as an exact-equality assertion (`assert findings == {"DIRECTIVE_035", "DIRECTIVE_039"}`), specifically because a `<=` or `len()` check would pass even if T030 accidentally over-deleted and produced 0 findings — that failure mode is explicitly named in NFR-003.

### Subtask T032 – Cascade `REFERENCE_RELATIONS` exclusion regression test

- **Purpose**: FR-013 — the test IS the deliverable (exclusion is by omission, there's no code to write).
- **Steps**: In `tests/charter/test_cascade.py`, add: `assert {Relation.IN_TENSION_WITH, Relation.RECONCILES_TENSION, Relation.REJECTS} & cascade.REFERENCE_RELATIONS == frozenset()`. Import `Relation` from `src/doctrine/drg/models.py` and `REFERENCE_RELATIONS`/module from `src/charter/cascade.py`.
- **Files**: `tests/charter/test_cascade.py`
- **Parallel?**: Yes.
- **Notes**: Do not write this as "no crash when cascading over a graph containing these relations" — that would pass vacuously. It must be the explicit frozenset-intersection assertion.

### Subtask T033 – Cascade non-auto-activation regression test (INV-003)

- **Purpose**: Behavioral proof that the exclusion in T032 actually matters at the CLI/cascade level, not just at the data-structure level.
- **Steps**: In new `tests/charter/test_tension_cascade_exclusion.py`: using WP02's real built-in tension pair (`directive:DIRECTIVE_024`/`DIRECTIVE_025`), assert that activating `DIRECTIVE_024` alone does not auto-activate `DIRECTIVE_025` via cascade, and that activating `reconcile-change-scope-tensions` does not auto-activate any of the three artefacts it reconciles. Use whatever cascade-invocation entry point existing tests in `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_*.py` use, for consistency.
- **Files**: `tests/charter/test_tension_cascade_exclusion.py` (new)
- **Parallel?**: Yes, relative to T030/T031.

## Test Strategy

- `.venv/bin/pytest tests/specify_cli/charter_lint/checks/test_orphan.py tests/charter/test_cascade.py tests/charter/test_tension_cascade_exclusion.py -q`
- `.venv/bin/ruff check` + `.venv/bin/mypy` on `owned_files`.

## Risks & Mitigations

- **Risk**: T030 over-deletes the `adr`/`supersedes` rule if `"references"` turns out to be a real, still-needed relation. **Mitigation**: explicitly called out as a check-before-delete step in T030.
- **Risk**: T032/T033 written as smoke tests that pass regardless of the actual exclusion. **Mitigation**: both subtasks specify the exact assertion shape required.

## Review Guidance

- Confirm `orphaned_directive` findings are exactly `{DIRECTIVE_035, DIRECTIVE_039}` — run the lint command yourself, don't just trust the test.
- Confirm `src/charter/cascade.py` itself was not modified in this WP (no source change needed, only tests).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP06 --to <status>` to change WP status.
- 2026-07-21T14:28:43Z – claude:sonnet:python-pedro:implementer – shell_pid=93054 – Assigned agent via action command
- 2026-07-21T14:49:36Z – claude:sonnet:python-pedro:implementer – shell_pid=93054 – Ready for review: orphan-lint fixed (exactly {DIRECTIVE_035, DIRECTIVE_039} verified against real built-in DRG + spec-kitty charter lint), cascade exclusion regression tests added (T032 data-level, T033 CLI-behavioral).
- 2026-07-21T15:10:40Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=99017 – Started review via action command
- 2026-07-21T15:14:50Z – user – shell_pid=99017 – Review passed. Verified independently: (1) orphan.py's _ORPHAN_RULES now maps directive -> {scope,requires,suggests,applies,refines}, adr rule fully removed (neither governs/supersedes/references is a Relation enum member per src/doctrine/drg/models.py, confirmed by reading it). (2) Ran 'spec-kitty charter lint' live: exactly 2 findings, DIRECTIVE_035 and DIRECTIVE_039, zero orphaned_adr findings. (3) Manually inspected the built-in DRG: RECONCILE_CHANGE_SCOPE_TENSIONS has zero incoming edges of any kind but an outgoing reconciles_tension edge to DIRECTIVE_024/025/change-apply-smallest-viable-diff -- correctly exempted by the new outgoing-edge check. DIRECTIVE_035/DIRECTIVE_039 have zero incoming AND zero outgoing edges (no reconciles_tension), so the exemption legitimately does not apply to them -- they are flagged for the right reason. (4) T031 uses exact set equality (==). (5) T032 is the explicit frozenset-intersection assertion; confirmed cascade.py has zero diff (last touched by unrelated commit bb5ddb849). (6) T033 exercises the real CLI (charter activate --cascade all) against real built-in fixtures, not mocks -- proves DIRECTIVE_024 activation doesn't cascade to DIRECTIVE_025, and reconciler activation doesn't cascade to any of the 3 reconciled artefacts. (7) Ran tests/specify_cli/charter_lint/ + test_cascade.py + test_tension_cascade_exclusion.py myself: 101 passed. (8) ruff + mypy clean on orphan.py. (9) No manual_review/bulk-edit gate applies to this WP's 4 files -- none reference opposed_by/Contradiction, confirmed via grep. Assessment of the reconciler-exemption design: this is principled, not a hack tuned to hit a count. It corrects a real category error (an incoming-edge-only orphan check applied to a relation, reconciles_tension, that is structurally always outbound from the reconciler) rather than special-casing WP02's specific directive URN. The exemption is expressed generically (_SELF_EXEMPTING_OUTGOING_RELATIONS keyed by node kind + relation), so it will correctly exempt any future reconciler, and does not accidentally suppress the two genuine orphans, which independently lack both incoming edges and any outgoing reconciles_tension edge.
