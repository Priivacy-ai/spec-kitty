# Contract — Negative-Invariant Provenance and Deferral

**Discharges**: FR-002, FR-003, FR-004, FR-005, FR-010, FR-014, **FR-015**
**Surfaces**: `acceptance/matrix.py`, `acceptance/gates_core.py`, `acceptance/post_consolidation.py`

---

## C1 — Provenance is mandatory on any judgement, with one typed legacy escape

**Given** a negative invariant with a `result` other than `pending` **and** `provenance_origin`
of `recorded`
**When** the acceptance matrix is validated
**Then** it must carry both `verified_ref` and `verified_surface_kind`
**And** a provenance-less `recorded` result is reported as a validation error.

**Given** a negative invariant with `provenance_origin` of `legacy_unrecorded` (the sentinel the
FR-014 migration writes for results recorded before provenance existed)
**When** the matrix is validated
**Then** null `verified_ref` and null `verified_surface_kind` are **accepted** for that origin only
**And** `legacy_unrecorded` is a `provenance_origin` value, never a `TopologySurface` member — the
surface enum's anti-phantom rule forbids an unresolvable member.

*This clause and data-model NI-1 must state the same rule; an earlier revision left C1
unconditional while NI-1 carried the escape, giving `validate_matrix_evidence` two contradictory
specs. Reconciled 2026-07-23.*

---

## C2 — Provenance round-trips

**Given** an invariant carrying provenance
**When** the matrix is serialised and re-read
**Then** `verified_ref`, `verified_surface_kind`, `deferred_reason` and `deferred_to_phase`
survive unchanged.

---

## C3 — A recorded judgement is never overwritten

**Given** an invariant already recorded as `confirmed_absent`, `still_present` or
`verification_error`
**When** any later gate runs in any phase
**Then** the recorded result and its provenance are preserved verbatim
**And** no re-execution occurs.

*Status*: already landed (`b918e66df`). This contract pins it as a ratchet so it cannot regress.

---

## C4 — Unjudgeable pending invariants defer

**Given** a `pending` invariant whose subject cannot exist in the current surface
**When** the acceptance gate runs
**Then** its result becomes `deferred_to_consolidation`
**And** `deferred_reason` names why
**And** `deferred_to_phase` is `POST_CONSOLIDATION`
**And** the result is **never** `still_present`.

---

## C5 — Deferral does not block acceptance

**Given** a mission whose only unresolved invariants are `deferred_to_consolidation`
**When** acceptance runs
**Then** `overall_verdict` does not compute `fail` on their account
**And** acceptance is not blocked by "criteria or invariants have not been verified".

*Failure this prevents*: the renamed failure mode — deferral must not simply relocate the block
from `fail` to `pending`.

---

## C6 — Deferral is honoured post-consolidation

**Given** an invariant recorded `deferred_to_consolidation`
**When** the post-consolidation verification op runs on the consolidated mission branch
**Then** it is judged against that consolidated tree
**And** its outcome is written back with `verified_surface_kind = CONSOLIDATED` and the
consolidation commit as `verified_ref`.

---

## C7 — A violated deferred invariant fails the op, NOT the consolidation

**Given** a `deferred_to_consolidation` invariant that proves `still_present` on the consolidated tree
**When** the post-consolidation verification op runs
**Then** **the op** fails and names the specific invariant
**And** lane consolidation itself is unaffected — it has already completed cleanly
**And** no rollback of the consolidation is attempted.

*Why the separation is load-bearing*: folding this into `spec-kitty merge` would introduce a new
abort trigger into the consolidation transaction at exactly the time IC-06 is collapsing its two
compensators into one. Keeping verification as a separate on-branch op after consolidation means
there is no new abort path, nothing half-applied, and no interaction with the rollback rework.
The blast radius is contained because the consolidated tree is the mission/PR branch, not
`origin/main` — a violation blocks the PR, which is where it should block.

---

## C8 — Single authoritative copy

**Given** a mission on any topology
**When** the acceptance matrix is authored
**Then** exactly one file exists, at its declared home
**And** no primary-scaffold second copy is created.

*Failure this prevents*: the provenance fields added by C1 diverging between two copies.

---

## C9 — Scoped absence checks remain judgeable pre-consolidation

**Given** an invariant using `grep_absence` scoped to a source directory that already exists on
the primary surface
**When** acceptance runs pre-consolidation
**Then** it is judged normally rather than deferred.

*Rationale*: this shape is verifiable pre-consolidation and is the one #1834 never broke. It is the
preferred shape for this mission's own invariants — see quickstart.md.


---

## C10 — Archiving refuses to hide a live problem

**Given** a mission that is not terminal (`merged` / `canceled`)
**When** an operator attempts to archive it
**Then** the operation is refused with a stated reason (AM-1).

**Given** a terminal mission with any invariant recorded `still_present`
**When** archiving is attempted
**Then** it is refused (AM-2) — a violation is resolved, not filed away.

**Given** a terminal mission with no `still_present` invariant
**When** it is archived
**Then** the `ArchivedMission` record names `archived_by`, `archived_at` and `reason`; the mission
is excluded from live validation; and it stays enumerable (AM-3).

**Given** the FR-014 migration encountering a mission it cannot bring onto the schema
**When** the migration runs
**Then** it does **not** auto-archive (AM-4) — archiving is operator-invoked only.
