# Research — Single-Authority Resolution Gates (Phase 0)

Consolidated from the binding ADR 2026-06-26-1, the investigation note (`docs/engineering_notes/2173-infra-logic-separation/00-SYNTHESIS.md`), and the 3-squad pre-planning check (priti/debbie/paula). No NEEDS CLARIFICATION remain.

## D-1 — Gate, not DI port, for the resolver boundary
- **Decision**: close the #2164 canonicalizer class with a **single sanctioned seam + an AST call-site gate**, not an injected `MissionResolver` port.
- **Rationale**: canonicalization is already centralized (`_canonicalize_primary_read_handle`); the defect is *callers bypassing it*, which a gate forbids by construction at ~10% of the port's churn and with no partial-adoption tax. The codebase already ships the pattern (`test_protection_resolver_call_sites.py`, `test_single_mission_surface_resolver.py`).
- **Alternatives**: full `MissionResolver` DI port (deferred to #2173 Phase 2 — it is the enumeration-consolidation/#1619 layer, over-built for bug-closure); fold canonicalization into the primitive (rejected — FR-011 infinite recursion, live-confirmed at `_read_path_resolver.py:454`).

## D-2 — Scan-by-name discriminator (the TBYD blind-spot)
- **Decision**: the canonicalizer gate scans **calls by name** to `primary_feature_dir_for_mission`, checking the handle was canonicalized first — not raw `KITTY_SPECS_DIR` joins.
- **Rationale**: the primitive is topology-blind-by-design and **auto-blessed** by both existing gates; it composes the `KITTY_SPECS_DIR` join *internally*, so the raw-join scanner (Idiom-B's first discriminator) is structurally blind to a bare handle reaching it. Idiom-B's `discover_selection_callsites()` already exists for exactly this blind-spot.
- **Alternatives**: a raw-join-only gate (misses the entire #2164 class — the 34 bare-handle sites compose no join at the call site).

## D-3 — Two discriminators, one shared module
- **Decision**: the canonicalizer discriminator and the coord-authority discriminator share **one** Idiom-B machinery module (composite-key allowlist, self-test, floor, shrink-only staleness guard) but are **two** AST predicates.
- **Rationale**: they detect structurally different violations (un-canonicalized handle vs kind-blind write); one predicate cannot catch both. Sharing the machinery (C-005) avoids duplicating the governance scaffolding.
- **Alternatives**: two separate modules (duplicates the machinery); one predicate (cannot express both).

## D-4 — #2154: route the write leg through the present authority
- **Decision**: route `mark_status`'s write (`tasks.py:1807`, kind-blind `resolve_feature_dir_for_mission` → coord) through the same kind-aware authority its commit (`:1905`) and `move_task` validation (`:660`) already use → primary. Intra-function.
- **Rationale**: the kind-aware authority *exists* and is correct on two of three legs; only the write leg bypasses it. No new authority needed — this is a routing fix.
- **Alternatives**: introduce a new authority (unnecessary duplication); change the validator instead (wrong — the validator and commit are already correct; the write is the outlier).

## D-5 — #2155: route the two mixed-bundle callers, DON'T touch the guard (revised post residual-hunt)
- **Decision**: route the `move_task` (`tasks.py:1555`) and `implement`/claim (`implement.py:1311`) mixed-partition auto-commit bundles through the `BookkeepingTransaction` pattern `workflow.py:_commit_workflow_change` already uses (coord status → coord surface; WP file → primary), surfacing rather than swallowing `SafeCommitPathPolicyError`. The `safe_commit` guard (`src/specify_cli/git/commit_helpers.py:983-991`) is **NOT modified**.
- **Rationale**: the residual hunt (debbie exhaustive + python-pedro cross-check, two independent traces) proved the guard is already surface-aware (keys on `worktree_root`-foreignness) and the genuine residual is two callers committing coord status paths through a *primary* worktree — a mixed-partition bundle #2154's routing does not dissolve. The swallow ("Auto-commit skipped" warning) is why it's been low-visibility. Mutating the guard to be "kind-aware" cannot distinguish a leak from a legit coord write (only `worktree_root`-relativity can) → re-opens #1887 for zero gain.
- **Alternatives**: mutate the guard to defer to the kind partition (REJECTED — re-opens #1887, the original spec framing); "regression test only" (REJECTED — there IS a real residual at the two callers; a test without the routing fix would just pin the bug).

## D-8 — Discriminator is provenance/def-use, not name-matching (post-plan squad)
- **Decision**: the canonicalizer discriminator judges "canonical" by **intra-function def-use** (the arg is assigned from `_canonicalize_primary_read_handle`, or is a known-canonical `feature_dir.name`, in the same function), not by name-substring; routing is the default over allowlisting, with a routed-count floor and a pre-sweep baseline.
- **Rationale**: a scan-by-name gate can only force the ~27 bare-handle consumer sites into the allowlist; nothing forbids mass-allowlisting all 38 and freezing that as the shrink-only baseline → SC-004 green with zero routing (alphonso + renata converged). A name-substring "canonical" check auto-passes the ~5 sites that already contain `canonical` in the arg name. Def-use + routed-count-floor + pre-sweep-baseline close the vacuity.
- **Alternatives**: pure name-matching (fakeable); full data-flow analysis (over-built — intra-function def-use suffices for the realistic site shapes).

## D-6 — Convergence test is stub-driven
- **Decision**: assert read-seam ≡ write/placement-seam for every handle form via an injectable/stub resolver, no live `kitty-specs/` fixtures.
- **Rationale**: deterministic, fast (fast tier), exercises every handle form including ambiguity-raises and cold-miss without filesystem setup. This is the testability win the ADR's Phase-2 port would also deliver — available here via stubbing.
- **Alternatives**: live `kitty-specs/` fixtures (slow, flaky, needs real ULID/mid8 scaffolding).

## D-7 — Folds are domain-matched only
- **Decision**: fold #1842's `/tmp`-literal-in-tests ratchet (via IC-01's gate pattern) and #2034's marker co-tag (on mission-owned `contract` files only).
- **Rationale**: both touch surfaces this mission already opens; cheap incremental hygiene. The domain-match guard excludes the #1842 litter sweep and the #2034 `ci-quality.yml` matrix change (paula).
- **Alternatives**: full #1842/#2034 (scope inflation, out-of-domain); skip the folds (leaves cheap wins on the table while the surfaces are open).

## Brownfield checks (post-planning, to run in the squad pass)
Per the standing post-planning cadence — to be executed by the post-plan squads, recorded back here/plan.md:
- **Foldable-issue search**: DONE in pre-planning (the issue-matrix; #1842/#2034 folded, everything else excluded with rationale).
- **Split-brain / dual-authority scan**: the mission *is* the split-brain fix; verify no NEW dual-authority is introduced (the gates enforce single authority).
- **LOC / sizing scan**: ~34 canonicalizer sites is the dominant cost; confirm the allowlist-vs-route split is calibrated (not 34 routes).
- **Deprecation check**: confirm `resolve_feature_dir_for_mission` (kind-blind) is being *narrowed* (writes routed away), not freshly adopted elsewhere.
