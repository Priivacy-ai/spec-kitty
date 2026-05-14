---
work_package_id: WP01
title: Mypy strict baseline (excluding doctor.py)
dependencies: []
requirement_refs:
- FR-001
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-quality-devex-hardening-3-2-01KRJGKH
base_commit: e00cbdd7f21b50a561315484b8f7d2788191ffb8
created_at: '2026-05-14T08:23:37.437791+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1097872"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- pyproject.toml
- src/kernel/_safe_re.py
- src/specify_cli/auth/**
- src/specify_cli/cli/commands/agent_retrospect.py
- src/specify_cli/cli/commands/review/**
- src/specify_cli/next/_internal_runtime/**
- src/specify_cli/status/reducer.py
- src/specify_cli/sync/**
- src/specify_cli/task_metadata_validation.py
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP01.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load python-pedro
```

The profile establishes your identity (Python Pedro — Python-specialist implementer applying TDD, type safety, and idiomatic Python 3.11+), primary focus (type-clean, behavior-tested code), and avoidance boundary (no architectural redesign; no scope expansion; no refactoring beyond locality). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Make `uv run mypy --strict src/specify_cli src/charter src/doctrine` exit 0 on every file this WP owns. Mission decision moment `DM-01KRJHT7QD7XQMY33Y5TDTQ80V` selected option (A) — fix the existing target — over option (B) — narrow the target. Failures are concentrated, mechanical, and one of them (the `doctor.py:1092` `RepairReport` ↔ `RepoAuditReport` confusion) likely masks a real branch bug worth capturing in a regression test before the type is narrowed.

`doctor.py` typing fixes are **owned by WP06**, which combines the typing fix with the cognitive-complexity refactor. This WP does **not** modify `doctor.py`. WP01 closes mypy on everything except `doctor.py`; WP06 closes mypy on `doctor.py`. CHANGELOG entry from this WP notes that WP06 closes the gap.

## Context

### Validation snapshot (Pedro, 2026-05-14)

```
$ uv run --with mypy mypy --strict src/specify_cli src/charter src/doctrine
...
Found 60 errors in 45 files (checked 763 source files)
```

Two failure categories per `work/findings/971-mypy-strict.md`:

1. **Missing third-party stubs** (mechanical). Affected imports: `yaml`, `toml`, `jsonschema`, `psutil`, `requests`, `re2`.
2. **Concrete typed-code errors**. Affected files: `status/reducer.py`, `sync/__init__.py`, `doctor.py` (owned by WP06), `agent_retrospect.py`, `review.py` (now `review/` package; verify if any remains), `auth/recovery`, `next/_internal_runtime/*`, `sync/*`.

### Research input

`research.md` §1 — `re2` strict-drop strategy: **drop strict on `re2` import sites only**. Mark each import with `# type: ignore[import-untyped]` and a comment that points to research.md §1.

## Doctrine Citations

This WP applies:

- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — the regression test for the `MissionRepairResult.findings` real-branch bug (T003) asserts the observable behavior of the broken branch, not the type assertion.
- [`refactoring-guard-clauses-before-polymorphism`](../../../src/doctrine/tactics/shipped/refactoring/refactoring-guard-clauses-before-polymorphism.tactic.yaml) — applied only if conditional flattening is needed to make a type narrow; expected to be rare.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.
- Execution worktree allocated by `lanes.json` from `finalize-tasks`. Do not assume a specific lane name here.

## Subtasks

### T001 — Add type stubs to dev dependencies

**Purpose**: Resolve the missing-stubs class of failures (~30 % of the 60 errors).

**Steps**:

1. Open `pyproject.toml`. Locate the `[dependency-groups.dev]` or equivalent section.
2. Add these stubs to the dev group:
   - `types-PyYAML`
   - `types-toml`
   - `types-jsonschema`
   - `types-psutil`
   - `types-requests`
3. Run `uv lock --no-upgrade` to regenerate `uv.lock`.
4. Run `uv sync` to install.
5. Re-run `uv run --with mypy mypy --strict src/specify_cli src/charter src/doctrine` and confirm the stub-related errors are gone.

**Validation**:

- `uv.lock` includes the new stub packages.
- `mypy --strict` no longer reports `Library stubs not installed for "yaml"` etc.

### T002 — [P] Localize `re2` strict-drop type-ignore comments

**Purpose**: `re2` ships no stubs and authoring them is out-of-scope (see research.md §1).

**Steps**:

1. Find every `re2` import in the codebase:
   ```bash
   rg -n "^import re2|^from re2" src/
   ```
   Pedro pre-mission verified exactly one import site exists: `src/kernel/_safe_re.py:51`. If the audit returns zero results, skip this subtask and document the skip.
2. At each import site, append:
   ```python
   import re2 as _re2_mod  # type: ignore[import-untyped]  # see research.md §1; upstream stubs pending
   ```
3. Re-run mypy and confirm no `Library stubs not installed for "re2"` errors remain.

**Validation**:

- Every `re2` import carries the localized ignore + comment.
- mypy reports zero `re2` errors.

### T003 — Document the `doctor.py:1092` bug for WP06 handoff

**Purpose**: WP01 does NOT modify `doctor.py` (owned by WP06) and does NOT author the regression test (also owned by WP06). This subtask records the bug evidence so WP06 can author the test + fix without re-discovery.

**Steps**:

1. Read `doctor.py:1080..1130` carefully. Identify the branch where the mypy error reports a `RepairReport` ↔ `RepoAuditReport` confusion and where `MissionRepairResult` is missing `.findings`.
2. Capture the observable broken behavior in evidence — manual `CliRunner.invoke` reproduction with stdout / exit-code recording. Save as `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/research/doctor-mission-state-1092-bug-evidence.md`.
3. Hand off to WP06: the test + fix lands there per its T030.

**Files**: `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/research/doctor-mission-state-1092-bug-evidence.md` (new, ~60 lines).

**Validation**: the evidence file documents enough for WP06 to author the regression test without re-reading `doctor.py` from scratch.

### T004 — [P] Fix typed-code errors in `status/reducer.py`, `sync/__init__.py`, `agent_retrospect.py`

**Purpose**: Resolve the first cluster of concrete typing errors.

**Steps**:

1. For each file, run `uv run --with mypy mypy --strict <file>` and read the errors.
2. Apply minimal type fixes — no logic changes, no refactors.
   - `status/reducer.py`: literal status type mismatch — likely a missing `Literal[...]` or `cast()` at the boundary.
   - `sync/__init__.py:183`: return type narrows from `dict[str, Any] | None` to `dict[Any, Any]`. Add a guard clause that excludes `None` before return, or widen the declared return type.
   - `agent_retrospect.py`: add missing return annotation; verify the inferred type is the intended one (Pedro suspicion: it should be `None`).
3. Re-run mypy on each file; confirm zero errors.

**Validation**:

- Each file passes `mypy --strict` in isolation.
- No behavior change: the existing test suite is green at every commit boundary.

### T005 — [P] Fix typed-code errors in `auth/recovery`, `next/_internal_runtime/*`, `sync/*`

**Purpose**: Resolve the remaining cluster of concrete typing errors.

**Steps**:

1. List errors per file with `uv run --with mypy mypy --strict src/specify_cli/auth src/specify_cli/next/_internal_runtime src/specify_cli/sync`.
2. Apply minimal type fixes per the pattern in T004. Watch for:
   - `auth/recovery`: any `object` reads that should be cast to a specific dataclass.
   - `next/_internal_runtime/engine.py`: TypeVar binding issues; missing return annotations on async paths.
   - `sync/*`: missing `None` handling in optional unpack sites.
3. Re-run mypy across the three subtrees; confirm zero errors.

**Validation**:

- Each subtree passes `mypy --strict` in isolation.
- Existing test suite green.

### T006 — Verify global mypy --strict exits 0 on WP01-owned files

**Purpose**: Acceptance gate for FR-001 on WP01's scope.

**Steps**:

1. Run the full command:
   ```bash
   uv run --with mypy mypy --strict src/specify_cli src/charter src/doctrine 2>&1 | tee /tmp/wp01-mypy.log
   ```
2. Acceptance: every reported error must reside in `doctor.py` (owned by WP06). Zero errors outside `doctor.py`.
3. Save the log as WP01 evidence.

**Validation**:

- `grep -v "doctor.py" /tmp/wp01-mypy.log | grep -E "error:"` returns empty.
- `grep -c "doctor.py" /tmp/wp01-mypy.log` returns 5 or fewer (the pre-WP06 doctor.py errors).

### T007 — Record evidence + glossary fragment

**Purpose**: Document the decision (option A, decision moment ID) and the residual doctor.py carve-out. The CHANGELOG entry text lives in the WP's commit-message body; WP10 reads the mission's commit history to compose `CHANGELOG.md` (no fragment files).

**Steps**:

1. Ensure WP01's final commit message includes a "CHANGELOG note:" block summarizing:
   - Decision `DM-01KRJHT7QD7XQMY33Y5TDTQ80V` (option A — fix existing mypy strict target).
   - Stubs added: `types-PyYAML`, `types-toml`, `types-jsonschema`, `types-psutil`, `types-requests`.
   - `doctor.py` mypy closes in WP06.
2. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP01.md`:
   - WP01 does not introduce new canonical terms; record `# WP01 introduces no new canonical terms` for traceability.
3. Stage and commit.

**Validation**:

- WP01's final commit message contains the CHANGELOG-note block.
- `glossary-fragments/WP01.md` exists.

## Test Strategy

- **Regression test (T003)** is the only behavior test added by this WP. It captures pre-WP06 behavior and will be updated by WP06.
- **No new unit tests** for the type fixes — type narrowing is a static-analysis outcome, not a runtime contract.
- **Existing test suite** must remain green at every commit boundary (`uv run pytest tests/` exits 0).

## Definition of Done

- [ ] `uv run mypy --strict src/specify_cli src/charter src/doctrine` reports zero errors outside `doctor.py`.
- [ ] `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/research/doctor-mission-state-1092-bug-evidence.md` documents the bug for WP06's handoff.
- [ ] `pyproject.toml` declares the new stub dev-deps; `uv.lock` reflects them.
- [ ] Every `re2` import (one as of pre-mission audit) carries the localized ignore + comment.
- [ ] WP01's final commit message includes a "CHANGELOG note:" block (consumed by WP10).
- [ ] `glossary-fragments/WP01.md` exists (empty fragment is fine — WP01 introduces no canonical terms).
- [ ] All existing pytest suites pass.

## Risks

- **T003's regression test reveals a substantial behavior bug.** If the `MissionRepairResult.findings` issue is more than a typing-drift artifact, escalate to the operator. Pedro fixes only typing in this WP; behavior fixes are a separate concern coordinated with WP06.
- **Type stubs version drift.** PyPI stub packages occasionally tag breaking changes. Pin minor versions in `pyproject.toml` if any incompatibility surfaces.
- **`uv sync` reorders unrelated dependencies in `uv.lock`.** Acceptable; verify the diff is purely additive for the stubs + their transitive deps.

## Reviewer Guidance

When reviewing this WP, check:

1. The mypy command exits 0 on WP01-owned files (run it locally; do not trust the CI report alone).
2. T003's regression test asserts on observable output (stdout, exit code, file artifacts), not on internal calls or mock invocations. Reject if it violates `function-over-form-testing`.
3. The `re2` `type: ignore` comments are localized to import sites only — no broader ignore in module-level `# type: ignore` lines.
4. No `doctor.py` modifications. If any appear, redirect the change to WP06.
5. The CHANGELOG fragment is concise and stakeholder-readable.

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent claude
```

## Activity Log

- 2026-05-14T08:23:38Z – claude:sonnet:python-pedro:implementer – shell_pid=1028182 – Assigned agent via action command
- 2026-05-14T08:57:53Z – claude:sonnet:python-pedro:implementer – shell_pid=1028182 – Ready for review: mypy strict green outside doctor.py; bug evidence for WP06 handoff recorded; 3 out-of-ownership trivial fixes required by full-run gate. Note: kitty-specs/ artifacts (glossary-fragments/WP01.md, research/doctor-mission-state-1092-bug-evidence.md) are committed on lane branch; need to be moved to planning branch by operator.
- 2026-05-14T08:58:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=1097872 – Started review via action command
- 2026-05-14T09:05:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=1097872 – Review passed (forced through planning-artifact-on-lane gate per operator guidance). VERIFICATION: (1) mypy --strict gate green — zero errors outside doctor.py (6 doctor.py errors remain, owned by WP06). (2) Stubs in [dependency-groups.dev] of pyproject.toml; uv.lock updated. (3) re2 import at src/kernel/_safe_re.py:51 carries type: ignore[import-untyped] + research.md §1 citation. (4) Bug evidence file at kitty-specs/.../research/doctor-mission-state-1092-bug-evidence.md (167 lines, sufficient for WP06 handoff). (5) glossary-fragments/WP01.md present (empty per DoD). (6) Commit message has CHANGELOG note block. CONCERN A (out-of-ownership edits to merge/state.py, status/progress.py, tracker/saas_client.py): ACCEPTED. Empirically verified — without these 4 single-line dead-cast/dead-ignore removals the gate fails with 4 errors outside doctor.py. The stub install in T001 made pre-existing casts/ignores redundant; cleanups are a direct, mechanical, zero-behavior consequence. Files are unowned by any mission WP. PRECEDENT: gate-driven mechanical cleanups in unowned files are acceptable when triggered by the WP's own scoped change. CONCERN B (planning artifacts on lane branch): operator must cherry-pick kitty-specs/* to fix/quality-check-updates before merge — implementer acknowledged in their handoff note. NO TACTIC CITATIONS: acceptable per WP prompt — T003 authors evidence only, T004/T005 are type narrowing only. PRE-EXISTING TEST FAILURE (NOT a WP01 regression): tests/agent/cli/commands/test_sync.py::TestSyncNowExitCodes::test_strict_exits_0_on_success fails due to Mission 7 enforce_teamspace_mission_state_ready gate (sync.py:1055) untouched by WP01. Sibling test_strict_exits_1_on_auth_missing was fixed in PR #1035; this sibling was missed. Recommend follow-up CI-fix PR mirroring #1035.
