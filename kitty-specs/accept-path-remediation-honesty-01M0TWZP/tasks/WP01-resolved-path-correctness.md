---
work_package_id: WP01
title: Resolved-path correctness
dependencies: []
requirement_refs:
- FR-001
- NFR-002
planning_base_branch: fix/accept-path-remediation-honesty-3730
merge_target_branch: fix/accept-path-remediation-honesty-3730
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-remediation-honesty-3730. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-remediation-honesty-3730 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T016
phase: Phase 1 - Implementation
history:
- timestamp: '2026-08-25T00:00:00Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: src/specify_cli/validators/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/validators/paths.py
- tests/specify_cli/acceptance/**
- tests/agent/test_validators_unit.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix `validate_mission_paths` (`src/specify_cli/validators/paths.py`) so the missing-path
string it stores and reports is the **resolved** filesystem location it actually tested
(`full_path`, `feature_dir`- or `project_root`-relative), not the bare declared token
(e.g. `"contracts/"`). Add a new field so downstream WP2 can identify which entries came
from the artifact-tagged branch. This is the foundation defect (#3085a) — WP2 and WP3 both
depend on this WP's resolved-string shape.

## Context

`validate_mission_paths` already computes `full_path` (the real location tested via
`full_path.exists()`) for every declared path, in one of three mutually-exclusive branches:

1. `if candidate.is_absolute():` → `full_path = candidate` (unaffected by this mission).
2. `elif _normalize_path_token(declared[key]) in artifact_tokens:` → `full_path = feature_dir / candidate`
   (mission-artifact-tagged token, e.g. `contracts/`).
3. `else:` → `full_path = project_root / candidate` (build/repo-root token, e.g. `src/`).

Today, after the `full_path.exists()` check fails, the loop does:

```python
result.missing_paths.append(relative_path)
result.warnings.append(f"{mission.name} expects {key} path: {relative_path} (not found)")
```

Both lines use `relative_path` — the `_prefix_required_path`-adjusted but still-*declared*
token — and discard `full_path` entirely. `relative_path` is the bare token as declared in
`mission.yaml` (e.g. `"contracts/"`), which for an artifact-tagged path names a different,
untested location (repo root) than what was actually checked
(`kitty-specs/<slug>/contracts/`).

`format_errors()`/`format_warnings()` (same file, `PathValidationResult` methods) render
`self.warnings` and `self.suggestions` — **never** `self.missing_paths` directly.
`suggest_directory_creation` builds `self.suggestions` from `missing_paths`. So both the
`missing_paths.append` and the `warnings.append` sites must be fixed together: fixing only
`missing_paths` would leave the actual first-read operator sentence
(`"{mission.name} expects {key} path: {relative_path} (not found)"`) wrong forever.

**Fix direction** (plan.md, WP1): compute the resolved, reportable string **once**, before
either `append` call, and reuse that single local value (`resolved`) for both
`result.missing_paths.append(resolved)` and the `result.warnings.append(f"...{resolved}...")`
f-string. Preserve:

- **Trailing-slash convention**: `suggest_directory_creation` decides `mkdir -p` vs. `touch`
  based on `path_str.endswith("/")`. `full_path` as a bare `Path` loses a trailing slash the
  declared token had, so `resolved` must re-append it when the declared token had one.
- **Safe fallback**: prefer `full_path.relative_to(project_root)` when it succeeds; fall back
  to `str(full_path)` on `ValueError` (e.g. a cross-worktree topology where `full_path` is not
  under `project_root`) rather than raising. `format_errors()`/`format_warnings()` must never
  crash on a resolvable-but-reported path.
- The `candidate.is_absolute()` branch and the no-`paths:`-declared no-op case are **unaffected**
  (spec.md Edge Cases) — for an absolute path, `relative_to(project_root)` raises `ValueError`
  by construction (the path is outside `project_root`), so `resolved` falls back to
  `str(full_path)`, i.e. the absolute path string itself, unchanged from today's behavior.

**New field** (this WP's own addition, additive on top of spec.md's Key Entities contract —
does not forbid a further field): add
`missing_paths_feature_relative: list[str] = field(default_factory=list)` to
`PathValidationResult`, alongside its existing list fields (`existing_paths`,
`missing_paths`, `warnings`, `suggestions`). WP2's token-normalization step needs to know,
per `missing_paths` entry, whether it came from the artifact-tagged branch and, if so, its
real `feature_dir`-relative token — nothing available to `evaluate_path_conventions` today
can derive that from `missing_paths` alone once it's `project_root`-relative resolved text.
Populate this field in parallel with `result.missing_paths.append(resolved)`, in **every**
one of the three branches, but its *values are not uniformly `feature_dir`-relative*:

- **Artifact-tagged branch** (`elif ... in artifact_tokens:`): append
  `_normalize_path_token(relative_path)` — the pre-resolution declared token itself (e.g.
  `"contracts"`). This IS `feature_dir`-relative by construction, since `full_path = feature_dir / candidate`
  is built directly from it.
- **Build/repo-root branch** (`else:`): append `_normalize_path_token(resolved)` instead — a
  `project_root`-relative placeholder, **not** `feature_dir`-relative.
- **Absolute branch** (`if candidate.is_absolute():`): also append `_normalize_path_token(resolved)`
  — folded into the same placeholder bucket as the build/repo-root case (unaffected value,
  per the Edge Cases pin above).

Do **not** special-case the placeholder entries here beyond this population rule — WP2 is
responsible for structurally excluding them from its comparison set via an `artifact_tokens`
membership check (recomputing the identical recipe `validate_mission_paths` already computes
internally), not by relying on the placeholder values happening not to collide with a real
artifact token. `evaluate_path_conventions` already holds the full `path_result` object
returned by `validate_mission_paths`, so this new field costs no extra plumbing to consume.

## ⚡ Subtask T001: Compute and reuse the single resolved/reportable string

**Purpose**: Fix the root cause — `missing_paths.append` and the `warnings.append` f-string
both currently use the bare declared token (`relative_path`) instead of the resolved,
actually-tested location (`full_path`). This is FR-001's core fix.

**Steps**:
1. In `validate_mission_paths` (`src/specify_cli/validators/paths.py`), inside the `for key,
   relative_path in required_paths.items():` loop, after the `if full_path.exists(): ...
   continue` block and before the current `result.missing_paths.append(relative_path)` line,
   compute a local `resolved: str` once:
   - Try `full_path.relative_to(project_root)`. On success, use its `.as_posix()` (or
     `str(...)`, matching existing string conventions in this module) as the base string.
   - On `ValueError`, fall back to `str(full_path)`.
   - If `relative_path` (the original declared/prefixed token) ends with `"/"` and the base
     string does not already end with `"/"`, append `"/"` to preserve the trailing-slash
     convention `suggest_directory_creation` depends on.
2. Replace `result.missing_paths.append(relative_path)` with
   `result.missing_paths.append(resolved)`.
3. Replace the `warnings.append` f-string's `{relative_path}` interpolation with `{resolved}`,
   i.e. `result.warnings.append(f"{mission.name} expects {key} path: {resolved} (not found)")`.
4. Confirm `candidate.is_absolute()` entries are unaffected in value: for that branch,
   `full_path = candidate` (already absolute), so `full_path.relative_to(project_root)` raises
   `ValueError` (an absolute path is not "under" `project_root` unless it literally is a
   subpath) and `resolved` falls back to `str(full_path)` — the same absolute string
   `relative_path` already was in that branch today (since `candidate` there IS
   `relative_path` as a `Path`). Verify this by inspection; no special-casing needed in code.

**Files**: `src/specify_cli/validators/paths.py`.

**Validation**: `test_strict_metadata_true_blocks_with_violation` and
`test_strict_metadata_false_downgrades_to_warning` (SC-005 pinned tests) still pass
unmodified — they assert on `evaluate_path_conventions`'s rendered text for the `src/` build
path case, whose resolved value is unchanged by this fix (Case B below). Run
`pytest tests/specify_cli/acceptance/test_acceptance_cores.py::TestEvaluatePathConventions -q`.

---

## ⚡ Subtask T002: Add `missing_paths_feature_relative` and populate per-branch

**Purpose**: Give WP2 a channel to identify which `missing_paths` entries are artifact-tagged
(and recover their real `feature_dir`-relative token) without re-deriving that from the
now-resolved `missing_paths` strings, which lost that information.

**Steps**:
1. Add the field to the `PathValidationResult` dataclass, alongside `missing_paths`,
   `warnings`, `suggestions`:
   ```python
   missing_paths_feature_relative: list[str] = field(default_factory=list)
   ```
2. In the same loop iteration as T001's `resolved` computation, in the artifact-tagged branch
   (`elif _normalize_path_token(declared[key]) in artifact_tokens:`), append
   `_normalize_path_token(relative_path)` to `result.missing_paths_feature_relative` — the
   pre-resolution declared token (e.g. `"contracts"`, stripped of slashes).
3. In the build/repo-root branch (`else:`) and the absolute branch
   (`if candidate.is_absolute():`), append `_normalize_path_token(resolved)` (T001's computed
   value) to `result.missing_paths_feature_relative` instead — these are placeholder entries,
   not real `feature_dir`-relative tokens. Do not attempt to compute a genuine
   `feature_dir`-relative value for these two branches; that is out of scope for WP1 (WP2
   structurally excludes them via an `artifact_tokens` membership check).
4. Ensure every one of the three branches appends exactly one entry to
   `missing_paths_feature_relative` per missing path, in the same order as `missing_paths`
   (index-parallel is not required by WP2's design — WP2 will filter by content, not
   position — but keep the append inside the same loop body as `missing_paths.append` so the
   two lists stay in sync in practice).

**Files**: `src/specify_cli/validators/paths.py`.

**Validation**: New unit assertions (T003/T004) directly inspect
`PathValidationResult.missing_paths_feature_relative` for both branches. No existing test
inspects this field (it is new), so nothing else can regress from its addition alone —
confirm via `ruff check` / `mypy` that the new field's type annotation is consistent with the
dataclass's other list fields.

---

## ⚡ Subtask T003: Revert test Case A — artifact-tagged path resolution

**Purpose**: Red-first proof that FR-001's fix is real for the artifact-tagged branch
(User Story 1 / Acceptance Scenario 1) — must fail against pre-WP1 code and pass after.

**Steps**:
1. In `tests/specify_cli/acceptance/` (co-locate with existing `validate_mission_paths`
   coverage, or `tests/agent/test_validators_unit.py` if that's where `validate_mission_paths`
   is already unit-tested — check both locations first and match the existing convention),
   add a test building a real `Mission`/`MissionConfig` (or the minimal fixture the existing
   suite already uses) declaring a mission-artifact-tagged path convention (e.g.
   `contracts/`, present in `mission.config.artifacts.optional` or `.required`) whose
   resolved location is `feature_dir/contracts/`, under a `feature_dir` that is a real,
   distinct subdirectory from `project_root` (e.g. `tmp_path / "kitty-specs" / "some-slug"`
   vs. `tmp_path` itself), with the directory absent on disk.
2. Call `validate_mission_paths(mission, project_root, feature_dir=feature_dir)` directly.
3. Assert:
   - `result.missing_paths` and `result.suggestions` both contain a string equal to the
     resolved `feature_dir`-relative path (e.g. `"kitty-specs/<slug>/contracts/"` —
     concretely, whatever `full_path.relative_to(project_root)` produces for this fixture's
     paths), and do **not** contain the bare token `"contracts/"` alone.
   - `result.warnings` (or `result.format_errors()`/`.format_warnings()`) also contains the
     resolved string and does **not** contain the bare token — this is the assertion that
     actually falsifies FR-001's defect, since `warnings`/`suggestions` (not `missing_paths`)
     are what get rendered to the operator.
   - `result.missing_paths_feature_relative` contains `_normalize_path_token(relative_path)`
     (i.e. `"contracts"`, the pre-resolution declared token, stripped of slashes) for this
     entry — this is the direct assertion on T002's new field for the artifact-tagged branch,
     independent of however WP02 chooses to build its own dedup fixture (TASKS-VERIFY-002).
4. Run the test against the current (pre-T001/T002) code first to confirm it is genuinely
   red (fails because the reported string is still the bare token), then implement T001/T002
   and re-run to confirm green.

**>>> DEVIATION FROM plan.md (TASKS-FRESH-002) <<<**
plan.md's "Red-first / revert discipline — summary table" (plan.md line 752), WP1 row,
"Revert test" column, reads **verbatim**:

> Case A asserts `missing_paths`/`suggestions`/`warnings` contain the resolved
> `feature_dir`-relative path, not the bare token, for a real artifact-tagged mission
> fixture; Case B (build-path companion) asserts the build/repo-root branch's reported
> string stays `project_root`-relative and unchanged.

That text names only the **path-resolution/namespace-correctness** assertions (Case A's
`missing_paths`/`suggestions`/`warnings` checks; Case B's build-path check) — it never
mentions `missing_paths_feature_relative`. **This WP's step 3 above adds a fourth, direct
assertion on `result.missing_paths_feature_relative`** (that it contains
`_normalize_path_token(relative_path)`, i.e. `"contracts"`, for the artifact-tagged entry) —
a tasks-phase addition beyond plan.md's WP1 row as quoted above. Reason: WP02's dedup logic
(T006) consumes `missing_paths_feature_relative` directly, so its per-branch population needs
its own independently-verified assertion here rather than being merely assumed correct because
Case A's other assertions pass (TASKS-VERIFY-002). Per this mission's CRITICAL CONSTRAINT,
plan.md is not edited to add this line — this note is the flag so a reviewer diffing plan.md's
literal WP1-row text (quoted above) against this WP file's step 3 sees the addition and its
rationale without opening plan.md, and reads this as a deliberate, tracked addition rather than
silent drift from the settled plan.md contract.

**Files**: `tests/specify_cli/acceptance/` (new test file or addition to an existing one) or
`tests/agent/test_validators_unit.py`.

**Validation**: `pytest <chosen file>::<test name> -v` — red before T001/T002's code change,
green after.

---

## ⚡ Subtask T004: Revert test Case B — build/repo-root companion (unchanged-value assertion)

**Purpose**: Confirm WP1's fix to the artifact-tagged branch's namespace does NOT change the
build/repo-root branch's reporting (User Story 1 / Acceptance Scenario 2) — a genuine
"stays the same" regression guard, not merely "doesn't crash."

**Steps**:
1. In the same test file as T003, add a fixture for a missing, non-artifact-tagged,
   `src/`-style declared path (the `else:` branch) under the same `project_root` used above
   (or a fresh one — either is fine as long as it is not artifact-tagged: not a member of
   `mission.config.artifacts.required`/`.optional`).
2. Call `validate_mission_paths(mission, project_root, feature_dir=feature_dir)` (or without
   `feature_dir` if the fixture doesn't need it for this branch).
3. Assert `result.missing_paths` and `result.warnings` contain a `project_root`-relative
   resolved string — the same namespace this branch already reported in before WP1 (pre-WP1,
   the bare declared token for a build path is itself already `project_root`-relative-shaped
   text, since build paths are declared relative to the repo root).
4. Assert the reported string's **value** is unchanged from what pre-WP1 code would produce
   for this exact fixture (e.g. compute the expected string directly as
   `str(project_root / "src") + "/"` or equivalent, matching this WP's trailing-slash rule,
   and assert equality) — this directly catches a regression where T001's refactor
   accidentally re-namespaces the build/repo-root branch too.
4a. Assert `result.missing_paths_feature_relative` contains
   `_normalize_path_token(resolved)` — the same placeholder value appended to `missing_paths`
   for this branch (per T002's population rule) — confirming the build/repo-root branch's
   placeholder entry is genuinely populated, not merely assumed (TASKS-VERIFY-002).
5. This test can be written green from the start relative to *this* WP's Case A change (it
   asserts "unchanged"), but per NFR-001/plan.md, it belongs in the same file as Case A and
   should be run alongside it as part of this WP's red-first discipline package — confirm it
   passes both before and after T001/T002 (a companion/regression guard, not itself required
   to flip red→green).

**Files**: same test file as T003.

**Validation**: `pytest <chosen file>::<Case B test name> -v` — passes both before and after
T001/T002 (regression guard, not a flip test).

---

## ⚡ Subtask T016: Extract `artifact_tokens` into an exported, pure helper

**Purpose**: `validate_mission_paths` computes its `artifact_tokens` set inline
(`paths.py:182-192` on this checkout: `if feature_dir is not None and not path_prefix:` ...
`artifact_tokens = {_normalize_path_token(name) for name in (*required, *optional)}`). WP02's
T006 needs the identical "what counts as a mission artifact token" recipe to build its dedup
comparison set — leaving it inline here forces WP02 to hand-duplicate the same
`getattr`/default chain in `summary_core.py`, a second independently-maintained copy of one
business rule. Extract it once, here, since this WP already owns and edits this exact code
block, so WP02 can import and call it instead of reimplementing it.

**Steps**:
1. In `src/specify_cli/validators/paths.py`, add a new top-level function, placed near
   `_normalize_path_token` (which it depends on):
   ```python
   def artifact_tokens_for_mission(mission: Mission) -> set[str]:
       """Return the normalized set of a mission's declared artifact tokens.

       Defensive: a real ``MissionConfig`` always carries ``artifacts``, but a
       partial mock/config may not — treat its absence as "no artifact paths"
       (the same fallback ``validate_mission_paths`` already applies).
       """
       artifacts = getattr(mission.config, "artifacts", None)
       required = getattr(artifacts, "required", ()) or ()
       optional = getattr(artifacts, "optional", ()) or ()
       return {_normalize_path_token(name) for name in (*required, *optional)}
   ```
2. Add `"artifact_tokens_for_mission"` to this module's `__all__` list — it must be
   importable from `specify_cli.validators.paths`, since WP02's `summary_core.py` (a
   different module) is the intended second caller.
3. In `validate_mission_paths`, replace the inline block:
   ```python
   artifact_tokens: set[str] = set()
   if feature_dir is not None and not path_prefix:
       artifacts = getattr(mission.config, "artifacts", None)
       required = getattr(artifacts, "required", ()) or ()
       optional = getattr(artifacts, "optional", ()) or ()
       artifact_tokens = {
           _normalize_path_token(name) for name in (*required, *optional)
       }
   ```
   with:
   ```python
   artifact_tokens: set[str] = set()
   if feature_dir is not None and not path_prefix:
       artifact_tokens = artifact_tokens_for_mission(mission)
   ```
   Do not change the `feature_dir is not None and not path_prefix` guard — the helper
   computes the token set unconditionally; `validate_mission_paths` still decides *whether*
   to compute it at all.
4. This subtask does not change `validate_mission_paths`'s external behavior for any existing
   caller — it is a pure extraction. No existing test should need to change because of this
   subtask alone.

**Files**: `src/specify_cli/validators/paths.py`.

**Validation**: `pytest tests/specify_cli/acceptance/test_acceptance_cores.py::TestEvaluatePathConventions -q`
and the three SC-005 pinned tests still pass unmodified — the extraction changes no observable
behavior. `ruff check` / `mypy` clean on the new function's signature and `__all__` entry.

## Definition of Done

- T001-T004 and T016 all recorded via `spec-kitty agent tasks mark-status <Txxx> --status done`
  (event-sourced status, not a ticked checkbox).
- Case A (T003) is red against pre-T001/T002 code and green after — genuinely red-first
  per NFR-001, not written green from the start.
- Case B (T004) passes both before and after T001/T002, confirming no namespace regression
  in the build/repo-root branch.
- `artifact_tokens_for_mission` (T016) is exported from `validators/paths.py` and
  `validate_mission_paths` calls it instead of inlining the recipe — confirmed by reading the
  diff, not just that tests still pass.
- The three SC-005 pinned tests
  (`test_strict_metadata_true_blocks_with_violation`,
  `test_strict_metadata_false_downgrades_to_warning`,
  `test_lenient_path_convention_warning_is_rendered_in_console`) remain green, **unmodified**
  (NFR-002) — run them explicitly as part of this WP's own validation, not just at mission end.
- Full baseline re-run: `pytest tests/specify_cli/acceptance/ tests/specify_cli/cli/commands/test_accept_warnings_render.py tests/agent/test_validators_unit.py tests/characterization/test_trio_json_envelope.py -q`
  completes with 0 failed (per plan.md's "Baseline honesty" section — this is the full
  committed accountability surface, not just the 3 named pinned tests above).
- `ruff check src/specify_cli/validators/paths.py tests/...` and `mypy` on touched files are
  clean.
- No change to the `candidate.is_absolute()` branch's behavior or the no-`paths:`-declared
  no-op case (spec.md Edge Cases) — confirmed by Case B-style inspection, not asserted away.

## Risks

- **Trailing-slash loss**: `Path`/`PurePosixPath` normalization can silently drop a trailing
  slash if the resolved-string computation is done carelessly (e.g. via `Path(...).as_posix()`
  on a path object that never had the slash in the first place). Mitigation: T001 explicitly
  re-appends `"/"` when the original declared token had one — do not rely on `Path` round-
  tripping to preserve it.
- **`ValueError` fallback path untested**: the cross-worktree case where `full_path` is not
  under `project_root` is a defensive fallback the spec calls out explicitly but for which no
  fixture may exist in today's test suite. Consider whether T003/T004's fixtures should add a
  minimal case, or note it as a residual gap for WP4's fixture design to consider (not
  required, but flag if skipped).
- **owned_files overlaps (full accounting, re-derived from `wps.yaml` live)**: this WP's
  `owned_files` overlap with three other WPs. All are deliberate — WP01, WP02, WP03, and WP04
  form a strict linear dependency chain (WP01→WP02→WP03→WP04) and are never worked
  concurrently, so the no-overlap convention (which exists to prevent parallel write
  collisions) does not apply to any of them:
  - **WP03** on `src/specify_cli/validators/paths.py` (both WPs edit this file) and on
    `tests/agent/test_validators_unit.py` (both WPs' test coverage lives here — WP01's T003/T004
    and WP03's T012).
  - **WP02** on the `tests/specify_cli/acceptance/**` glob (WP01's T003/T004 and WP02's T009
    revert tests may land in the same directory).
  - **WP04** on the same `tests/specify_cli/acceptance/**` glob — WP04's single owned file
    (`tests/specify_cli/acceptance/test_accept_contracts_path_repro.py`) falls inside it.

## Reviewer Guidance

- Confirm both `missing_paths.append` and the `warnings.append` f-string were changed
  together — a fix to only one leaves the primary operator-visible sentence wrong (plan.md
  WP1's explicit warning against this partial fix).
- Confirm the trailing-slash convention is preserved for artifact-tagged paths (check
  `suggest_directory_creation`'s `mkdir -p` vs. `touch` decision still fires correctly for a
  directory-shaped token).
- Confirm the `candidate.is_absolute()` branch and the no-`paths:` no-op case are untouched in
  behavior (spec.md Edge Cases) — this is C-002's "no change to what's enforced" applied to
  reporting only, not enforcement.
- Confirm `missing_paths_feature_relative` is populated in all three branches, with the
  correct per-branch semantics (real `feature_dir`-relative for artifact-tagged; placeholder
  for the other two) — WP2's dedup correctness depends entirely on this being right.
- Confirm the SC-005 pinned tests were run and are genuinely unmodified (diff the test file,
  not just "still pass").

---

Run `spec-kitty agent action implement WP01 --agent claude` to begin implementation.
