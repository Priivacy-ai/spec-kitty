# Issue matrix — merge-coord-rollback-transactionality-01KXTM59

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2786 | Failed coord-`done` revert during rollback swallowed → re-opens #2711 split-brain | fixed | WP01 red-first repro (50f4143b, now GREEN); WP03 mark-not-raise + strand-gated heal (ad4af8034); WP04 doctor detect/`--fix`; WP05 behavioral class-closing guard. All 5 WPs approved. |
| #2711 | Rollback/resume incoherence (coord-done revert) | verified-already-fixed | Prior mission (PR #2785, Option A coord-done-revert); this mission's tests build on that harness |
| #2367 | merge blocked by coord worktree: VCS-lock at claim (A) + non-transactional coord rollback (B) | deferred-with-followup | Mechanism B (non-transactional coord rollback) FIXED by WP03 (byte-restore-without-revert closed); Mechanism A (claim-time VCS-lock resync) deferred to #2795. PR partially-addresses #2367 — does NOT auto-close (A residual tracked by #2795). |
| #2222 | Merge-owned churn classifier | verified-already-fixed | Classifier already in place; reused by the deferred #2795 (Mechanism A) |
| #2017 | Epic: Workflow guards that block legitimate actions | deferred-with-followup | Mechanism-A (claim-time VCS-lock resync) work carried by child #2795 |
| #1826 | Coord split-brain recurrence (chain origin) | verified-already-fixed | Recurrence-chain predecessor (#1826→#1878→#2711→#2786); historical, fixed upstream |
| #1878 | Coord split-brain recurrence (chain) | verified-already-fixed | Recurrence-chain predecessor; historical, fixed upstream |
| #1827 | INV-5 phase-ordering ratchet | verified-already-fixed | Constraint respected; `test_executor_phase_boundary.py` stays green (WP03 inner-only, heal not in expected_order) |
| #2795 | merge blocked by claim-time VCS-lock resync (Mechanism A, split from #2367) | deferred-with-followup | Filed this mission under epic #2017; out of scope, own design pass (reuses #2222) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
