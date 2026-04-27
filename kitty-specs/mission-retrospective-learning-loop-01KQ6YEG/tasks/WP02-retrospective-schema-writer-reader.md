---
work_package_id: WP02
title: retrospective.yaml Schema, Writer, Reader
dependencies: []
requirement_refs:
- C-014
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer:reviewer"
shell_pid: "83863"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/retrospective/__init__.py
- src/specify_cli/retrospective/schema.py
- src/specify_cli/retrospective/writer.py
- src/specify_cli/retrospective/reader.py
- tests/retrospective/__init__.py
- tests/retrospective/test_schema_roundtrip.py
- tests/retrospective/test_writer_atomicity.py
- tests/retrospective/test_reader_tolerance.py
priority: P1
status: planned
tags: []
---

# WP02 — `retrospective.yaml` Schema, Writer, Reader

## Objective

Establish the durable governance contract for retrospective records: Pydantic v2 schema, atomic round-trip-safe writer, schema-validating reader. This is the foundation that WP03/WP05/WP07/WP09 build on.

## Spec coverage

- **FR-005** schema fields: mission identity, mode + source signal, status enum, started/completed timestamps, helped/not_helpful/gaps/proposals, provenance.
- **FR-006** provenance on every finding/proposal.
- **FR-007** nine proposal kinds.
- **FR-008** writer round-trips a fixture finding set.
- **FR-009** canonical durable path keyed by `mission_id`.
- **NFR-001** schema validation < 200 ms on typical (≤200 findings) record.
- **NFR-002** atomic writer.
- **NFR-005** append-only event invariant (writer interacts with event log via WP03; this WP must not violate the invariant).
- **C-014** path keyed by `mission_id` (ULID), not `mission_number`.

## Context

Source-of-truth shapes are pinned in:
- [`../data-model.md`](../data-model.md) — entity definitions.
- [`../contracts/retrospective_yaml_v1.md`](../contracts/retrospective_yaml_v1.md) — required vs. optional, per-proposal-kind payload schemas, forward-compat rules.

Use `pydantic` v2 with `Annotated[..., Field(discriminator="kind")]` for proposal payloads. Use `ruamel.yaml` round-trip dumper for stable byte output.

## Subtasks

### T005 [P] — Pydantic schema models per data-model.md

In `src/specify_cli/retrospective/schema.py`, define:

- `MissionId`, `Mid8`, `EventId`, `ProposalId`, `Timestamp` (type aliases / `Annotated[str, …]` with regex constraints).
- `ActorRef`.
- `MissionIdentity`, `ModeSourceSignal`, `Mode`.
- `TargetReference` with closed `kind` enum.
- `FindingProvenance`, `ProposalProvenance`, `RecordProvenance`.
- `Finding`.
- `ProposalState`, `ProposalApplyAttempt`.
- `Proposal` with discriminated-union payload per kind (closed set: `synthesize_directive`, `synthesize_tactic`, `synthesize_procedure`, `rewire_edge`, `add_edge`, `remove_edge`, `add_glossary_term`, `update_glossary_term`, `flag_not_helpful`).
- `RetrospectiveFailure`.
- `RetrospectiveRecord` top-level model.

`schema_version: Literal["1"]` is pinned. Status-conditional cross-field validators must enforce: `skipped ⇒ skip_reason`, `completed ⇒ completed_at`, `failed ⇒ failure`. The writer must refuse `pending`.

### T006 — Atomic round-trip writer

In `src/specify_cli/retrospective/writer.py`:

```python
def write_record(record: RetrospectiveRecord, *, repo_root: Path) -> Path:
    """Atomically write a retrospective record to its canonical path.

    Returns the absolute path written. Raises WriterError on validation
    or IO failure. The write is atomic: on crash, the canonical file
    either does not exist or holds the prior version unchanged.
    """
```

Steps:
1. Validate the record (Pydantic).
2. Compute canonical path: `repo_root / ".kittify/missions" / record.mission.mission_id / "retrospective.yaml"`.
3. Create the target directory if needed.
4. Serialize via `ruamel.yaml` round-trip dumper to a tempfile in the same directory: `<canonical>.tmp.<pid>.<urandom>`.
5. `fsync()` the tempfile, close.
6. `os.replace(tmp, canonical)`.
7. Best-effort `fsync()` on the directory fd.

### T007 — Schema-validating reader

In `src/specify_cli/retrospective/reader.py`:

```python
def read_record(path: Path) -> RetrospectiveRecord:
    """Load a retrospective record from disk, schema-validated.

    Raises:
        FileNotFoundError: file is absent.
        SchemaError: file exists but fails schema validation.
        YAMLParseError: file exists but is not valid YAML.
    """
```

The reader MUST refuse to return any record with `status=pending`. Cross-field validation runs after Pydantic. Soft evidence-reachability check is OPTIONAL (gated by a `verify_evidence: bool = False` parameter; default off so plain reads stay fast).

### T008 — Required vs optional + status-conditional cross-field validation

Implement and unit-test the cross-field invariants from `contracts/retrospective_yaml_v1.md`:

- `status="completed"` requires `completed_at`.
- `status="skipped"` requires `skip_reason` (non-empty).
- `status="failed"` requires `failure`.
- `status="pending"` is rejected at write/read boundaries.
- All `Finding.id` values are unique within a record.
- All `Proposal.id` values are unique within a record.
- Per-kind payload conforms to its schema (Pydantic discriminated-union catches most; add manual checks where needed for hash fields and edge canonicalization).

### T009 — Tests

Three test modules:

- `tests/retrospective/test_schema_roundtrip.py` — fixture record (rich, brief, skipped, failed) → write → read → equals; canonical path includes the ULID.
- `tests/retrospective/test_writer_atomicity.py` — simulated mid-write crash (e.g., monkeypatch `os.replace` to raise after tempfile written) leaves no canonical file or leaves the prior version. Sibling tempfile may exist; test asserts the canonical file is correct.
- `tests/retrospective/test_reader_tolerance.py` — corrupt YAML → `YAMLParseError`; missing required field → `SchemaError`; `status=pending` → `SchemaError`; missing file → `FileNotFoundError`.

Performance microbenchmark: a 200-finding fixture validates in < 200 ms. Use `pytest.mark.benchmark` or a simple `time.perf_counter()` assertion with generous slack.

## Definition of Done

- [ ] All Pydantic models in `schema.py` carry `model_config = ConfigDict(extra="forbid")` to prevent silent typos.
- [ ] Writer uses `os.replace` (no in-place writes anywhere).
- [ ] Reader refuses `status=pending`.
- [ ] Tests pass; coverage ≥ 90% on new modules.
- [ ] `mypy --strict` passes on `src/specify_cli/retrospective/{__init__,schema,writer,reader}.py`.
- [ ] No changes outside `owned_files`.

## Risks

- **Discriminated-union with payload variants**: Pydantic v2 has nuance around discriminator + Annotated unions. Test each proposal kind explicitly.
- **Atomicity on macOS APFS vs. Linux ext4**: `os.replace` is documented atomic on both. Avoid `tempfile.NamedTemporaryFile` in a different directory (cross-fs replace is not atomic).
- **Round-trip stability**: `ruamel.yaml` round-trip can preserve key order; verify the writer produces canonical, sorted-keys output (or accept the round-trip dumper's natural output and document that fact).

## Reviewer guidance

- Confirm `os.replace` is the only durable-write call.
- Confirm cross-field validators exercise every status branch.
- Confirm a write-followed-by-read on a fixture produces an identical Pydantic model (use `model_dump()` equality, not byte equality).

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Activity Log

- 2026-04-27T09:00:16Z – claude:sonnet:implementer:implementer – shell_pid=76686 – Started implementation via action command
- 2026-04-27T09:06:30Z – claude:sonnet:implementer:implementer – shell_pid=76686 – Ready for review: schema + writer + reader + tests; 31 tests, 96% coverage, mypy --strict passes
- 2026-04-27T09:06:53Z – claude:opus:reviewer:reviewer – shell_pid=83863 – Started review via action command
- 2026-04-27T09:09:58Z – claude:opus:reviewer:reviewer – shell_pid=83863 – Review passed: schema/writer/reader meet contract; 31/31 tests pass; 96% coverage; mypy strict clean; ULID-keyed canonical path verified
