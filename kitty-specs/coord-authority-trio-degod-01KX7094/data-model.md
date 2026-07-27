# Phase 1 Data Model: Coord-Authority Trio Degod

Structural (not persistent) entities — the decomposition's building blocks.

## Ports façade (per command)
Injected infrastructure boundary, passed as data (today's monkeypatch targets):
- workflow: `safe_commit`, `feature_status_lock`, `subprocess`, `resolve_workspace_for_wp`, `_ensure_target_branch_checked_out`, `build_charter_context`
- implement: `git`, `safe_commit`, `BookkeepingTransaction`, `console`
- acceptance: file I/O for `normalize_feature_encoding`, commit for `_commit_acceptance_meta`
**Invariant**: cores receive ports as parameters; cores import no infra module directly (FR-007 arch pin).

## Request dataclass (per Typer command)
Marshals the ~20 `Annotated`/`typer.Option` params into a plain dataclass the pure core consumes. The Typer signature stays in the shell (impure, ~150-200 LOC).

## Pure core
Deterministic in→out logic, NO I/O. Extracted:
- workflow: review-context builder, review-feedback resolution, decision mapping, banner/prompt renderers, status-error classifier
- implement: git-porcelain/diff family, staging-decision, placement family
- acceptance: `summary_core` (collect_feature_summary, recommended-fix-order), `gates_core` (lane gates, terminal/unchecked checks)
**Invariant**: unit-testable without a repo; S3776 ≤15.

## Executor
Thin layer wiring ports → core → output/commit: `_commit_workflow_change` (workflow), git executor (implement), `perform_acceptance`/`_commit_acceptance_meta` (acceptance).

## Read-contract set (the partition seam — PRESERVE all three)
| Contract | Function | Behaviour | Trio usage (corrected) |
|----------|----------|-----------|------------------------|
| (a) lenient | `placement_seam.read_dir(kind)` / `resolve_handle_to_read_path(require_exists=False)` | never raises; degrades to primary anchor | **what the trio uses** (workflow.py:323, acceptance `_status_read_feature_dir:747`) |
| (b) fail-closed guarded | `resolve_handle_to_read_path(require_exists=True)` | raises `StatusReadPathNotFound`/`CoordinationBranchDeleted` (#1848) | seam offers it; used by OTHER modules — **NOT the trio** |
| (c) topology-blind primary | `primary_feature_dir_for_mission` | meta.json must not follow to coord | primary anchors where used |
**Invariant**: the trio imports only seam wrappers (SC-002 arch pin) AND keeps each read's existing laxity — no lenient→fail-close flip (or vice-versa); the acceptance not-exists degrade is preserved verbatim.

## Re-export shim (FR-009)
Old module path re-exports a moved symbol so module-qualified monkeypatch targets stay valid; retired once patch paths are repinned. Behaviour-preserving, no logic.
