# Contracts — Resolution Gates & Seams (Phase 1)

Behavioral contracts for the two architectural gates and the two routing fixes. Each is testable; gate contracts include the mandatory self-mutation proof.

## Contract 1 — Canonicalizer gate (FR-004, IC-02)

- **Input**: the `src/**/*.py` tree (AST).
- **Discriminator**: scan **calls by name** to `primary_feature_dir_for_mission`. For each call, the handle argument must provably originate from the canonical fold `_canonicalize_primary_read_handle` (or be a value already known canonical — a `feature_dir.name`), OR the call site must appear in the allowlist with a rationale.
- **PASS**: every call is canonical-sourced or allowlisted.
- **FAIL (CI red)**: a call passes a bare/un-canonicalized handle and is not allowlisted → error names the `file:enclosing_qualname` and the sanctioned seam to route through. (The 34 current bare-handle sites must each be routed or allowlisted before this gate is green.)
- **Self-mutation proof (NFR-002)**: inject a `primary_feature_dir_for_mission(repo_root, raw_handle)` call → gate FAILS; revert → PASSES.
- **Floor**: a minimum discovered-call count so the scanner cannot silently match nothing.

## Contract 2 — Coord-authority gate (FR-003, IC-03)

- **Input**: the `src/**/*.py` tree (AST).
- **Discriminator**: scan for mission-artifact **write** sites that resolve their target via the kind-blind `resolve_feature_dir_for_mission`. Each must either route through the kind-aware authority (`commit_for_mission(kind=)` / `resolve_planning_read_dir(kind=)`) or be allowlisted (legitimate kind-blind read/probe) with a rationale.
- **PASS**: every mandated kind-aware write routes through the authority; kind-blind reads are allowlisted.
- **FAIL (CI red)**: a mission-artifact write uses the kind-blind resolver and is not allowlisted → error names the site + the kind-aware authority to use.
- **Self-mutation proof**: inject a kind-blind write at a mandated site → FAILS; revert → PASSES.

## Shared machinery (IC-01, both gates, C-005)

- Allowlist keyed by `(enclosing_qualname, token_line)` computed live from source (survives benign line drift; NFR-001).
- Shrink-only: a staleness twin-guard fails if any allowlist entry no longer matches a live site (NFR-003).
- Both run in the fast tier, `<30 s` on full `src/` (NFR-004).

## Contract 3 — `mark_status` write routing (FR-001, IC-04)

- **Input**: a `mark_status` invocation on a mission under coordination topology.
- **Behavior**: the **write** leg resolves its target dir through the same kind-aware authority that the commit leg (`tasks.py:1905`) and `move_task`'s validation (`:660`) use — landing the write on the surface the validator reads (primary).
- **PASS**: after `mark_status`, `move_task --to for_review` does **not** report phantom "unchecked subtasks"; the WP advances.
- **Invariant**: ambiguity/cold-miss handling unchanged (C-002).

## Contract 4 — `safe_commit` surface-aware guard (FR-002, IC-04)

- **Input**: a legitimate coordination-owned status write staged from the repo root.
- **Behavior**: the `.worktrees/`-path policy (`commit_helpers.py:298-320`) defers to the kind/topology partition and **permits** the coord-owned write; it still **refuses** a genuinely wrong-surface write (the guard becomes surface-aware, not removed).
- **PASS**: the status transition commits successfully (no `SafeCommitPathPolicyError`); a deliberately wrong-surface write is still refused.
- **Co-land**: ships with Contract 3 (routing alone leaves commits blocked).
