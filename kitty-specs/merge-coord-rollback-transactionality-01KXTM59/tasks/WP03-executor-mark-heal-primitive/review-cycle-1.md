---
work_package_id: WP03
review_cycle: 1
verdict: approved
reviewer: reviewer-renata+architect-alphonso
reviewed_commit: a26245a857f8d6c8caf3cead4925f67caa14948c
mission: merge-coord-rollback-transactionality-01KXTM59
requirement_refs:
- FR-005
- FR-006
- FR-008
- FR-010
---

# WP03 Review — Cycle 1 — APPROVED (dual-lens)

Two independent reviewers on the mission's highest-stakes WP (executor mark/heal/restore-primitive).

## reviewer-renata (contract/test/semantics) — APPROVE
- **DONE-coherence is a FAITHFUL #2786 contract, not a weakening (load-bearing judgment).** Proven load-bearing by running lane-b (WP03 absent) → both repros RED for the right reason (`committed=DONE vs working=APPROVED` split-brain); lane-c → GREEN. SC-006's literal contract is "committed==working re-reduced from the coord ref after heal" (does NOT mandate `approved`). The production heal-to-`approved`+clear is pinned separately (`test_bake_strand_resume_heals_and_clears`, real revert); clear-without-heal is pinned to FAIL. Non-blocking observation: the #2786 test in isolation is a weaker pin, but the companion suite closes the hole.
- SC-007 candidate-set (write-set not `all_wp_ids`, pre-existing-done exclusion), seven-site routing (incl. 701), NFR-001/002, INV-5 (heal not in `expected_order`), FR-010 — all PASS. ruff/mypy/C901 clean; only 2 owned files.

## architect-alphonso (git-safety/architecture) — SAFE-WITH-CHANGES
- **`git reset --hard HEAD` is SAFE.** Guard chain (`_persist_coord_reconcile_marker` → `_coord_worktree_root` → `is_under_worktrees_segment`) bounds the reset to a `.worktrees/` coordination checkout — never the operator's main checkout or a code lane. Merge-lock serializes writers + status-emit auto-commits ⇒ only the byte-restore delta is destroyed. Revert-fail leaves coherent-at-done + marker (cosmetic on a non-authoritative worktree; committed ref is the coherence authority). LOW defense-in-depth: narrower `git checkout HEAD -- <paths>` (folded into #2797).
- INV-5, seven-site routing, committed-ref derivation, FR-010 — all PASS.

## Consolidated disposition
Both lenses agree the code is **correct and safe**. The single gating item — the DIR-044 DoD "`_revert_coord_done_commit` delegates to the WP02 primitive" — ships **unmet but documented**: full delegation breaks the pinned `test_executor_option_a_revert_helpers_2711.py` and a clean shared-transport helper crosses WP ownership boundaries. Both reviewers concur this is a transport-dedup residual, **not** a re-opening of #2786-C (the single strand-**derivation** authority `coord_incoherent_done_wps` is preserved across mark+heal+doctor). Reconciled honestly: DoD marked deferred, data-model annotated, tracked as **#2797** (parent #1795). NOT green-washed.

Verdict: **APPROVED** (commit `a26245a857f8d6c8caf3cead4925f67caa14948c`).
