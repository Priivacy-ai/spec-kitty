# Tasks — Verdict-Seam Write-Side Unification

**Mission**: `verdict-seam-write-unification-01KZ9Q35`
**Branch**: `feat/verdict-seam-write-unification` (planning base == merge target)
**Topology**: `coord` (coordination branch materialized)
**Source of truth**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

> This file is the WP manifest. Each WP has a prompt at `tasks/WP##-slug.md`. Status lives in
> `status.events.jsonl`, not in frontmatter. Do **not** hand-edit lane state — use
> `spec-kitty agent tasks move-task`.

## The load-bearing ordering (spec C-008, D-PLAN-1)

Collapse-first. Harden the census so it can *prove* reader retirement → populate + serialize the
event authority (backfill + durability-add) → repoint **every** verdict reader atomically and
demote the `.md` → then the schema/placement/driver clean-up. The `.md` durability demote **never
precedes** the reader flip (D-PLAN-11). The shared `verdict_seam_census.yaml` **forbids parallel
lanes** across census-touching WPs, so the census chain is serial by dependency.

```
WP01 (census predicate) ──┬───────────────────────────────┐
                          ▼                                ▼
WP02 (backfill + durability-ADD)                    WP04 (vocab bridge + guard)
     │  .md still hard-error                               │
     ▼                                                     │
WP03 (durability via event log; emit_status_transition)    │
     └──────────────────┬────────────────────────────────┘
                        ▼
WP05 (ALL verdict readers die + .md demote)  ← SC-008 provenance interlock gates this
                        ▼
   ┌────────────────────┼───────────────────┐
   ▼                    ▼                    ▼
WP06 (schema:            WP07 (arbiter        WP09 (gate-artifact drivers
remove verdict field)    root threading)      + review-cycle driver relax)

WP08 (gate-artifact WRITE de-husk #2804/#2404) ── parallel lane ──▶ WP10 (flatten primitive #3219)
```

## Dependency table

| WP | Title | Concern | Deps | Subtasks |
|----|-------|---------|------|----------|
| WP01 | Census predicate hardening | IC-01 | — | T001–T005 |
| WP02 | Verdict-provenance backfill + provenance gate | IC-02a | WP01 | T006–T010 |
| WP03 | Durability via the event log (FR-008 add-leg owner) | IC-02b(add) | WP02 | T012–T015 |
| WP04 | Vocabulary bridge module + guard | IC-02b | WP01 | T016–T020 |
| WP05 | Reader collapse: all verdict readers die atomically | IC-03 | WP02, WP03, WP04 | T021–T029 |
| WP06 | Artifact schema: remove verdict field + resolver retirements | IC-04 | WP05 | T030–T035, T055 |
| WP07 | Arbiter root threading | IC-05 | WP05 | T036–T038 |
| WP08 | Gate-artifact WRITE surface de-husk (#2804/#2404) | IC-06a | — | T039–T043 |
| WP09 | Gate-artifact drivers + review-cycle driver relax | IC-06b + FR-014 | WP05 | T044–T048 |
| WP10 | Canonical `flatten_coordination_metadata` primitive (#3219) | IC-07 | WP08 | T049–T054 |

## Shared-file serialization (owner + out-of-map editors)

| Shared file | Owner (owned_files) | Out-of-map editors (serialized by deps) |
|---|---|---|
| `tests/architectural/verdict_seam_census.yaml` | WP01 | WP02 (backfill-module row), WP05 (two-verdict-function reader-row + merge-gate-leg shrink; `.latest`/`.from_file` kept active), WP06 (5 resolver-retire + 3 unrouted + 2 raw-join rows) |
| `tests/architectural/test_verdict_seam_census.py` | WP01 | **none** — WP01 authors all `_EXCLUDED_MODULE_REASONS` entries (backfill module + `verdict_vocab.py`) so neither WP02 nor WP04 edits the census test (squad F8) |
| `src/specify_cli/review/cycle.py` | WP05 | WP06 (docstring FR-011 reconcile; `_guard_feedback_source_provenance` re-express) |
| `src/specify_cli/review/artifacts.py` | WP05 | WP06 (remove `verdict` field from dataclass/`to_dict`/`from_dict`) |
| `tests/architectural/test_verdict_vocab_single_source.py` | WP04 | WP05 (remove its 2 allowlist entries when it sweeps cycle.py:794 + review_artifact_consistency.py) |
| `src/specify_cli/cli/commands/agent/tasks_move_task.py` | WP04 | WP07 (`_run_arbiter_override` main_repo_root threading) |
| `src/specify_cli/merge/executor.py` | WP08 | WP10 (converge the #3218 flatten call site onto the primitive) |

All out-of-map editors depend (transitively) on the owner, so no two lanes touch a shared file
concurrently. Rationale for each out-of-map edit is stated in the editor WP's prompt
(ownership-map-leeway).

## Requirement coverage (recommended `map-requirements` input)

| WP | Requirements |
|----|--------------|
| WP01 | FR-010; NFR-002; SC-006 |
| WP02 | FR-012; SC-008; SC-003 (partial) |
| WP03 | FR-008 (add-leg owner); NFR-001, NFR-004, NFR-005; SC-003 |
| WP04 | FR-005 |
| WP05 | FR-001 (safety guarantee via collapse), FR-002, FR-004, FR-013, FR-003 (two verdict fns retired; `.latest`/`.from_file` kept), FR-006 (reader rows), FR-008 (demote); SC-002, SC-003, SC-004 |
| WP06 | FR-001 (SC-001 verifications, T055), FR-003 (SC-007), FR-006 (resolver rows), FR-007, FR-011; SC-001, SC-007 |
| WP07 | FR-016 |
| WP08 | FR-009 (write surface); SC-005 |
| WP09 | FR-009 (drivers), FR-014 |
| WP10 | FR-015; SC-009 |

> **Requirement-ID note (report to orchestrator):** the tooling flattens the spec's sub-lettered IDs —
> `FR-011a → FR-011` (WP06) and `FR-011b → FR-016` (WP07). `spec.md`'s requirements table still spells
> `FR-011a`/`FR-011b` (verified this session); the WP frontmatter/bodies use the flattened registry IDs.
> Reconcile `spec.md` prose or confirm the registry mapping before finalize.
> **requirement_refs changes since first author:** WP02 dropped `FR-008` (add-leg moved to WP03/T013,
> squad F6); WP06 added `FR-001` (SC-001 verifications, T055).

## Carry-red pins (green, do not rewrite — spec C-002)

- `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` → greened by **WP08**.
- (`tests/regression/test_issue_3086_*` is OUT OF SCOPE — parallel session; must not regress.)

## Gates (from quickstart.md)

Run affected packages, not the full suite. `-n auto --dist loadfile` locally; real-port/daemon and
the durability matrix run `-n0`. Before push: `pytest tests/architectural/test_no_legacy_terminology.py`
and `ruff check . && mypy --strict` on touched surfaces.


---

## Work Package Sections

## WP01 — Census predicate hardening

- **Prompt**: `tasks/WP01-census-predicate-hardening.md`
- **Depends on**: —
- **Goal**: Extend the verdict-seam census AST to classify .from_dict/factory records; named exclusions. Lands first so the census can prove reader retirement.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T001 Census predicate hardening (WP01)
T002 Census predicate hardening (WP01)
T003 Census predicate hardening (WP01)
T004 Census predicate hardening (WP01)
T005 Census predicate hardening (WP01)

## WP02 — Verdict-provenance backfill + gate

- **Prompt**: `tasks/WP02-verdict-provenance-backfill.md`
- **Depends on**: WP01
- **Goal**: Idempotent backfill of historical .md verdicts into the event log (append_events_atomic_verified, historical timestamp) + provenance gate. Precondition for the collapse.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T006 Verdict-provenance backfill + gate (WP02)
T007 Verdict-provenance backfill + gate (WP02)
T008 Verdict-provenance backfill + gate (WP02)
T009 Verdict-provenance backfill + gate (WP02)
T010 Verdict-provenance backfill + gate (WP02)

## WP03 — Durability via the event log

- **Prompt**: `tasks/WP03-durability-via-event-log.md`
- **Depends on**: WP02
- **Goal**: Add emit_status_transition as the authoritative verdict-durability write; keep the .md commit hard-error here (demote is WP05).
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T012 Durability via the event log (WP03)
T013 Durability via the event log (WP03)
T014 Durability via the event log (WP03)
T015 Durability via the event log (WP03)

## WP04 — Vocabulary bridge module + guard

- **Prompt**: `tasks/WP04-vocabulary-bridge-module.md`
- **Depends on**: WP01
- **Goal**: One canonical verdict-vocabulary bridge + non-vacuous single-source arch-guard (scoped {approved,rejected}; overrides never synthesize a verdict).
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T016 Vocabulary bridge module + guard (WP04)
T017 Vocabulary bridge module + guard (WP04)
T018 Vocabulary bridge module + guard (WP04)
T019 Vocabulary bridge module + guard (WP04)
T020 Vocabulary bridge module + guard (WP04)

## WP05 — Reader collapse: all verdict readers die atomically

- **Prompt**: `tasks/WP05-reader-collapse.md`
- **Depends on**: WP02, WP03, WP04
- **Goal**: Repoint EVERY verdict reader to the event snapshot, retire the artifact verdict-parser family, delete the frontmatter readers, demote the .md commit. MUST NOT SPLIT (atomicity — splitting reopens the fail-open).
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T021 Reader collapse: all verdict readers die atomically (WP05)
T022 Reader collapse: all verdict readers die atomically (WP05)
T023 Reader collapse: all verdict readers die atomically (WP05)
T024 Reader collapse: all verdict readers die atomically (WP05)
T025 Reader collapse: all verdict readers die atomically (WP05)
T026 Reader collapse: all verdict readers die atomically (WP05)
T027 Reader collapse: all verdict readers die atomically (WP05)
T028 Reader collapse: all verdict readers die atomically (WP05)
T029 Reader collapse: all verdict readers die atomically (WP05)

## WP06 — Artifact schema: remove verdict field + resolver retirements

- **Prompt**: `tasks/WP06-artifact-schema-remove-verdict.md`
- **Depends on**: WP05
- **Goal**: Remove the verdict field from ReviewCycleArtifact (schema); new serialized no-verdict-field assertion; retire the 5 census resolver rows; reconcile docstrings.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T030 Artifact schema: remove verdict field + resolver retirements (WP06)
T031 Artifact schema: remove verdict field + resolver retirements (WP06)
T032 Artifact schema: remove verdict field + resolver retirements (WP06)
T033 Artifact schema: remove verdict field + resolver retirements (WP06)
T034 Artifact schema: remove verdict field + resolver retirements (WP06)
T035 Artifact schema: remove verdict field + resolver retirements (WP06)
T055 Artifact schema — SC-001 co-resolution + AST invariant (WP06)

## WP07 — Arbiter root threading

- **Prompt**: `tasks/WP07-arbiter-root-threading.md`
- **Depends on**: WP05
- **Goal**: Thread the caller-resolved main_repo_root into persist_arbiter_decision so a coord-topology override resolves the COORD root; repoint the arbiter verdict reader.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T036 Arbiter root threading (WP07)
T037 Arbiter root threading (WP07)
T038 Arbiter root threading (WP07)

## WP08 — Gate-artifact WRITE surface de-husk (#2804/#2404)

- **Prompt**: `tasks/WP08-gate-artifact-write-dehusk.md`
- **Depends on**: —
- **Goal**: Single write surface for acceptance-matrix (accept→COORD, suppress the PRIMARY husk producer); green the existing test_issue_2804 pin. Parallel lane.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T039 Gate-artifact WRITE surface de-husk (#2804/#2404) (WP08)
T040 Gate-artifact WRITE surface de-husk (#2804/#2404) (WP08)
T041 Gate-artifact WRITE surface de-husk (#2804/#2404) (WP08)
T042 Gate-artifact WRITE surface de-husk (#2804/#2404) (WP08)
T043 Gate-artifact WRITE surface de-husk (#2804/#2404) (WP08)

## WP09 — Gate-artifact drivers + review-cycle driver relax

- **Prompt**: `tasks/WP09-gate-artifact-drivers.md`
- **Depends on**: WP05
- **Goal**: Guarantee matrix drivers registered before the squash; fix the .md→.json seed drift; downgrade the review-cycle driver to non-aborting (FR-014).
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T044 Gate-artifact drivers + review-cycle driver relax (WP09)
T045 Gate-artifact drivers + review-cycle driver relax (WP09)
T046 Gate-artifact drivers + review-cycle driver relax (WP09)
T047 Gate-artifact drivers + review-cycle driver relax (WP09)
T048 Gate-artifact drivers + review-cycle driver relax (WP09)

## WP10 — Canonical flatten_coordination_metadata primitive (#3219)

- **Prompt**: `tasks/WP10-flatten-coordination-primitive.md`
- **Depends on**: WP08
- **Goal**: Extract the 3-mutation flatten primitive; converge the executor(#3218)/doctor/mission-close sites; fix the mission-close partial-flatten bug; non-vacuous single-source guard.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`):
T049 Canonical flatten_coordination_metadata primitive (#3219) (WP10)
T050 Canonical flatten_coordination_metadata primitive (#3219) (WP10)
T051 Canonical flatten_coordination_metadata primitive (#3219) (WP10)
T052 Canonical flatten_coordination_metadata primitive (#3219) (WP10)
T053 Canonical flatten_coordination_metadata primitive (#3219) (WP10)
T054 Canonical flatten_coordination_metadata primitive (#3219) (WP10)
