---
work_package_id: WP02
title: Interview-driven synthesis path (plan alias WP3.2)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-014
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222
base_commit: 9d239e76b5e1eef0f31811a179a5de91ff0c8149
created_at: '2026-04-17T17:21:44.930971+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
shell_pid: "63719"
agent: "claude:sonnet-4.6:implementer:implementer"
history:
- at: '2026-04-17T16:43:25Z'
  actor: tasks
  event: generated
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
mission_id: 01KPE222CD1MMCYEGB3ZCY51VR
mission_slug: phase-3-charter-synthesizer-pipeline-01KPE222
owned_files:
- src/charter/synthesizer/interview_mapping.py
- src/charter/synthesizer/targets.py
- src/charter/synthesizer/synthesize_pipeline.py
- tests/charter/synthesizer/test_interview_mapping.py
- tests/charter/synthesizer/test_orchestrator_synthesize.py
- tests/charter/synthesizer/test_schema_conformance.py
tags: []
---

# WP02 · Interview-driven synthesis path

## Objective

Populate `orchestrator.synthesize()` end-to-end **in memory**. Map interview answers to a list of `SynthesisTarget`s, order them, enforce duplicate-slug rejection, dispatch the adapter (single or batched), validate each `AdapterOutput.body` against the shipped Pydantic schema for its `kind` (FR-019), and assemble `ProvenanceEntry` value objects. **No filesystem writes** — WP03 owns persistence.

Downstream contracts delivered by this WP:
- `synthesize_pipeline.run(request) -> list[tuple[body, ProvenanceEntry]]` — WP03's `write_pipeline` consumes this tuple stream.
- Interview-section → target kind mapping is a visible table; WP04's `test_context_reflects_synthesis` reads it.

## Context

Read before writing code:
- [plan.md §Work Package Breakdown](../plan.md) — scope for WP3.2.
- [data-model.md §E-1, §E-2, §E-3, §E-4](../data-model.md) — entity fields.
- [research.md §R-0-1](../research.md) — interview-answer surfaces → artifact kind mapping.
- Existing interview surface at `src/charter/interview.py` — use its section labels as the mapping keys.
- Shipped Pydantic models: `src/doctrine/directives/models.py::Directive`, `src/doctrine/tactics/models.py::Tactic`, `src/doctrine/styleguides/models.py::Styleguide` — call `.model_validate(body)` for FR-019.

## Branch strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: allocated by finalize-tasks (Lane A, reuses WP01 worktree since serial dependency)
- Branch name: `kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222-lane-a`

## Subtasks

### T009 — `interview_mapping.py` [P]

**File**: `src/charter/synthesizer/interview_mapping.py`

Build an explicit **data table** mapping interview section labels → expected artifact kinds. Data-driven, not imperative. Example shape:

```python
@dataclass(frozen=True)
class InterviewSectionMapping:
    section_label: str
    kinds: tuple[Literal["directive", "tactic", "styleguide"], ...]
    # slug template receives (section_label, answer_context) and returns a kebab slug

INTERVIEW_MAPPINGS: tuple[InterviewSectionMapping, ...] = (
    InterviewSectionMapping("testing-philosophy", ("tactic", "styleguide")),
    InterviewSectionMapping("language-scope", ("styleguide",)),
    InterviewSectionMapping("neutrality-posture", ("directive",)),
    # etc.
)
```

The mapping drives WP04's `test_context_reflects_synthesis` — keep it public and explicitly enumerated.

**R-9 mitigation**: the interview-time DRG resolver must use **shipped-only** DRG; do not merge project layer during interview. Document this invariant at the top of the module; lock it in `test_interview_mapping.py`.

### T010 — `targets.py` [P]

**File**: `src/charter/synthesizer/targets.py`

Functions:
- `build_targets(interview_snapshot, mappings, drg_snapshot) -> list[SynthesisTarget]` — resolves answers + source URN references; assigns `artifact_id` per kind (for directives, generate `PROJECT_<NNN>` deterministically from the target index; for tactic/styleguide, `artifact_id == slug`).
- `order_targets(targets) -> list[SynthesisTarget]` — stable deterministic ordering (kind priority: directive → tactic → styleguide; within kind, lexicographic slug). Idempotency depends on this (FR-014).
- `detect_duplicates(targets) -> None` — raises `DuplicateTargetError` if any `(kind, slug)` appears twice (EC-7).

Every URN in `target.source_urns` must resolve in `drg_snapshot`; if not, raise `ProjectDRGValidationError` early — don't wait for WP04's validation gate to catch it (EC-2 says synthesis fails closed **before any artifact is written**).

### T011 — `synthesize_pipeline.py`

**File**: `src/charter/synthesizer/synthesize_pipeline.py`

Public entry: `run(request, adapter) -> list[tuple[Mapping[str, Any], ProvenanceEntry]]`.

Flow:
1. Call `interview_mapping.resolve_sections(request.interview_snapshot)` → list of `(section_label, answer_context)`.
2. Call `targets.build_targets(...)` → `list[SynthesisTarget]`.
3. Call `targets.order_targets` + `detect_duplicates`.
4. For each target, construct a per-target `SynthesisRequest` (cloning the shared snapshots, setting `target`).
5. Dispatch: if `hasattr(adapter, 'generate_batch')`, call batch; else sequential `generate` calls.
6. For each `AdapterOutput`, run schema conformance (T012); on failure raise `SynthesisSchemaError` — no provenance entry, no downstream progress.
7. Assemble `ProvenanceEntry` in memory (T013) using override-first identity: `adapter_id = output.adapter_id_override or adapter.id`; same for version.
8. Return the `(body, provenance)` tuple list.

The pipeline must be **deterministic under the fixture adapter**: same `request` → byte-identical `(body, provenance)` tuple. This is the FR-014 / NFR-006 test surface.

### T012 — Schema conformance gate

Inside `synthesize_pipeline.run`, add:

```python
from doctrine.directives.models import Directive
from doctrine.tactics.models import Tactic
from doctrine.styleguides.models import Styleguide

_SCHEMA_BY_KIND = {"directive": Directive, "tactic": Tactic, "styleguide": Styleguide}

def _assert_schema(target, output):
    try:
        _SCHEMA_BY_KIND[target.kind].model_validate(output.body)
    except ValidationError as e:
        raise SynthesisSchemaError(
            artifact_kind=target.kind,
            artifact_slug=target.slug,
            validation_errors=[str(err) for err in e.errors()],
        ) from e
```

This is the FR-019 / NFR-005 gate.

### T013 — In-memory provenance-object assembly

Build `ProvenanceEntry` per data-model.md §E-4:
- `artifact_content_hash` = blake3-256 of the canonicalized YAML bytes that WP03 will emit (use the same YAML serializer WP03 will use — call `charter.synthesizer.serialize.canonical_yaml(body)` which you add as a small helper inside `synthesize_pipeline.py` or a sibling module you own).
- `inputs_hash` = blake3-256 over `normalize_request_for_hash(request, adapter_id, adapter_version)` from WP01.
- `source_section` and `source_urns` copied verbatim from `target`.
- `generated_at` from `AdapterOutput.generated_at` (ISO 8601 UTC).
- `adapter_notes` from `AdapterOutput.notes`.

No provenance is persisted in this WP — just assembled as `ProvenanceEntry` values in the returned tuple list.

### T014 — Tests

**Files**:
- `tests/charter/synthesizer/test_interview_mapping.py` — table-driven: every `INTERVIEW_MAPPINGS` entry resolves cleanly; R-9 lock (shipped-only DRG during interview).
- `tests/charter/synthesizer/test_orchestrator_synthesize.py` — end-to-end **in-memory** synthesis through the fixture adapter; returns a list of `(body, ProvenanceEntry)` tuples with correct counts; idempotent — run twice, assert byte-identical `inputs_hash` and `artifact_content_hash` (FR-014, NFR-006); duplicate target → `DuplicateTargetError` (EC-7); dangling source URN → `ProjectDRGValidationError` (EC-2).
- `tests/charter/synthesizer/test_schema_conformance.py` — adapter returns invalid body (extra required field missing) → `SynthesisSchemaError`; valid body passes; error contains the target kind + slug + validation errors.

## Definition of Done

- All 6 subtasks complete.
- `pytest tests/charter/synthesizer/test_interview_mapping.py test_orchestrator_synthesize.py test_schema_conformance.py` is green.
- `mypy --strict` clean on all WP02 files.
- Coverage ≥ 90% on new modules (NFR-001).
- Idempotency test (run synthesis twice, compare hashes) is green.
- PR description lists which interview sections map to which artifact kinds, and explains why.

## Risks & premortem

- **R-9 · Silent project-layer DRG reads during interview** — Mitigation: `interview_mapping.py` top-of-module invariant + locked by `test_interview_mapping.py`.
- **R-8 · Normalization drift** — Mitigation: the fixture hash comes from WP01's `normalize_request_for_hash`; don't reinvent it in WP02.
- **Serialization drift** — The `canonical_yaml` helper WP02 uses to compute `artifact_content_hash` must match what WP03's writer emits byte-for-byte. Expose it as a shared helper; WP03 imports the same function.

## Reviewer guidance

1. `interview_mapping.INTERVIEW_MAPPINGS` — does every entry align with a real interview section label? Is anything missing?
2. `targets.build_targets` — determinism under reorderings; duplicate detection; URN resolution against shipped-only DRG at interview time.
3. `synthesize_pipeline.run` — override-first adapter identity; schema gate placement (before provenance assembly).
4. `canonical_yaml` — is this the same serializer WP03 will use? Otherwise hashes will diverge at write time.
5. Idempotency test — does it actually compare full hashes or just shapes?

## Next command

```bash
spec-kitty agent action implement WP02 --agent <your-agent>
```

## Activity Log

- 2026-04-17T17:21:45Z – claude:sonnet-4.6:implementer:implementer – shell_pid=63719 – Assigned agent via action command
- 2026-04-17T17:40:20Z – claude:sonnet-4.6:implementer:implementer – shell_pid=63719 – WP02 complete: interview_mapping.py, targets.py, synthesize_pipeline.py + 3 test files + 7 fixture YAML files. 125 tests passing, ruff clean. Committed to lane-b branch.
