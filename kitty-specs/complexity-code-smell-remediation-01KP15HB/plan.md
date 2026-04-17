# Implementation Plan: Complexity and Code Smell Remediation

**Branch**: `feat/complexity-debt-remediation` | **Date**: 2026-04-12 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/complexity-code-smell-remediation-01KP15HB/spec.md`

---

## Summary

Structural refactoring of four functional slices — status, charter, doctrine, kernel — to eliminate
65 `# noqa: C901` suppressions and drive down 23 Sonar CRITICAL S3776 violations. No behaviour
changes; all public contracts remain stable. Fourteen functional requirements decompose into four
parallel work packages across three execution lanes. The refactoring procedure governs every WP:
characterize → lock with tests → apply tactic → verify quality gates.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (strict), ruff
**Storage**: Filesystem only — no database changes
**Testing**: pytest; characterization tests required before each structural change (DIRECTIVE_034)
**Target Platform**: Linux / macOS / Windows 10+ (cross-platform CLI)
**Project Type**: Single Python project
**Performance Goals**: No regression to < 2 s CLI response time
**Constraints**: Zero behaviour changes; zero new ruff/mypy suppressions; NFR-001–NFR-004 gates
**Scale/Scope**: ~14 functions across 4 slices; 27 call-site files for largest change (FR-001)

---

## Charter Check

*GATE: Must pass before Phase 0. Re-checked after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | ✓ Pass | All modified files are pure Python 3.11+ |
| mypy --strict | ✓ Pass | NFR-002 mandates zero new mypy errors |
| pytest ≥ 90% coverage for new code | ✓ Pass | NFR-003 + DIRECTIVE_034 mandate characterization tests before changes |
| No `--feature` CLI flag in new code | ✓ Pass | No CLI surface added; refactoring only |
| No spec-kitty-events local path dependency | ✓ Pass | No dependency changes |
| No behaviour changes | ✓ Pass | C-003 is an absolute constraint |
| Charter terminology canon (Mission, not Feature) | ✓ Pass | No user-facing strings modified |

No charter violations. No complexity tracking required.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/complexity-code-smell-remediation-01KP15HB/
├── spec.md              # Specification
├── plan.md              # This file
├── research.md          # Phase 0 output (call-site maps, DRG status, interface drafts)
├── data-model.md        # Phase 1 output (TransitionRequest, GuardContext, BaseDoctrineRepository[T])
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not yet created)
```

### Source Code (affected paths only)

```
src/specify_cli/status/
├── emit.py              # FR-001: emit_status_transition boundary reduction
├── transitions.py       # FR-003: validate_transition + _run_guard parameter consolidation
├── wp_metadata.py       # FR-002: resolved_agent CC reduction; FR-004: exception chain fix
├── locking.py           # FR-005: FeatureStatusLockTimeout → FeatureStatusLockTimeoutError

src/charter/
├── extractor.py         # FR-006: _extract_governance dispatch table (CC 28 → ≤ 10)
├── resolver.py          # FR-007: resolve_governance decomposition (conditional on C-001)
├── compiler.py          # FR-008: _build_references_from_service parameter reduction
├── context.py           # FR-009: named depth constants
├── parser.py            # FR-010: else:if → elif (line 170)

src/doctrine/
├── <repositories>/      # FR-011: shared _load() via common base
└── curation/workflow.py # FR-012: CurationAborted → CurationAbortedError
src/doctrine/agent_profiles/repository.py  # FR-013: named workload constants

src/kernel/
├── atomic.py            # FR-014: TC003, PTH, I001 fixes
├── _safe_re.py          # FR-014: import organization
└── glossary_runner.py   # FR-014: import organization

tests/
└── (characterization tests added per-WP before structural changes)
```

---

## Work Package Decomposition

Four work packages across three parallel execution lanes. All lanes are independent
of each other and may proceed concurrently. Within Lane A, WP02 follows WP01.

| WP | Lane | FRs | Primary work | Relative size |
|----|------|-----|-------------|---------------|
| WP01 | A | FR-001, FR-003 | Status parameter objects (call sites: ~35 files) | Large |
| WP02 | A | FR-002, FR-004, FR-005 | Status CC reduction, chain fix, rename | Medium |
| WP03 | B | FR-006, FR-007*, FR-008, FR-009, FR-010 | Charter dispatch + decomposition | Medium |
| WP04 | C | FR-011, FR-012, FR-013, FR-014 | Doctrine base class + kernel imports | Medium |

*FR-007 is conditional on C-001 (DRG rebuild gate). The implementer must check before starting.

### Dependency graph

```
WP01 → WP02    (Lane A: status, sequential — same module namespace)
WP03           (Lane B: charter, independent)
WP04           (Lane C: doctrine + kernel, independent)
```

### Lane rationale

- **Lane A** (status): WP01 and WP02 both modify `src/specify_cli/status/` — sequential to
  prevent merge conflicts. WP01 first because parameter-object call sites must stabilise before
  the CC reduction in WP02 can be cleanly committed.
- **Lane B** (charter): Entirely isolated to `src/charter/`. No inter-lane dependency.
- **Lane C** (doctrine + kernel): `src/doctrine/` and `src/kernel/` are in separate namespaces;
  bundled into one WP because FR-014 (kernel) is trivial and benefits from a single quality-gate run.

---

## Phase 0: Research

See `research.md` for full findings. Summary:

### R-01 — DRG rebuild EPIC status (governs FR-007)

**Finding**: No active DRG rebuild mission exists in `kitty-specs/` as of 2026-04-12. FR-007 is
**unblocked**. Implementer must re-verify at WP03 start; if a DRG mission appears, defer FR-007
and complete FR-006, FR-008, FR-009, FR-010 only.

### R-02 — emit_status_transition call-site map (governs WP01 scope)

**Finding**: 27 files import or call `emit_status_transition`. The function has 19 parameters
(4 positional, 15 keyword-only). The natural grouping for a parameter object is:

| Group | Parameters | Rationale |
|-------|-----------|-----------|
| Identity | `feature_dir`, `mission_dir`, `mission_slug`, `_legacy_mission_slug`, `repo_root` | Locate the mission |
| Transition | `wp_id`, `to_lane`, `force`, `reason` | Describe the state change |
| Actor | `actor`, `execution_mode` | Who is making the change |
| Evidence | `evidence`, `review_ref`, `review_result` | Supporting context |
| Guard hints | `workspace_context`, `subtasks_complete`, `implementation_evidence_present`, `policy_metadata` | Guard condition inputs |

A `TransitionRequest` dataclass capturing these groups can reduce the public boundary to 1 positional
parameter while keeping all fields named and discoverable.

### R-03 — validate_transition / _run_guard call-site map (governs WP01 scope)

**Finding**: `validate_transition` appears in 10 files; `_run_guard` in 3 files (internal).
The 10 keyword-only parameters of `validate_transition` map cleanly onto a `GuardContext` struct
(same fields as the `_run_guard` signature minus `from_lane`/`to_lane`).

### R-04 — Doctrine _load() duplication pattern (governs FR-011)

**Finding**: 7 sub-repositories each implement `_load()` with the same 3-step pattern:
1. Walk the YAML directory (`_dir`)
2. Parse each file with `self._schema.model_validate(yaml_data)`
3. On parse failure: emit a warning, skip the entry

The generic base can be `BaseDoctrineRepository[T](ABC)` with `_schema: type[T]` and `_dir: Path`
as abstract properties, and a concrete `_load() -> dict[str, T]` implementation.

---

## Phase 1: Design

See `data-model.md` for full interface contracts.

### New constructs introduced

#### `TransitionRequest` (status slice — WP01)

Dataclass consolidating all inputs to `emit_status_transition`. Lives in
`src/specify_cli/status/models.py` alongside `StatusEvent` and `StatusSnapshot`.

Key design decisions:
- All fields optional with `None` defaults (preserves the existing "pass only what you need" ergonomics)
- `feature_dir` and `mission_dir` remain the two path resolution inputs (no change to resolution logic)
- No validation in the dataclass itself — existing validation in `emit_status_transition` body moves to a `_validate_request()` helper
- Migration: implement `TransitionRequest`, update `emit_status_transition` to accept it as its first positional argument (keeping old kwargs as a deprecated but functional path for one release cycle)

#### `GuardContext` (status slice — WP01)

Dataclass consolidating guard condition inputs. Lives in `src/specify_cli/status/transitions.py`
(same file as `_run_guard` and `validate_transition`, to keep locality).

Key design decisions:
- Fields map 1:1 to current `_run_guard` keyword parameters
- `validate_transition` constructs `GuardContext` from its own keyword arguments, delegates to `_run_guard(from_lane, to_lane, ctx)`
- `_run_guard` signature becomes `(from_lane, to_lane, ctx: GuardContext) -> tuple[bool, str | None]`

#### `BaseDoctrineRepository[T]` (doctrine slice — WP04)

Generic abstract base class. Lives in `src/doctrine/base.py` (new file).

Key design decisions:
- `T` bound to `BaseModel` (Pydantic)
- Abstract properties: `_schema: type[T]`, `_dir: Path`
- Concrete method: `_load() -> dict[str, T]` (the shared walk + parse + warn pattern)
- Migration path: convert one repository at a time (strangler-fig); each class shrinks to 3 lines (properties + no `_load()` override)

### Quality gate sequence (per WP)

Each WP follows this strict sequence per DIRECTIVE_034 and the refactoring procedure:

```
1. Read the function(s) to be refactored (confirm baseline CC)
2. Write characterization tests covering all observed behaviours
3. Verify tests pass against current code (green baseline)
4. Apply one tactic at a time
5. Run: ruff check src/ && mypy src/ && pytest tests/
6. All gates green → commit; if red → revert tactic and diagnose
7. Repeat steps 4–6 for each tactic in the WP
```

### Agent context update

No agent-specific context update is required — this mission creates no new CLI commands,
no new configuration keys, and no new public API surface. The quality gate sequence above
is sufficient operational guidance for implementing agents.

### Placement principle for extracted logic

**Every extraction decision has two parts: what to extract, and where to put it.**

When decomposing a complex function, the extracted helpers default to the same module
(local private functions). That is correct for logic that is tightly coupled to local
domain concerns. However, when an extracted function turns out to be generic — i.e., it
has no dependency on local types, config, or domain invariants — the implementing agent
**must** evaluate whether it belongs in `src/kernel/` instead.

#### What "generic" means in this codebase

A helper is generic (and therefore a candidate for `kernel/`) if ALL of the following hold:
1. Its parameters are plain Python types or stdlib types (`str`, `Path`, `dict`, etc.) — not
   domain models like `GovernanceConfig`, `StatusSnapshot`, or `WPMetadata`
2. It would be useful unchanged in at least one other slice (status, charter, doctrine, kernel)
3. It has no side effects tied to local state (no `self`, no closure over module globals)

Examples that ARE generic: string normalization, path existence checks, depth-bounded
directory walking, YAML-safe-load wrappers, slug normalization, pattern matching against
a configurable regex, throttled warning emission.

Examples that are NOT generic: `_resolve_agent_from_dict` (depends on `AgentAssignment`),
`_handle_paradigms` (depends on `GovernanceConfig`), `_load` in doctrine repositories
(generic in structure, but scoped to the doctrine ABC — stays in `doctrine/base.py`).

#### How to apply this during implementation

When you extract a function and its signature contains only `str`, `Path`, `int`, `float`,
`bool`, `dict`, `list`, or `None`:

1. **Check `src/kernel/` first**: does a utility with this behaviour already exist?
   If yes, use it. If close but not exact, consider extending the existing utility.
2. **Check for logical duplication**: search for the same pattern in other slices
   (`rg` the key operation). If two or more slices independently implement the same
   primitive, that is a signal that `kernel/` is missing a utility function.
3. **If neither above applies**: place the helper as a local private function in the
   current module. Do not create a new `kernel/` file for a single use-case.

#### Kernel module conventions

New utilities added to `src/kernel/` must:
- Follow the existing module structure (one file per concern: `atomic.py`, `_safe_re.py`, etc.)
- Be free of imports from `specify_cli`, `charter`, or `doctrine`
- Have unit tests in `tests/kernel/`
- Pass mypy and ruff on the first commit

If in doubt, keep it local. Do not over-abstract. The principle guards against duplication,
not against simplicity.

---

## Branch Contract (final)

| Field | Value |
|-------|-------|
| Current branch at plan start | `feat/complexity-debt-remediation` |
| Planning base branch | `feat/complexity-debt-remediation` |
| Final merge target | `feat/complexity-debt-remediation` |
| Branch matches target | ✓ Yes |

Completed work packages merge into `feat/complexity-debt-remediation`. The overall feature branch
(`feat/complexity-debt-remediation`) then merges into `main` via PR after all WPs are merged.

---

*Next step: `/spec-kitty.tasks` to generate work package task files.*
