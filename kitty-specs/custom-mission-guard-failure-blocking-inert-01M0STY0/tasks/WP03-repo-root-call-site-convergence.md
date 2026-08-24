---
work_package_id: WP03
title: repo_root call-site convergence (FR-003)
dependencies:
- WP02
requirement_refs:
- FR-003
- NFR-004
planning_base_branch: fix/custom-mission-guard-3704
merge_target_branch: fix/custom-mission-guard-3704
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-guard-3704. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/custom-mission-guard-3704 unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 3 - Call-site convergence (FR-003), making WP02's org-tier reach genuinely live end-to-end
history:
- timestamp: '2026-08-24T15:45:00Z'
  agent: tasks-author
  action: Prompt authored directly during tasks-phase authoring (spec-kitty agent tasks tasks-outline/tasks-packages do not exist as CLI subcommands in this checkout's v3.2.6rc3 build; authored per tasks.md decomposition of plan.md's WP03).
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge.py
- src/runtime/next/runtime_bridge_composition.py
- tests/runtime/next/test_cli_guard_family.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – `repo_root` call-site convergence (FR-003)

## Mission context

Issue #3704, the wiring that makes Part 1 (WP01) + Part 2 (WP02) genuinely reachable from the
real CLI/WP-iteration/composition entry points, not just from a unit test that calls
`gather_artifact_presence` directly. STACKED on `fix/org-tier-expected-artifacts-3703` (PR
#3708) — red-verify against that branch, never `main`. Full spec: `../spec.md`. Full plan:
`../plan.md`. This WP implements plan.md's WP03 exactly as scoped there.

## Goal

Three real call sites currently drop `repo_root` on the floor even though the enclosing function
already holds it as a local:

1. `_check_cli_guards` (`src/runtime/next/runtime_bridge.py:751`) — gains
   `repo_root: Path | None = None`, forwards to `gather_artifact_presence`.
2. `_dn_dependency_gate` (`src/runtime/next/runtime_bridge.py:1538`; `repo_root = ctx.repo_root`
   local already set at line 1549) — its two `_check_cli_guards` call sites (WP-iteration
   pre-check ~line 1607-1610, CLI pre-check ~line 1631-1643) currently call
   `_check_cli_guards(current_step_id, feature_dir)` with no `repo_root` argument at all. Both
   MUST forward the already-live `repo_root` local.
3. `_check_composed_action_guard` (`src/runtime/next/runtime_bridge_composition.py:429`) — gains
   `repo_root: Path | None = None`, forwards to `gather_artifact_presence`. Its caller,
   `_dispatch_via_composition` (`src/runtime/next/runtime_bridge_composition.py:502`, already
   REQUIRES `repo_root` as a required keyword parameter), currently drops it at its own call site
   (`src/runtime/next/runtime_bridge_composition.py:626`:
   `_rb._check_composed_action_guard(action, feature_dir, mission=mission, legacy_step_id=legacy_step_id)`)
   — this call MUST stop dropping it (`repo_root=repo_root`).

Without this WP, WP02's org-tier reach is reachable only in a unit test that calls
`gather_artifact_presence`/`_presence_filenames_for` directly with an explicit `repo_root` — it is
NOT reachable from the actual `next`/WP-iteration/composed-action decision paths a real mission
run exercises. This WP closes that gap (AC-8).

## Independent Test

With an org-tier manifest reachable and no built-in manifest for a custom family, drive BOTH the
CLI/WP-iteration pre-check path AND the composed-action guard path for the same step and the same
on-disk artifact state. Assert both report the same `guard_failures` — neither disagrees with the
other (FR-003's convergence requirement; the two paths currently "agree" only because both do
nothing today, which is not the same as genuinely converging). Assert `resolve_org_roots` is
invoked with the real, non-`None` `repo_root` the enclosing function already holds (AC-8) — not a
default `repo_root=None` left unthreaded.

## Requirement Refs

FR-003, AC-1, AC-2, AC-8, NFR-004

## Subtasks

**T016 [ATDD-RED — separate commit BEFORE any implementation commit]** Add AC-1/AC-2 test cases to
`tests/runtime/next/test_cli_guard_family.py`: given a custom mission family `qa` with a declared
manifest requiring `qa-coverage.json` (`blocking: true`) at step `accept`, and the file absent,
the composed-action guard's `guard_failures` for step `accept` is non-empty and the resulting
`Decision.kind` is `blocked` (AC-1). With the file present, `guard_failures` is empty and this
emptiness is reachable only via real evaluation (provable by flipping presence and observing the
failure list change) (AC-2). Verify RED against `fix/org-tier-expected-artifacts-3703`:

```bash
git fetch origin fix/org-tier-expected-artifacts-3703
uv run pytest tests/runtime/next/test_cli_guard_family.py -v   # baseline first
```

**T017 [ATDD-RED — same commit family as T016, before implementation]** Add an AC-8 test case
asserting `resolve_org_roots` is invoked with the real, non-`None` `repo_root` the enclosing
function (`_dn_dependency_gate` or the composed-action dispatch path) already holds, when the
CLI/WP-iteration dispatch path runs a custom mission family with an org-tier manifest and no
built-in manifest. Verify RED against `fix/org-tier-expected-artifacts-3703`.

**T018** `_check_cli_guards` (`src/runtime/next/runtime_bridge.py:751`) gains
`repo_root: Path | None = None`, forwards it to `gather_artifact_presence`.

**T019** `_dn_dependency_gate` (`src/runtime/next/runtime_bridge.py:1538`) forwards the already-live
`repo_root = ctx.repo_root` local (set at line 1549) at BOTH of its `_check_cli_guards` call
sites: the WP-iteration pre-check (~line 1607-1610, inside the `try`/`except
UnregisteredMissionFamilyError` block that degrades to `[]`) and the CLI pre-check (~line
1631-1643, the `software-dev`-family-scoped block that lets the exception raise uncaught). Neither
call site currently passes `repo_root` at all — both must start doing so.

**T020** `_check_composed_action_guard` (`src/runtime/next/runtime_bridge_composition.py:429`)
gains `repo_root: Path | None = None`, forwards it to `gather_artifact_presence`. Preserve its
existing docstring's semantics otherwise (tolerant: catches `UnregisteredMissionFamilyError`,
logs at WARNING, degrades to `[]` — unlike `_check_cli_guards`, which lets it raise).

**T021** `_dispatch_via_composition` (`src/runtime/next/runtime_bridge_composition.py:502`) stops
dropping `repo_root` at its call site (`src/runtime/next/runtime_bridge_composition.py:626`):
change `_rb._check_composed_action_guard(action, feature_dir, mission=mission,
legacy_step_id=legacy_step_id)` to also pass `repo_root=repo_root` (the function already receives
`repo_root` as a required keyword parameter at its own signature — this is purely about not
dropping an already-available value at the call site).

**T022** Run this WP's full regression scope; confirm T016/T017 go GREEN; confirm
`test_non_software_dev_missing_artifact_owned_by_composed_guard`
(`tests/runtime/test_bridge_parity.py:1242`) stays GREEN — this is the regression guard pinning
that the CLI pre-check stays scoped to the `software-dev` mission family alone (#3407 M3), which
is the actual mechanism keeping `_GUARD_BRANCH_FLOOR` (18) met, NOT FR-005's family-scoping
(NFR-004); budget test coverage for T018-T021's new/changed lines toward the enforced 90%
diff-coverage floor:

```bash
uv run pytest tests/runtime/next/test_cli_guard_family.py -v
uv run pytest tests/runtime/test_bridge_parity.py -v
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v
uv run pytest tests/runtime/next/test_pertype_presence_gate.py -v
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v
uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v
```

## Gates that apply to this WP's files

**ENFORCED**: commitlint; doctrine schema freshness (trivial pass); Contextive glossary (trivial
pass); TID251; `patch()` target validation (T016/T017's new tests, if they patch
`resolve_org_roots` or similar, every target must resolve to a real importable path); Bandit;
pip-audit; `uv.lock` freshness; **`diff-coverage` 90% floor on `src/runtime/next/*`** — applies to
all three files this WP touches (`runtime_bridge.py`, `runtime_bridge_composition.py`; this WP
does not edit `runtime_bridge_cores.py` itself, but re-runs its import-boundary gate as a
regression check since it is in the same package).

**ADVISORY-ONLY**: `ruff`, `mypy` — run `make lint` locally.

## Dependencies

- Depends on WP02. (The org-tier reach WP03 threads through call sites does not exist to be
  threaded until WP02's real resolution lands.)

## Risks

- Widening the CLI pre-check's `software-dev`-only family scoping while threading `repo_root`.
  Mitigated: T019 explicitly says "preserve the existing scoping," and T022 re-runs the exact
  regression test (`test_non_software_dev_missing_artifact_owned_by_composed_guard`) that would
  catch this.
- The WP-iteration pre-check and composed-action guard disagreeing for the same on-disk state once
  either consults a declared manifest (Edge Cases in spec.md). Mitigated: both MUST route through
  the same `evaluate_guards_strict`/`evaluate_guards` over the same
  `ArtifactPresenceSnapshot`-shaped input for the same `(mission_family, step_id)` — this WP does
  not introduce a second, divergent evaluation path.
