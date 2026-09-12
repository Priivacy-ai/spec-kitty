# Grounding and Campsite Report — 2026-08-10

**Point cut**: after WP01 cycle-4 implementation submission, before its independent review  
**Mode**: read-only repository, runtime-state, evidence, and GitHub PR audit  
**Lenses**: Debugger Debbie, Reviewer Renata, Randy Reducer  
**Verdict at point cut**: **STOP** for WP01 approval, mission-complete, or PR-ready claims. Continue only through corrective review work.

This report consolidates the campsite squad's inputs and findings. Earlier planning squads were described in prose but their raw agent transcripts were not persisted; this report does not fabricate those missing transcripts.

## Confirmed blockers

1. WP01 was `for_review`; the latest durable verdict remained cycle-3 `changes_requested`. Cycle 4 was an implementation resubmission, not an approval.
2. `audit.py` validated route IDs and some environment fields but did not bind the complete selector, event, required/role membership, command, cwd, environment, or base/HEAD mapping to the frozen workload and tracked CI configuration. A schema-valid fabricated route could pass.
3. `raw/base-full-suite-summary.txt` contained aggregate counts and wall time only. It lacked the exact nodeid/outcome set, timestamp, environment identity, raw-log hash, and failure attribution required to freeze known-red membership.
4. Review-cycle artifacts 1–3 existed byte-identically on PRIMARY and COORD despite the accepted COORD-partition ADR. COORD must remain the single current authority.
5. COORD held an uncommitted cycle-4 annotation/materialized-state update.
6. PRIMARY `meta.json` lacked `status_phase`; PR #3285's `cutover-guard` failed. The PR head was also eight local planning commits behind.
7. The PRIMARY `.venv` was half-built: `pytest` loaded as an empty namespace, `pip` missed modules, and console entry points failed. The lane environment remained healthy.
8. `analysis-report.md` and the tracer stopped at planning/cycle 1 and overstated durable squad evidence.

## Confirmed campsite priorities

- Freeze WP01's evidence schema after correcting the concrete route-provenance and exact-outcome gaps. No further schema expansion without a reproducible bypass.
- Treat the 2,139-line mission-local auditor and 23.5 MB census as evidence overhead to contain, not product architecture to expand.
- Prioritize #2645: every pytest collection enters the 2,037-line wall-clock assertion scanner. Measure deterministic operation count and pathological fixtures before refactoring.
- Report test deletion, scanner optimization, and CI routing savings separately. The 15% route target must not be attributed to deletions unless measured.
- Split proven inert deletion from flake/red/timing adjudication. Thirteen zero-assertion permanent skips/placeholders are ready for deletion after the foundation gate; outcome-sensitive work waits for repaired bootstrap evidence.

## Proven delete-now cohort

- Ten permanently skipped #2309 bodies in `tests/sync/test_daemon_singleton_reaper_consolidation.py`.
- Two permanently skipped #2316 bodies in `tests/readiness/test_upgrade_ux.py`.
- One manual-live-server placeholder in `tests/sync/test_client_integration.py`.

These tests execute no assertions. The linked tracker issues, not inert pytest bodies, retain product authority.

## Positive evidence

- Prepared workspace contains only the core repo and the required E2E sibling; both were clean at the point cut.
- Immutable-base content-equivalence passed; recorded raw hashes and `uv.lock` hash matched.
- Canonical census validated: 29,766 source units, 37,444 pytest nodes, 173 strict duplicate groups, 365 group members.
- WP01 cycle-4 selftests passed 85/85; `ruff`, `mypy --strict`, artifact validation, and `tests/docs` (1,381 tests) passed.
- Fifteen WPs / lanes and 365 write-scope paths had no ownership overlap; the dependency graph was acyclic.
- Referenced issues were open, assigned, and mission-commented at the point cut.

## Remediation log

- PRIMARY copies of review cycles 1–3 were removed; byte-identical COORD copies remain authoritative.
- The pending cycle-4 submission annotation was committed on COORD.
- Runtime cutover was backfilled and `cutover-guard` passed. The single-target CLI remedy and the topology-aware two-target seam wrote different seed surfaces; retain this as a tooling defect for campsite follow-up.
- PRIMARY `.venv` was rebuilt with `uv sync --frozen --all-extras --reinstall`; `pytest`, `pip`, `ruff`, and `mypy` entry points were restored.
- Remaining STOP conditions: canonical independent WP01 review, full route-provenance binding, exact node/outcome baseline evidence, and current PR integration/push.

## Review boundary

No test was deleted and no WP was approved during this audit. The next lifecycle action is the canonical independent review of WP01 cycle 4.
