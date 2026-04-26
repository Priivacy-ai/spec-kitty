---
work_package_id: WP05
title: Cross-Repo Package Contracts + Release Gates
dependencies: []
requirement_refs:
- FR-022
- FR-023
- FR-024
- FR-025
- FR-026
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
- T031
agent: "claude:opus-4-7:reviewer:reviewer"
shell_pid: "13083"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: tests/contract/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- tests/contract/test_events_envelope_matches_resolved_version.py
- tests/contract/snapshots/**
- tests/architectural/test_events_tracker_public_imports.py
- tests/architectural/test_no_runtime_pypi_dep.py
- tests/integration/test_release_gate_downstream_consumer.py
- tests/integration/test_mission_review_contract_gate.py
- scripts/snapshot_events_envelope.py
- architecture/2.x/adr/2026-04-26-1-contract-pinning-resolved-version.md
- .github/workflows/release.yml
- docs/development/contract-pinning.md
tags: []
---

# WP05 — Cross-Repo Package Contracts + Release Gates

## Objective

Pin contract tests to the resolved version of `spec-kitty-events`. Make
`tests/contract/` a hard mission-review gate. Freeze public imports of
`spec_kitty_events.*` and `spec_kitty_tracker.*`. Assert no production
dep on `spec-kitty-runtime`. Require downstream-consumer verification
before stable promotion of any cross-repo package. Record an ADR.

## Context

The shared-package-boundary cutover (mission
`shared-package-boundary-cutover-01KQ22DS`, 2026-04-25) made
`spec-kitty-events` and `spec-kitty-tracker` external PyPI packages and
retired the standalone `spec-kitty-runtime` from production. This WP
makes those decisions enforced and tested. Contract surfaces in
[`contracts/events-envelope.md`](../contracts/events-envelope.md) and
[`contracts/tracker-public-imports.md`](../contracts/tracker-public-imports.md).
Decisions in `research.md` D8.

## Branch strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP05 --agent <name>`.

## Subtasks

### T025 — Resolved-version contract test for events envelope

**Purpose**: Contract tests reflect the actually resolved version, not a
hard-coded one.

**Steps**:

1. Add `scripts/snapshot_events_envelope.py` that introspects the
   currently installed `spec_kitty_events.EventEnvelope` (via
   `pydantic.BaseModel.schema()` or equivalent) and writes a JSON
   snapshot to
   `tests/contract/snapshots/spec-kitty-events-<resolved-version>.json`.
2. Add `tests/contract/test_events_envelope_matches_resolved_version.py`:
   - Resolve `spec-kitty-events` version. Prefer `uv.lock` via
     `tomllib`; fall back to
     `importlib.metadata.version("spec-kitty-events")`.
   - Load the snapshot at the resolved version. If missing, fail with
     a clear message pointing at the snapshot script.
   - Assert all envelopes emitted by `spec-kitty` match the snapshot
     field-by-field for every event_type currently produced.
3. Generate the initial snapshot by running the script in this WP's
   workspace. Commit the snapshot file.

**Validation**:
- `pytest tests/contract/test_events_envelope_matches_resolved_version.py -v`
  green.
- Bumping `spec-kitty-events` in `pyproject.toml` (test only — do not
  actually bump) without regenerating the snapshot fails the test with
  the documented diagnostic.

### T026 — `tests/contract/` as hard mission-review gate

**Purpose**: A failing contract test blocks mission acceptance.

**Steps**:

1. Add `tests/integration/test_mission_review_contract_gate.py` that:
   - Spawns a sub-process running `pytest tests/contract/ -v`.
   - Asserts the process exit code propagates correctly.
   - Asserts the mission-review skill reads the result and treats
     non-zero as a hard block.
2. Update the mission-review skill artifact (in `.kittify/skills/` or
   the corresponding shipped skill source path) so its instructions
   include "run `pytest tests/contract/ -v`; if non-zero, mission
   review FAILS". (Implementation note: the skill is co-owned by WP08;
   in this WP we wire the test that proves the contract.)
3. Document this gate in
   [`contracts/events-envelope.md`](../contracts/events-envelope.md) §
   "Mission-review gate".

**Validation**:
- Test passes (intentionally injects a contract failure, verifies the
  gate fails the review).

### T027 — Architectural test for public imports

**Purpose**: Public surface of events / tracker is frozen.

**Steps**:

1. Add `tests/architectural/test_events_tracker_public_imports.py`:
   - Walk `src/specify_cli/` for `import` statements referencing
     `spec_kitty_events` and `spec_kitty_tracker`.
   - Assert no caller imports from `_internal.*` paths.
   - Assert the symbol set imported is a subset of the documented
     public surface (declared in the contract markdown files).
2. Run the test; fix any caller that reaches into `_internal`.

**Validation**:
- Test passes.
- The contract markdown files are referenced in the test docstring so
  reviewers know where to update both together.

### T028 — Architectural test: no `spec-kitty-runtime` production dep

**Purpose**: Pin the C-003 invariant.

**Steps**:

1. Add `tests/architectural/test_no_runtime_pypi_dep.py`:
   - Read `pyproject.toml` and assert
     `spec-kitty-runtime` is NOT in `[project.dependencies]` or
     `[project.optional-dependencies]`'s production groups.
   - Attempt `import spec_kitty_runtime`; if it imports, that is fine
     for dev environments; the test asserts the CLI does not require
     it. Spawn a sub-process running
     `python -c "from specify_cli.next.command import next_decision"` and
     assert it succeeds without `spec_kitty_runtime` being installed.
   - For the sub-process check, set `PYTHONPATH` minus the dev egg.

**Validation**:
- Test passes on current `main`.
- Test would fail if anyone re-adds the dep in `pyproject.toml`.

### T029 — Downstream-consumer release gate

**Purpose**: A candidate release is not promoted until a downstream
consumer verifies it.

**Steps**:

1. Add `tests/integration/test_release_gate_downstream_consumer.py`:
   - Build a fake "release candidate" by tagging a local commit and
     setting a `release_candidate: true` flag.
   - Run a fixture consumer suite (skeleton in
     `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py`,
     reused via stub).
   - Assert: promotion (a script that bumps `version` from
     `X.Y.Z-rc.N` to `X.Y.Z`) refuses to run until the consumer
     suite has passed and recorded a verification artifact at
     `.kittify/release/downstream-verified.json`.
2. Modify `.github/workflows/release.yml` to add a `needs:` edge from
   the `promote` job to a new `downstream-consumer-verify` job. The
   job runs `pytest spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py`
   and uploads the verification artifact.

**Validation**:
- Test passes locally (with fake release tag).
- Workflow changes pass `actionlint` (or equivalent) syntax check.

### T030 — ADR-2026-04-26-1: Contract pinning to resolved version

**Purpose**: Capture the decision in a referenceable ADR (DIRECTIVE_003).

**Steps**:

1. Create `architecture/2.x/adr/2026-04-26-1-contract-pinning-resolved-version.md`
   following the pattern of existing ADRs. Cover:
   - Context: drift between contract tests and resolved package.
   - Decision: pin via `uv.lock` + snapshot file at
     `tests/contract/snapshots/spec-kitty-events-<version>.json`.
   - Consequences: bumping the package is a 2-step (`update` →
     `snapshot`) workflow; test failures on missing snapshots are by
     design.
   - Alternatives considered: hardcoded version in tests (rejected).
2. Reference the ADR from `research.md` and from the contract markdown.

**Validation**:
- ADR file exists with required sections.
- Cross-references resolve.

### T031 — `scripts/snapshot_events_envelope.py` + dev workflow doc

**Purpose**: Operators can regenerate the snapshot in a single step.

**Steps**:

1. Make sure `scripts/snapshot_events_envelope.py` (created in T025)
   is operator-friendly: argparse for output path, idempotent if the
   snapshot is already present, prints the resolved version.
2. Add `docs/development/contract-pinning.md` documenting the dev
   workflow: bump version → run snapshot script → run contract test
   → commit.

**Validation**:
- `python scripts/snapshot_events_envelope.py --help` prints usage.
- Doc renders cleanly (no broken internal links).

## Definition of Done

- All seven subtasks complete.
- `pytest tests/contract/ tests/architectural/` green.
- `pytest tests/integration/test_release_gate_downstream_consumer.py
   tests/integration/test_mission_review_contract_gate.py` green.
- ADR committed and cross-referenced.
- Workflow change validates syntactically.

## Risks

- T025 / T031: snapshot regeneration is a 2-step dev workflow; if
  contributors skip step 2, their PRs fail on the contract gate. The
  doc must make the workflow obvious.
- T028: the sub-process test must not have `spec_kitty_runtime`
  importable from the dev egg. Use `PYTHONPATH` rewrite or a
  `--no-install` venv.
- T029: the workflow change is the highest-risk piece; it can break
  releases. Use `if: github.event.release.prerelease == false` style
  guards so the gate fires only on stable promotion.

## Reviewer guidance

1. T025: open the snapshot file and confirm the schema fields match
   the contract markdown. Drift here is exactly what we are pinning
   against.
2. T028: a quick `grep` for `spec-kitty-runtime` in `pyproject.toml`
   should return 0 hits in production deps. Dev / docs / CI fixtures
   may still mention it.
3. T029: read `release.yml` carefully. The `needs:` graph must form a
   DAG with `downstream-consumer-verify` strictly before `promote`.
4. T030: ADR must be referenced from at least one of `research.md` and
   the contract markdown to avoid orphaning.

## Activity Log

- 2026-04-26T08:54:50Z – claude:opus-4-7:implementer:implementer – shell_pid=5842 – Started implementation via action command
- 2026-04-26T09:07:41Z – claude:opus-4-7:implementer:implementer – shell_pid=5842 – WP05 ready: T025 resolved-version envelope contract test+snapshot; T026 mission-review contract gate test; T027 events/tracker public-import freeze; T028 no spec-kitty-runtime production dep; T029 release.yml downstream-consumer-verify job + promotion gate; T030 ADR-2026-04-26-1 contract pinning; T031 snapshot script + docs/development/contract-pinning.md. Closes the WP04-flagged drift in test_cross_repo_consumers.py.
- 2026-04-26T09:08:31Z – claude:opus-4-7:reviewer:reviewer – shell_pid=13083 – Started review via action command
- 2026-04-26T09:11:48Z – claude:opus-4-7:reviewer:reviewer – shell_pid=13083 – Review passed: 7/7 subtasks fixed. Resolved-version snapshot at tests/contract/snapshots/spec-kitty-events-4.0.0.json closes the WP04-flagged drift; release.yml gate has needs: ordering; ADR-2026-04-26-1 committed; snapshot script + dev doc operator-friendly. test_terminology_guards.py::test_no_visible_feature_alias_in_cli_commands remains red as expected -- it points at charter.py:2134 owned by WP07/T042.
