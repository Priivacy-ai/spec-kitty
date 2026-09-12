---
work_package_id: WP01
title: Snapshot field + evaluate_guards_strict dispatch branch
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-006
planning_base_branch: fix/custom-mission-guard-3704
merge_target_branch: fix/custom-mission-guard-3704
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-guard-3704. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/custom-mission-guard-3704 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-custom-mission-guard-failure-blocking-inert-01M0STY0
base_commit: 8685dec23a28ee51026cfcebbf2ecea17ad619ed
created_at: '2026-08-24T15:48:50.856229+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Dispatch branch (FR-001/FR-002/FR-006 core)
history:
- timestamp: '2026-08-24T15:45:00Z'
  agent: tasks-author
  action: Prompt authored directly during tasks-phase authoring (spec-kitty agent tasks tasks-outline/tasks-packages do not exist as CLI subcommands in this checkout's v3.2.6rc3 build; authored per tasks.md decomposition of plan.md's WP01).
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_cores.py
- src/runtime/next/runtime_bridge_io.py
- tests/runtime/test_bridge_cores.py
- tests/runtime/next/test_pertype_presence_gate.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Snapshot field + `evaluate_guards_strict` dispatch branch

## Mission context

Issue #3704 ("A custom mission family can never report a guard failure, and its `blocking:`
manifest is never read"), Part 1 (dispatch). This mission is STACKED on
`fix/org-tier-expected-artifacts-3703` (PR #3708 — merged into `origin/main` on 2026-08-24, after
this WP file was first authored; see `../tasks.md`'s Baseline section for the live
merge-state/rebase-need correction) — do not diff, rebase, or red-verify against `main`;
`planning_base_branch` stays `fix/org-tier-expected-artifacts-3703` regardless of PR #3708's
GitHub state. Full spec: `../spec.md`. Full plan: `../plan.md`. This WP implements plan.md's WP01
exactly as scoped there — do not re-litigate the design, only implement it.

## Goal

`evaluate_guards_strict` (`src/runtime/next/runtime_bridge_cores.py:684`) currently only
dispatches through the 4-key `_GUARD_TABLES` (lines 676-681); any family outside it raises
`UnregisteredMissionFamilyError` at line 693-695 with no other branch. This WP adds the second
branch: once the table lookup misses, check `snapshot.blocking_artifact_names is None`. If `True`
(no manifest reachable at any tier), the existing raise stays exactly as-is (FR-002 outcome 1 /
AC-3 / C-001 — unchanged). If `False` (a real, possibly-empty `frozenset`), evaluate genuinely by
comparing `snapshot.present_artifacts` against `snapshot.blocking_artifact_names`, returning `[]`
when the blocking set is a subset of what's present (FR-002 outcomes 2/3).

**This WP does NOT implement org-tier manifest resolution.** The field is populated by a
**minimal test-only stub** inside `gather_artifact_presence` — just enough to drive the two states
(`None` / real frozenset) for WP01's own ATDD tests. WP02 replaces this stub with the real
org-tier-aware resolution. This staging keeps the import-boundary-sensitive change (this WP) as
its own small, easily-reviewed diff, separate from WP02's larger org-tier plumbing (plan.md
"Design decisions left to this plan" #2).

## Independent Test

Construct (or reuse an existing test-double factory for) an `ArtifactPresenceSnapshot`-shaped
object with `blocking_artifact_names` set to:
1. `None` → `evaluate_guards_strict` raises `UnregisteredMissionFamilyError` (unchanged from
   today).
2. `frozenset()` (manifest resolved, nothing blocking at this step) → returns `[]`, and this
   emptiness must be provably reached via genuine evaluation, not a swallowed exception.
3. A non-empty `frozenset` whose members are NOT a subset of `present_artifacts` → returns a
   non-empty failure list naming the missing artifact(s).

All three are reachable without any org-tier manifest resolution existing yet — WP01's stub only
needs to let a test construct/monkeypatch the field into these three states.

## Requirement Refs

FR-001, FR-002, FR-006 (Protocol property + dataclass field + cores.py branch — real population
is WP02's job, not this WP's), AC-3, AC-9

## The hard constraint this WP protects (SPEC-ARCH-002 / import-boundary gate)

`src/runtime/next/runtime_bridge_cores.py` is bound by
`tests/architectural/test_bridge_cores_import_boundary.py` — a live, GREEN, AST-walk gate
(catches in-function and in-`try` imports, not just module-level ones) asserting this file
imports nothing but stdlib (`sys.stdlib_module_names`) and `runtime.next.decision`.
`evaluate_guards_strict` MUST ONLY EVER read `snapshot.blocking_artifact_names` — already-computed
data handed to it. It must NEVER call `required_artifacts_for` or any manifest-loading,
non-stdlib-importing function directly. This WP's new branch is a pure comparison over data the
snapshot already carries; if your implementation imports anything beyond stdlib/`runtime.next.decision`
into `runtime_bridge_cores.py`, it is wrong regardless of whether the tests pass.

Re-run this gate as part of your own green verification, every time you touch this file:

```bash
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v
```

## Subtasks

**T001 [ATDD-RED — separate commit BEFORE any implementation commit]** Extend
`tests/runtime/test_bridge_cores.py` with failing test case(s) exercising
`evaluate_guards_strict`'s new `snapshot.blocking_artifact_names is None` branch: (a) `None` →
raise `UnregisteredMissionFamilyError`; (b) `frozenset()` → return `[]` via genuine evaluation;
(c) non-empty `frozenset` not a subset of `present_artifacts` → non-empty failure list. Verify RED
against `fix/org-tier-expected-artifacts-3703` (git fetch it first if not present locally,
`git merge-base` confirms this branch's current HEAD equals that parent's HEAD — no functional
commits sit between them yet) BEFORE writing any implementation code:

```bash
git fetch origin fix/org-tier-expected-artifacts-3703
uv run pytest tests/runtime/test_bridge_cores.py -v   # confirm baseline first (accepted #3284 red only)
# then add the new failing test case(s), re-run, confirm the NEW case(s) fail for the right reason
```

**T002 [ATDD-RED — same commit family as T001, before implementation]** Extend
`TestCustomFamilyPresenceGateFailsClosedBothDirections` in
`tests/runtime/next/test_pertype_presence_gate.py` with AC-9's two-family distinguishability case:
(a) a family `qa` with a manifest present (built-in or org tier — built-in is sufficient to test
this story alone per spec.md's own Independent Test framing) whose `required_artifacts_for`
returns `[]` for the step (so `blocking_artifact_names == frozenset()`); (b) a genuinely typeless
family with no manifest at any tier (`blocking_artifact_names is None`). Assert (a) does NOT raise
and returns `guard_failures == []`; assert (b) still raises `UnregisteredMissionFamilyError`. Both
have an empty `required_artifacts_for` result, but must NOT be treated identically — this is the
whole point of AC-9 / the `None`-vs-`frozenset()` distinction.

**T003** Add `blocking_artifact_names -> frozenset[str] | None` as a read-only `@property` to the
`_ArtifactPresenceSnapshotLike` Protocol in `src/runtime/next/runtime_bridge_cores.py:354`,
alongside the existing `legacy_step_id` and `wp_advance_ready` properties (follow the exact same
declaration idiom already used for those two — read-only `@property`, not a plain attribute
annotation, because `ArtifactPresenceSnapshot` is a frozen dataclass).

**T004** In `evaluate_guards_strict` (`src/runtime/next/runtime_bridge_cores.py:684`), immediately
after the existing dispatch-miss check (`guard_table_entry = _GUARD_TABLES.get(snapshot.mission_family)`
at line 693, `if guard_table_entry is None: raise ...` at 694-695), add the new branch: check
`snapshot.blocking_artifact_names is None` — if `True`, the existing raise is unchanged
(do not add a second raise path, the existing one already covers this); if `False`, evaluate by
comparing `snapshot.present_artifacts` (a `frozenset[str]`) against
`snapshot.blocking_artifact_names` (also a `frozenset[str]`), returning a list of the artifacts
in `blocking_artifact_names` that are NOT in `present_artifacts` (empty list when
`blocking_artifact_names` is a subset of `present_artifacts`). **Use `is None` explicitly — never
bare falsiness** (`frozenset()` is falsy in Python; `if not snapshot.blocking_artifact_names:`
would silently collapse the `None`-vs-`frozenset()` distinction this whole mission exists to
restore — see spec.md's SPEC-FRESH-001 note and plan.md's "SPEC-FRESH-001 preservation" section).

**T005** Add `blocking_artifact_names: frozenset[str] | None = None` as a new field to the
`ArtifactPresenceSnapshot` dataclass in `src/runtime/next/runtime_bridge_io.py:900`, following the
same `X | None = None` optional-field idiom the dataclass already uses for `legacy_step_id` and
`wp_advance_ready`. The default of `None` means every existing construction call site (including
test fixtures) keeps compiling unchanged (additive, per plan.md's Contract-moves check).

**T006** Inside `gather_artifact_presence` (`src/runtime/next/runtime_bridge_io.py:931`), populate
`blocking_artifact_names` with a **minimal test-only stub** — just enough logic to produce `None`
in the "no manifest" case and a real (possibly empty) `frozenset` in the "manifest present" case,
sufficient for T001/T002's tests to drive both branches. Do NOT implement org-tier lookup here —
that is WP02's T013, which replaces this stub entirely. Label this stub clearly in its own commit
message (e.g. "test-only stub, replaced by WP02") so a reviewer does not mistake it for the final
implementation.

**T007** Run this WP's full regression scope; confirm T001/T002 go GREEN; confirm the
import-boundary gate stays GREEN; budget test coverage for T003-T006's new/changed lines in
`src/runtime/next/runtime_bridge_cores.py` and `runtime_bridge_io.py` toward the enforced 90%
diff-coverage floor (`ci-quality.yml:3333`, `critical_paths` includes `'src/runtime/next/*'`,
`ci-quality.yml:3366`):

```bash
uv run pytest tests/runtime/test_bridge_cores.py tests/runtime/next/test_pertype_presence_gate.py -v
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v
uv run pytest tests/runtime/test_bridge_parity.py -v
uv run pytest tests/runtime/next/test_cli_guard_family.py -v
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v
uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v
```

## Gates that apply to this WP's files

**ENFORCED**: commitlint; markdown lint (N/A here, no markdown authored by this WP); doctrine
schema freshness (always-on, trivial pass); Contextive glossary (always-on, trivial pass); TID251
banned-API lint; Typer JSON error surface (N/A, no CLI surface touched); `patch()` target
validation (applies to T001/T002's new test code if it patches anything); Bandit; pip-audit;
`uv.lock` freshness (no dependency change); **`diff-coverage` job's 90% DIFF-coverage floor on
`critical_paths`, which includes `src/runtime/next/*`** — both files this WP touches
(`runtime_bridge_cores.py`, `runtime_bridge_io.py`) are covered by this enforced gate. This WP
must budget test coverage for its own new/changed lines accordingly (T007).

**ADVISORY-ONLY**: `ruff`, `mypy` (run `make lint` locally regardless — this WP adds a
`frozenset[str] | None` Protocol property and dataclass field, worth type-checking for
correctness even though CI does not gate on it).

## Dependencies

- None (first work package in this mission's implementation chain).

## Risks

- Conflating the T006 stub with WP02's real implementation. Mitigated by an explicit "test-only
  stub, replaced by WP02" note in T006's commit message and in this file.
- Reintroducing SPEC-FRESH-001's collapse via bare falsiness instead of `is None`. Mitigated by
  T001's explicit `frozenset()` test case (must pass, not raise) and this file's explicit warning
  in T004.
