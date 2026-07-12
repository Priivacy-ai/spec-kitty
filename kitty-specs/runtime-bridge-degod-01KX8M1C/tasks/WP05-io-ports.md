---
work_package_id: WP05
title: Clean I/O ports
dependencies: [WP04]
requirement_refs:
- FR-001
- FR-003
- FR-006
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Extraction spine
shell_pid: '2190657'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/runtime_bridge_io.py
- tests/runtime/test_bridge_io.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_io.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_io.py
role: implementer
tags: []
task_type: implement
---

# WP05 — Clean I/O ports

## Context

Extracts the **narrow I/O ports** out of `runtime_bridge.py` into a new
`runtime_bridge_io.py` seam (IC-04). These are the clean, near-mechanical
boundaries — 60 function-local lazy imports already isolate them at module load,
so the moves are low-risk. This seam is the **fact-provider** the later pure
cores depend on: it produces the `gather_artifact_presence` snapshot (FR-009,
consumed by WP06's pure `evaluate_guards`) and lifts the one pure decision that
was interleaved inside I/O (`resolve_commit_target`).

**Depends on WP01 + WP02** (both green on unmodified source). WP06 (pure cores)
depends on this WP for the `gather_artifact_presence` fact-port. Acceptance gate
unchanged: **oracle stays green, compat guard stays green** after the move.

Read `data-model.md §Ports` and `research.md §Seams` (io row). Ports **inject
I/O** so downstream cores can be pure (FR-003): purity = **no-I/O +
port-injected**, NOT "no `specify_cli` import" — runtime and specify_cli are
co-equal production packages with no arch gate between them. Behavior-preserving
only (C-001).

## Ordered steps

### T017 — Create `runtime_bridge_io.py`; move the I/O ports
Move the narrow I/O ports into `runtime_bridge_io.py`:
- **feature-runs.json index** — `load_feature_runs(path) -> dict` /
  `save_feature_runs(path, dict)` (textbook narrow port; the existing
  `_load/_save_feature_runs`).
- **template / pack discovery**.
- **run lifecycle** (start / lookup).
- **operational-context (OC) builder**.
Grep the call sites to bound the cluster and confirm no bidirectional coupling
that would create an import cycle (C-007). Identical call semantics, new home.

### T018 — `gather_artifact_presence` fact-port (feeds FR-009)
Introduce `gather_artifact_presence(feature_dir, …) -> ArtifactPresenceSnapshot`
as the **port** that gathers the filesystem/status/bulk-edit/requirement-mapping
facts the guards read (see `data-model.md §ArtifactPresenceSnapshot`:
`present_artifacts`, `status_facts`, `mission_family`, `step_id`/`legacy_step_id`).
This is the fact side of the FR-009 guard inversion — WP06 consumes the snapshot
in a pure `evaluate_guards(snapshot)`. Gather **only** facts here; make **no**
decisions (those belong to WP06's pure core). Preserve exactly the facts the two
guards read today so the fail-closed default and `guard_failures` order are
reproducible downstream (SC-007).

### T019 — Lift pure `resolve_commit_target` out of `_wrap_with_decision_git_log:226–261`
`_wrap_with_decision_git_log` (`:187`) is the **one port that interleaves a pure
decision inside I/O**. Lift its commit-target **selection** logic (the pure
decision at `:226–261`) into a pure `resolve_commit_target(...)` in
`runtime_bridge_io.py`, and have `_wrap_with_decision_git_log` call it.
`_wrap_with_decision_git_log` itself is **KEEP-IN-PLACE** in the residual (compat
anchor — `contracts/compat-surface.md`); only the pure selection moves out. This
keeps the coord-commit side-effect (captured by the WP01 oracle at `:2563`/`:3427`)
byte-identical.

### T020 — Port unit tests (stubbed I/O); re-export; oracle + compat green
Add focused port unit tests (FR-006) — the ports contract-tested against stubs,
and `resolve_commit_target` unit-tested as a **pure** function in isolation
(no I/O — NFR-003). Re-import every moved patched symbol into `runtime_bridge`'s
guarded compat re-export block (+ `_wf`-style LAZY-ACCESSOR for sibling-called
names per WP02's inventory). Then run **both safety nets**: WP01 parity oracle
(all 3 entries, full floor) and WP02 compat guard (per-entry sentinels + AST
identity). Both MUST be green.

## Acceptance
- I/O ports extracted into `runtime_bridge_io.py` (feature-runs index, template
  discovery, run lifecycle, OC builder); boundary clean (no new import cycle — C-007).
- `gather_artifact_presence` fact-port present, producing an
  `ArtifactPresenceSnapshot`; gathers facts only (no decisions).
- `resolve_commit_target` lifted as a **pure** function; `_wrap_with_decision_git_log`
  stays KEEP-IN-PLACE in the residual and calls it; coord-commit side-effect
  unchanged.
- Ports have contract tests against stubs; `resolve_commit_target` has a direct
  no-I/O unit test (NFR-003).
- **WP01 oracle green** and **WP02 compat guard green** — the acceptance gate.
- `ruff --select C901` zero new offenders; `mypy` clean; no suppressions.

## Safeguards
- `gather_artifact_presence` must capture **exactly** the facts the two guards
  read today (incl. the fail-closed-default inputs and the `tasks` legacy-union),
  or WP06's pure `evaluate_guards` cannot preserve `guard_failures` content/order
  (SC-007). Do not decide here — facts only.
- `_wrap_with_decision_git_log` is a KEEP-IN-PLACE compat anchor — do **not**
  relocate it; only lift the pure `:226–261` selection out. Moving the wrapper
  breaks the identity-trio + coord-commit compat surface.
- Purity = no-I/O + port-injected, NOT "no specify_cli import" (FR-003/C-002).
- Behavior-preserving only (C-001); the coord-commit payload captured by the WP01
  oracle must stay byte-identical.

## References
- `data-model.md:27-30` §Ports (feature-runs port, discovery, run lifecycle, `resolve_commit_target`)
- `data-model.md:5-13` §ArtifactPresenceSnapshot (fact-port output shape)
- `research.md:16,37` §Seams (io row; `resolve_commit_target` refinement 3)
- `plan.md:109-111` IC-04 (clean I/O ports purpose)
- `src/runtime/next/runtime_bridge.py:187` `_wrap_with_decision_git_log` (KEEP-IN-PLACE; pure selection at `:226–261`)
- `contracts/parity-oracle.md:28-33` (coord-commit captured at `:2563`/`:3427`)
- `contracts/parity-oracle.md`, `tests/runtime/test_bridge_compat_surface.py` (re-run as acceptance gate)

## Activity Log

- 2026-07-11T20:39:07Z – user – shell_pid=2190657 – Moved to for_review
- 2026-07-11T20:46:44Z – user – shell_pid=2190657 – Moved to approved
