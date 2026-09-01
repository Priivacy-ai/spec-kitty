---
work_package_id: WP02
title: Cascade-activation report renders kind-filtered nodes
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-008
- FR-009
- C-002
- NFR-002
- NFR-004
planning_base_branch: fix/cascade-asset-silent-drop-3705
merge_target_branch: fix/cascade-asset-silent-drop-3705
branch_strategy: Planning artifacts for this mission were generated on fix/cascade-asset-silent-drop-3705. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cascade-asset-silent-drop-3705 unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/activate.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/charter/activate.py
- tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Cascade-activation report renders kind-filtered nodes

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface`
(`src/specify_cli/cli/commands/charter/activate.py`).

---

## ⚠️ Mission-wide instructions (restated briefly — full text lives in WP01)

- **Baseline discipline applies to this WP too**: re-run the scoped baseline
  command from WP01's prompt file (`tasks/WP01-shared-collection-seam.md`,
  "Mission-wide instructions" item 1) before your first commit and after your
  final commit; diff against the baseline captured in WP01.
- **FR-006 is not implemented by this WP** (or any WP) — see WP01's prompt for
  the full rationale. Do not add PR-body or ADR-citation logic here.
- **No campsite-clean commit is warranted anywhere in this mission** (plan.md
  §8) — do not invent one.
- **This WP depends on WP01 and must not start until WP01's final commit is
  merged/available**: this WP reads `CascadeActivationResult.not_cascaded_kind_filtered`,
  a field WP01 introduces. Do not begin implementation before verifying that
  field exists on your base commit.
- **Ownership overlap note**: this WP and WP03 both own
  `src/specify_cli/cli/commands/charter/activate.py`. This is expected and
  correct — WP01 → WP02 → WP03 → WP04 is a strict sequential chain (not
  parallelizable), and `finalize-tasks`'s ownership validator exempts
  same-lane sequential pairs from the no-overlap check.

---

## Objective

Add the FR-009 shared rendering helper (its first definition, in `activate.py`),
call it from `_render_cascade_activation` to print one line per kind-filtered
node (FR-003), and add the FR-004 explicit zero-activatable-targets message with
the exact, scoped trigger condition that avoids conflating it with pure
scope-narrowing (FR-008, SC-007). This is the first WP with any user-visible
console change.

## Context

`_render_cascade_activation` (`activate.py:274-338`) currently renders
`Cascade-activated:` lines and `Skipped (out of scope)` lines from
`CascadeActivationResult.activated` / `.skipped_by_scope`. WP01 added
`.not_cascaded_kind_filtered` with real data but nothing renders it yet — this
WP is that renderer.

**FR-009's shared helper — the exact decision from plan.md §2.** All three
render call sites across this mission (this WP's
`_render_cascade_activation`, WP03's `_render_no_cascade_warning`, WP04's
`_render_cascade_deactivation` in `deactivate.py`) must print IDENTICAL
wording for a kind-filtered node. Define ONE new private function in
`activate.py`:

```python
_render_kind_filtered_line(kind_token: str, config_id: str) -> None
```

that prints exactly one line using a single module-level string constant,
co-located with the existing `RESYNTHESIZE_HELP` constant
(`activate.py:59-65`, following that file's existing convention for shared
render-string constants). Candidate wording (plan.md §2 — finalize the exact
literal in this WP's ATDD test, then never re-coin it in WP03/WP04):

```
[dim]Not cascaded[/dim]: {kind_token}/{config_id} (kind not charter-activatable)
```

This echoes the existing `[dim]Skipped (out of scope)[/dim]: ...` line's
`[dim]` styling (FR-003: never phrased as a warning/error/failure) while using
different literal text ("Not cascaded" vs. "Skipped") so the two remain
grep-distinguishable (FR-008) — an operator or script must never mistake a
structurally-non-activatable kind for a scope-excluded one. `deactivate.py`
will import this helper from `activate.py` in WP04, mirroring the existing
precedent (`deactivate.py:45-50` already imports four names from
`activate.py`).

**FR-004's exact trigger condition** (plan.md §12, do not use a broader
condition):

```python
not result.activated and bool(result.not_cascaded_kind_filtered)
```

This fires ONLY when the cascade resolved zero activatable targets AND at
least one referenced node was specifically kind-filtered — never for a source
with zero referenced nodes at all (spec.md Edge Case 1 / Scenario 3), and
never for a pure scope-narrowing case where every referenced node is
activatable-kind but excluded by a narrow `--cascade <scope>` (spec.md
Scenario 4 / SC-007 — that case is already fully communicated by the existing
`Skipped (out of scope)` lines and must NOT also print this message).

**NFR-002**: the rise in console output volume for sources reaching
`template`/`asset` is a deliberate, operator-approved trade-off (see spec.md
Clarifications) — do not cap, truncate, or sample the per-node lines.

**NFR-004**: no existing `console.print(...)` call's f-string in
`_render_cascade_activation` may be modified — only new, separate
`console.print` calls are added alongside the existing ones.

## Subtasks

### Subtask T008: Write the RED-first ATDD tests (CLI-level, FR-003/FR-004/FR-008)

**Purpose**: Pin all four console-output scenarios this WP delivers before any
implementation exists, per charter C-011. Four scenarios share one code path,
so they land together in this WP.

**Steps**:
1. In `test_charter_activate_commands_cascade_output.py`, using the
   User-Story-1 fixture (one `suggests` edge to a `tactic`, one to
   `asset:qa-traceability-lint`), invoke `charter activate toolguide
   qa-carrier-lint --cascade all` (or the fixture's equivalent kind/id) and
   assert the console output contains BOTH:
   - the existing `[cyan]Cascade-activated[/cyan]` line for the tactic
     (unchanged wording), AND
   - the new, distinct kind-filtered line for the asset (spec.md Scenario 1).
2. Add a second test: construct a source whose ONLY outgoing reference-relation
   edges target non-activatable kinds (e.g. only `asset`/`template`); run
   `--cascade all`; assert the console explicitly states the cascade resolved
   zero activatable targets (spec.md Scenario 2 / SC-002), exit code remains 0.
3. Add a third test: construct a source whose referenced nodes are ALL
   activatable-kind but ALL excluded by a narrow `--cascade <scope>` (e.g.
   `--cascade tactic` against a source referencing only `directive` nodes);
   assert the FR-004 zero-activatable-targets message does NOT appear, while
   the existing per-node `Skipped (out of scope)` lines DO appear (spec.md
   Scenario 4 / SC-007 — this is the over-reporting guard).
4. Add a fourth test proving the kind-filtered line renders the RESOLVED
   config-stem ID, not the raw DRG bare ID: use or extend an org-pack fixture
   (per `_drg_id_to_config_id`'s docstring, `activate.py:123-152` — an
   org-pack-2..N node's bare DRG id and config-stem id differ) so the
   kind-filtered target's bare DRG id and config-stem id are DIFFERENT
   strings; run `--cascade all`; assert the rendered kind-filtered line
   contains the resolved config-stem ID token and does NOT contain the raw
   bare DRG id. This assertion must fail if the implementation passed the
   unresolved bare ID straight to `_render_kind_filtered_line`.
5. Confirm all four assertions are RED on `fix/cascade-asset-silent-drop-3705`
   today. Commit as one RED-first commit, before any implementation commit in
   this WP.

**Files**: `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py`
(four new test functions, ~25-40 lines each).

**Validation**: all four new tests fail against current `activate.py`; the
reviewer independently re-runs on `fix/cascade-asset-silent-drop-3705` to
confirm RED before any implementation commit is reviewed.

---

### Subtask T009: Add the shared `_render_kind_filtered_line` helper + label constant

**Purpose**: FR-009's first definition — the one place the exact wording is
picked, for all three render call sites across the mission to share.

**Steps**:
1. In `activate.py`, add a module-level string constant (co-located with
   `RESYNTHESIZE_HELP`, `activate.py:59-65`) holding the label template
   settled by T008's test assertions.
2. Add `_render_kind_filtered_line(kind_token: str, config_id: str) -> None`
   that prints exactly one `console.print(...)` call using that constant.
3. Do not inline the literal anywhere else — every call site must go through
   this one helper (Sonar `S1192` repeated-literal avoidance, plan.md §5).

**Files**: `activate.py` (~10-15 new lines: one constant + one function).

**Validation**: `ruff check` clean; no repeated literal.

---

### Subtask T010: Wire the helper into `_render_cascade_activation`, add FR-004's message

**Purpose**: The actual FR-003/FR-004 rendering behavior.

**Steps**:
1. In `_render_cascade_activation` (`activate.py:274-338`), add a loop over
   `sorted(result.not_cascaded_kind_filtered)` (kind) and each kind's sorted
   bare IDs — matching the existing loop pattern used for
   `activated`/`skipped_by_scope`. **For each bare ID, resolve it to its
   config-stem ID first**, via the SAME call the adjacent `activated`/
   `skipped_by_scope` loops already make a few lines above
   (`activate.py:305-315`): `_drg_id_to_config_id(kind_value, cascade_drg_id,
   doctrine_root, layer_roots, org_roots)` — `doctrine_root`, `layer_roots`,
   and `org_roots` are already local variables in this function, so no new
   parameters are needed. Only pass the RESOLVED config-stem ID to
   `_render_kind_filtered_line(kind_token, config_id)` — never the raw bare
   ID. This mirrors why the existing loops resolve before rendering: the
   cascade engine reports DRG bare IDs, but every other line in this
   function's output already prints the operator-facing config-stem ID, and
   an org-pack-2..N node's bare ID and config-stem ID can differ.
2. Add the FR-004 zero-activatable-targets message, gated on EXACTLY:
   `not result.activated and bool(result.not_cascaded_kind_filtered)` — see
   Context above for why this exact condition is required.
3. Do not modify any existing `console.print(...)` f-string in this function —
   only add new calls (NFR-004).
4. Watch the complexity ceiling (plan.md §5): if this addition pushes
   `_render_cascade_activation` past 15 (ruff `C901`), extract a private
   `_render_kind_filtered_section(...)` helper rather than inlining a fourth
   loop into the existing function body.

**Files**: `activate.py` (~10-15 line addition inside
`_render_cascade_activation`).

**Validation**: T008's four tests now pass (GREEN).

---

### Subtask T011: Verify GREEN, confirm SC-006, diff against baseline, commit

**Purpose**: Close out the WP cleanly.

**Steps**:
1. Re-run the scoped baseline command (WP01 item 1); diff against the
   baseline captured before WP01's first commit.
2. Grep the diff to confirm no existing `Cascade-activated:` or `Skipped (out
   of scope)` line's exact string changed (SC-006).
3. Run `ruff check` / `mypy` over `activate.py` and the test file — zero new
   issues, no suppressions.
4. Commit implementation AFTER T008's RED commit.

**Files**: none new; verification + commit only.

**Validation**: all T008 tests GREEN; SC-006 confirmed by diff inspection;
scoped baseline shows no new red.

## Definition of Done

- `_render_kind_filtered_line` + its label constant exist in `activate.py`,
  used by exactly one call site so far (`_render_cascade_activation`) — WP03
  and WP04 will add the other two call sites without re-coining wording.
- `_render_cascade_activation` prints one distinct line per kind-filtered node
  (FR-003) and the FR-004 zero-activatable-targets message under the exact
  scoped trigger condition (FR-004, SC-002, SC-007).
- The new line is visibly distinct from `Skipped (out of scope)` (FR-008).
- The new line renders each kind-filtered node's RESOLVED config-stem ID
  (via `_drg_id_to_config_id`), never the raw DRG bare ID — matching how the
  adjacent `activated`/`skipped_by_scope` loops already resolve before
  rendering, and pinned by T008's fourth test. (This is the resolved ID
  when resolution succeeds; the documented raw-ID fallback for kinds with
  no on-disk artifact file, e.g. `template`, is unaffected — see
  `_drg_id_to_config_id`'s docstring.)
- No existing console line shape/string changed (NFR-004, SC-006).
- T008's RED-first commit precedes all implementation commits in this WP;
  reviewer verifies RED on `fix/cascade-asset-silent-drop-3705` → GREEN on
  this WP's final commit.
- Scoped baseline diff shows no new red.

## Risks

- **Conflating FR-004's trigger with the broader "zero landed in `activated`"
  condition** (which would also fire for pure scope-narrowing, violating
  SC-007). Mitigated by using the exact condition specified in Context above.
- **Complexity ceiling breach** in `_render_cascade_activation` — mitigated by
  the extraction fallback named in T010.
- **Inlining the label string at the call site** instead of going through the
  shared helper — breaks FR-009 and Sonar `S1192`; do not do this.

## Reviewer Guidance

- Confirm T008's tests were RED on `fix/cascade-asset-silent-drop-3705` before
  any implementation commit, GREEN on this WP's final commit.
- Confirm the label wording exists as exactly one module-level constant,
  consumed only by `_render_kind_filtered_line`.
- Confirm FR-004's trigger condition matches `not result.activated and
  bool(result.not_cascaded_kind_filtered)` literally — not a looser check.
- Confirm no existing `console.print` f-string changed (diff every line inside
  `_render_cascade_activation` against `main`/base branch).
- Confirm the kind-filtered loop resolves each bare DRG id to its config-stem
  id via `_drg_id_to_config_id` (same call as the adjacent `activated`/
  `skipped_by_scope` loops) BEFORE calling `_render_kind_filtered_line` —
  never passes the raw bare id — and that T008's fourth test (differing bare
  id vs. config-stem id) is present and GREEN.

Implementation command: `spec-kitty agent action implement WP02 --agent claude`
