# Issue matrix — landing-pass-campsite-followups-01KXKWD7

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2670 | Parent landing pass that spawned this follow-up bundle | verified-already-fixed | PR #2670 already merged to upstream/main; this mission is its campsite follow-up |
| #2671 | Shard-registry default fallback + doctrine header | fixed | WP01 commit 57c6edf29 |
| #2673 | Bite-battery mutation isolation | fixed | WP02 commit 996bbdf2c |
| #2638 | Second scanner victim (duplicate of #2673) | fixed | WP02 commit 996bbdf2c (same isolation fix; close as fixed-by #2673) |
| #2672 | Color/synthesis-manifest hygiene via CliConsole | fixed | WP03 commit 7429768cd |
| #2674 | Sync remediation registry + guard | fixed | WP04 commit c5d03461c |
| #2675 | Type-debt: 17 mypy errors → 6 roots | fixed | WP05 6ed52c7ff / WP06 66343ab8b / WP07 304f4410d (3 mission_type_profiles.py casts deferred to mission-type work; 2 emit.py/m_2_1_4 casts config-verified load-bearing, left in place) |
| #2475 | Arch marker gate vacuous under dotted .worktrees checkout | deferred-with-followup | Out of scope (spec Scope Boundaries) — separate design effort under #1931/#2071 |
| #2476 | Proto-spec: local arch-pole pre-PR parity CLI | deferred-with-followup | Out of scope — larger design effort, not folded |
| #2607 | GC-2b baseline abs-path-id portability | deferred-with-followup | Out of scope — different surface |
| #2625 | golden-count excluded co-owned dir sites | deferred-with-followup | Out of scope — different surface |
| #2631 | FR-016 ratchet/parity-suite harm audit | deferred-with-followup | Out of scope — unrelated concern |
| #1843 | Tiered coding standards by DDD domain (epic) | deferred-with-followup | Out of scope — strategic doctrine epic |
| #1928 | Reduce ruff/mypy/Sonar debt (epic) | deferred-with-followup | Parent epic for #2675; this mission delivers the #2675 slice, epic remains open |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

**Follow-up to file at close (SC-006):** the ~6 residual `_SourceMutation`/`_SourceInsertion` real-file-mutation sites in `test_single_mission_surface_resolver.py` (beyond the #2673/#2638 pair) — tracked issue to be filed during mission wrap-up.
