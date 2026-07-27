---
affected_files: []
cycle_number: 2
mission_slug: topology-aware-legacy-warning-01KWQ8WH
reproduction_command:
reviewed_at: '2026-07-04T20:09:34Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

# WP01 Review — Cycle 1 (Independent reviewer: reviewer-renata / claude)

## Verdict: RETURN FOR ONE COMPLETION ITEM (code is otherwise APPROVED)

The implementation, tests, docs, and all quality gates PASS (details below).
The ONLY blocker to approval is an unresolved Gate-4 mission artifact that the
CLI enforces on `move-task --to approved`:

    ERROR: issue-matrix.md has unresolved entries. Unknown: #2218, #2351

### Required action (single fix)

Fill `kitty-specs/topology-aware-legacy-warning-01KWQ8WH/issue-matrix.md`
(replace the `<fill at WP-implementation time>` / `unknown` placeholders) with
terminal verdicts, then re-submit for review:

- **#2351** — Title: "Once-per-mission legacy-topology warning over-fires on
  intentional coordination-less (single_branch/lanes) missions."
  Verdict: `fixed`. Evidence: commit `e46347bd4` — topology-aware
  `_warrants_legacy_warning` classifier gates only the emit; 20 tests green.
- **#2218** — Referenced in spec.md only as pre-existing context (the
  MissionTopology-SSOT design where single_branch/lanes deliberately never
  write `coordination_branch`; ADR docs/adr/3.x/2026-06-22-1-mission-topology-ssot.md).
  This mission does NOT modify that behavior — it depends on it and the
  routing-invariance test verifies it. Recommended verdict:
  `verified-already-fixed` (evidence: `test_legacy_routing_and_write_contract_unaffected_by_topology`
  + the ADR). If the orchestrator scopes #2218 differently, use another
  terminal verdict — but it must not remain `unknown`.

### Process gap to flag (not implementer's fault)

`issue-matrix.md` is NOT in WP01's `owned_files`, yet the approval gate requires
editing it. It is a mission-level artifact edited in the coord/main checkout,
not the lane worktree. The orchestrator should fill it there (or add it to the
lane write-scope). This is a planning/gate-coupling gap worth flagging upstream.

## What was verified and PASSES (no code changes required)

- **C-005 (split, don't repurpose):** `_is_legacy_mission` (:200-230), routing
  (`legacy_mode` at :758), `_legacy_mode` (:872), and the write-contract branch
  (:950 `primary_checkout_append`) are all byte-for-byte unchanged. Only the
  warning gate + message + runbook changed.
- **C-001 (reader-choice trap):** classifier reads topology via the
  non-deriving `stored_topology_from_meta` (function-local import), NOT
  `read_topology`/`resolve_topology`/`_derive_topology`. Absent/malformed → None
  → warns (fail-closed default). `flattened` read inline via `meta.get`.
- **Message:** now cites BOTH `docs/migrations/legacy-to-coordination.md` AND
  `spec-kitty migrate backfill-topology`. Marker/idempotency logic untouched.
- **Tests non-vacuous:** warn cases assert the "legacy topology" line PRESENT +
  both citation strings + marker written; no-warn cases assert it ABSENT +
  marker NOT written. Full matrix: genuine-legacy, single_branch, lanes,
  flattened, coord, lanes_with_coord, malformed/inadmissible topology.
  Plus mandatory routing-invariance (spies append_event_log target — identical
  across all three shapes) and backfill-suppression (clears marker, backfills
  topology, re-runs → no warning) tests. 20 passed.
- **Gates:** ruff clean on all changed files; terminology gate green
  (3 passed); no new suppressions in production code (only one narrow,
  justified `# type: ignore[attr-defined]` on a test spy). mypy `--strict`
  adds ZERO new errors (the 3 pre-existing `ulid`/seam-return errors are
  identical on the base branch and are an environment stub artifact).
- **Scope:** diff confined to the 4 `owned_files`.
