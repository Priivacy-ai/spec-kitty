# Contracts — Resolution Gates & Seams (Phase 1)

Behavioral contracts for the two architectural gates and the two routing fixes. Each is testable; gate contracts include the mandatory self-mutation proof.

## Contract 1 — Canonicalizer gate (FR-004, IC-02)

- **Input**: the `src/**/*.py` tree (AST).
- **Discriminator**: scan **calls by name** to `primary_feature_dir_for_mission` (incl. keyword-arg forms, e.g. `tasks.py:1346`). For each call the handle argument must provably originate — by **intra-function def-use** (assigned from `_canonicalize_primary_read_handle` or a known-canonical `feature_dir.name` *in the same function*), **not** name-substring — OR the call site appears in the allowlist with an already-canonical rationale. Routing is the default; **≥ the bare-handle census count must be routed, not allowlisted** (SC-004).
- **PASS**: every call is def-use-canonical or allowlisted within the pre-sweep baseline.
- **FAIL (CI red)**: a call passes a non-provably-canonical handle and is not allowlisted → error names `file:enclosing_qualname` and the sanctioned seam. (Of 38 sites, ~9–11 are canonical today; the rest route or allowlist before green.) `_read_path_resolver.py:454` is a sanctioned bare probe (C-001/FR-011) and is regression-pinned in the allowlist.
- **Self-mutation proof (NFR-002)**: inject a `primary_feature_dir_for_mission(repo_root, raw_handle)` call **at a site distinct from any IC-04 fix** → gate FAILS; revert → PASSES.
- **Floor**: concrete integer ≥ 38 (live census) — the scanner cannot silently match nothing.

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

## Contract 3 — `mark_status` write routing (FR-001, IC-04a)

- **Input**: a `mark_status` invocation on a mission under coordination topology (and, for acceptance, a flat/legacy mission too).
- **Behavior**: the **write** leg (`tasks.py:1807`) resolves its target dir through the same kind-aware authority the commit leg (`tasks.py:1906`) and `move_task`'s validation (`:658`) use — landing the write on the surface the validator reads (primary).
- **PASS**: after `mark_status`, `move_task --to for_review` does **not** report phantom "unchecked subtasks"; write-target dir == validation-read dir under **both** coord and flat topologies.
- **Invariant**: ambiguity/cold-miss handling unchanged (C-002).

## Contract 4 — Mixed-bundle routing, guard UNCHANGED (FR-002, IC-04b)

- **Input**: `move_task` (`tasks.py:1555`) / `implement`-claim (`implement.py:1311`) auto-committing a primary WP file together with coord-owned status artifacts, under coordination topology + unprotected target branch.
- **Behavior**: the bundle is split/routed so coord-owned status artifacts commit to the **coord** surface (via the `BookkeepingTransaction` pattern `workflow.py:_commit_workflow_change` uses) and the WP file to **primary**. The `safe_commit` guard (`git/commit_helpers.py:983-991`) is **NOT modified** — it stays the #1887 `worktree_root`-foreignness backstop (C-006).
- **PASS**: both callers commit cleanly with **no swallowed `SafeCommitPathPolicyError`** (the activity-log update is committed, tree clean); a deliberately wrong-surface `.worktrees/` write staged from primary is **still refused** by the unchanged guard.
- **Note**: independent of Contract 3 — this is the genuine #2155 residual the routing fix (Contract 3) does NOT dissolve (the coord status legitimately lives on coord). The current swallow must be surfaced, not re-swallowed.
