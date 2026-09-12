---
work_package_id: WP03
title: No-cascade warning path reports the same kind-filtered nodes
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-005a
- C-002
- NFR-001
- NFR-004
planning_base_branch: fix/cascade-asset-silent-drop-3705
merge_target_branch: fix/cascade-asset-silent-drop-3705
branch_strategy: Planning artifacts for this mission were generated on fix/cascade-asset-silent-drop-3705. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cascade-asset-silent-drop-3705 unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/activate.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/cascade.py
- src/specify_cli/cli/commands/charter/activate.py
- tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – No-cascade warning path reports the same kind-filtered nodes

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
  final commit; diff against the mission-wide baseline captured before WP01.
- **FR-006 is not implemented by this WP** (or any WP) — see WP01's prompt for
  the full rationale.
- **No campsite-clean commit is warranted anywhere in this mission.**
- **This WP depends on WP02 and must not start until WP02's final commit is
  available**: this WP reuses WP02's `_render_kind_filtered_line` helper and
  its label constant (imported/called from the same file, no new import
  needed) and WP01's `_referenced_artifacts` two-tuple return shape.
- **Ownership overlap note**: this WP owns both `src/charter/cascade.py` (also
  owned by WP01, and by WP04) and `activate.py` (also owned by WP02). This is
  expected — WP01 → WP02 → WP03 → WP04 is a strict sequential chain and
  `finalize-tasks`'s ownership validator exempts same-lane sequential pairs
  from the no-overlap check.

---

## Objective

Rename `_kind_filtered` back to `kind_filtered` in `referenced_but_not_cascaded`
(the value WP01 left underscore-prefixed), thread it through a new field on
`NoCascadeReport`, render it via WP02's shared helper from
`_render_no_cascade_warning`, and fix the `has_skipped` render guard so it also
fires on a source whose ONLY referenced nodes are kind-filtered (FR-005,
FR-005a).

## Context

`referenced_but_not_cascaded` (`cascade.py:413-444`) and
`_render_no_cascade_warning` (`activate.py:383-417`) are the "no `--cascade`
flag supplied" path — today it warns about activatable-kind refs with a
recovery hint ("re-run with `--cascade`"). Two distinct bugs live here per
spec.md User Story 2:

1. **FR-005**: a kind-filtered node (`asset`/`template`) reached by this path
   produces NO line at all today — the exact silent-drop bug, one render path
   over. The new line must use DIFFERENT wording than the existing recovery
   hint — re-running with `--cascade` would NOT activate an asset/template, so
   reusing that hint would be actively misleading.

2. **FR-005a — the render-guard gap** (spec.md User Story 2 Scenario 2,
   explicitly named): `NoCascadeReport.has_skipped`
   (`cascade.py:407-410`, `return any(self.skipped.values())`) inspects ONLY
   the pre-existing `skipped` dict. `_render_no_cascade_warning`
   (`activate.py:404-405`, `if not report.has_skipped: return`) gates its
   ENTIRE body on this. A source whose ONLY referenced nodes are kind-filtered
   leaves `skipped` empty — `has_skipped` is `False` — and the function returns
   before the render loop is ever reached, reproducing the EXACT silent-drop
   bug #3705 reports, one level up, inside this mission's own fix. Fix the
   guard (either by redefining `has_skipped` to check both `skipped` AND the
   new field, or by replacing the guard with an explicit "anything to report
   across both fields" check) so it evaluates `True` when kind-filtered nodes
   are present even if `skipped` is empty. This is additive to control flow
   (NFR-004's Reflexivity guarantee) — it does not remove the existing
   `any(self.skipped.values())` check, so a source with only activatable-kind
   skipped refs (today's only case) still triggers the guard exactly as
   before.

**Reuse WP02's helper — do not re-coin wording.** `_render_no_cascade_warning`
is already in `activate.py`, the same file `_render_kind_filtered_line` lives
in — no new import needed, just call it.

## Subtasks

### Subtask T012: Write the RED-first ATDD tests (CLI-level, FR-005/FR-005a)

**Purpose**: Pin the missing-line bug, the render-guard gap, and the
ID-resolution requirement before any implementation exists, per charter
C-011.

**Steps**:
1. In `test_charter_activate_commands_cascade_output.py`, using the same
   fixture as WP01/WP02 (mixed tactic + `asset:...` edges), run `charter
   activate <kind> <id>` with NO `--cascade` flag. Assert:
   - the existing `[yellow]Warning[/yellow]: referenced .../was not activated
     (no --cascade)` line still appears for the tactic (unchanged wording,
     unchanged recovery hint), AND
   - a new, distinctly-labelled line appears for the asset target that does
     NOT reuse the recovery-hint wording verbatim (spec.md User Story 2
     Scenario 1).
2. Add a second test: construct a source whose ONLY referenced nodes are
   kind-filtered (zero activatable-kind refs at all). Run `charter activate
   <kind> <id>` with no `--cascade`. Assert the kind-filtered line(s) STILL
   render, even though `skipped` would be empty (spec.md User Story 2 Scenario
   2 — the exact `has_skipped`-guard gap this WP fixes).
3. Add a third test proving the kind-filtered line renders the RESOLVED
   config-stem ID, not the raw DRG bare ID: use or extend an org-pack fixture
   (per `_drg_id_to_config_id`'s docstring, `activate.py:123-152`) so the
   kind-filtered target's bare DRG id and config-stem id are DIFFERENT
   strings; run `charter activate <kind> <id>` with no `--cascade`; assert
   the rendered kind-filtered line contains the resolved config-stem ID
   token and does NOT contain the raw bare DRG id. This assertion must fail
   if the implementation passed the unresolved bare ID straight to
   `_render_kind_filtered_line`.
4. Confirm all three are RED on `fix/cascade-asset-silent-drop-3705` today.
   Commit as one RED-first commit, before any implementation commit in this
   WP.

**Files**: `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py`
(three new test functions, ~25-35 lines each).

**Validation**: all three new tests fail against current code; reviewer
independently re-runs on `fix/cascade-asset-silent-drop-3705` to confirm RED.

---

### Subtask T013: Rename `_kind_filtered` → `kind_filtered`, thread `NoCascadeReport`

**Purpose**: FR-005's data-layer half.

**Steps**:
1. In `referenced_but_not_cascaded` (`cascade.py:413-444`), rename the
   underscore-prefixed binding WP01 left (`_kind_filtered`) back to
   `kind_filtered` — this WP is now the point where the value starts being
   used.
2. Add a new field to `NoCascadeReport` (`cascade.py:388-410`):
   ```python
   not_cascaded_kind_filtered: dict[str, list[str]] = field(default_factory=dict)
   ```
   alongside the existing `skipped` field, same kind→sorted-bare-IDs shape.
3. Populate this field from `kind_filtered` in `referenced_but_not_cascaded`.

**Files**: `src/charter/cascade.py` (`NoCascadeReport` dataclass +
`referenced_but_not_cascaded` body).

**Validation**: field populates correctly; existing `skipped`-based tests
still pass unmodified.

---

### Subtask T014: Fix the `has_skipped` render guard (FR-005a)

**Purpose**: Close the exact gap spec.md User Story 2 Scenario 2 names.

**Steps**:
1. Redefine `has_skipped` (or replace its use as the sole guard at
   `activate.py:404-405`) so it evaluates `True` when EITHER `skipped` is
   non-empty OR `not_cascaded_kind_filtered` is non-empty.
2. Do not remove the existing `any(self.skipped.values())` check — only add
   the OR-condition (NFR-004: additive to control flow, not a removal).

**Files**: `src/charter/cascade.py` (`has_skipped` property/method) and/or
`activate.py` (the guard call site, if the guard is restructured rather than
redefined).

**Validation**: T012's second test now passes (GREEN).

---

### Subtask T015: Wire the shared helper into `_render_no_cascade_warning`

**Purpose**: FR-005's render-layer half.

**Steps**:
1. In `_render_no_cascade_warning` (`activate.py:383-417`), add a loop over
   `sorted(report.not_cascaded_kind_filtered)` (kind) and each kind's sorted
   bare IDs. `report.not_cascaded_kind_filtered`'s values are DRG bare IDs
   (same space as `NoCascadeReport.skipped`, populated from
   `ReferencedArtifact.artifact_id` — see `cascade.py`'s `_referenced_artifacts`).
   **Resolve each bare ID to its config-stem ID first**, the SAME way this
   function's own existing `report.skipped` loop already does it a few lines
   above (`activate.py:406-412`): `_drg_id_to_config_id(kind_value, bare_id,
   doctrine_root, layer_roots, org_roots)`. `org_roots` and `doctrine_root`
   are already local variables in this function (computed at
   `activate.py:397` and `406` respectively); `layer_roots` is already a
   parameter — no new parameters or imports are needed. Only pass the
   RESOLVED config-stem ID to WP02's `_render_kind_filtered_line(...)` —
   same helper, same wording — never the raw bare ID.
2. Do not modify the existing `[yellow]Warning[/yellow]: ... (no --cascade)`
   f-string (NFR-004) — only add new, separate `console.print` calls.
3. The new line must never suggest `--cascade` as a recovery path for a
   kind-filtered node (spec.md FAILS-if condition for User Story 2) — this is
   guaranteed by reusing the shared helper's fixed wording rather than writing
   a bespoke message here.

**Files**: `activate.py` (~5-10 line addition inside
`_render_no_cascade_warning`).

**Validation**: T012's first and third tests now pass (GREEN) (the
second depends on T014's guard fix, as before).

---

### Subtask T016: Verify GREEN, confirm SC-006, diff against baseline, commit

**Purpose**: Close out the WP cleanly.

**Steps**:
1. Re-run the scoped baseline command; diff against the mission-wide baseline.
2. Grep the diff to confirm the existing `Warning: ... was not activated (no
   --cascade)` line's exact string is unchanged (SC-006).
3. Run `ruff check` / `mypy` over the touched files — zero new issues.
4. Commit implementation AFTER T012's RED commit.

**Files**: none new; verification + commit only.

**Validation**: all three T012 tests GREEN; SC-006 confirmed; scoped baseline
shows no new red.

## Definition of Done

- `NoCascadeReport.not_cascaded_kind_filtered` exists and is populated by
  `referenced_but_not_cascaded` (FR-005).
- `_render_no_cascade_warning` prints one distinct line per kind-filtered node
  using WP02's shared helper — never the "no --cascade" recovery hint (FR-005).
- The `has_skipped` guard (or its replacement) fires on a kind-filtered-only
  source even though `skipped` is empty (FR-005a).
- The new line renders each kind-filtered node's RESOLVED config-stem ID
  (via `_drg_id_to_config_id`), never the raw DRG bare ID — matching how
  this function's own existing `report.skipped` loop already resolves
  before rendering, and pinned by T012's third test. (This is the resolved
  ID when resolution succeeds; the documented raw-ID fallback for kinds
  with no on-disk artifact file, e.g. `template`, is unaffected — see
  `_drg_id_to_config_id`'s docstring.)
- No existing console line shape/string changed (NFR-004, SC-006).
- T012's RED-first commit precedes all implementation commits in this WP;
  reviewer verifies RED on `fix/cascade-asset-silent-drop-3705` → GREEN on
  this WP's final commit.
- Scoped baseline diff shows no new red.

## Risks

- **Reusing the recovery-hint wording for the asset line** — explicitly
  forbidden by spec.md's FAILS-if condition; mitigated by routing through the
  shared helper, which never contains that phrase.
- **Only fixing the missing-line bug (T013/T015) without also fixing the
  render guard (T014)** — this would reproduce the silent-drop bug one level
  up for kind-filtered-only sources; both must land together in this WP.
- **Removing the existing `any(self.skipped.values())` check instead of OR-ing
  a new condition into it** — would violate NFR-004's additive-only guarantee.

## Reviewer Guidance

- Confirm T012's tests were RED on `fix/cascade-asset-silent-drop-3705` before
  any implementation commit, GREEN on this WP's final commit.
- Confirm the asset/template line never contains "--cascade" as a recovery
  suggestion.
- Confirm the `has_skipped` guard change is additive (existing
  `any(self.skipped.values())` still present, OR-ed with the new condition,
  not replaced outright in a way that could regress the existing case).
- Confirm no existing `console.print` f-string changed in
  `_render_no_cascade_warning`.
- Confirm the kind-filtered loop resolves each bare DRG id to its
  config-stem id via `_drg_id_to_config_id` (same call this function's own
  `report.skipped` loop already makes) BEFORE calling
  `_render_kind_filtered_line` — never passes the raw bare id — and that
  T012's third test (differing bare id vs. config-stem id) is present and
  GREEN.

Implementation command: `spec-kitty agent action implement WP03 --agent claude`
