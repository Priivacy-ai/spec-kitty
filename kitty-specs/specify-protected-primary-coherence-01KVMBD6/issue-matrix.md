# Issue matrix — specify-protected-primary-coherence-01KVMBD6

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1619 | Epic: unify mission execution context (P0 specify-deadlock driver) | deferred-with-followup | The specify-phase coord-worktree materialization deadlock (this epic's P0 driver) is FIXED by WP02; the broader coord/primary epic remains tracked in #1619 (Follow-up: #1619) |
| #1718 | Create→first-write window must read primary | verified-already-fixed | NFR-001 preserved; WP07 extends `test_read_path_create_window_invariant.py` (materialize at commit, not read) |
| #1868 | Canonical seams / authority-in-name-only | deferred-with-followup | WP05 FR-010 single-resolver guard closes the protection "authority in name only" instance; the canonical-seams epic remains tracked in #1868 (Follow-up: #1868) |
| #1828 | Hatch honored inconsistently (safe_commit vs assert_not_protected_branch) | fixed | WP01 folds the hatch into ProtectionPolicy.is_protected() (single decision path) + a mutation-verified symmetry regression pin; closes #1828 |
| #1850 | PR that de-facto fixed the #1828 hatch asymmetry | verified-already-fixed | #1828 hatch symmetry already landed in #1850; WP01 pins it structurally |
| #1716 | Coordination topology coherence (create→planning) | deferred-with-followup | This mission fixes the create→specify materialization facet (WP02); the create→planning write-side residual remains tracked in #1716 |
| #1878 | Coordination placement/identity strangler umbrella | deferred-with-followup | Discharges the specify-phase protected-primary evidence; the remaining strangler work stays tracked in #1878 (Follow-up: #1878) |
| #1829 | Decision: drop local-main protected-branch refusals (divergent) | verified-already-fixed | Superseded by the configure-and-route decision (ADR 2026-06-21-1); CLOSED not-planned 2026-06-21 with explanatory comment |
| #2040 | Single mission-surface read/write resolver | deferred-with-followup | Distinct seam (C-005); this mission is create-time materialization, not the read/write surface-authority desync — tracked in #2040 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
