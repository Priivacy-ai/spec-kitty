---
work_package_id: WP01
title: Synthesizer skeleton + adapter seam + path guard (plan alias WP3.1)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history:
- at: '2026-04-17T16:43:25Z'
  actor: tasks
  event: generated
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
mission_id: 01KPE222CD1MMCYEGB3ZCY51VR
mission_slug: phase-3-charter-synthesizer-pipeline-01KPE222
owned_files:
- src/charter/synthesizer/__init__.py
- src/charter/synthesizer/adapter.py
- src/charter/synthesizer/errors.py
- src/charter/synthesizer/fixture_adapter.py
- src/charter/synthesizer/orchestrator.py
- src/charter/synthesizer/path_guard.py
- src/charter/synthesizer/request.py
- architecture/adrs/2026-04-17-1-charter-synthesizer-adapter-seam.md
- architecture/adrs/2026-04-17-2-charter-synthesizer-atomicity.md
- tests/charter/synthesizer/__init__.py
- tests/charter/synthesizer/conftest.py
- tests/charter/synthesizer/test_adapter_contract.py
- tests/charter/synthesizer/test_fixture_adapter.py
- tests/charter/synthesizer/test_path_guard.py
- tests/charter/fixtures/synthesizer/**
tags: []
---

# WP01 · Synthesizer skeleton + adapter seam + path guard

## Objective

Land the foundational layer of `src/charter/synthesizer/`: the frozen adapter seam (`SynthesisAdapter` Protocol + `AdapterOutput`), the `PathGuard` that makes writes under `src/doctrine/` physically impossible, the fixture adapter with hash-keyed loading, the orchestrator skeleton, and the two ADRs that lock the load-bearing decisions. No interview mapping, no persistence, no DRG work — those are WP02/WP03/WP04.

Every downstream WP imports from here. **Interface stability matters more than breadth.**

## Context

Read before writing code:
- [plan.md §KD-1, §KD-3, §KD-4, §KD-5, §KD-6](../plan.md) — ownership, adapter shape, fixture keying, path guard, ADR schedule.
- [data-model.md §E-1, §E-2, §E-3, §E-8](../data-model.md) — entity shapes for `SynthesisRequest`, `SynthesisTarget`, `AdapterOutput`, the error taxonomy.
- [contracts/adapter.py](../contracts/adapter.py) — the Protocol shape is already pinned by this contract file; your implementation must match exactly.
- [research.md §R-0-6](../research.md) — normalization rules for the fixture hash (canonical JSON, sorted keys, stable int/float repr; `run_id` excluded).
- `src/charter/` — existing charter package layout; match its style.

## Branch strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: allocated by finalize-tasks (`lanes.json` → Lane A)
- Branch name: `kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222-lane-a`

## Subtasks

### T001 — Scaffold package + errors taxonomy

**Files**: `src/charter/synthesizer/__init__.py`, `src/charter/synthesizer/errors.py`

Create the package. `__init__.py` re-exports only what downstream WPs need publicly (`SynthesisAdapter`, `AdapterOutput`, `SynthesisRequest`, `SynthesisTarget`, `PathGuardViolation`, `FixtureAdapterMissingError`, `SynthesisError`).

`errors.py` defines the structured error taxonomy from data-model.md §E-8 as exceptions inheriting from `SynthesisError(Exception)`. Every error must carry structured fields (not just a message) rendered via a shared `rich` panel helper. Ship all error classes now; WP02-WP05 raise them but don't add new ones unless strictly necessary.

- `SynthesisError` (base)
- `PathGuardViolation(attempted_path, caller)`
- `SynthesisSchemaError(artifact_kind, artifact_slug, validation_errors)`
- `ProjectDRGValidationError(errors, merged_graph_summary)`
- `DuplicateTargetError(kind, slug, occurrences)`
- `TopicSelectorUnresolvedError(raw, candidates, attempted_forms)`
- `TopicSelectorAmbiguousError(raw, candidates)`
- `FixtureAdapterMissingError(expected_path, kind, slug, inputs_hash)`
- `ProductionAdapterUnavailableError(adapter_id, reason, remediation)`
- `StagingPromoteError(run_id, staging_dir, cause)`
- `ManifestIntegrityError(manifest_path, offending_artifact)`

Each class is a `@dataclass` exception; include `__str__` that renders a terse human message from the fields.

### T002 — `request.py` [P]

**Files**: `src/charter/synthesizer/request.py`

Define `SynthesisRequest` and `SynthesisTarget` as frozen dataclasses per data-model.md §E-1 / §E-2. Include:
- `SynthesisTarget` validation: `slug` matches `^[a-z][a-z0-9-]*$`; for `kind == "directive"` the `artifact_id` matches `^[A-Z][A-Z0-9_-]*$` and MUST NOT start with `DIRECTIVE_` (that prefix is reserved for shipped directives).
- At least one of `source_section` or `source_urns` is non-empty.
- URN rule (computed property): `urn = f"{kind}:{artifact_id}"`.
- Filename rule (computed property): `<NNN>-<slug>.directive.yaml` / `<slug>.tactic.yaml` / `<slug>.styleguide.yaml`; for directive, extract `<NNN>` as the first digit run in `artifact_id` (e.g. `PROJECT_001` → `001`).
- `normalize_request_for_hash(request, adapter_id, adapter_version) -> bytes` — canonical JSON, sorted keys, stable int/float repr, `run_id` excluded. This is the **sole** source of fixture-hash bytes; WP01 freezes it so WP02-WP05 inherit stable hashes.

### T003 — `adapter.py` [P]

**Files**: `src/charter/synthesizer/adapter.py`

Define `SynthesisAdapter` as a `Protocol` (runtime-checkable) with exactly:
```python
id: str
version: str
def generate(self, request: SynthesisRequest) -> AdapterOutput: ...
# Optional:
def generate_batch(self, requests: Sequence[SynthesisRequest]) -> Sequence[AdapterOutput]: ...
```

`AdapterOutput` is a frozen dataclass per data-model.md §E-3. No retry policy, no prompt templating, no model parameters — those belong inside adapter implementations. This file is the frozen seam; changes require an ADR amendment.

Ensure `contracts/adapter.py` (already in the mission dir) and `src/charter/synthesizer/adapter.py` expose structurally identical shapes; add a conformance test in T008 that proves it.

### T004 — `path_guard.py` [P]

**Files**: `src/charter/synthesizer/path_guard.py`

Implement `PathGuard` as the sole write seam for all synthesizer code:
- Methods: `replace(src, dst)`, `write_text(path, text)`, `write_bytes(path, data)`, `mkdir(path, parents=True, exist_ok=True)`.
- Constructor takes `repo_root: Path` plus an allowlist of prefixes (initialised to `.kittify/doctrine/` + `.kittify/charter/`). Any target outside the allowlist — in particular anything under `src/doctrine/` — raises `PathGuardViolation` **before** the filesystem is touched.
- Resolve both the path and the allowlist prefixes to absolute form before comparison; guard against `..` traversal.

Write a lint-style regression test (T008, `test_path_guard.py`) that greps `src/charter/synthesizer/` for `open(..., 'w')`, `Path.write_text`, `Path.write_bytes`, `shutil.move`, `os.replace`, and similar direct write primitives used outside `path_guard.py`. Any hit fails the test. This is the R-10 mitigation.

### T005 — `fixture_adapter.py`

**Files**: `src/charter/synthesizer/fixture_adapter.py`

Fixture adapter with layout `tests/charter/fixtures/synthesizer/<kind>/<slug>/<blake3-short>.<kind>.yaml` (short = first 16 hex chars of blake3-256 over normalized bytes from T002). The `.<kind>.yaml` suffix matches the shipped repository glob so fixtures round-trip through the same loaders.

On `generate(request)`:
1. Compute the expected path via normalized hash.
2. If present → load, return as `AdapterOutput` with `adapter_id="fixture"`, `adapter_version=<pinned>`, `generated_at=<deterministic UTC>` (seeded from hash or a fixed epoch — see NFR-006 / FR-014).
3. If absent → raise `FixtureAdapterMissingError(expected_path=..., kind=..., slug=..., inputs_hash=...)`.

This module lives in `src/` (not `tests/`) so integration tests can import it, but it is wired only in test entrypoints; the production CLI path (WP05) never selects it unless `--adapter fixture` is passed.

### T006 — `orchestrator.py` skeleton

**Files**: `src/charter/synthesizer/orchestrator.py`

Skeleton dispatcher with public entry points:
```python
def synthesize(request: SynthesisRequest) -> SynthesisResult: ...
def resynthesize(request: SynthesisRequest, topic: str) -> SynthesisResult: ...
```

Both functions use lazy imports to delegate:
- `synthesize` → `from .synthesize_pipeline import run as _run` (module lives in WP02; ImportError before WP02 is fine at module level — the skeleton keeps the import inside the function body, so WP01's tests don't trip it).
- `resynthesize` → `from .resynthesize_pipeline import run as _run` (WP05).

Until WP02/WP05 land their pipelines, the function bodies raise `NotImplementedError("WP02 will populate this")` / `NotImplementedError("WP05 will populate this")` with a helpful message.

This keeps orchestrator.py **owned by WP01 permanently** — downstream WPs deliver their pipelines, not edits to this file.

### T007 — ADRs [P]

**Files**:
- `architecture/adrs/2026-04-17-1-charter-synthesizer-adapter-seam.md`
- `architecture/adrs/2026-04-17-2-charter-synthesizer-atomicity.md`

Follow the existing ADR template (check `architecture/adrs/` for format). ADR-1 documents KD-3 (adapter Protocol shape, optional batch, override-first provenance) and KD-4 (fixture keying). ADR-2 documents KD-2 (stage + ordered promote + manifest-last), including rejected alternatives (pure in-memory, journal+replay) and recovery semantics (`.failed/` preservation).

Both ADRs must cross-reference this mission and the Phase 3 EPIC.

### T008 — Tests

**Files**:
- `tests/charter/synthesizer/__init__.py` (empty package marker)
- `tests/charter/synthesizer/conftest.py` — shared fixtures (doctrine snapshot, drg snapshot factories); one sample fixture per kind under `tests/charter/fixtures/synthesizer/`.
- `tests/charter/synthesizer/test_adapter_contract.py` — `isinstance(FixtureAdapter(), SynthesisAdapter)` holds; contract file and module file expose structurally identical shapes; adapter overrides propagate to `AdapterOutput`.
- `tests/charter/synthesizer/test_path_guard.py` — write under `.kittify/doctrine/` succeeds; write under `src/doctrine/` raises `PathGuardViolation` **before** touching the filesystem; lint-style grep passes (no direct writes outside `path_guard.py`).
- `tests/charter/synthesizer/test_fixture_adapter.py` — missing fixture raises `FixtureAdapterMissingError` with correct `expected_path`; identical normalized inputs produce identical hashes (key-order permutation invariance); present fixture returns `AdapterOutput` with `adapter_id == "fixture"`.

## Definition of Done

- All 8 subtasks complete; tests green locally and in CI (`pytest tests/charter/synthesizer/` + `mypy --strict src/charter/synthesizer/`).
- `src/charter/synthesizer/` is a mypy-strict-clean package with 0 `type: ignore`.
- Both ADRs merged to `architecture/adrs/` with cross-references.
- Coverage on new code ≥ 90% (NFR-001).
- Lint-style path-guard test is green (R-10 locked).
- PR description links to [plan.md §KD-1..6](../plan.md) and explains the seam + atomicity decisions.

## Risks & premortem

- **R-1 · Seam leak** — Mitigation: keep `SynthesisAdapter` Protocol minimal; any field outside `id`/`version`/`generate`/`generate_batch` must be justified in ADR-1 or rejected.
- **R-8 · Normalization drift** — Mitigation: `test_fixture_adapter.py` asserts hash stability under key-order permutations; change-control `normalize_request_for_hash` via ADR.
- **R-10 · Path guard bypass** — Mitigation: lint-style grep test runs in CI; every new write site in downstream WPs must go through `PathGuard` methods.

## Reviewer guidance

Review in this order per `review-intent-and-risk-first`:
1. ADR-1 (adapter seam) and ADR-2 (atomicity) — if these are wrong, nothing else matters.
2. `src/charter/synthesizer/adapter.py` — Protocol fidelity vs `contracts/adapter.py`.
3. `src/charter/synthesizer/request.py::normalize_request_for_hash` — deterministic byte output is load-bearing for WP05's idempotency claims.
4. `src/charter/synthesizer/path_guard.py` — does every possible bypass route hit the guard?
5. `orchestrator.py` skeleton — late-bound imports keep WP02/WP05 ownership clean.
6. Tests — do the negative cases actually exercise the failure mode, not just the happy path?

## Next command

```bash
spec-kitty agent action implement WP01 --agent <your-agent>
```
