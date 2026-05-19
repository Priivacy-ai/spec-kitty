---
affected_files: []
cycle_number: 2
mission_slug: retrospective-default-policy-01KS049J
reproduction_command:
reviewed_at: '2026-05-19T16:54:03Z'
reviewer_agent: unknown
verdict: approved
wp_id: WP05
review_artifact_override_at: "2026-05-19T17:10:08Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP05"
review_artifact_override_reason: "Review passed cycle 2: Both blockers resolved. Blocker 1: _create_empty_retrospective_record correctly produces GenRetrospectiveRecord(provenance.kind=synthesize_fabricate), written via write_gen_record, event emitted with provenance_kind=explicit_create; two new tests confirm disk round-trip and writer rejects synthesize_fabricate+has_findings. Blocker 2: emit_skipped no longer dead -- _maybe_emit_skip closure correctly gates on emit_skipped and not dry_run with skip_reason_source=cli_flag (in-contract enum value); three tests confirm writes, non-write, and dry-run-suppressed cases. 91 tests pass (495 total suite). retrospect.py=99% coverage. agent_retrospect.py WP05-touched portions covered; pre-existing paths are the gap. Ruff clean. Help shows 3 commands. RetrospectiveSkipped semantic stretch accepted: skip_reason_source=cli_flag is in-contract enum."
---

# WP05 Review Cycle 1 — Feedback

Reviewer: reviewer-renata
Date: 2026-05-19

## Overall

85/85 tests pass, ruff clean, 99% coverage, all four `--help` surfaces confirmed via `uv run`. Two contract fidelity defects block approval.

---

## Issue 1 (BLOCKING): `--fabricate-empty` does not write `provenance.kind = "synthesize_fabricate"` to the record

**Contract requirement** (T028, step 3 and `contracts/retrospect-cli.contract.md § synthesize`):

> `provenance.kind = "synthesize_fabricate"`, `provenance.command = "agent retrospect synthesize --fabricate-empty"`

**What the implementation does**: `_create_empty_retrospective_record` in `agent_retrospect.py` uses `RetrospectiveRecord` + `RecordProvenance` (Pydantic model). `RecordProvenance` has no `kind` field (it only has `authored_by`, `runtime_version`, `written_at`, `schema_version`). The fabricated record therefore carries no `provenance.kind` attribute at all.

**Why the tests miss it**: `test_fabricate_empty_creates_record_when_missing` patches `_create_empty_retrospective_record` entirely, so it never exercises the real function or the written record. The assertion `result.exit_code != 1 or "RETROSPECTIVE_RECORD_MISSING" not in result.output` only checks that the error path was bypassed — it does not assert the record's provenance.

**How to fix**:

Option A (preferred): Change `_create_empty_retrospective_record` to produce a `GenRetrospectiveRecord` (dataclass) with `provenance=GenProvenance(kind="synthesize_fabricate", command="agent retrospect synthesize --fabricate-empty", ...)` and write via `write_gen_record` (which runs `validate_record` as a defense-in-depth check). Then `read_record` the written YAML to continue the synthesize flow.

Option B: Add a `kind` field to `RecordProvenance` (schema change) — this is a larger blast radius and not recommended for this WP.

**Required test addition**: A test that does NOT patch `_create_empty_retrospective_record` and instead asserts that the YAML written to disk contains `provenance.kind: synthesize_fabricate` (read back via `read_record` or direct YAML parse). The T028 DoD item "Writer rejects a `synthesize_fabricate` record with `findings_status=has_findings`" also needs a test exercising the real writer path.

---

## Issue 2 (BLOCKING): `--emit-skipped` is a dead parameter — no event is emitted

**Contract requirement** (`contracts/retrospect-cli.contract.md § backfill`, `--emit-skipped` flag):

> "Append a `RetrospectiveSkipped` event for skipped missions. Default: skips are CLI-output only."

**What the implementation does**: The parameter is declared with `# noqa: ARG001` on line 577 of `retrospect.py`, meaning it is accepted but entirely ignored. No `RetrospectiveSkipped` event is ever emitted regardless of the flag value.

**How to fix**: Either:
- Implement the event emission: when `emit_skipped` is True and a mission is skipped, call `emit_skip_recorded(...)` (or equivalent) in `_process_candidate` for each skipped entry.
- OR explicitly document this as a deferred/out-of-scope stub and add a test asserting the no-op is intentional, noting it in a `# TODO` with the issue number. If the event type doesn't exist yet, a minimal stub that logs a warning and explicitly does nothing is acceptable if the test covers the no-op path.

The current state is silently broken — the flag is user-visible with a documented contract but has zero effect. At minimum, if `emit_capture_failed` exists for failures, a parallel `emit_skip_recorded` should exist for skips, or the flag should document why it is not yet implemented.

---

## Non-blocking observations (informational only)

- **B904 scope**: Narrow and justified (per-file on two CLI files, consistent with existing `agent/config.py`, `agent/status.py`, `agent/workflow.py` pattern). All B904 instances are `raise typer.Exit(N)` inside `except` clauses — the standard Typer pattern.
- **File structure**: 1046 lines but well-sectioned with clear `# ---` dividers between `create`, `backfill`, and `summary` command blocks plus a shared helpers section. Readable; no copy-paste detected.
- **`--feature` regression**: No `--feature` flags introduced. `--mission` used throughout. Charter compliance confirmed.
- **FR-016 env-mutation**: Zero hits. Clean.
- **Coverage**: 99% (5 uncovered lines are error-path branches in `summary_cmd` for `policy_source` from event log — acceptable edge cases).
- **Back-compat**: `spec-kitty agent retrospect summary` delegates to canonical `retrospect summary_cmd`. Verified.
- **`summary` read-only**: `test_summary_no_filesystem_mutation` correctly snapshots mtime before/after. Pass.
- **Contract shape verification sampled**:
  - `RETROSPECTIVE_RECORD_EXISTS` (lines 278-284): all 6 contract fields present (`result`, `code`, `mission_id`, `mission_slug`, `record_path`, `blocked_reason`, `exit_code`). Match.
  - `MISSION_NOT_COMPLETED` (lines 306-313): `result`, `code`, `mission_id`, `open_wps` array with `wp_id`+`lane`. Match.
  - `RETROSPECTIVE_RECORD_MISSING` (lines 775-781): all 5 contract fields. Match.
  - Backfill JSON aggregate shape (line 591): all 7 keys present. `created` is int (verified line 493). Match.
