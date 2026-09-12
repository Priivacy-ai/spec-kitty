# Tasks: DRG Reachability Metric & Orphan Wiring

**Mission**: `drg-reachability-metric-wiring-01KZS5VR` | **Branch**: `fix/drg-reachability-metric-wiring`
**Topology**: coord (single lane — WPs are strictly sequential; see coupling note)

## Decomposition rationale

The plan's three concerns (IC-01 wiring, IC-02 metric+pins, IC-03 curation) collapse to **two work
packages** because of the shared-file coupling the post-plan squad flagged: `tests/doctrine/drg/
test_reachability.py` is touched by *both* the wiring pin-moves and the new companion guard, and both depend
on the graph change in `extractor.py`. Disjoint `owned_files` (finalize-tasks requirement) + green-at-each-WP
boundary therefore force the entire coupled code change into **one atomic WP**, with residual curation +
ticket closure as a **second, docs-only WP**. This is the correct resolution of the shared-surface coupling.

- **WP01** — the atomic code change: author the 6 edges, regenerate the graph, reconcile every moved pin,
  add the `_ACTION_UNREACHABLE_SHIPPED` companion guard + partition + mechanical ledger coverage, ratchet the
  ceiling. Sequential root.
- **WP02** — residual curation (full enumeration of the 75), follow-up filing, CHANGELOG, ticket closure.
  Depends on WP01 (reflects the final pinned sets).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author 6 curated edges in `_CURATED_ARTIFACT_EDGES` with traced rationale comments | WP01 | |
| T002 | Regenerate `packs/built-in/*.graph.yaml` deterministically (byte-identical on re-run) | WP01 | |
| T003 | Behavioral red-first reach assertions per wired node + delete-edge negative test | WP01 | |
| T004 | Reconcile incidence pins (`test_extractor_projection.py`) + numbered-ledger entry + ceiling ratchet | WP01 | |
| T005 | Reconcile reachability pins (`test_reachability.py`) with correct per-member accounting | WP01 | |
| T006 | Add `_ACTION_UNREACHABLE_SHIPPED` guard + partition subsets + by-design-kind filter + exclusion test | WP01 | |
| T007 | Mechanical ledger-coverage test for the new pin + wiring-table rows + `inventory_lockfile --write` | WP01 | |
| T008 | Full DRG suite + ruff/mypy green; verify C-003 no-new-orphan + regeneration determinism | WP01 | |
| T009 | Full enumeration/disposition of the 75-member residual in the #1923 residual doc | WP02 | |
| T010 | File 3 follow-up issues (systemic projection; consolidation; quadruple-a/DIRECTIVE_041) | WP02 | |
| T011 | CHANGELOG entry | WP02 | |
| T012 | Prepare #3009 + #1923 closure notes (reconciliation + doctrine-doctor CI-only) | WP02 | |
| T013 | Terminology guard + final verification | WP02 | |

## Work Packages

### WP01 — Wiring + companion metric + pin reconciliation (atomic code change)

- **Goal**: Author the six genuine edges, regenerate the graph, add the action-only reachability companion
  guard (88→75) with its 34-dead/41-profile-delivered partition, reconcile every moved pin with a
  wiring-table ledger row, and keep every existing DRG guard green.
- **Priority**: P1 (foundational; MVP).
- **Independent test**: `PWHEADLESS=1 .venv/bin/python -m pytest tests/doctrine/drg/ tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py -q` green; each wired node proven unreachable→reachable behaviorally; deleting a genuine edge names the URN.
- **Subtasks**: T001, T002, T003, T004, T005, T006, T007, T008.
- **Prompt**: [WP01-wiring-and-companion-metric.md](tasks/WP01-wiring-and-companion-metric.md)
- **Dependencies**: none.
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-010.
- **Risks**: D18 ledger surface (now partly mechanized); partition totality/disjointness; determinism;
  RECONCILE must only shrink `_ACTIVATED_BUT_ORPHANED` (C-003).

### WP02 — Residual curation, follow-up filing, ticket closure (docs)

- **Goal**: Give every member of the 75-node pinned residual a disposition; truth-up the #1923 residual doc
  (retire rtk, promote the genuinely-reachable, atomic-design as inert-edge residual, human-in-charge as
  incidence-only); file the three deferred follow-ups; CHANGELOG; close #3009 + #1923 with reconciled
  evidence.
- **Priority**: P2 (closure).
- **Independent test**: the residual doc's set matches the graph's true residual; the retired entry is absent
  from disk+graph; each honest residual carries a rationale; the follow-up issues exist.
- **Subtasks**: T009, T010, T011, T012, T013.
- **Prompt**: [WP02-residual-curation-and-closure.md](tasks/WP02-residual-curation-and-closure.md)
- **Dependencies**: WP01.
- **Requirements**: FR-008, FR-009, FR-011.
- **Risks**: must match the graph's true residual exactly; no valid-artifact deletion (NFR-002).

## MVP

WP01 is the MVP — it delivers the guard + the genuine wiring + green gates. WP02 is closure.
