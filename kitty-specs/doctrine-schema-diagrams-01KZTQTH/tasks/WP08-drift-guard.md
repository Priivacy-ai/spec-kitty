---
work_package_id: WP08
title: Schema-diagram drift guard + explicit file:class binding table
dependencies:
- WP05
- WP06
- WP07
requirement_refs:
- C-003
- C-004
- FR-004
- NFR-001
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 4 - Fidelity
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/docs/diagram_drift/
create_intent:
- tests/docs/test_diagram_drift_guard.py
- tests/docs/diagram_drift/__init__.py
- tests/docs/diagram_drift/binding_table.py
- tests/docs/diagram_drift/guard.py
execution_mode: code_change
model: ''
owned_files:
- tests/docs/test_diagram_drift_guard.py
- tests/docs/diagram_drift/**
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Schema-diagram drift guard + binding table

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (implementer) and behave per its guidance first.

---

## Objectives & Success Criteria

Enforce **zero** diagram/code drift by comparing each authored `@startyaml` diagram's field set against
its bound model(s), with **both sides introspected/parsed — never hand-counted**.

**Definition of Done:**

1. An explicit **`file:class` binding table** (1:N), covering the WP05–WP07 diagrams, with a
   **disposition for EVERY `ArtifactKind` member** (`diagrammed` | `consciously-omitted`).
2. A guard engine that introspects the three model families and parses the diagram side, and FAILs on
   any field-set mismatch or unregistered kind.
3. The four non-fakeable tests below all pass on the real corpus and FAIL on the injected regressions.
4. ATDD **RED-first** (tests committed before the engine passes); `ruff` + `mypy --strict` clean.

## Context & Constraints

- **Source of truth**: [contracts/diagram-drift-guard.md](../contracts/diagram-drift-guard.md),
  spec FR-004 / NFR-001 / C-003 / C-004, [plan.md](../plan.md) IC-04.
- **Parallel to the render pipeline** — this is pure pytest (parse text + introspect models); it does
  NOT need WP01/WP02's docker render. It depends on WP05–WP07 only because it validates their diagrams.
- **Model families (verified)**:
  - Pydantic-with-aliases: `AgentProfileSchema` (+ nested, e.g. `AgentSpecialization`). Use
    `model_fields` with **`FieldInfo.alias or name`** normalization + **transitive nested recursion**.
  - Frozen dataclass: `ActionIndex` → `dataclasses.fields()`.
  - StrEnum: `NodeKind` (16), `Relation` (15), `ArtifactKind` (12) → `list(EnumType)`, never a literal.
- **Diagram side is PINNED**: top-level `@startyaml` YAML keys (recursing into nested-model sub-maps) =
  the declared field set; scalar example values are excluded.
- **C-004 binding hygiene**: bind `styleguides/models.py:AntiPattern` vs the DRG `anti_pattern` NodeKind
  (a string with NO backing class) correctly — they share a name, different concepts.

## Subtasks & Detailed Guidance

### Subtask T026 – The binding table

- **Steps**:
  1. `tests/docs/diagram_drift/binding_table.py`: an explicit registry mapping each diagram
     (`file:anchor`) → the model class(es) it depicts (1:N). Include the WP05 **cross-kind overview**,
     the WP05 **agent-profile schema** (`AgentProfileSchema` + nested `AgentSpecialization` — T035; this
     is the aliased+nested corpus diagram that forces the alias/recursion path), the WP06 DRG, and the
     WP07 mission-type/step + action-index diagrams.
  2. Add a **disposition map over ALL `ArtifactKind`** members: each is `diagrammed` (bound to a diagram)
     or `consciously-omitted` (with a one-line reason). Derived key set = `list(ArtifactKind)`.
  3. **Three-way `anti pattern` disambiguation** (do not conflate): `ArtifactKind.ANTI_PATTERN` (enum
     member — gets its OWN disposition in the completeness map, bound to neither the class nor the DRG
     string), `NodeKind.ANTI_PATTERN` (DRG string, no backing class), and `styleguides/models.py:AntiPattern`
     (a real `BaseModel`). All three are distinct.
- **Files**: `tests/docs/diagram_drift/binding_table.py`.

### Subtask T027 – The guard engine

- **Steps**:
  1. `tests/docs/diagram_drift/guard.py`:
     - **Model-side field extraction** dispatched by family: Pydantic (`FieldInfo.alias or name` +
       recurse into nested `BaseModel` fields), dataclass (`fields()`), StrEnum (`list()`).
     - **Diagram-side field extraction**: parse the `@startyaml` block text, collect top-level keys,
       recurse into nested sub-maps, exclude scalar example values.
     - **Compare** and return a structured diff (missing-in-diagram / extra-in-diagram).
     - **Patchable seams (REQUIRED for the non-fakeable tests)**: expose the kind-set and per-model
       field-set through overridable functions — e.g. `_artifact_kind_values() -> list[str]` (returns
       `[k.value for k in ArtifactKind]`) and the model→fields extractor — so T028/T030 can monkeypatch
       *those* to inject a synthetic kind / nested field. **You cannot add a member to a StrEnum at
       runtime** (subclassing a StrEnum-with-members raises `TypeError`; member assignment raises), and
       the models are `frozen=True, extra="forbid"` — so the injection MUST go through the seam, never
       by mutating the enum or the pydantic class.
  2. Pure stdlib + pydantic (already a dep). No new third-party deps.
- **Files**: `tests/docs/diagram_drift/guard.py`, `tests/docs/diagram_drift/__init__.py`.

### Subtask T028 – Completeness-over-ALL-kinds test

- **Steps**: derive the expected key set from `list(ArtifactKind)` + the priority-artefact list; assert
  every member has a disposition in the binding table. Two complementary forcing tests (neither fakeable):
  1. **Synthetic-kind injection via the seam**: `monkeypatch` `guard._artifact_kind_values()` to return
     the real values **plus** a synthetic string, and assert the guard **FAILS** until that string carries
     a disposition. (Do NOT try to extend the StrEnum — infeasible; patch the seam.)
  2. **Delete-a-disposition**: remove an existing member's entry (e.g. `anti_pattern`) from the binding
     table and assert the guard **FAILS** — this forces the completeness derivation to actually read
     `list(ArtifactKind)` (a stand-in key set would not catch it). Covers ALL kinds, not just the 4 priority.
- **Files**: `tests/docs/test_diagram_drift_guard.py`.

### Subtask T029 – Omit-a-field + AntiPattern-vs-anti_pattern tests

- **Steps**:
  1. **Omit-a-field**: take a bound diagram, remove one field from the parsed diagram set (fixture), and
     assert the guard FAILS (proves it catches diagram-missing-a-model-field, not only model-gains-field).
  2. **Binding hygiene**: assert the guard binds `styleguides/models.py:AntiPattern` (a real class) and
     the DRG `anti_pattern` NodeKind (a string, no class) as **distinct** — a diagram bound to one must
     not be validated against the other.
- **Files**: `tests/docs/test_diagram_drift_guard.py`.

### Subtask T030 – Nested depth-2 test

- **Steps**: force a nested-model drift on a genuinely **nested** value-object —
  `AgentProfileSchema → AgentSpecialization` (verified real at `schema_models.py:78,237`) or
  `MissionStepContract → MissionStepContractStep → inputs` (depth-3) — by patching the **extracted
  field set for the nested model via the seam** (the models are `frozen=True, extra="forbid"`, so you
  cannot add an attribute), and assert the guard FAILS (proves transitive nested recursion runs). Because
  WP05's shipped agent-profile diagram (T035) binds this nested model, the guard already exercises the
  recursion on the **real corpus** — this test pins the failure direction. **Do NOT use the DRG — it is FLAT.**
- **Files**: `tests/docs/test_diagram_drift_guard.py`.

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- `python3 -m pytest tests/docs/test_diagram_drift_guard.py -q`. No docker needed.
- The guard runs on the **real** WP05–WP07 diagrams (must pass) AND the four injected regressions (must
  fail closed). ATDD RED-first: commit the failing tests before the engine satisfies them.

## Risks & Mitigations

- **Fake-green via naive `model_fields` compare** → misses alias/nested drift. Mitigation: `FieldInfo.alias
  or name` + transitive recursion; the nested + omit tests pin it.
- **Literal counts creep in** → violates C-003. Mitigation: derive every member/count via `list(...)`;
  add a test that greps the guard + diagrams for suspicious integer literals if practical.
- **Synthetic-member injection leaks** → pollutes other tests. Mitigation: scope the monkeypatch to the test.

## Review Guidance

- Confirm all four non-fakeable tests exist and genuinely fail on their injected regression.
- Confirm the binding table dispositions EVERY `ArtifactKind` member (completeness).
- Confirm alias normalization + transitive nested recursion (not naive `model_fields`).
- Confirm no literal counts; everything via `list(...)`/`fields()`/`model_fields`.
- Reviewer ≠ implementer; verify RED-first.

## Activity Log

> Append newest entries at the END, chronological.
