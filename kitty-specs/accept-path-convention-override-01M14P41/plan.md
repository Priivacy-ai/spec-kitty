# Implementation Plan: Accept path-convention portability

**Branch**: `fix/accept-path-convention-override` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/accept-path-convention-override-01M14P41/spec.md`

## Summary

Add a project-level `path_conventions` override (`.kittify/config.yaml` → `project.path_conventions`)
resolved **ahead of** mission-type doctrine `paths:` defaults, so a repo whose real source layout is
not `src/` (Django `apps/`, Go `internal/`) is honestly accepted without fabricating an empty
directory. The override is a **value channel only** — blocking-by-default policy (merged as #3783) is
preserved. Technical approach: one new typed project-config section reader (WP01), a single upstream
composition merge into `declared` inside `validate_mission_paths` before the per-key loop (WP02, the
enforcement of C-008 and the ≤15 complexity gate), all-four-mission-types + Go coverage by construction
(WP03), and a severable fold of tech-debt #3785 (`_missing_artifacts` reads
`mission.config.artifacts.optional`) as WP04.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (config read), pydantic-style `MissionConfig` dataclass; no new third-party dependency
**Storage**: Files — `.kittify/config.yaml` (project config), `mission.yaml` (doctrine defaults); no database
**Testing**: pytest (`PWHEADLESS=1 pytest -n auto --dist loadfile`); unit via `_MissionStub`, integration via the `feature_repo` fixture in `tests/cross_cutting/misc/test_acceptance_support.py`
**Target Platform**: Linux/macOS/Windows CLI (the `spec-kitty` tool)
**Project Type**: single (CLI library under `src/specify_cli/`)
**Performance Goals**: no accept-path latency regression; override adds ≤1 config read/run, no per-key filesystem re-read (NFR-002 structural bound)
**Constraints**: `validate_mission_paths`/`evaluate_path_conventions` complexity ≤15 (ruff C901 / Sonar S3776); current `validate_mission_paths` is 12/15 — compose the override before the per-key loop (NFR-003, C-008); no new blanket `# noqa`/`# type: ignore`; ruff + mypy --strict clean
**Scale/Scope**: ~4 source files touched (`validators/paths.py`, `acceptance/summary_core.py`, `acceptance/__init__.py`, `mission.py`) + 1 new config-reader module + 1 ADR + tests; both `mission.yaml` trees only if doctrine values change (they should NOT — the override supersedes without editing doctrine)

**No `[NEEDS CLARIFICATION]` remain** — design settled by the pre-spec and post-spec adversarial squads.

## Constitution Check (Charter)

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

Charter present (`.kittify/charter/charter.md`). Action-critical gates for this mission:

- **DIRECTIVE_001 (Architectural Integrity):** override boundary is explicit — project config is the
  authority for project layout; doctrine remains the authority for defaults. No new circular
  dependency; the config reader is a leaf. **PASS** (C-008 enforces the single boundary seam).
- **DIRECTIVE_043 (Close defect class by construction):** generic override at the one shared seam →
  all four mission types fixed at once, no per-type branch. **PASS.**
- **DIRECTIVE_044 (Canonical sources):** one typed section reader (C-004); extract `valid_path_keys`
  to a shared constant rather than re-declare (C-005). **PASS by design.**
- **DIRECTIVE_030/034 (Test-and-typecheck gate / test-first):** every FR/NFR maps to a red-first test
  (see quickstart). **PASS by design.**
- **DIRECTIVE_003 (Decision documentation):** one ADR records the precedence order + non-reversal of
  #3783 (C-006), authored inside WP02 (not a standalone action-WP → avoids the #3590 no-terminal-state
  trap). **PASS.**
- **Terminology Canon:** no `feature*` aliases introduced; config key is `path_conventions`. **PASS.**
- **Supply-chain (051):** no dependency added/upgraded/removed → section N/A (advisory, documented as
  no-op in research.md).

No charter violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/accept-path-convention-override-01M14P41/
├── plan.md              # This file
├── research.md          # Phase 0 — squad-consolidated decisions
├── data-model.md        # Phase 1 — override entity + resolved-path composition
├── quickstart.md        # Phase 1 — test map + dev walkthrough
├── contracts/           # Phase 1 — precedence + config-schema contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── config/
│   └── path_conventions.py        # NEW (WP01): typed reader; reads project.path_conventions subkey (C-011); fail-closed section (FR-008)
├── mission.py                     # WP01: extract VALID_PATH_KEYS → shared constant (C-005)
├── validators/
│   └── paths.py                   # WP01: merge override into `declared` at line 199, before comprehension + artifact check (C-008, C-010, NFR-003)
└── acceptance/
    ├── summary_core.py            # WP01: read override in evaluate_path_conventions (repo_root in scope), pass into validate_mission_paths
    └── __init__.py                # WP03: _missing_artifacts reads mission.config.artifacts.optional (#3785)

docs/adr/3.x/
└── 2026-08-28-<n>-project-path-convention-override-precedes-doctrine.md   # WP01 (C-006)

tests/
├── specify_cli/config/test_path_conventions_reader.py      # WP01
├── agent/test_validators_unit.py                           # WP02: _MissionStub apps/ + override
├── specify_cli/acceptance/test_acceptance_cores.py         # WP02/WP03: evaluate_path_conventions seam
├── cross_cutting/misc/test_acceptance_support.py           # WP02: no-override regression (beside :767) + apps/ integration
└── specify_cli/acceptance/test_missing_artifacts_from_config.py  # WP04 (#3785)
```

**Structure Decision**: Single CLI library. The override is introduced as a new leaf module under
`src/specify_cli/config/` and wired at the existing `validate_mission_paths`/`evaluate_path_conventions`
seam. No doctrine `mission.yaml` edits (C-002). Arch-gate re-pin (dead-symbol / shard-orphan /
golden-count) budgeted in WP02 where the new symbol / `PathValidationResult` parameter is introduced
(C-007).

## Complexity Tracking

No Constitution violations — table intentionally empty. The one complexity risk (`validate_mission_paths`
at 12/15) is handled by NFR-003/C-008 (compose before the loop, or extract `_resolve_required_paths`),
not by a justified violation.

## Parallel Work Analysis

> **WP restructure (post-plan brownfield squad):** the former WP01 (reader) and WP02 (merge+seam) are
> UNIFIED into one anchor WP — a reader reviewed in isolation trips the dead-symbol gate (its only `src/`
> caller lands in the wiring WP; tests don't count as callers). Reader + its caller land together.

### Dependency Graph

```
WP01 (config reader + valid_path_keys extraction + precedence merge + seam wiring + ADR + re-pin)  [ANCHOR]
        │  override honored end-to-end; no-override regression pinned; SC-006 discriminator green
        ▼
WP02 (all-four-types + Go coverage — TEST-ONLY)     WP03 (#3785 optional-artifact fold)  [SEVERABLE]
   depends on WP01 (test-additive)                    independent module; sequence last
```

### Work Distribution

- **WP01 [ANCHOR]** — owned files: `config/path_conventions.py` (new, **omit `__all__` OR ship with its
  caller**), `mission.py` (extract `VALID_PATH_KEYS`), `validators/paths.py` (merge at **line 199**,
  before the `required_paths` comprehension), `acceptance/summary_core.py` (read override in
  `evaluate_path_conventions`, which already has `repo_root`), the ADR (`docs/adr/3.x/…`). Reader
  fail-closed on **section shape** must be **built** (the preflight template is lenient — do not inherit
  its `except→default` swallow). `done` = software-dev accepts on `apps/`; no-override regression pins
  exact payload + `format_errors()`; SC-006 (declared-but-absent still blocks) green; arch-gate pins
  refreshed (C-007).
- **WP02** — **STRICTLY TEST-ONLY** (no residual seam edits; any seam fix routes back to WP01). Owned:
  new test files for the other three mission types + Go `internal/`. The NFR-004b single-caller guard
  lives here as a plain unit test **outside `tests/architectural/`** (dodges shard-orphan + golden-count
  cascade); new-dir tests use frozenset/dict-equality, not `len()==N`.
- **WP03 [SEVERABLE, P3]** — owned: `acceptance/__init__.py::_missing_artifacts` (+ call-site reorder:
  fetch `mission` before the call, `None` fallback) + its test. Independent of WP01's files → can run
  parallel to WP02 after WP01.

### Coordination Points

- **Sequential**: WP01 first (WP02/WP03 both depend on it). WP02 ∥ WP03 after (no file overlap —
  WP02 test-only, WP03 owns `acceptance/__init__.py`).
- **Integration tests**: `feature_repo` fixture exercises `apps/` end-to-end (WP01/WP02).
- **Split-tripwire (WP03)**: if #3785 forces any `contracts/` dedup/severity change or exceeds the
  `_missing_artifacts` signature + call-site reorder, split it back to its own mission (C-003/C-009).
- **Cross-links (coordinate, not fold):** #2652 (mission.yaml two-tree retirement), #3495 (sibling
  `project`-scoped config surface), #3084 / #2744 (accept-gate neighbours), #2330 (Item 1 folded).
