# Phase 0 Research: Reliability Papercut Sweep

This research was produced by a pre-flight investigation squad (debugger-debbie ×3 verifying
per-issue code-state against current main, planner-priti for the tracker landscape, and a
paula-patterns campsite/undersizing pass) **before** this plan. Findings are consolidated
here as the authoritative Phase 0 record; the plan does not re-derive them.

## Decisions

### D1 — Keep `classify_topology` pure; probe git at the boundary (FR-002 / C-001)
- **Decision**: do NOT add git-existence awareness to `classify_topology` (`mission_runtime/context.py`). Add the probe at the backfill / surface-resolver boundary (`backfill_topology.py`, `surface_resolver._coord_branch_exists`).
- **Rationale**: `classify_topology` is the pure FR-001 SSOT with 8 consumers (`backfill_topology`, `mission_creation`, `resolution.py` ×2, `status_transition`, `surface_resolver`). A probe there ripples into `resolution.py` and the `runtime_bridge` topology path — which Lane B (#2138) also edits — creating a cross-lane collision.
- **Alternatives rejected**: git-aware SSOT (ripple + collision); a parallel classifier (duplication).

### D2 — `target_branch`: one primitive, three thin adapters (FR-005 / C-005)
- **Decision**: collapse the read logic into one shared primitive that distinguishes *field-absent* (documented default) from *read-failure* (fail closed); keep `get_feature_target_branch` (str), `resolve_merge_target_branch` (tuple+provenance), `resolve_target_branch` (BranchResolution) as thin adapters so ~18 call sites are unchanged.
- **Rationale**: the three serve different concerns/return types; one public function would force ~18 call-site rewrites + return-type changes. The silent fallback is currently identical in all three (`return primary_branch` on missing OR malformed) — splitting absent-vs-failed is the correctness fix.
- **Alternatives rejected**: single public reader (bulk churn); leave as-is (silent wrong-merge-target persists).

### D3 — Slug-as-mission_id fail-closed, flat path mints/reads ULID (FR-004)
- **Decision**: remove the `or mission_slug` fallback at both sites (`decision_log.py:98`, `runtime_bridge._resolve_mission_ulid`), and have the flat/coord-less path source a real ULID (read meta `mission_id`, or mint) before logging; fail closed when none is available.
- **Rationale**: the coord-routing path already fails closed; the leak survives only on the flat path. Deleting the fallback alone would break flat missions that legitimately carry a ULID via a legacy caller.
- **Test note**: `test_slug_fallback_when_no_mission_id` asserts the bug as correct and MUST be inverted; a correct sibling (`mission_id == ulid`) already coexists.

### D4 — #2240 is mostly fixed; residual is real-recovery + regression guard (FR-003)
- **Decision**: the phantom `agent worktree repair` string is already removed (#1890 / `ecf45f52c`). Scope #2240 to (a) a standing regression test guarding the dead-command class, (b) ensuring the recommended recovery actually recreates/handles the worktree, (c) the stale-behind-tip sub-ask.
- **Rationale**: #2240 is a recurrence of closed #1890 — the fix shipped but the class recurred, so a permanent guard is the durable fix.

### D5 — #2123 and #2241 already fixed (closed this session)
- #2123 (lane-worktree data-loss over-match) fixed by `c22ac6655`; #2241 (map-requirements coord-vs-primary) fixed by #2064 / `ede98fca9`. Both live-verified (regression tests green) and CLOSED. Not in scope.

## Sizing (verified)
- IC-01 (#2251): **S**, one site + one test arm.
- IC-02 (#2250): **M**, spread across 4 files (surface_resolver, backfill, doctor hint, masking selector).
- IC-03 (#2240): **thin**, regression-pin + stale sub-ask.
- IC-04 (#2138): **M**, two fallback sites + flat-path ULID source + invert test.
- IC-05 (#2139): **M–L**, primitive + 3 adapters, ~18 call sites behavior-stable.
- IC-06 (#2091): **S–M**, mint boundary in `runtime_bridge`.

## Cross-cutting constraints (binding)
- **C-001**: `classify_topology` stays pure (D1).
- **C-002**: IC-02 → IC-03 sequenced (shared `_coordination_doctor.py`); IC-04 ↔ IC-06 coordinate on `runtime_bridge.py`.
- **C-003**: invert the stale slug test; re-pin two doctor-hint tests; extend (not replace) the healthy allowlist + merge-target tests.
- **C-005**: #2139 keeps call sites unchanged (thin adapters; not a bulk rename).

## Precedent to cite (do not re-fold)
#2102 (dirty-tree allowlist), #1890 (doctor-hint), #2219 (backfill-topology), #2136 (canonical handle), #2065 (surface-resolver single-authority).

---

## Post-plan squad findings & adjustments (2026-06-30)

A post-plan adversarial squad (architect-alphonso on plan/IC architecture; paula-patterns on
brownfield missed-surfaces) reviewed the plan as written. Verdict: sound architecture,
NEEDS-ADJUSTMENT on precision + scope. All folded into plan.md:

### Corrections
- **Paths**: `surface_resolver.py` is under `coordination/` (not `missions/`); `backfill_topology.py`
  is under `migration/` (not `cli/commands/agent/`).
- **Counts**: `classify_topology` has **6** consumers (not 8) — strengthens C-001. IC-05 has
  ~18–20 genuine call sites (~64 raw refs incl. the 2 delegating wrappers `orchestrator_api/commands.py`
  + `merge/resolve.py`, which need no separate edit).

### C-001 widened to `read_topology` (alphonso)
`migration/backfill_topology.py` exports `read_topology` (→ `_derive_topology` → `classify_topology`),
consumed by **Lane B's** `runtime_bridge.py:173,189`, plus `resolution.py:764`, `status_transition.py:601`.
A git-probe in `read_topology`/`_derive_topology` would silently reclassify a never-created branch
for Lane B too (cross-lane behavioral shift, no merge conflict). **Decision**: IC-02's probe is pinned
to `surface_resolver` remediation + the backfill **write** path; both `classify_topology` and
`read_topology` stay pure.

### IC-04 ⇄ IC-06 MERGED (alphonso; operator-confirmed)
They are one contract: the mint boundary calls `_resolve_mission_ulid`, and `runtime_bridge:224`
(`mission_id if mission_id != mission_slug else None`) encodes the slug-as-sentinel that #2138 removes.
Split across two WPs = the define-here/consume-there split-brain the mission fights. **Decision**: one
IC/WP owns the full fail-closed identity contract (decision_log.py:98 + prompt_metadata.py:149 +
runtime_bridge `_resolve_mission_ulid`/`:224`/mint). IC map is now 5 ICs.

### IC-01 widened to all dirty-tree gates (paula; operator-confirmed)
`is_self_bookkeeping_path` feeds only record-analysis. The accept gate (`acceptance/__init__.py`
`_accept_dirty_gate`) and merge preflight keep **independent** allowlists with no kitty-ops arm —
they'd block on the same orphan. **Decision**: make the kitty-ops arm a shared authority consumed by
record-analysis + accept + merge gates (else partial split-brain fix). Reference umbrella **#1914**
(no-op-stable gates) as the deeper framing; do not undertake the full no-op-stable rework here.

### Missed surface added
- `review/prompt_metadata.py:149` (`mission_id=str(mission_id or mission_slug)`) — third slug→mission_id
  site, folded into IC-04. Other `or mission_slug` hits are legacy-guarded or a different field (aggregate_id).

### Confirmed complete / no change
- IC-05 target_branch: exactly 3 primitive readers (2 higher resolvers delegate) — no missed split-brain.
- IC-06 mint: `runtime_bridge` is the sole mint boundary, already fails closed (`BranchIdentityUnresolved`).
- No deprecation hazard — all targets are canonical homes (notably `runtime/next/runtime_bridge.py`, not the `specify_cli/next/` shim).

### See-also (not folded)
- **#1914** umbrella (IC-01 deeper framing), **#2017** workflow-guard friction (adjacent to IC-01/IC-03),
  **#2263** config.yaml worktree-clean (same no-op-stable family, sync-owned — not folded).
