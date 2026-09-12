---
work_package_id: WP04
title: Deactivation-side symmetry — charter deactivate --cascade agrees with activate
dependencies:
- WP03
requirement_refs:
- FR-007
- C-002
- C-006
- NFR-003
- NFR-004
planning_base_branch: fix/cascade-asset-silent-drop-3705
merge_target_branch: fix/cascade-asset-silent-drop-3705
branch_strategy: Planning artifacts for this mission were generated on fix/cascade-asset-silent-drop-3705. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cascade-asset-silent-drop-3705 unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/deactivate.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/cascade.py
- src/specify_cli/cli/commands/charter/deactivate.py
- tests/charter/test_cascade.py
- tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Deactivation-side symmetry

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface`
(`src/specify_cli/cli/commands/charter/deactivate.py`).

---

## ⚠️ Mission-wide instructions (restated briefly — full text lives in WP01)

- **Baseline discipline applies to this WP too**: re-run the scoped baseline
  command from WP01's prompt file (`tasks/WP01-shared-collection-seam.md`,
  "Mission-wide instructions" item 1) before your first commit and after your
  final commit; diff against the mission-wide baseline captured before WP01.
  This is the LAST WP — its final diff should show the complete mission with
  no new red anywhere in the scoped test set.
- **FR-006 is not implemented by this WP** (or any WP) — see WP01's prompt for
  the full rationale. This WP does NOT touch PR-body content; that is a
  mission-close reviewer step (SC-005), not a WP.
- **No campsite-clean commit is warranted anywhere in this mission.**
- **This WP depends on WP03 and must not start until WP03's final commit is
  available**: this WP reuses WP02's shared `_render_kind_filtered_line`
  helper (imported into `deactivate.py`) and WP01's `_referenced_artifacts`
  two-tuple return shape.
- **Ownership overlap note**: this WP owns `src/charter/cascade.py` (also
  owned by WP01 and WP03) and `tests/charter/test_cascade.py` (also owned by
  WP01). This is expected — WP01 → WP02 → WP03 → WP04 is a strict sequential
  chain and `finalize-tasks`'s ownership validator exempts same-lane
  sequential pairs from the no-overlap check.
- **This WP completes C-006's required test.** WP01 landed the
  activation-side half (kind-filtered node never leaks into `activated`/
  `skipped_by_scope` under `CascadeScope.all()`). This WP lands the
  deactivation-side half (same guarantee for `DeactivationPlan`'s
  `.deactivate`/`.skipped_shared`). C-006 as a whole is satisfied only once
  BOTH halves exist — this WP's T018 is not optional.

---

## Objective

Rename `_kind_filtered` back to `kind_filtered` in `deactivation_plan` (the
value WP01 left underscore-prefixed), thread it through a new field on
`DeactivationPlan`, render it via the shared helper (imported into
`deactivate.py`) from `_render_cascade_deactivation`, and land the two
DISTINCT tests plan.md §12 specifies for this WP — do not conflate them.

## Context

`deactivation_plan` (`cascade.py:489-565`) already calls the shared
`_referenced_artifacts` seam internally for its candidate set. Per ADR
2026-08-20-1's Symmetry section and spec.md User Story 3 (P2 — deactivation
cascades only fire with explicit `--cascade`, there is no deactivation-side
"no-cascade warning" equivalent), `charter deactivate <kind> <id> --cascade
all` must agree with `charter activate <kind> <id> --cascade all` on what a
source references, including kind-filtered nodes.

**`DeactivationPlan`'s field shape is intentionally different from the other
two** (plan.md §2, C-002 requires field-name consistency, NOT identical
container types): `deactivate` (`cascade.py:485`) is a flat `list[str]` of
URNs — NOT kind-bucketed — because `deactivate.py`'s existing render loop
already partitions a URN into kind/config-id itself (`urn.partition(":")`,
`deactivate.py:166`). So the new field here is:

```python
not_cascaded_kind_filtered: list[str] = field(default_factory=list)  # sorted URNs
```

alongside `deactivate` and `skipped_shared` (`cascade.py:486`, a
`list[SharedSkip]`) — a flat sorted-URN list is the form this call site
already knows how to render; this is the minimal-friction shape, not an
inconsistency with `CascadeActivationResult`'s/`NoCascadeReport`'s
dict-shaped fields.

**Reuse the shared helper — import it into `deactivate.py`.**
`_render_cascade_deactivation` (`deactivate.py:133-194`) needs
`_render_kind_filtered_line` from `activate.py`. `deactivate.py` already
imports four names from `activate.py` (`deactivate.py:45-50`:
`RESYNTHESIZE_HELP`, `render_pack_config_error`, `run_full_synthesize`,
`validate_pack_config`) — this is existing, precedented cross-command sharing.
Add the new helper to that same import block; do not duplicate its
definition.

## Subtasks

### Subtask T017: Write the RED-first CLI-level ATDD test (NFR-003/SC-003 cross-command)

**Purpose**: The single test that IS the NFR-003/SC-003 cross-command
verification — exercises BOTH `charter activate` and `charter deactivate`
against the SAME fixture graph and checks they AGREE on the same
kind-filtered node. This is a different assertion from T018 below — do not
conflate them.

**Steps**:
1. In `test_charter_deactivate_commands.py`, activate the User-Story-1
   fixture with `charter activate <kind> <id> --cascade all` (the asset
   kind-filtered line appears — this exercises WP01/WP02's already-landed
   behavior as a precondition, not new behavior).
2. Then run `charter deactivate <kind> <id> --cascade all` on the SAME
   source and assert the equivalent kind-filtered line appears in the
   deactivation console output too — using language consistent with the
   activation-side rendering (same shared helper, same underlying data
   shape/label). This is NOT `Cascade-deactivated:` and NOT `Skipped (shared
   artifact)` — a third, distinctly-labelled line.
3. Use or extend an org-pack fixture (per `_drg_id_to_config_id`'s docstring,
   `activate.py:123-152`) so the kind-filtered target's bare DRG id and
   config-stem id are DIFFERENT strings, and assert the ID token in the
   deactivation-side kind-filtered line equals the RESOLVED config-stem ID —
   the same ID token the activation-side line in step 1 already renders —
   and is NOT the raw bare DRG id / URN suffix. This assertion must fail if
   `_render_cascade_deactivation` passed `urn.partition(":")[2]` (the bare
   id) straight to `_render_kind_filtered_line` instead of resolving through
   `resolve_config_id(...)` first.
4. Confirm RED on `fix/cascade-asset-silent-drop-3705` today (deactivation
   reports nothing for the asset). Commit as part of this WP's RED-first
   commit (may be combined with T018 in one commit, or its own — either way,
   both land before any implementation commit in this WP).

**Files**: `tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py`
(one new test function, ~30-40 lines, exercising two CLI invocations).

**Validation**: fails against current `deactivate.py`; reviewer independently
re-runs on `fix/cascade-asset-silent-drop-3705` to confirm RED.

---

### Subtask T018: Write the RED-first engine-level test (C-006 deactivation-side half)

**Purpose**: Completes C-006's required regression test (WP01 landed the
activation-side half). A DIFFERENT assertion from T017: this checks
`DeactivationPlan`'s OWN dataclass fields never leak a kind-filtered node into
the activatable-shaped fields — not console agreement between two commands.

**Steps**:
1. In `tests/charter/test_cascade.py`, using the same fixture, call
   `deactivation_plan(graph, source, CascadeScope.all())` directly and assert:
   - the kind-filtered asset URN appears in `.not_cascaded_kind_filtered`
   - the asset URN does NOT appear in `.deactivate`
   - the asset URN does NOT appear inside any `SharedSkip` in
     `.skipped_shared`
2. Confirm RED on `fix/cascade-asset-silent-drop-3705` today (the field does
   not exist / the URN would be absent from all three today). Commit as part
   of this WP's RED-first commit, before any implementation commit.

**Files**: `tests/charter/test_cascade.py` (one new test function, ~20-25
lines).

**Validation**: fails against current `cascade.py`; reviewer independently
re-runs on `fix/cascade-asset-silent-drop-3705` to confirm RED.

---

### Subtask T019: Rename `_kind_filtered` → `kind_filtered`, thread `DeactivationPlan`

**Purpose**: FR-007's data-layer half.

**Steps**:
1. In `deactivation_plan` (`cascade.py:489-565`), rename the
   underscore-prefixed binding WP01 left (`_kind_filtered`) back to
   `kind_filtered`.
2. Add the new field to `DeactivationPlan` (`cascade.py:470-486`):
   ```python
   not_cascaded_kind_filtered: list[str] = field(default_factory=list)
   ```
   (sorted URNs), alongside `deactivate` and `skipped_shared`.
3. Populate this field from `kind_filtered`, sorted by URN.
4. Confirm the existing candidate-collection loop (`cascade.py:533-535`, gated
   on `scope.selects(ref.kind)`) is untouched — `kind_filtered` nodes populate
   this new field via a path that never passes through `CascadeScope.selects()`
   or this loop (C-006).

**Files**: `src/charter/cascade.py` (`DeactivationPlan` dataclass +
`deactivation_plan` body).

**Validation**: T018's assertions now pass (GREEN).

---

### Subtask T020: Wire the shared helper into `_render_cascade_deactivation`

**Purpose**: FR-007's render-layer half.

**Steps**:
1. In `deactivate.py`, add `_render_kind_filtered_line` to the existing
   import block from `activate.py` (`deactivate.py:45-50`).
2. In `_render_cascade_deactivation` (`deactivate.py:133-194`), add a loop
   over `sorted(plan.not_cascaded_kind_filtered)` (URNs). For each URN,
   extract `kind_value` via `urn.partition(":")` the same way the existing
   `plan.deactivate` loop does (`deactivate.py:166`) — **but do NOT stop at
   that partition for the ID to render.** The existing loop's `kind_value`
   partition is only step one of ITS OWN ID resolution; it goes on to call
   `resolve_config_id(urn, doctrine_root=doctrine_root, org_roots=org_roots,
   layer_roots=layer_roots)` (with the existing `except
   (UnknownArtifactIdError, ValueError): config_id = urn.partition(":")[2]`
   fallback) a few lines later to get the `config_id` it actually renders.
   Do the SAME `resolve_config_id(...)` call (with the same fallback) for
   each `not_cascaded_kind_filtered` URN before calling
   `_render_kind_filtered_line(kind_token, config_id)` — never pass the raw
   URN's bare-id partition straight to the helper.
3. Do not modify any existing `console.print(...)` f-string for
   `Cascade-deactivated:` or `Skipped (shared artifact)` (NFR-004) — only add
   new, separate calls.

**Files**: `deactivate.py` (~10 line addition inside
`_render_cascade_deactivation` plus one import-line edit).

**Validation**: T017's test now passes (GREEN).

---

### Subtask T021: Verify GREEN both tests, confirm SC-006, final mission-wide baseline diff, commit

**Purpose**: Close out this WP AND the mission's implementation phase — this
is the last WP.

**Steps**:
1. Re-run the scoped baseline command; diff the final state against the
   mission-wide baseline captured before WP01's first commit. No new red
   anywhere in the scoped test set.
2. Grep the diff to confirm `Cascade-deactivated:` and `Skipped (shared
   artifact)` exact strings are unchanged (SC-006).
3. Confirm `tests/charter/test_cascade.py::test_instantiates_is_followed_but_template_dropped_at_candidacy`
   (C-004, line 648) AND `tests/charter/test_cascade.py::test_cascade_never_proposes_template_or_asset`
   (C-004, line 603) — both pinned template/asset-blindness tests — still
   pass unmodified.
4. Run `ruff check` / `mypy` over all touched files across the whole mission —
   zero new issues, no suppressions added anywhere.
5. Commit implementation AFTER T017/T018's RED commit.
6. Report: this mission is now ready for PR-prep. Remind whoever opens the PR
   that FR-006/C-003/SC-005 require the PR body to explicitly cite ADR
   2026-08-20-1 and state this is a visibility addition, not a policy
   reversal — that is NOT this WP's job to write, but it must not be
   forgotten at PR-open time.

**Files**: none new; verification + commit only.

**Validation**: T017 and T018 both GREEN; SC-006 confirmed; both C-004 tests
(line 648 and line 603) unmodified and passing; scoped baseline diff clean
across the full mission.

## Definition of Done

- `DeactivationPlan.not_cascaded_kind_filtered` exists (flat sorted `list[str]`
  of URNs) and is populated by `deactivation_plan` (FR-007).
- `_render_cascade_deactivation` prints one distinct line per kind-filtered
  node using the shared helper imported from `activate.py` (FR-007, FR-009
  reuse).
- The line renders each kind-filtered URN's RESOLVED config-stem ID — via
  `resolve_config_id(urn, doctrine_root=..., org_roots=..., layer_roots=...)`
  with the existing `except (UnknownArtifactIdError, ValueError)` fallback,
  the SAME call the adjacent `plan.deactivate` loop already makes — never the
  raw bare id from `urn.partition(":")` alone; pinned by T017's ID-resolution
  assertion. (This is the resolved ID when resolution succeeds; the
  documented raw-ID fallback for kinds with no on-disk artifact file, e.g.
  `template`, is unaffected — see `_drg_id_to_config_id`'s docstring.)
- T017 (NFR-003/SC-003 cross-command CLI test) and T018 (C-006
  deactivation-side engine test) are both present, distinct, and both landed
  in this WP's RED-first commit before any implementation commit.
- Reviewer verifies RED on `fix/cascade-asset-silent-drop-3705` → GREEN on
  this WP's final commit, for both tests independently.
- No existing console line shape/string changed (NFR-004, SC-006).
- Both C-004 pinned tests — `test_instantiates_is_followed_but_template_dropped_at_candidacy`
  (line 648) and `test_cascade_never_proposes_template_or_asset` (line 603) —
  still pass unmodified.
- Mission-wide scoped baseline diff (captured before WP01, checked after this
  WP) shows no new red anywhere.
- Per-subtask completion evidence recorded via
  `spec-kitty agent tasks mark-status <Txxx> --status done`.

## Risks

- **Conflating T017 and T018 into one assertion** — they check different
  things (console agreement between two commands vs. a dataclass's own field
  never leaking into the wrong bucket); both are required, separately.
- **Kind-filtered URNs leaking into `.deactivate` or `.skipped_shared`** — a
  C-006/C-001 violation at runtime (an asset/template could actually get
  deactivated under `--cascade all`). Mitigated by T019's explicit
  instruction to populate the new field via a path that never touches the
  existing `scope.selects()`-gated candidate loop.
- **Forgetting the PR-body ADR citation reminder** — this WP is the last one;
  its final subtask exists specifically to carry that reminder forward to
  PR-prep, since no WP itself implements FR-006.

## Reviewer Guidance

- Confirm T017 and T018 were both RED on `fix/cascade-asset-silent-drop-3705`
  before any implementation commit, both GREEN on this WP's final commit.
- Confirm `DeactivationPlan.not_cascaded_kind_filtered` is a flat
  `list[str]` of URNs (not kind-bucketed like the other two dataclasses) —
  this is an intentional, documented shape difference, not an inconsistency.
- Confirm the kind-filtered URN never appears in `.deactivate` or inside any
  `SharedSkip` in `.skipped_shared` under `CascadeScope.all()`.
- Confirm `deactivate.py`'s import of `_render_kind_filtered_line` from
  `activate.py` follows the existing precedent at `deactivate.py:45-50`.
- Confirm no existing `console.print` f-string changed in
  `_render_cascade_deactivation`.
- Confirm the kind-filtered loop resolves each URN's bare id to its
  config-stem id via `resolve_config_id(...)` (same call, same fallback, as
  the adjacent `plan.deactivate` loop) BEFORE calling
  `_render_kind_filtered_line` — never passes `urn.partition(":")[2]`
  directly — and that T017's ID-resolution assertion (differing bare id vs.
  config-stem id) is present and GREEN.
- Confirm both C-004 pinned tests —
  `test_instantiates_is_followed_but_template_dropped_at_candidacy` (line
  648) and `test_cascade_never_proposes_template_or_asset` (line 603) — are
  present, unmodified, and still passing.
- At mission close (not this WP): confirm the PR body cites ADR
  2026-08-20-1 (SC-005) before accepting/merging.

Implementation command: `spec-kitty agent action implement WP04 --agent claude`
