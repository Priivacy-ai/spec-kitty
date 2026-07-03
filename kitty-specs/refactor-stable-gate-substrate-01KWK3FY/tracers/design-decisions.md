# Tracer: Design Decisions

**Mission**: refactor-stable-gate-substrate-01KWK3FY
**Created**: 2026-07-03 (seeded at planning)

## Seed decisions (from spec)

1. **Family E ruled IN** (FR-005, Low) with a demotion clause: any surprise beyond the
   known seed-derivation pattern demotes it to a filed follow-up (no mission growth).
2. **Ephemeral-seed principle**: line numbers may exist as LOAD-TIME seeds only; the
   stored/compared identity is always content-addressed (spec Key Entities).
3. **Fail-closed seed validation** (FR-003): a stale seed aborts loudly — never a
   silent wrong-token derivation.
4. **Audit-inventory redesign** (FR-004) is the one design item: identity =
   (path, qualname/sink-kind, token); path changes stay meaningful, line changes do not.
5. **Stay-behind honesty** (C-003): wrong quarantine reasons are corrected even when the
   fix itself is out of domain.

## New decisions (append during implement)

_(none yet)_

## Post-spec squad decisions (2026-07-03, rev 2)

6. **Design-P over Design-S (THE mission ADR)**: renata's empirical probe proved
   seed-derivation (Design-S, `_RAW_JOIN_SITES`) is content-FOLLOWING — a fixed seed
   still breaks on drift (Scenario A: MATCH=False) and a content change is invisible
   (Scenario B: MATCH=True) — failing both NFR-001 halves. Design-P (frozen tool-derived
   `(path, qualname, token)` comparand + live membership scan, the
   `test_no_worktree_name_guess.py` pattern) satisfies both. FR-001/002/003 rewritten;
   FR-005's conversion CANCELLED (it would have regressed the reference implementation).
7. **rel_path joins the gate key** (paula): qualname collisions (`implement`/`review`
   ×2) are disambiguated only by line today; post-conversion, by path+token. YAML gains
   `file:`; violation messages keep a non-authoritative line locator for jump-to.
8. **FR-004 split into two sub-streams** (paula): the audits are copy-paste twins
   (~4 comparison sites across 3 files incl. test_untrusted_path_containment.py:328 and
   the surface SelectionRow check); line-drop struck (7/30 + 6/27 identity collisions);
   overcount/staleness tripwire ADDED (ghost rows for deleted sinks are silent today —
   doctrine consistency demands the symmetric guard before the unshim deletions land).
9. **CT9 determinism bar raised** (renata): local-only double-runs would re-prove what
   the stale quarantine reasons already claimed; evidence = real CI shard invocation
   form + a green CI run pre-merge.

## Post-tasks squad + operator fold (2026-07-03, rev 3)

10. **WP03 split-brain premise struck** (debbie HIGH + renata HIGH, convergent): the
    resolver test imports `discover_rows` live and never reads inventory.md (its
    docstring says so at :15-19/:90-96) — the upstream rebase had already decoupled
    it. Real coupling = the audit module's public shape (row fields + discover_rows
    signature). WP03 reworked; the unmodified-green proof now guards the code
    coupling, honestly.
11. **Pure-seam theater rule** (renata MED-HIGH): the new overcount checks are
    vacuously green at conversion — theater must drive `main()`'s real path (pure
    check_undercount/check_overcount seams that main() calls, or monkeypatched
    main()); helper-only theater is a review reject. Applied to WP02+WP03.
12. **FR-010 CI-green fold (operator)**: quarantine-visibility lane goes green —
    remediation/deletion/disablement only. Trigger evidence: ALL 31 quarantined
    tests fail on CI (run 28643092421) vs 16 passing locally; the old WP05 would
    have shipped 15 CI failures into blocking shards. WP05 rescoped to a 31-row
    CI-evidence adjudication; lane run on the mission PR is the acceptance gate.
13. **Smaller hardenings**: WP01 content-leg entry-point rule (violation-class
    synthetic), str(node.lineno) review reject, bidirectional count: test,
    converter fail-closed demo; WP04 content-script contract fit to the real schema
    + additive-only snapshot; WP06 full-diff proof; errata (10 constructors not ~6;
    staleness-guard symbol names; Check-2/Check-4 ranges).
