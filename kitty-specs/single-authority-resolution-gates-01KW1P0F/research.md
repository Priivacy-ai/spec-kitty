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

## D-5 — #2155: surface-aware guard, co-landed
- **Decision**: make `safe_commit`'s `.worktrees/` blanket-refusal (`commit_helpers.py:298-320`) **surface-aware** — defer to the kind/topology partition — and co-land it with D-4.
- **Rationale**: the blanket refusal conflicts with the legitimate coord-owned status write under coordination topology; fixing D-4's routing alone leaves commits blocked (debbie). The guard must still refuse genuinely-wrong-surface writes — it becomes *surface-aware*, not *relaxed*.
- **Alternatives**: remove the guard (unsafe — loses the wrong-surface protection); fix routing only (commits stay blocked — the #2155 conflict persists).

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
