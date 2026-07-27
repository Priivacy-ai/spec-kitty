# Read-Side Placement-Seam Migration

> Reviewer summary for PR `read-side-placement-seam-migration`. Written for a
> reader who has **not** followed the mission — the background below is enough to
> review the diff without extra context.

## Background (for a non-maintainer reader)

Spec Kitty stores each mission's files on one of two "partitions":

- **PRIMARY** — stable planning and metadata (spec, plan, `meta.json`), on the
  mission's planning branch.
- **COORD** — lifecycle surfaces (the append-only status event log, notes,
  traces), on a separate *coordination* branch.

A single component — the **placement seam** — is meant to be the one authority
answering "where does this artifact live?". You ask it for an artifact *kind*
(`STATUS_STATE`, `LANE_STATE`, `WORK_PACKAGE_TASK`, `PRIMARY_METADATA`, …) and it
resolves the right partition, **failing loud** if the partition it needs is gone
(e.g. a coordination branch consolidated away).

A previous change hardened that seam — but only for **writes**. On the read side,
~50 modules still called the low-level, *kind-blind* resolvers
(`candidate_feature_dir_for_mission`, `resolve_planning_read_dir`) directly. Those
resolvers don't know which partition an artifact belongs to, so a read could
silently fall back to the primary checkout when a coord-partition artifact's branch
was deleted — returning plausible-but-wrong data instead of failing. That is the
"whack-a-read" gap (#2922, parent #1878).

This PR closes it, and makes the bypass structurally impossible going forward.

## Summary

- Route every read that *should* fail loud through the kind-aware seam with the
  correct artifact kind — while deliberately leaving diagnostic/audit readers
  lenient, because reporting surfaces must not start crashing.
- Add a whole-tree gate so a *new* kind-blind read can't be introduced silently,
  with a shrink-only allow-list that forces its own entries to be deleted once
  they're no longer needed.
- Fold in two small related fixes that were blocked behind this work (#2921, and
  the part-1 remainder of #2966).

## Why Now

The write side was already enforced; the read side was still "hardened one caller
at a time", which is unbounded — every new module could reintroduce the bug. The
asymmetry was tracked as #2922 (parent #1878). Doing it as one mission let a
per-site classification be decided **once**, up front, and then be mechanically
enforced — rather than re-litigated in each future PR.

## What This PR Does

**1. Classify first (one authority).** A per-site ledger
(`docs/development/read-side-seam-classification.md`) records, for every production
caller of the kind-blind resolvers: the target artifact kind, the disposition
(*migrate-fail-loud* / *stay-lenient* / *sanction-infra*), and the rationale —
**72 migrate + 16 stay-lenient + 2 sanction-infra**. Every subsequent change was
executed and reviewed against this document.

**2. Migrate the 72 fail-loud sites** across five clusters (agent-CLI,
CLI-commands, merge+lanes, diagnostic, core/context/workspace/plan) to
`placement_seam(...).read_dir(<kind>)`. Coord-partition reads now fail loud: a
lane-based merge's event-log read, the decision-log companion read, and the
doctrine synthesizer must not treat a deleted coordination branch as healthy.

**3. Keep 16 readers lenient — on purpose.** Dashboard scan, dossier API (SaaS
facing, answers 404 for "not found"), retrospective summary, status aggregation,
the manifest drift probe, and several CLI diagnostics stay on the lenient resolver
with their existing degrade paths, recorded as justified allow-list entries.

**4. Make new bypasses unrepresentable.** A new whole-tree AST gate
(`tests/architectural/test_no_read_side_bypass.py`) reds on any direct kind-blind
read in a non-sanctioned `src/` module. It **reuses the write-side gate's scanner**
(a symmetry test proves runtime identity — no forked tree walk), asserts the three
read-primitive authority modules as *sanctioned* rather than silently skipping
them (with a non-vacuity test), and keys its allow-list by content descriptor
(no path blankets) with a **staleness twin-guard**: an entry that is no longer
needed reds until it is deleted.

**5. Two folded fixes.** `repair_lane_mismatch` no longer feeds raw frontmatter
text into the document-padding slot (it was duplicating the whole frontmatter into
the body on every legacy lane repair, #2921); and `backfill_runtime_state`'s
mission-id read is anchored on the PRIMARY leg (#2966 part-1 remainder).

## Effect on Existing Projects

- **Runtime / compatibility:** Behavior-preserving in the healthy case — for a
  materialized mission every migrated site resolves the same directory as before.
  The intended change is narrow: reads of **coord-partition** artifacts now raise
  instead of silently returning a primary-checkout substitute when the coordination
  branch is gone. Diagnostic/audit/SaaS readers are explicitly unchanged.
- **Upgrade / migration:** None. No data format, config, or CLI surface change.
- **Operator / reviewer impact:** A wrong-partition read now fails loudly instead
  of silently, and a future kind-blind read is caught by CI rather than by a
  reviewer noticing.

## Validation

- [x] Red-first per behavioral fix (each cluster proved which sites genuinely
      change behavior; a discriminating-negative test pins that primary-partition
      kinds stay primary-anchored even on a deleted-coord mission).
- [x] All nine work packages independently reviewed and approved
      (implement / review split; one WP was rejected and re-implemented for a real
      regression before approval).
- [x] Targeted gates green on the rebased tip: read gate + write gate + trio-seam
      + surface-audit + dead-symbols + terminology = **118 passed**; mission
      suites = **94 passed**.
- [x] `ruff` clean; `mypy --strict src/specify_cli src/charter src/doctrine` =
      **no issues in 1088 files**.
- [x] Docs freshness: `check_docs_freshness --ci` 0 errors; docs suite 602 passed.
- [x] Post-migration campsite pass closed every regression the migration itself
      caused (see below); each was classified against the pre-mission base before
      being fixed.
- [x] Follow-up work called out (see Follow-ups).

### Note on the campsite pass

Migrating the call sites left four *stale ratchets* behind — artifacts that
referenced the old shape: a gate allow-list still blessing resolver names nobody
imports anymore, two audit-inventory rows pointing at moved call sites, a public
export with no remaining importer, and eight test mocks patching helpers the
migration had removed. Each was verified to be **green before the mission and red
after** (i.e. genuinely caused here, not pre-existing) and then fixed by tightening
— shrinking allow-lists, unexporting, and repointing mocks at the real seam. No
assertion was weakened; the affected merge suites collect and pass the same count
as before the mission.

One honest pre-existing failure is **not** addressed here and stays red:
`test_no_raw_mission_spec_paths` (offender `cli/commands/accept.py:239`), which is
red on the pre-mission base too.

## Tickets / Contracts

| Ticket | Relationship |
|--------|--------------|
| #2922 | Closed — read-side whack-a-read migration (classification → migration → structural gate) |
| #1878 | Closed — parent of the read-side placement port |
| #2921 | Closed — `repair_lane_mismatch` frontmatter corruption |
| #2920 | Verified already fixed (pre-mission write+read seam hardening) |
| #2966 | Partially addressed — part-1 remainder (PRIMARY-leg mission-id read) fixed here; parts 2/3/4 deferred |
| #2964 | Deferred — `feature*` → `mission*` terminology migration, out of scope |
| #3011 | Filed during this mission — `rekey_inventory.py` is not round-trip-safe over hand-adjudicated audit rows |

## Mission Artifacts

- Spec: `kitty-specs/read-side-placement-seam-migration-01KYHP67/spec.md`
- Plan: `kitty-specs/read-side-placement-seam-migration-01KYHP67/plan.md`
- Tasks: `kitty-specs/read-side-placement-seam-migration-01KYHP67/tasks.md`
- Classification ledger: `docs/development/read-side-seam-classification.md`
- Acceptance matrix: `kitty-specs/read-side-placement-seam-migration-01KYHP67/acceptance-matrix.json` (12 criteria verified)
- Issue matrix: `kitty-specs/read-side-placement-seam-migration-01KYHP67/issue-matrix.md`
- Reviews: `kitty-specs/read-side-placement-seam-migration-01KYHP67/tasks/WP*/review-cycle-*.md`
- PR summary: this file (`pr-summary.md`)

## Follow-ups

- **#2966** parts 2/3/4 — remaining write-target / read-leg consolidation.
- **#2964** — `feature*` → `mission*` terminology migration (separate bulk-edit mission).
- **#3011** — make `rekey_inventory.py` round-trip-safe (it currently overwrites
  hand-adjudicated audit rows; the surface-audit edit in this PR was therefore made
  surgically, which the reviewer confirmed was correct).
