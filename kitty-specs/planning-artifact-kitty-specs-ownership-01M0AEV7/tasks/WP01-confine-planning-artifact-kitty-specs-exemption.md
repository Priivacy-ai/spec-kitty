---
work_package_id: WP01
title: Confine and exempt planning_artifact from the finalize kitty-specs ban
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
planning_base_branch: feat/3222-2643-kitty-specs-ownership
merge_target_branch: feat/3222-2643-kitty-specs-ownership
branch_strategy: Planning artifacts for this mission were generated on feat/3222-2643-kitty-specs-ownership. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/3222-2643-kitty-specs-ownership unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history:
- Created by /spec-kitty.tasks (post-plan squad findings folded in)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/tasks/test_finalize_planning_artifact_kitty_specs.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_parsing.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_mission_parsing.py
- tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
- tests/tasks/test_finalize_tasks_owned_files_validation.py
- tests/tasks/test_finalize_planning_artifact_kitty_specs.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and
tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved
initialization. State which directives/tactics you applied before writing code.

## Objective

Narrow the `finalize-tasks` "owned_files cannot include paths under `kitty-specs/`" ban so a
`planning_artifact` work package whose ownership is **confined to planning surfaces** may declare
its `kitty-specs/<mission>/…` deliverables — while the ban stays **fail-closed for `code_change`**
and for any WP that also owns code. This closes #3222 (primary) and #2643.

The ownership model already blesses this shape (`ownership/validation.py` `_PLANNING_PREFIXES`,
`validate_execution_mode_consistency`) and the lane layer already routes such WPs to the repo-root
planning lane; only the finalize ban disagrees. This WP aligns finalize to the model.

**Read first**: `spec.md`, `plan.md` (IC-01/IC-02), `data-model.md` (decision table + INV-1..4),
`contracts/finalize-ownership-contract.md`, and `squad-findings-post-plan.md` (the adversarial
findings that shaped the exemption and the tests — do not regress them).

## ATDD discipline

Drive red-first: write T001 (the positive acceptance test) and watch it FAIL for the *right*
reason before T002. Then implement T002 and turn it green. The confinement/floor/inference/overlap
tests (T003–T005) each assert a distinct branch — write them alongside the code they pin.

## Subtasks

### T001 — Red-first positive acceptance test

**Purpose**: Prove a `planning_artifact` WP owning only `kitty-specs/<slug>/…` finalizes cleanly and
lands in the planning lane — end-to-end, not "the ban did not fire".

**Critical (squad finding D-1)**: post-fix, control falls through to two downstream HARD gates the
ban previously shadowed — `validate_authoritative_surface` (surface must prefix a kitty-specs owned
file) and `validate_glob_matches` (a literal owned deliverable must exist or be in `create_intent`;
this gate runs even under `--validate-only`). A naive test that sets `authoritative_surface: src/…`
or names a non-existent literal deliverable will be **RED both pre- and post-fix** and prove nothing.

**Build it the reliable way** — pedro verified two working constructions; prefer **surface+create_intent** for the crisp positive (no dependence on inference heuristics):
- `execution_mode: planning_artifact`, `owned_files: [kitty-specs/<slug>/disposition-matrix.md]`,
  `authoritative_surface: kitty-specs/<slug>/`, `create_intent: [kitty-specs/<slug>/disposition-matrix.md]`.
  Use `disposition-matrix.md` (a **non-managed** kind), NOT `analysis-report.md` (managed — that is the
  durability negative in T007). You MUST override the default `authoritative_surface: src/example/` from
  the existing `_build_feature` helper — a `src/` surface hard-fails `validate_authoritative_surface`
  against a kitty-specs owned file (red pre- and post-fix, the D-1 trap).
- The inference-driven variant (used in T004 ACCEPT) OMITS `execution_mode`/`owned_files`/
  `authoritative_surface` entirely (field-absent — NOT `owned_files: []`, which is respected-as-empty
  and leaves the ban nothing to see) with a planning-only body (zero `src/`/`.py`/`tests/` tokens).
- **Assertions (all three — the first is the anti-vacuity guard, finding renata-HIGH):**
  1. the finalized/reduced `owned_files` for the WP contains **at least one `kitty-specs/` entry**
     (`assert any(f.startswith("kitty-specs/") for f in reduced_owned_files)`) — proves the ban's
     trigger condition is mechanically present, so a `docs/`-only vacuous green cannot masquerade as
     a pass;
  2. finalize (`--validate-only`) exits 0;
  3. `wp_id in compute_lanes(...).planning_artifact_wps` (`lanes/models.py:151` — placement positively,
     not by absence-of-error, finding D-5).

**Files**: new `tests/tasks/test_finalize_planning_artifact_kitty_specs.py`. Model fixtures on the
existing `_build_feature` helper in `tests/tasks/test_finalize_tasks_owned_files_validation.py`, but
with a planning-artifact shape. Reuse #2643's reproduction YAML shape as the canonical case.

### T002 — Implement the confined exemption

**Purpose**: Make the ban predicate execution-mode-aware and confined.

**Where**: `src/specify_cli/cli/commands/agent/mission_parsing.py` — `_invalid_mission_specs_owned_files`
(~line 220). It already iterates each WP's `WPMetadata`, so `execution_mode` and `owned_files` are
in hand.

**Exemption condition** (skip flagging the WP's kitty-specs paths) — grant iff BOTH:
1. `str(metadata.execution_mode) == ExecutionMode.PLANNING_ARTIFACT.value` (compare against the enum
   `.value`/normalized — do NOT rely on incidental `StrEnum` equality; finding R-3), AND
2. every entry in `metadata.owned_files` starts with a prefix in `_PLANNING_PREFIXES`
   (`kitty-specs/`, `docs/`) — **import `_PLANNING_PREFIXES` from `specify_cli.ownership.validation`**
   (single authority; do not re-derive the prefixes here). This confinement (finding R-1) means a
   `planning_artifact` WP that also owns `src/`/`tests/` is NOT exempted.
   **Normalize each entry with the existing `_normalize_owned_file_path` before the prefix check**
   (pedro Q5): the ban predicate `_is_mission_specs_owned_file` matches on the *normalized* path, so
   the confinement check MUST use the same path semantics — otherwise a `./kitty-specs/<slug>/spec.md`
   entry trips the ban (normalized) yet fails a raw `startswith("kitty-specs/")` and the WP is
   wrongly judged not-confined → false-reject. Normalizing keeps confinement symmetric with the gate
   it guards. **Decision (blessed): normalize before the prefix check.**

**Extract the predicate** into `_is_confined_planning_wp(metadata) -> bool` (mode `.value` compare AND
`all(normalize(f) starts with a _PLANNING_PREFIXES prefix)`). Pedro confirmed the inline form is only
~cyclomatic 5 (helper not required for the ≤15 ceiling), but the helper gives T006 a clean direct-call
seam to unit-test the exemption predicate in isolation.

**Constraints**:
- Preserve the function identity and the dynamic alias `_invalid_kitty_specs_owned_files`
  (`mission_parsing.py:236`) and shim re-exports — no rename (C-001).
- Do NOT touch `_is_mission_specs_owned_file` (bare `path: str`, no mode).
- `mission_finalize.py`: confirm `_validate_owned_files_not_in_mission_specs` (~:2069) runs *after*
  `_apply_ownership_inference` so `execution_mode` is populated at ban time. No change expected there;
  if a change proves necessary, keep it minimal and record why.

### T003 — Confinement + fail-closed floor tests

**Purpose**: Lock every guardrail the exemption newly exposes; prove the exemption is
*mode-discriminating and confined*, not accidentally broad.
- **Confinement — code prefix (FR-004)**: a `planning_artifact` WP owning `kitty-specs/<slug>/x.md`
  **and** `src/foo.py` is still rejected with `INVALID_WP_OWNED_FILES_KITTY_SPECS`.
- **Confinement — non-code, non-planning prefix (FR-004, decision-table row 4)**: a `planning_artifact`
  WP owning `kitty-specs/<slug>/x.md` **and** `scripts/verify.py` is still rejected — proving
  confinement excludes ANY non-`_PLANNING_PREFIXES` path, not only `src/`/`tests/`.
- **Normalization symmetry (pedro Q5)**: a `planning_artifact` WP whose only owned entry is spelled
  `./kitty-specs/<slug>/x.md` **is still exempted/accepted** (confinement normalizes before the prefix
  check) — this fixture fails if T002 uses a raw `startswith`.
- **Paired accept/reject (REQUIRED — SC-004 / FR-006)**: one shared fixture flipped between
  `execution_mode: planning_artifact` (→ ACCEPT) and `execution_mode: code_change` (→ REJECT with
  `INVALID_WP_OWNED_FILES_KITTY_SPECS`). This near-identical pair is what proves mode-discrimination;
  it is **not** optional and must not be deferred to the existing ban tests (which use different
  fixtures).
- **FR-005 warning preserved (regression / characterization)**: a `planning_artifact` manifest owning
  a `scripts/` path still yields the "owns files outside planning paths" **warning** (not a hard error)
  from `validate_execution_mode_consistency` (`ownership/validation.py:279-284`, untouched by T002).
  Assert as a **direct unit test** of that validator (it runs at finalize `:2085`, after the ban, so it
  is only reachable end-to-end for a WP that owns no kitty-specs path — a unit test is the crisp home).

### T004 — Inference tests

**Purpose**: Pin the inference→ban ordering (finding A-2/D-3).
- **ACCEPT**: a WP with unset `execution_mode` whose owned_files/body carry only planning signals
  infers `planning_artifact` and is accepted.
- **REJECT**: a WP with unset `execution_mode` whose body contains a `src/`/`.py` **code signal**
  infers `code_change`; assert the resolved `execution_mode == "code_change"` BEFORE asserting the
  `INVALID_WP_OWNED_FILES_KITTY_SPECS` rejection — otherwise a naive kitty-specs-owning WP infers
  planning and the test is a false negative. **Read-back seam (pedro)**: either run finalize
  *without* `--validate-only` and read the written WP frontmatter's `execution_mode`, or read the
  in-memory `state.would_modify[<wp>]["changes"]["execution_mode"]` from a `--validate-only` run
  (finalize rejects before commit but after in-memory inference, so both the mode and the error are
  observable). Do not weaken this to asserting only the rejection.

### T005 — Negative-overlap floor

**Purpose**: The exemption now exposes `validate_no_overlap` (finding A-1). Assert two
`planning_artifact` WPs owning overlapping `kitty-specs/<slug>/…` scopes with no dependency edge are
still rejected (an overlap error), proving the exemption is not a blanket kitty-specs bless.

### T006 — Predicate unit-test updates + seam identity

**Purpose**: Keep the direct-call tests honest and the seam intact.
- `tests/specify_cli/cli/commands/agent/test_mission_parsing.py` and
  `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py`: update the direct-call
  tests of `_invalid_mission_specs_owned_files` / `_validate_owned_files_not_in_mission_specs` to
  supply `execution_mode` (add a `planning_artifact`-exempt case and keep a `code_change`-rejected
  case).
- Assert the dynamic alias `_invalid_kitty_specs_owned_files` still resolves to the same object
  (identity), matching the existing `test_mission_shim_reexports.py` / `test_mission_parsing.py`
  contracts.

### T007 — Seam-bound regression guards

**Purpose**: Guard the two research-identified regressions as **pure predicate unit tests**, not
fragile finalize integration tests (finding D-4).
- **authoritative_surface**: exercise `infer_authoritative_surface` (`ownership/inference.py:154`) →
  `validate_authoritative_surface`; assert a `kitty-specs/<slug>/…` owned file yields a compatible
  surface (no surface hard-error for the accepted case).
- **Durability is filename-scoped (finding D-2 / C-003)**: exercise the real authorities pedro
  confirmed — `kind_for_mission_file` (`src/mission_runtime/artifacts.py:393`, filename-anchored via
  `_MISSION_FILE_KIND_BY_BASENAME` at `artifacts.py:211` and `_COORD_RESIDUE_DIRS["tasks"]` at
  `artifacts.py:260`) and the managed frozenset `_AUTO_REBASE_MANAGED_LAYOUT_KINDS` (`auto_rebase.py:105`
  = `{ANALYSIS_REPORT, LANE_STATE, WORK_PACKAGE_TASK}`). Assert `kitty-specs/<slug>/disposition-matrix.md`
  → `kind is None` (durable, C-003 holds); **negative** assertions that `kitty-specs/<slug>/analysis-report.md`
  → `ANALYSIS_REPORT` and `kitty-specs/<slug>/tasks/WP01-x.md` → `WORK_PACKAGE_TASK` are in the managed
  frozenset (reconciled). Quote the frozenset/basename map so the test asserts the real authority, not
  a re-derived set.

### T008 — Quality gate + follow-up

**Purpose**: Prove the change is clean and record the deferred follow-up.
- `ruff check` and `mypy --strict` clean on the two changed source files (no `# noqa`/`# type: ignore`).
- Cyclomatic complexity of the changed predicate ≤ 15.
- Run the targeted suites green (NFR-001):
  ```bash
  PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 .venv/bin/python -m pytest \
    tests/specify_cli/cli/commands/agent/test_mission_parsing.py \
    tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py \
    tests/tasks/test_finalize_tasks_owned_files_validation.py \
    tests/agent/test_finalize_tasks_owned_files_validation.py \
    tests/tasks/test_finalize_planning_artifact_kitty_specs.py \
    tests/lanes/test_compute_planning_artifact.py \
    -q -p no:cacheprovider
  ```
- Record the deferred **follow-up (finding A-4)** — **REQUIRED at merge, not optional** (priti): file a
  tech-debt issue for the duplicated topology rule (`policy/commit_guard.py:88` runtime kitty-specs rule
  vs the finalize plan-time ban, no shared helper — a `can_lane_commit(path, mode)` unification is a
  later slice), and reference that issue number in the PR body. File **at merge** (the duplication is a
  confirmed, locatable invariant only once this predicate-local fix lands), not now.

## Branch Strategy

- Planning/base branch: `feat/3222-2643-kitty-specs-ownership`.
- Final merge target: `feat/3222-2643-kitty-specs-ownership` (later PR'd to `upstream/main`).
- The execution worktree for this WP is allocated per the computed lane from `lanes.json`
  (`spec-kitty implement WP01` prepares it) — do not reconstruct the path by hand.

## Definition of Done

- All 8 subtasks complete; the acceptance test (T001) is red before T002 and green after, and its
  anti-vacuity assertion (finalized `owned_files` contains a `kitty-specs/` entry) is present.
- **Every behavior-changing decision-table row is covered by a test**: planning+kitty-specs ACCEPT
  (T001), planning+kitty-specs+`src/` REJECT (T003), planning+kitty-specs+`scripts/` REJECT (T003,
  row 4), `./`-normalized planning ACCEPT (T003), paired code_change REJECT on the flipped fixture
  (T003, SC-004), unset→planning ACCEPT (T004), unset→code REJECT with resolved-mode assertion (T004),
  overlapping-planning REJECT (T005). Unchanged rows (docs-only ACCEPT, no-kitty-specs ACCEPT) are
  low-risk and need no new test.
- FR-005 warning preserved is asserted by a direct `validate_execution_mode_consistency` unit test (T003).
- `ruff` + `mypy --strict` clean; complexity ≤ 15; targeted suites green.
- Alias/shim seam preserved (identity test passes); the confinement predicate normalizes paths
  symmetrically with the ban (pedro Q5).
- Durability carve-out documented + negatively asserted against the real managed-kind authority.
- Follow-up (A-4) filed as a tracked issue at merge and referenced in the PR body.

## Risks & Reviewer Guidance

- **Reviewer**: verify the exemption keys on `ExecutionMode.PLANNING_ARTIFACT.value` AND the
  confinement to `_PLANNING_PREFIXES` (imported, not re-derived) — a mode-only guard is the MEDIUM
  hole. Verify T001 actually clears the two downstream gates (inference-driven or surface+create_intent)
  and asserts planning-lane placement, not just exit-0. Verify T004's reject case asserts the resolved
  `code_change` mode. Verify the durability test is filename-scoped (analysis-report.md negative).
- **Do not** implement the `owned_files: []` end-to-end direction (C-002) — out of scope.
