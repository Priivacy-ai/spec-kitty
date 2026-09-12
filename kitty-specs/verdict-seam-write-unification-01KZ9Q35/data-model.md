# Data Model — Verdict-Seam Write-Side Unification

Entities, invariants, and state. This mission changes *authority* and *placement*, not schemas —
so the "model" here is the authority/placement contract, not new tables.

## Entities & authority

| Entity | Home (authority) | Vocabulary | Role after this mission |
|---|---|---|---|
| **Current verdict** | `ReviewResult` slot on the reducer snapshot (`status.events.jsonl` reduced) | `{approved, changes_requested}` | **Sole** authority for "is this WP approved?" |
| **Review-cycle artifact** (`review-cycle-N.md`) | file on COORD partition (coord topology) / PRIMARY otherwise | prose only — **no verdict field** | Write-only prose (body, affected files, repro); never read for verdict |
| **Vocabulary bridge** | one canonical surface beside `status/models.py` | maps `{approved, rejected, arbiter_override, approved_after_orchestrator_fix} ↔ {approved, changes_requested}` | Single source; inline equivalence forbidden elsewhere |
| **Verdict-seam census row** | `verdict_seam_census.yaml` | `category/module/function/status/retiring_fr` | Derived from all-`src/` AST; reds on growth AND shrinkage |
| **Provenance-gate finding** | computed (not persisted) | `{wp_id, has_md_verdict, has_event_slot}` | Blocks reader deletion while any WP has `.md` verdict + no event slot |
| **Gate artifacts** (`acceptance-matrix.json`, `issue-matrix.json`) | COORD partition, single write surface | JSON rows | Authored once (COORD); COORD-authoritative at merge |

## Invariants (checkable)

- **INV-1 (single authority)**: exactly one home answers the verdict question — the reducer snapshot.
  No consumer resolves the verdict from `.md` frontmatter. *(SC-002; census + `test_2093` ratchet)*
- **INV-2 (structural, not disciplinary)**: the written `review-cycle-N.md` carries no field the
  census classifies as a verdict. *(SC-007)*
- **INV-3 (one directory)**: every read/write/gate/display/dashboard path resolves one identical
  review-cycle directory — COORD under coord topology, PRIMARY otherwise; none from a caller-supplied
  dir. *(SC-001)*
- **INV-4 (no stranded history)**: every WP with a terminal verdict has that verdict in the event log
  before any frontmatter reader is deleted. *(SC-008; provenance gate)*
- **INV-5 (durability)**: two concurrent verdicts → two durable event records or one explicit refusal;
  no inter-process lock across a git subprocess; exactly one authoritative durability call per verdict.
  *(SC-003; NFR-001/004)*
- **INV-6 (single write surface for gate artifacts)**: no PRIMARY-partition acceptance-matrix is
  authored under a coordination topology. *(SC-005)*
- **INV-7 (census completeness)**: a new writer/resolver/reader — including `.from_dict`/helper — reds
  the census. *(SC-006)*

## State transition — a WP verdict (post-mission)

```
reviewer/arbiter records verdict
   │  emit_status_transition(review_result=…)      ← authoritative durable write (event log)
   ▼
reducer snapshot: ReviewResult slot populated       ← the one authority
   │  (best-effort) write review-cycle-N.md prose    ← no verdict field; commit may warn, not error
   ▼
every reader (approval guard, merge gate, dashboard, fix-mode) → event_sourced_review_result
```

`ReviewResultLookup` three-way (preserved): `absent` (`slot_present=False`) / `damaged`
(`slot_present=True, result=None`) / `present`. Safety-gate readers fail closed on `damaged`.

## Backfill state (one-time, idempotent)

```
for each mission/WP with a terminal .md verdict and no event review_result slot:
    reduce the .md verdict → emit_status_transition (idempotent key: mission,wp,verdict,cycle)
provenance gate: assert zero (has_md_verdict ∧ ¬has_event_slot)  → unblocks reader deletion
```
