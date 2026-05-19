---
work_package_id: WP03
title: Writer + retrospective lifecycle events + reducer fixtures
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-013
- FR-014
- FR-021
- FR-025
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main. Execution worktrees are allocated per computed lane from lanes.json after finalize-tasks.
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Foundation
assignee: ''
agent: claude
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/writer.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/retrospective/writer.py
- src/specify_cli/retrospective/events.py
- src/specify_cli/retrospective/summary.py
- tests/retrospective/test_writer.py
- tests/retrospective/test_events.py
- tests/retrospective/test_reducer_fixtures.py
- tests/retrospective/fixtures/event_logs/**
role: implementer
tags: []
---

# Work Package Prompt: WP03 — Writer + Retrospective Lifecycle Events + Reducer Fixtures

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Persist generated records to disk with overwrite/update/error semantics. Emit `RetrospectiveCaptured` and `RetrospectiveCaptureFailed` events (reuse existing wire types if already exposed on the frozen `spec_kitty_events` public surface; else add additively in the local emit path). Prove FR-021's byte-identical reducer guarantee with a fixture set under `tests/retrospective/fixtures/event_logs/`. Tighten `summary` to distinguish 4 record states.

## Context

- Record schema and merge semantics: [data-model.md § RetrospectiveRecord](../data-model.md#retrospectiverecord) and [§ Merge semantics](../data-model.md#merge-semantics-retrospect-create---update).
- Event payloads: [contracts/retrospective-events.contract.md](../contracts/retrospective-events.contract.md).
- Frozen surface for `spec_kitty_events`: FR-024 architectural contract. Importing from `spec_kitty_events.models.*` would violate it. Read the top-level public surface and decide whether `RetrospectiveCaptured` exists already.
- Reducer no-op guarantee: [contracts/retrospective-events.contract.md § Reduction guarantees](../contracts/retrospective-events.contract.md#reduction-guarantees-fr-021).

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved via `lanes.json` after `finalize-tasks`.

## Subtasks

### T013 — `writer.write_record(record, mode)` with three modes

**Purpose**: Persist `RetrospectiveRecord` to disk with `error` (default), `overwrite`, and `update` modes.

**Steps**:

1. Extend `src/specify_cli/retrospective/writer.py` with `write_record(record: RetrospectiveRecord, *, mode: Literal["error","overwrite","update"], repo_root: Path) -> Path`.
2. Canonical path: `.kittify/missions/<mission_id>/retrospective.yaml`. Create parent directory if missing.
3. **mode="error"**: if path exists, raise `RecordExistsError(path)` with structured message pointing at `--overwrite` / `--update` flags. Otherwise write.
4. **mode="overwrite"**: write unconditionally. Preserve nothing from prior record.
5. **mode="update"**: load existing record (validate it round-trips through `validate_record`). Merge per [data-model.md merge semantics](../data-model.md#merge-semantics-retrospect-create---update):
   - `helped/not_helpful/gaps/proposals`: dedupe by `(category, summary.lower())`. New entries append with newly-minted ids that don't collide with existing ones.
   - `evidence_refs`: dedupe by `(kind, path, range, url)`. New entries append with newly-minted ids.
   - `policy_source`: replace wholesale. If changed from prior, record prior in `provenance.prior_policy_resolved_from` (via the merged `provenance` snapshot in `provenance_history`).
   - `provenance`: replace with new; append prior to `provenance_history` (most-recent-first).
   - Recompute `findings_status` from final lists.
6. Write atomically: write to `<path>.tmp` then rename. Use `os.fsync` on the file before rename.
7. Format: YAML via `ruamel.yaml` with `preserve_quotes=True` and a width that doesn't wrap long string fields awkwardly.

**Files**:
- `src/specify_cli/retrospective/writer.py` (extend, ~200 lines added)

**Validation**:
- [ ] mode="error" raises on existing path; writes cleanly on absent path
- [ ] mode="overwrite" replaces wholesale
- [ ] mode="update" merges per spec; provenance_history accumulates
- [ ] Atomic write: kill -9 between `tmp` and `rename` leaves no partial record at the canonical path

---

### T014 — Enforce `synthesize_fabricate ⇒ ran_no_findings` invariant

**Purpose**: Writer refuses to persist any record where `provenance.kind == "synthesize_fabricate"` AND `findings_status != "ran_no_findings"`.

**Steps**:

1. Add a validation step at the top of `write_record` (after `validate_record` from WP02 runs):
   ```python
   if record.provenance.kind == "synthesize_fabricate" and record.findings_status != "ran_no_findings":
       raise RecordValidationError(
           "synthesize_fabricate provenance MUST imply findings_status=ran_no_findings; "
           "got findings_status={record.findings_status!r}. See data-model.md invariants."
       )
   ```
2. This is a defense-in-depth check — `validate_record` from WP02 also enforces it. The writer enforcement guarantees we never persist a violating record even if upstream validation is skipped.
3. Unit test: construct a record with `provenance.kind="synthesize_fabricate"` and `findings_status="has_findings"` → writer rejects.

**Files**:
- `src/specify_cli/retrospective/writer.py` (extend, ~15 lines added)

**Validation**:
- [ ] Bad combination rejected with clear error message
- [ ] Good combination (`synthesize_fabricate` + `ran_no_findings`) writes cleanly

---

### T015 — Add `RetrospectiveCaptured` + `RetrospectiveCaptureFailed` event types

**Purpose**: Emit lifecycle events that join the canonical event log additively.

**Steps**:

1. **First**: inspect the `spec_kitty_events` public surface to determine whether `RetrospectiveCaptured` / equivalent already exists:
   ```bash
   python -c "import spec_kitty_events; print([n for n in dir(spec_kitty_events) if 'etrospec' in n.lower()])"
   grep -rn "RetrospectiveCaptured\|RetrospectiveCaptureFailed" $(python -c "import spec_kitty_events, pathlib; print(pathlib.Path(spec_kitty_events.__file__).parent)")
   ```
   - If found at top level: REUSE with additive `policy_source` field. Document the import path in this WP's review notes.
   - If found only at a sub-path: do NOT import from sub-path (violates FR-024). Treat as not-exposed and proceed to step 2.
   - If not found: add new event types in the local emit path.

2. Create `src/specify_cli/retrospective/events.py` with the canonical envelopes per [contracts/retrospective-events.contract.md](../contracts/retrospective-events.contract.md):
   ```python
   @dataclass
   class RetrospectiveCaptured:
       schema_version: int = 1
       event_id: str       # ULID
       lamport: int
       at: str             # RFC 3339
       actor: Actor
       mission_id: str
       mission_slug: str
       wp_id: None = None
       force: bool = False
       execution_mode: Literal["worktree", "main"]
       findings_status: Literal["has_findings","ran_no_findings"]
       record_path: str
       generator_version: str
       policy_source: dict[str, str]
       provenance_kind: ProvenanceKind
       proposal_count: int
       evidence_ref_count: int
       # serialize to JSON envelope of the canonical event log
   ```
   And the `RetrospectiveCaptureFailed` analog with `failure_category`, `failure_message`, `remediation_hint`, `attempted_provenance_kind`, `missing_artifacts`.

3. Provide an `emit_captured(record, repo_root, *, provenance_kind, actor) -> Event` helper and `emit_capture_failed(...) -> Event` helper. Use the existing per-mission `kitty-specs/<mission_slug>/status.events.jsonl` writer infrastructure (do NOT re-implement JSONL append).

4. Round-trip test: serialize an event, write to JSONL, read it back via the canonical reader — payload byte-equal after `sort_keys` normalization.

**Files**:
- `src/specify_cli/retrospective/events.py` (new, ~180 lines)

**Validation**:
- [ ] Public-surface inspection result documented in commit message
- [ ] Both event types serialize/round-trip cleanly
- [ ] No imports from `spec_kitty_events.models.*` or other sub-paths (FR-024 architectural test stays green)

---

### T016 — Reducer no-op fixtures (FR-025)

**Purpose**: Lock the FR-021 guarantee with concrete fixtures.

**Steps**:

1. Create `tests/retrospective/fixtures/event_logs/` with two fixture pairs:

   **Fixture A — historical baseline**:
   - `historical-no-retrospective.events.jsonl` — a real-shape JSONL with WP lifecycle events (claimed, in_progress, for_review, in_review, approved, done, etc.) and a `MissionCompleted` at the end. NO retrospective events.
   - `historical-no-retrospective.snapshot.json` — the materialized `status.json` snapshot expected from the reducer.

   **Fixture B — with retrospective events appended**:
   - `historical-with-retrospective.events.jsonl` — same as A, with `RetrospectiveCaptured` and `RetrospectiveCaptureFailed` events appended.
   - `historical-with-retrospective.snapshot.json` — same lane/lifecycle state as A; PLUS new top-level keys for retrospective state (e.g. `retrospective.last_captured_at`, `retrospective.last_failure`). Lane and lifecycle keys MUST be byte-identical to A's snapshot.

2. Create `tests/retrospective/test_reducer_fixtures.py`:
   - `test_baseline_reduces_byte_identically_pre_and_post_mission()` — reduce fixture A; assert it matches the recorded snapshot.
   - `test_retrospective_events_are_lane_state_noops()` — reduce fixture A and fixture B; assert lane/lifecycle keys are byte-identical between snapshots; assert additive retrospective keys appear only in B.

3. If new top-level snapshot keys are added, document them in `data-model.md` (already covered in the contracts file — confirm the names match).

**Files**:
- `tests/retrospective/fixtures/event_logs/historical-no-retrospective.events.jsonl` (new, ~40 lines)
- `tests/retrospective/fixtures/event_logs/historical-no-retrospective.snapshot.json` (new, ~30 lines)
- `tests/retrospective/fixtures/event_logs/historical-with-retrospective.events.jsonl` (new, ~50 lines)
- `tests/retrospective/fixtures/event_logs/historical-with-retrospective.snapshot.json` (new, ~40 lines)
- `tests/retrospective/test_reducer_fixtures.py` (new, ~120 lines)

**Validation**:
- [ ] Fixture A and B share byte-identical lane/lifecycle state in their snapshots
- [ ] The reducer treats both retrospective event types as no-ops for lane state
- [ ] Snapshot diff between A and B is exactly the additive retrospective keys

---

### T017 — Tighten `summary` to distinguish 4 record states (FR-013)

**Purpose**: `spec-kitty retrospect summary` remains read-only but learns to distinguish `has_findings` / `ran_no_findings` / `missing` (no record on disk) / `failed` (most recent `Failed` not followed by a `Captured`).

**Steps**:

1. Extend `src/specify_cli/retrospective/summary.py` with a per-mission classifier:
   ```python
   def classify_mission_record(feature_dir: Path) -> Literal["has_findings","ran_no_findings","missing","failed"]:
       record_path = ...
       if record_path.exists():
           record = read_record(record_path)
           return record.findings_status
       last_failed = most_recent_event(feature_dir, "RetrospectiveCaptureFailed")
       last_captured = most_recent_event(feature_dir, "RetrospectiveCaptured")
       if last_failed and (not last_captured or last_failed.lamport > last_captured.lamport):
           return "failed"
       return "missing"
   ```
2. Update the `summary` JSON output shape to include `findings_status` per mission and `policy_source` (snapshot from the most recent `RetrospectiveCaptured` event).
3. Backward compatibility: existing `summary` output keys preserved; only new keys are added (NFR-007 additive).
4. Tests: cover all four states with fixtures.

**Files**:
- `src/specify_cli/retrospective/summary.py` (extend, ~80 lines added)
- `tests/retrospective/test_writer.py` and `tests/retrospective/test_events.py` (full coverage of T013-T017, ~350 lines total)

**Validation**:
- [ ] Summary distinguishes all four states correctly
- [ ] No-record + no-Failed-event → `missing`
- [ ] No-record + recent Failed → `failed`
- [ ] Record on disk → reflects record's own `findings_status`
- [ ] Coverage on writer.py, events.py, summary.py ≥ 90%

---

## Definition of Done

- [ ] All 5 subtasks complete
- [ ] `uv run pytest tests/retrospective/ -q` exits 0
- [ ] `uv run ruff check src/specify_cli/retrospective/ tests/retrospective/` exits 0
- [ ] `uv run pytest tests/architectural/test_events_tracker_public_imports.py -q` exits 0 (FR-024 frozen surface stays intact)
- [ ] Coverage on `src/specify_cli/retrospective/{writer,events,summary}.py` ≥ 90%
- [ ] Atomic write verified: deliberate kill during write leaves no partial record
- [ ] Reducer fixtures committed; snapshots byte-stable

## Risks & Reviewer Guidance

- **FR-024 risk**: importing from `spec_kitty_events.models.*` violates the frozen public surface. The architectural test (`tests/architectural/test_events_tracker_public_imports.py`) catches this. Reviewer must verify no such imports were added.
- **Merge semantics risk**: `--update` mode is non-trivial. Reviewer should walk a hand-traced merge case (e.g. add a Finding with category `process` and summary `"Same Thing"` to a record that already has it) and confirm dedupe behavior matches data-model.md.
- **Reducer fixtures**: these are the single biggest regression catcher for FR-021. Reviewer should re-run the snapshot comparison locally.

## Next

After this WP merges, WP04 (Runtime Wiring) can emit events and write records.

Implementation command:

```bash
spec-kitty agent action implement WP03 --agent claude
```
