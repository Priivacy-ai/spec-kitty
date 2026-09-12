---
work_package_id: WP01
title: Shared collection seam — _referenced_artifacts partitions kind-filtered nodes
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-006
- C-001
- C-002
- C-006
- NFR-001
planning_base_branch: fix/cascade-asset-silent-drop-3705
merge_target_branch: fix/cascade-asset-silent-drop-3705
branch_strategy: Planning artifacts for this mission were generated on fix/cascade-asset-silent-drop-3705. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cascade-asset-silent-drop-3705 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cascade-asset-silent-drop-01M0RME0
base_commit: cf5264c15b62671da0326fbe83b1da51e04843ee
created_at: '2026-08-24T03:26:34.079485+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/cascade.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/cascade.py
- tests/charter/test_cascade.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Shared collection seam (`_referenced_artifacts` partitions kind-filtered nodes)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/charter/cascade.py`).

---

## ⚠️ Mission-wide instructions that live ONLY here (read before starting)

`finalize-tasks` regenerates `tasks.md` from `wps.yaml` on every re-run and has no
mission-level notes/preamble slot (ledger SK-80) — any hand-added prose to
`tasks.md` itself does not survive. The three items below are therefore recorded
in this WP's prompt file (WP01, the numerically-first WP) as the durable home for
mission-wide instructions, and are restated briefly in WP02/WP03/WP04:

1. **Baseline capture is mandatory before this WP's first commit** (plan.md §6).
   Run, from the repo root, before touching any source file:
   ```bash
   .venv/bin/python -m pytest \
     tests/charter/test_cascade.py \
     tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py \
     tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_flags.py \
     tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py \
     tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py \
     -q --tb=short > /tmp/cascade-3705-baseline.txt 2>&1
   ```
   Capture the pass/fail/error COUNT and the exact failing/erroring node-ID list.
   After every WP's final commit (this WP included), re-run the identical command
   and diff the failing-node-ID set against this baseline: a node ID red in BOTH
   is pre-existing (do not "fix" it, do not attribute it to this mission); a node
   ID green in baseline but red post-WP was introduced by this mission and must
   be fixed before the WP is done. `main` carries a known-red baseline (~23
   tests/2 errors, GitHub issue #3284) — classify against it per CLAUDE.md's
   "Test-run baseline-red gotcha" before attributing any red to this mission.

2. **FR-006 is explicitly NOT a work package.** Per spec.md's FR-006 and plan.md
   §7 (both binding, already R1-R6 reviewed), FR-006 — "the eventual PR body
   must cite ADR 2026-08-20-1 and state this is a visibility addition, not a
   policy reversal" — is a PR-open-time process gate verified by the pre-merge
   review squad / accept gate against the PR body text, NOT runtime behavior.
   **No WP implements FR-006 and no red-first ATDD test exists for it anywhere
   in this mission** — manufacturing one would violate charter C-011's intent
   (ATDD pins *user-observable behavior*; FR-006 has none to pin). FR-006 is
   listed in this WP's `requirement_refs` **only** to satisfy
   `finalize-tasks`'s mechanical FR-coverage gate (every `FR-###` in spec.md
   must map to at least one WP, with no exemption mechanism for
   process-gate FRs) — it is NOT implemented, tested, or otherwise touched by
   this WP's diff. Do not write code or a test for FR-006 in this WP or any
   other. SC-005 (verifying the PR body cites the ADR) is owned by a reviewer
   step at mission close, not a WP.

3. **Campsite-clean scope: none.** Plan.md §8 read all four touched-surface
   files live and found no domain-matched pre-existing debt in the functions
   this mission touches (the one pre-existing `# noqa: PLC0415` per render
   function is an unrelated, repo-wide lazy-import convention). No
   campsite-clean commit is warranted anywhere in this mission — do not invent
   one.

4. **Sequential-chain ownership overlap is expected and fine.** WP01 and WP03
   both own `src/charter/cascade.py`; WP02 and WP03 both own
   `src/specify_cli/cli/commands/charter/activate.py`. This is intentional:
   plan.md §12 states WP01 → WP02 → WP03 → WP04 is a strict, non-parallelizable
   sequential dependency chain — each WP needs the field(s)/helper the prior WP
   introduced. `finalize-tasks`'s ownership validator exempts same-lane
   sequential pairs (any two WPs connected by a directed dependency path,
   including transitively) from the no-overlap check — only WPs that could run
   *concurrently* must have disjoint `owned_files`. Nothing in this mission can
   run concurrently, so overlapping ownership across WP01/WP03 and WP02/WP03 is
   correct as designed, not an error to fix.

---

## Objective

Change `_referenced_artifacts` (`src/charter/cascade.py:266-295`) to return both
partitions of the nodes it reaches — the existing activatable-refs list AND the
kind-filtered (structurally non-activatable, `template`/`asset`) nodes it
currently drops via a bare `continue` — from the same single pass, thread the new
partition through all three existing call sites' unpacking, and populate it as a
real field (`not_cascaded_kind_filtered`) on `CascadeActivationResult` only (the
other two dataclasses get their field populated in WP03/WP04). This is FR-001 and
FR-002, and it establishes the ONE shared seam (C-002's "single canonical
authority" requirement) that WP02/WP03/WP04 all build on.

## Context

Today, `_referenced_artifacts` walks the DRG forward-reference closure and, for
every reached node whose `ArtifactKind` is not in `CHARTER_ACTIVATABLE_KINDS`
(`template`/`asset`), drops it silently (`cascade.py:291-292`). Nothing
downstream ever sees it existed — this is the exact defect issue #3705 reports.
`_referenced_artifacts` is called by all three of `cascade_activation_targets`
(`cascade.py:340-379`), `referenced_but_not_cascaded` (`cascade.py:413-444`), and
`deactivation_plan` (`cascade.py:489-565`) — this is the literal shared seam ADR
2026-08-20-1 calls the symmetry primitive, and per C-001 the actual
`CHARTER_ACTIVATABLE_KINDS` filter itself is never touched or reopened by this
mission.

Only `cascade_activation_targets` populates its dataclass's new field with real
data in this WP (`CascadeActivationResult.not_cascaded_kind_filtered`).
`referenced_but_not_cascaded` and `deactivation_plan` are updated ONLY to keep
compiling against the new two-tuple return shape — they bind the second value
with a leading underscore (`_kind_filtered`) since they do not read it yet, per
the explicit ruff-F841 avoidance rule in plan.md §12 (no `# noqa` is planned
anywhere in this mission — see plan.md §5 Sonar constraints). WP03 renames
`_kind_filtered` → `kind_filtered` in `referenced_but_not_cascaded`; WP04 does
the same in `deactivation_plan`.

## Subtasks

### Subtask T001: Capture the mission-wide baseline test run

**Purpose**: Establish the red/green reference point required by charter's
red-first/never-retry-to-green discipline, before any implementation commit in
this mission.

**Steps**:
1. Run the exact command in "Mission-wide instructions" item 1 above.
2. Save the output and note the pass/fail/error counts and the exact set of
   failing/erroring test node IDs.
3. Do not proceed to T002 until this baseline is captured.

**Files**: none changed (verification only); baseline output stored locally
(e.g. `/tmp/cascade-3705-baseline.txt`), not committed.

**Validation**: baseline output exists and its failing-node-ID set is recorded
for later diffing (T007 and every subsequent WP's own verification step).

---

### Subtask T002: Write the RED-first ATDD test (engine-level, FR-001/FR-002)

**Purpose**: Pin the user-observable behavior this WP delivers — a kind-filtered
node is collected and threaded into `CascadeActivationResult` — before any
implementation code exists, per charter C-011.

**Steps**:
1. In `tests/charter/test_cascade.py`, construct a fixture `DRGGraph` with one
   source node that has two outgoing `suggests` edges: one to a `tactic`-kind
   node, one to an `asset:...`-kind node (the issue's own repro fixture shape —
   see spec.md User Story 1's Independent Test).
2. Call `cascade_activation_targets(graph, source, CascadeScope.all())` and
   assert:
   ```python
   result.not_cascaded_kind_filtered == {"asset": ["qa-traceability-lint"]}
   ```
   (or whatever bare-ID the fixture uses — assert the exact kind→sorted-IDs
   shape, matching `activated`'s and `skipped_by_scope`'s existing convention).
3. Confirm this assertion is RED on `fix/cascade-asset-silent-drop-3705` today
   (the field does not exist yet — expect an `AttributeError` or equivalent).
4. Commit this test as its OWN commit, before any implementation commit in this
   WP. Use a conventional-commit type (e.g. `test(charter): ...`).

**Files**: `tests/charter/test_cascade.py` (new test function, ~20-30 lines).

**Validation**: `pytest tests/charter/test_cascade.py::<new_test_name> -q` fails
with the new field missing; the reviewer independently re-runs this on
`fix/cascade-asset-silent-drop-3705` to confirm RED before any implementation
commit is reviewed.

---

### Subtask T003: Change `_referenced_artifacts`'s return shape

**Purpose**: Implement the single shared collection seam (FR-001).

**Steps**:
1. In `src/charter/cascade.py`, change `_referenced_artifacts`'s return type from
   `list[ReferencedArtifact]` to
   `tuple[list[ReferencedArtifact], list[ReferencedArtifact]]` —
   `(activatable, kind_filtered)`.
2. At the exact point of today's bare `continue` (`cascade.py:291-292`), append
   the `ReferencedArtifact` to the new `kind_filtered` list instead of
   discarding it, per plan.md §2's exact shape:
   ```python
   for urn in reachable:
       kind = _kind_of(urn)
       if kind is None:
           continue
       ref = ReferencedArtifact(kind=kind, artifact_id=_bare_id(urn), urn=urn)
       if kind not in CHARTER_ACTIVATABLE_KINDS:
           kind_filtered.append(ref)
           continue
       activatable.append(ref)
   ```
3. Do NOT touch the `kind not in CHARTER_ACTIVATABLE_KINDS` membership test
   itself (C-001) — reuse it verbatim; this remains the ONLY place in the
   codebase that runs this test (FR-001's single-canonical-authority
   requirement).
4. Reuse the existing `ReferencedArtifact` dataclass (`cascade.py:304-319`)
   for the kind-filtered partition — do not invent a sibling dataclass.

**Files**: `src/charter/cascade.py` (~10-line change inside
`_referenced_artifacts`).

**Validation**: function still type-checks; no other call site is touched yet
(that's T004) so the module will not import cleanly until T004 lands in the
same commit — land T003 and T004 together as one implementation commit if your
tooling requires an importable intermediate state, or as sequential commits if
it does not; either way this WP's own FINAL commit must be green.

---

### Subtask T004: Update all three call sites' unpacking

**Purpose**: Keep every consumer of `_referenced_artifacts` compiling against
its new two-tuple return shape, per plan.md §12's explicit per-call-site rule.

**Steps**:
1. `cascade_activation_targets` (`cascade.py:340-379`): change to
   ```python
   activatable, kind_filtered = _referenced_artifacts(graph, source_urn)
   ```
   — **unqualified**, because this function populates the real field value
   from it (T005).
2. `referenced_but_not_cascaded` (`cascade.py:413-444`): change to
   ```python
   activatable, _kind_filtered = _referenced_artifacts(graph, source_urn)
   ```
   — **leading underscore**, because this WP does not read the second value
   here yet. This is required to keep this WP's own commit lint-clean under
   ruff's `F841` (no `# noqa` additions are planned per plan.md §5).
3. `deactivation_plan` (`cascade.py:489-565`): same leading-underscore
   treatment as step 2, same reason.
4. All three call sites continue iterating `activatable` through their
   EXISTING scope-bucketing logic completely unchanged — this is what keeps
   C-006 true (kind-filtered nodes must never flow through
   `CascadeScope.selects()` or the existing bucketing loops). Do not merge
   `kind_filtered`/`_kind_filtered` into the same iterable as `activatable`
   before or during scope-partitioning.

**Files**: `src/charter/cascade.py` (three small edits, one per function).

**Validation**: `ruff check src/charter/cascade.py` reports zero new
`F841`/other issues; all three functions still import and run.

---

### Subtask T005: Populate `CascadeActivationResult.not_cascaded_kind_filtered`

**Purpose**: Give `_render_cascade_activation` (WP02) real data to render — the
literal deliverable of FR-002.

**Steps**:
1. Add a new field to `CascadeActivationResult` (`cascade.py:322-337`):
   ```python
   not_cascaded_kind_filtered: dict[str, list[str]] = field(default_factory=dict)
   ```
   alongside the existing `activated` and `skipped_by_scope` fields, following
   their same kind→sorted-bare-IDs shape.
2. In `cascade_activation_targets`, populate this field from the `kind_filtered`
   list produced by T003/T004's unpacking (group by kind, sorted bare IDs per
   kind — same convention as `activated`/`skipped_by_scope`).
3. Do NOT populate `NoCascadeReport`'s or `DeactivationPlan`'s equivalent field
   in this WP — those are WP03's and WP04's jobs respectively. This WP does not
   touch the CLI layer at all; there is no user-visible console change from
   this WP alone.

**Files**: `src/charter/cascade.py` (`CascadeActivationResult` dataclass +
`cascade_activation_targets` body).

**Validation**: T002's ATDD test now passes (GREEN).

---

### Subtask T006: Land the C-006 required test — activation-side half

**Purpose**: C-006 requires proof that a kind-filtered node, under
`--cascade all` (`CascadeScope.all()`, kind-agnostic — `is_all=True` selects
ANY kind), never leaks into `activated` or `skipped_by_scope`. This WP lands
the activation-side half; WP04 lands the deactivation-side half against
`DeactivationPlan`.

**Steps**:
1. Using the same fixture as T002, under `CascadeScope.all()`, assert:
   - the asset URN appears in `result.not_cascaded_kind_filtered`
   - the asset URN does NOT appear anywhere in `result.activated`
   - the asset URN does NOT appear anywhere in `result.skipped_by_scope`
2. This can be additional assertions in T002's same test function, or a
   separate test function in the same commit — either is acceptable as long as
   it is RED before T003-T005's implementation and GREEN after.

**Files**: `tests/charter/test_cascade.py`.

**Validation**: assertions pass after T003-T005 land; this is the
activation-side half of C-006 — note in the PR/WP notes that WP04 completes
the deactivation-side half, since C-006 as a whole is only satisfied once both
land.

---

### Subtask T007: Verify GREEN, diff against baseline, commit

**Purpose**: Close out the WP with a clean, green, lint-passing final commit.

**Steps**:
1. Re-run the exact scoped command from "Mission-wide instructions" item 1.
2. Diff the failing-node-ID set against T001's captured baseline. Any newly-red
   node ID must be fixed before this WP is done; any node ID red in both is
   pre-existing and must not be "fixed" here.
3. Run `ruff check src/charter/cascade.py tests/charter/test_cascade.py` and
   `mypy` over the touched files — zero new issues, no `# noqa`/`# type:
   ignore` additions.
4. Commit the implementation as one or more commits AFTER T002's RED test
   commit — never before it.

**Files**: none new; verification + commit only.

**Validation**: T002's and T006's assertions are GREEN; scoped baseline diff
shows no new red; `ruff`/`mypy` clean on touched files.

## Definition of Done

- `_referenced_artifacts` returns `tuple[list[ReferencedArtifact],
  list[ReferencedArtifact]]`; the `kind not in CHARTER_ACTIVATABLE_KINDS` test
  is unchanged and still the only place in the codebase running it (C-001,
  FR-001).
- All three call sites (`cascade_activation_targets`,
  `referenced_but_not_cascaded`, `deactivation_plan`) unpack the new tuple per
  T004's underscore-prefix rule and still pass their existing tests unmodified.
- `CascadeActivationResult.not_cascaded_kind_filtered` exists and is populated
  with real data by `cascade_activation_targets` (FR-002).
- The RED-first ATDD test from T002 is a separate commit preceding all
  implementation commits in this WP, and is verified RED on
  `fix/cascade-asset-silent-drop-3705` → GREEN on this WP's final commit.
- T006's C-006 activation-side assertions pass: the kind-filtered node never
  appears in `activated` or `skipped_by_scope` under `CascadeScope.all()`.
- `tests/charter/test_cascade.py::test_instantiates_is_followed_but_template_dropped_at_candidacy`
  (line 648, C-004) still passes UNMODIFIED.
- `tests/charter/test_cascade.py::test_cascade_never_proposes_template_or_asset`
  (line 603, C-004) — the sibling pinned template/asset-blindness test — also
  still passes UNMODIFIED.
- No CLI file is touched; no console output changes.
- Scoped baseline diff (T001 vs. T007) shows no new red.
- Per-subtask completion evidence is recorded via
  `spec-kitty agent tasks mark-status <Txxx> --status done` (event-sourced), not
  a ticked checkbox.

## Risks

- **Ruff F841 on the two underscore-bound call sites.** Mitigated by the
  explicit leading-underscore rule in T004 — do not skip it or reach for
  `# noqa` instead.
- **Accidentally merging `kind_filtered` into the `activatable` iterable before
  scope-partitioning**, which would be a C-006 violation (a kind-filtered node
  could then land in `activated` under `--cascade all`, a functional reversal
  of C-001 at runtime). T003's exact shape (append to `kind_filtered` at the
  bare-`continue` site, never merge lists afterward) avoids this by
  construction — do not restructure the loop.
- **Weakening or touching either C-004-pinned test** at line 648 or line 603
  — do not modify their existing assertions; only add new, separate
  assertions elsewhere.

## Reviewer Guidance

- Confirm T002's test was RED on `fix/cascade-asset-silent-drop-3705` (check
  out that commit and re-run) before any implementation commit, and GREEN on
  this WP's final commit.
- Confirm the `kind not in CHARTER_ACTIVATABLE_KINDS` test appears exactly
  once in the diff (inside `_referenced_artifacts`) — no sibling
  reimplementation anywhere else.
- Confirm `referenced_but_not_cascaded` and `deactivation_plan` bind the
  underscore-prefixed name and do not yet construct/populate their dataclass's
  new field — that is WP03's/WP04's job, not this WP's.
- Confirm no CLI file (`activate.py`, `deactivate.py`) is touched.
- Confirm the C-004-pinned test at `tests/charter/test_cascade.py:648` is
  present, unmodified, and still passing.
- Confirm the second C-004-pinned test,
  `tests/charter/test_cascade.py::test_cascade_never_proposes_template_or_asset`
  (line 603), is also present, unmodified, and still passing.

Implementation command: `spec-kitty agent action implement WP01 --agent claude`
