---
work_package_id: WP02
title: Reconcile research/documentation/software-dev manifests
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-expected-artifacts-manifest-repair-01KZY498-lane-a
base_commit: 281eb9b901f8d375d1a066b97f44e65f96dc6c87
created_at: '2026-08-14T03:47:39.777674+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Content reconciliation (depends on WP01)
assignee: ''
agent: claude
history:
- timestamp: '2026-08-14T00:00:00Z'
  agent: claude
  action: Prompt generated via manual /spec-kitty.tasks-outline + /spec-kitty.tasks-packages equivalent (tasks-authoring agent)
agent_profile: implementer-ivan
authoritative_surface: packs/built-in/missions/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- packs/built-in/missions/research/expected-artifacts.yaml
- packs/built-in/missions/documentation/expected-artifacts.yaml
- packs/built-in/missions/software-dev/expected-artifacts.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Reconcile research/documentation/software-dev manifests

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Correct the 8 named divergences between the three shipped manifests'
`required_by_step` content and `runtime_bridge_cores.py`'s guard-table reality
(FR-001 through FR-008), and record the `manifest_version`-stability rationale
(FR-013/Decision 2) inline in each of the three edited files. This is
**Implementation Concern IC-02** from `plan.md`.

## Context

**Why this WP exists**: `spec.md` User Story 1 — the manifests must describe
exactly what the guard tables already check, no more, no less, so a future gate
built on this manifest doesn't retroactively block missions on artifacts no guard
requires and no observed mission has produced. **Reconciliation direction is
manifest-to-match-guard, never the reverse** (`tracer-approach.md`) — even for
FR-008, which reads at first glance like "the guard is wrong." It is not fixed
here; a guard-side bug reading is filed as an independent follow-up, never
patched into `runtime_bridge_cores.py` (C-001).

**Dependency on WP01**: this WP depends on WP01 landing first so any accidental
new-key typo introduced while editing this WP's content is caught immediately by
the hardened `extra="forbid"` schema, not silently ignored.

**Do not touch**: `src/runtime/next/runtime_bridge_cores.py`,
`runtime_bridge_composition.py`, `runtime_bridge_io.py` (C-001, always).

### ⚠️ Out-of-map edit: `tests/dossier/test_manifest.py`

This WP does **not** list `tests/dossier/test_manifest.py` in its `owned_files` —
WP01 owns that file. This WP nonetheless makes a **small, well-justified
out-of-map edit** to it (permitted per the ownership rules: "a small,
well-justified out-of-map edit is acceptable when recorded with a one-line
rationale"): it adds a new class, `TestManifestReconciliation`, and separately
corrects **three pre-existing tests** in *other*, already-existing classes that
this WP's own content edits make stale (see T011/T013 below — this was verified by
reading the current file, not assumed from the plan). **Stay strictly within
`TestManifestReconciliation` for new tests, and touch only the three named
pre-existing tests for corrections** — do not edit any other test in this file.
Rationale to record in the commit message: "FR-006/FR-008 content changes make
three pre-existing assertions stale; corrected in the same commit that changes the
content they pin, per ATDD discipline."

**⚠️ Chokepoint**: WP03 and WP04 similarly each make an out-of-map edit to this
same file (different new sections, `TestPlanManifest` and
`TestOverrideMirrorDeprecation` respectively) and each depends only on WP01, the
same as this WP — per `lanes.json`, WP02, WP03, and WP04 all sit in
`parallel_group: 1`, so all three are nominally parallel and none has a
dependency edge on either of the other two. See `tracer-approach.md`'s
"Chokepoints & execution sequencing" addendum for the recommended execution
order to avoid a git merge collision on this shared file.

### Finding surfaced during tasks-authoring (not named in `plan.md`'s Test Strategy table)

Reading the *current* `tests/dossier/test_manifest.py` (492 lines) found **two
additional pre-existing tests**, beyond the one `plan.md`/FR-012 already names
(`test_software_dev_manifest_plan_step_has_plan_and_tasks`, line 395), that pin
content this WP's own edits make stale:

1. **`TestManifestRegistry.test_get_required_artifacts_plan_step`** (lines
   249-257): asserts `len(specs) >= 2` at the `plan` step and asserts
   `output.tasks.list` (`tasks.md`) is present. This breaks under FR-006 (which
   removes `tasks.md` from the `plan` step). Must be corrected in the same commit
   as FR-006's content edit.
2. **`TestManifestIntegration.test_software_dev_implement_requires_analysis_report`**
   (lines 415-423): asserts `analysis-report.md` is required, blocking, at the
   `implement` step. This breaks under FR-008 (which removes this entry). Must be
   corrected in the same commit as FR-008's content edit.

Both are **pre-existing, currently-passing tests in classes this WP does not
otherwise own** (`TestManifestRegistry`, `TestManifestIntegration`) — correcting
them is a direct, unavoidable consequence of this WP's own content edits (the
same category as the one stale test `plan.md` already named), not scope creep.
Flagging this explicitly here per this mission's brief to surface findings rather
than silently expand or work around them.

## Subtask T008: Red-first test — `research/gathering` (FR-001, AS1)

**Purpose**: Pin the corrected `research/gathering` step content before editing it.

**Steps**:
1. In `tests/dossier/test_manifest.py`, add a new class `TestManifestReconciliation`.
2. Add `test_research_manifest_gathering_requires_source_register`: load the
   `research` manifest, call `ManifestRegistry.get_required_artifacts(manifest,
   "gathering")`, and assert it returns a spec with `path_pattern ==
   "source-register.csv"` and `blocking is True`.

**Files**: `tests/dossier/test_manifest.py` (new class + first test, ~15 lines).
**Validation**: RED — `research/expected-artifacts.yaml`'s current `gathering:`
block is `[]`.

## Subtask T009: Red-first test — `documentation/audit` + `documentation/design` (FR-002/FR-003, AS2)

**Purpose**: Pin the corrected `audit`/`design` step content.

**Steps**:
1. Add `test_documentation_manifest_audit_design_reconciled` to
   `TestManifestReconciliation`: load the `documentation` manifest;
   `get_required_artifacts(manifest, "audit")` returns exactly one blocking spec
   with `path_pattern == "gap-analysis.md"` (assert `plan.md`/`tasks.md` are
   **absent** — explicit "must NOT contain" assertions, not just "contains
   gap-analysis.md"); `get_required_artifacts(manifest, "design")` returns exactly
   one blocking spec with `path_pattern == "plan.md"` (assert `tasks.md` is
   absent).

**Files**: `tests/dossier/test_manifest.py` (~20 lines).
**Validation**: RED — current `audit:` has 3 entries (`plan.md`, `tasks.md`,
`gap-analysis.md`); current `design:` has 2 entries (`plan.md`, `tasks.md`).

## Subtask T010: Red-first test — `documentation/validate` + `documentation/publish` (FR-004/FR-005, AS3)

**Purpose**: Pin the corrected `validate`/`publish` step content.

**Steps**:
1. Add `test_documentation_manifest_validate_publish_reconciled` to
   `TestManifestReconciliation`: `get_required_artifacts(manifest, "validate")`
   returns exactly one blocking spec with `path_pattern == "audit-report.md"`;
   `get_required_artifacts(manifest, "publish")` returns exactly one blocking spec
   with `path_pattern == "release.md"`.

**Files**: `tests/dossier/test_manifest.py` (~15 lines).
**Validation**: RED — both steps are currently `[]`.

## Subtask T011: Red-first test — `software-dev/plan` (FR-006, AS4) + correct 2 pre-existing stale tests

**Purpose**: Pin the corrected `plan` step content and fix the tests it breaks.

**Steps**:
1. Add `test_software_dev_manifest_plan_step_has_plan_only` to
   `TestManifestReconciliation`: `get_required_artifacts(manifest, "plan")`
   returns exactly one blocking spec with `path_pattern == "plan.md"`; explicitly
   assert `tasks.md` (`output.tasks.list`) is **absent** from the returned specs.
2. **Delete** the stale `test_software_dev_manifest_plan_step_has_plan_and_tasks`
   (`TestManifestIntegration`, lines 395-404) — its assertion
   (`assert all(s.blocking for s in plan_md + tasks_md)`) is superseded by T011.1's
   new test (FR-012's named correction).
3. **Correct** `TestManifestRegistry.test_get_required_artifacts_plan_step` (lines
   249-257, the finding noted in Context above): change the `len(specs) >= 2`
   assertion to `len(specs) == 1`, and change `assert any(s.artifact_key ==
   "output.tasks.list" for s in specs)` to an explicit "must NOT contain"
   assertion (`assert not any(...)`), keeping the `output.plan.main` assertion
   as-is. Update the test's docstring to reflect the corrected shape.

**Files**: `tests/dossier/test_manifest.py` (~20 new lines in
`TestManifestReconciliation`; ~10 changed lines across
`TestManifestIntegration`/`TestManifestRegistry`).
**Validation**: The new test is RED against current content; the two corrected
tests should already be GREEN against their **new** assertions once T014's content
edit lands (they are being corrected to match the target state, not left red).

## Subtask T012: Red-first test — CLI-native tasks steps (FR-007, AS5)

**Purpose**: Pin the new `tasks_outline`/`tasks_packages`/`tasks_finalize` entries.

**Steps**:
1. Add `test_software_dev_manifest_tasks_outline_packages_finalize` to
   `TestManifestReconciliation`: `get_required_artifacts(manifest,
   "tasks_outline")` returns one blocking spec with `path_pattern == "tasks.md"`;
   `get_required_artifacts(manifest, "tasks_packages")` and `(..., "tasks_finalize")`
   each return one blocking spec whose `path_pattern` is **exactly `"tasks/WP*.md"`**
   — this is the glob spec.md's FR-007/AS5 names explicitly and the one the guard
   itself checks (`tasks_dir.glob("WP*.md")` in
   `runtime_bridge_cores.py`/`runtime_bridge_io.py:796`); do not use the broader
   `tasks/*.md` pattern, which would match non-`WP`-prefixed files the guard
   ignores.

**Files**: `tests/dossier/test_manifest.py` (~20 lines).
**Validation**: RED — none of these three step keys currently exist in
`required_by_step`.

## Subtask T013: Red-first test — `software-dev/implement` (FR-008, AS6) + correct 1 pre-existing stale test

**Purpose**: Pin the corrected (empty) `implement` step content and fix the test
it breaks.

**Steps**:
1. Add `test_software_dev_manifest_implement_has_no_filesystem_requirement` to
   `TestManifestReconciliation`: `get_required_artifacts(manifest, "implement")`
   returns `[]`.
2. **Correct** `TestManifestIntegration.test_software_dev_implement_requires_analysis_report`
   (lines 415-423, the second finding noted in Context above). This test's
   current assertions (`len(report) > 0`, `blocking is True`,
   `path_pattern == "analysis-report.md"`) directly contradict FR-008's target
   state. Rewrite it to assert `get_required_artifacts(manifest, "implement") ==
   []` (or delete it and fold its intent into T013.1's new test — prefer deleting
   plus a docstring note pointing at the replacement, to avoid two tests asserting
   the same fact under different names).

**Files**: `tests/dossier/test_manifest.py` (~15 new lines; ~10 changed/removed
lines in `TestManifestIntegration`).
**Validation**: New test RED against current content (`analysis-report.md` still
present); corrected test reflects the target state.

## Subtask T014: Implement — all 8 content edits + FR-013 rationale comment

**Purpose**: Land the actual YAML content changes matching T008-T013's red-first
tests, plus the `manifest_version` rationale comment in each of the three files.

**Steps**:
1. **`packs/built-in/missions/research/expected-artifacts.yaml`**: under
   `gathering:`, replace the `[]` with one blocking entry:
   `artifact_key: "evidence.source-register"` (pick a key consistent with the
   file's existing naming convention — `evidence.*` for filesystem-checked
   evidence artifacts), `artifact_class: "evidence"`, `path_pattern:
   "source-register.csv"`, `blocking: true`. Add an inline YAML comment
   immediately below documenting that `_evaluate_gathering_guard` also enforces
   `source_documented_count >= 3`, a non-filesystem-expressible check this schema
   has no field for.
2. **`packs/built-in/missions/documentation/expected-artifacts.yaml`**:
   - `audit:` — remove the `workflow.plan.documentation` (`plan.md`) and
     `workflow.tasks.documentation` (`tasks.md`) entries; keep only the
     `evidence.gap-analysis` entry.
   - `design:` — remove the `workflow.tasks.documentation` (`tasks.md`) entry;
     keep only `workflow.plan.documentation` (`plan.md`).
   - `validate:` — replace `[]` with one blocking entry:
     `artifact_key: "evidence.audit-report"` (the file's `optional_always` block
     already has a matching key/path convention for `audit-report.md` — reuse
     `evidence.audit-report` for consistency, moving it from optional-only to also
     required-at-`validate`, or keep both if the schema allows an artifact_key to
     appear in both `optional_always` and `required_by_step` — verify this is not
     rejected by any uniqueness constraint before finalizing), `artifact_class:
     "evidence"`, `path_pattern: "audit-report.md"`, `blocking: true`.
   - `publish:` — replace `[]` with one blocking entry: `artifact_key:
     "output.release.main"`, `artifact_class: "output"`, `path_pattern:
     "release.md"`, `blocking: true`.
3. **`packs/built-in/missions/software-dev/expected-artifacts.yaml`**:
   - `plan:` — remove the `output.tasks.list` (`tasks.md`) entry; keep only
     `output.plan.main` (`plan.md`).
   - Add three new `required_by_step` keys after `plan:` and before `implement:`
     (matching `runtime_bridge_cores.py`'s CLI-native tasks vocabulary order):
     `tasks_outline:` → one blocking entry, `artifact_key: "output.tasks.list"`,
     `path_pattern: "tasks.md"`; `tasks_packages:` → one blocking entry,
     `artifact_key: "output.tasks.per_wp"`, `path_pattern: "tasks/WP*.md"`
     (matching spec.md's FR-007/AS5 text and the guard's actual
     `tasks_dir.glob("WP*.md")` call — not the broader `tasks/*.md`), with an
     inline comment documenting that `_evaluate_tasks_packages_guard` also
     enforces `requirement_mapping_failures` (non-expressible); `tasks_finalize:`
     → the same `tasks/WP*.md` glob entry, blocking, with an inline comment
     documenting the occurrence-gate/dependency-frontmatter checks
     (non-expressible), matching the existing AS7/SC-001 inline-comment pattern
     already used elsewhere in this file style.
   - `implement:` — replace the `evidence.analysis-report` entry with `[]`.
4. **All three files**: add (or extend, if a FR-013 comment placeholder does not
   yet exist) an inline YAML comment at/near `manifest_version: "1"` recording
   Decision 2's rationale — e.g. "`manifest_version` is a sync-namespace identity
   key (feeds `NamespaceRef`), not a content-freshness counter; do not bump on
   content-only changes — see `tracer-design-decisions.md` Decision 2." This
   comment's *presence* is checked cross-file by WP05's
   `test_manifest_version_rationale_comment_present` — write it now so WP05 need
   only verify, not chase you down for it later.

**Files**: `packs/built-in/missions/research/expected-artifacts.yaml`,
`packs/built-in/missions/documentation/expected-artifacts.yaml`,
`packs/built-in/missions/software-dev/expected-artifacts.yaml` (all edited,
existing files — ~10-20 changed/added lines each).
**Validation**: All of T008-T013's new/corrected tests go GREEN. Re-run
`tests/dossier/test_manifest.py` in full (not just the new section) to confirm
zero new failures elsewhere in the file.

## Definition of Done

- [ ] `TestManifestReconciliation` section exists with all 6 new tests
      (T008-T013), each committed **before** T014's content-edit commit (C-011).
- [ ] The 3 pre-existing stale tests (1 named by `plan.md`/FR-012, 2 found during
      tasks-authoring) are corrected in the same commit as the content edit that
      makes them stale, not left red.
- [ ] All 8 divergences (FR-001-FR-008) are corrected in the 3 YAML files.
- [ ] Each of the 3 files carries the FR-013 `manifest_version` rationale comment.
- [ ] `mypy --strict` / `ruff check .` — N/A for YAML content; applies to the
      corrected/added Python test code (NFR-002).
- [ ] No change to `runtime_bridge_cores.py`/`runtime_bridge_composition.py`/
      `runtime_bridge_io.py` (C-001).
- [ ] `manifest_version` unchanged at `"1"` in all 3 files (C-002 — final
      cross-file check happens in WP05, but this WP must not regress it).

## Risks

- **FR-008's `implement`-step removal reads, at first glance, like "the guard is
  wrong, not the manifest."** This WP explicitly rejects that reading
  (`tracer-approach.md`) — do not "fix" `runtime_bridge_cores.py` instead.
  Mitigated by the inline YAML comment (none needed here since the entry is
  simply removed, not replaced with a non-expressible-check comment) and this
  prompt's own restatement.
- **Chokepoint**: see the Context section's chokepoint note re: WP03 and WP04
  sharing `test_manifest.py`.
- **The two newly-found stale tests (T011.3, T013.2)** are a real, unplanned
  addition to this WP's scope relative to `plan.md`'s Test Strategy table (which
  only named one). Flag any further stale-test discoveries the same way — do not
  silently patch and move on without noting it in the PR body.

## Reviewer Guidance

- Confirm every content edit traces to exactly one FR (FR-001 through FR-008) and
  matches the guard-table branch cited in `plan.md`'s Test Strategy table — spot
  check at least 2 of the 8 against `runtime_bridge_cores.py` directly, don't just
  trust the WP's own description.
  - Confirm the two newly-found stale-test corrections (T011.3, T013.2) are
  present and correctly scoped — this is new information relative to `plan.md`,
  worth extra reviewer attention.
- Confirm the `manifest_version` rationale comment is present in all 3 files and
  is specific (references Decision 2 / sync-namespace identity), not generic.
- Confirm red→green evidence for all 6 new tests.

Implementation command: `spec-kitty agent action implement WP02 --agent claude`
