---
mission_slug: migration-shim-ownership-rules-01KPDYDW
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
generated_at: "2026-04-19T12:50:41Z"
target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: main
---

# Tasks — Migration and Shim Ownership Rules

**Mission**: `migration-shim-ownership-rules-01KPDYDW`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW` → merges into `main`

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------:|
| T001 | Audit existing shims: grep `src/specify_cli/` for `__deprecated__`; document zero-shim baseline | WP01 | | [D] |
| T002 | Confirm `packaging` is an explicit dep in `pyproject.toml`; add if absent | WP01 | [D] |
| T003 | Create `src/specify_cli/compat/` package (`__init__.py` with public exports) | WP02 | | [D] |
| T004 | Implement `src/specify_cli/compat/registry.py`: load + validate `shim-registry.yaml` | WP02 | | [D] |
| T005 | Implement `src/specify_cli/compat/doctor.py`: `check_shim_registry()` engine | WP02 | | [D] |
| T006 | Add `spec-kitty doctor shim-registry` subcommand to `src/specify_cli/cli/commands/doctor.py` | WP03 | | [D] |
| T007 | Write `architecture/2.x/shim-registry.yaml` (initial empty registry) | WP04 | | [D] |
| T008 | Write `architecture/2.x/06_migration_and_shim_rules.md` (rulebook, 4 rule families + worked example) | WP04 | [D] |
| T009 | Write `tests/architectural/test_shim_registry_schema.py` (FR-011 schema validation) | WP05 | | [D] |
| T010 | Write `tests/architectural/test_unregistered_shim_scanner.py` (FR-010 AST scanner) | WP05 | [D] |
| T011 | Write `tests/doctor/test_shim_registry.py` (FR-009 CLI integration) | WP06 | | [D] |
| T012 | Update `CHANGELOG.md` with Unreleased/Added entry (FR-015) | WP06 | [D] |

---

## Work Packages

### WP01 — Package Bootstrap and Dependency Hygiene

**Goal**: Establish the `src/specify_cli/compat/` package, verify the zero-shim baseline, and lock the `packaging` dependency.
**Priority**: Critical — WP02 and WP05 depend on this package existing.
**Estimated prompt size**: ~280 lines
**Dependencies**: none

**Included subtasks**:
- [x] T001 Audit existing shims: grep `src/specify_cli/` for `__deprecated__`; document zero-shim baseline (WP01)
- [x] T002 Confirm `packaging` is an explicit dep in `pyproject.toml`; add if absent (WP01)
- [x] T003 Create `src/specify_cli/compat/` package (`__init__.py` with public exports) (WP01)

**Implementation sketch**:
1. Grep `src/specify_cli/` for `__deprecated__ = True`; commit the empty result as the baseline fact in a code comment inside `compat/__init__.py`.
2. Check `pyproject.toml` `[project.dependencies]` for `packaging`; add `packaging>=23.0` if absent; run `uv sync` to confirm resolution.
3. Create `src/specify_cli/compat/__init__.py` with public re-exports stub (initially empty; filled in by WP02).

**Parallel opportunities**: T002 can run in parallel with T001 (different files).
**Risks**: `src/specify_cli/shims/` is an unrelated domain (agent-skill shims); do not confuse it with the compat package.
**Owned files**: `src/specify_cli/compat/`, `pyproject.toml`

---

### WP02 — Registry Loader and Doctor Engine

**Goal**: Implement the Python infrastructure that loads and validates `shim-registry.yaml` and classifies each entry into pending/overdue/grandfathered/removed states.
**Priority**: Critical — WP03 (CLI) and WP05/WP06 (tests) depend on this.
**Estimated prompt size**: ~420 lines
**Dependencies**: WP01

**Included subtasks**:
- [x] T004 Implement `src/specify_cli/compat/registry.py`: load + validate `shim-registry.yaml` (WP02)
- [x] T005 Implement `src/specify_cli/compat/doctor.py`: `check_shim_registry()` engine (WP02)

**Implementation sketch**:
1. `registry.py`: `load_registry(repo_root) -> list[ShimEntry]`, `validate_registry(entries) -> None | raise RegistrySchemaError`. Uses `ruamel.yaml` safe loader. Manual field-by-field validation per data-model.md rules. `ShimEntry` is a frozen dataclass.
2. `doctor.py`: `check_shim_registry(repo_root) -> ShimRegistryReport`. Reads `pyproject.toml` via `tomllib`, calls `load_registry`, classifies entries (R1 semver comparison via `packaging.version.Version`, R6 file-existence probe), returns structured `ShimRegistryReport` dataclass with per-entry status and exit-code recommendation.
3. Update `compat/__init__.py` to re-export `check_shim_registry`, `ShimRegistryReport`, `RegistrySchemaError`.

**Parallel opportunities**: none (T005 depends on T004).
**Risks**: Pre-release version strings (`3.2.0a3`) must round-trip correctly through `packaging.version.Version`.
**Owned files**: `src/specify_cli/compat/registry.py`, `src/specify_cli/compat/doctor.py`, `src/specify_cli/compat/__init__.py`

---

### WP03 — CLI Doctor Subcommand

**Goal**: Wire `spec-kitty doctor shim-registry` into the existing doctor command group following the established doctor.py pattern.
**Priority**: High — needed for CI enforcement (FR-009).
**Estimated prompt size**: ~300 lines
**Dependencies**: WP02

**Included subtasks**:
- [x] T006 Add `spec-kitty doctor shim-registry` subcommand to `src/specify_cli/cli/commands/doctor.py` (WP03)

**Implementation sketch**:
1. Add `@app.command(name="shim-registry")` to `doctor.py` following the exact pattern of the `identity` subcommand: import `check_shim_registry` inside the handler, call `locate_project_root()`, handle missing project gracefully (exit 2).
2. Render a Rich table with columns: `legacy_path`, `canonical_import`, `removal_target`, `status` (color-coded: pending=cyan, overdue=red, grandfathered=yellow, removed=dim).
3. Print a summary footer: count per status, per-overdue remediation block (per data-model.md Entity 4).
4. Exit codes: 0 (all ok), 1 (any overdue), 2 (config/registry error).
5. Support `--json` flag for CI machine-readable output (same structural convention as `doctor identity --json`).

**Parallel opportunities**: none (single subtask).
**Risks**: Exit code 2 for config error must be distinct from exit 1 (overdue) — preserve that distinction.
**Owned files**: `src/specify_cli/cli/commands/doctor.py`

---

### WP04 — Architecture Artifacts (Rulebook + Registry)

**Goal**: Write the human-readable rulebook and the initial empty machine-readable shim registry.
**Priority**: High — downstream missions (#612, #613, #614) cite these artifacts.
**Estimated prompt size**: ~380 lines
**Dependencies**: none (can run in parallel with WP01)

**Included subtasks**:
- [x] T007 Write `architecture/2.x/shim-registry.yaml` (initial empty registry) (WP04)
- [x] T008 Write `architecture/2.x/06_migration_and_shim_rules.md` (rulebook) (WP04)

**Implementation sketch**:
1. `shim-registry.yaml`: top-level `shims: []`. Add a YAML comment block at the top citing the schema contract (`contracts/shim-registry-schema.yaml`) and the rulebook section for new entries.
2. `06_migration_and_shim_rules.md`: structured around 4 rule families:
   - (a) **Schema/version gating** — current schema-version contract; reference #461 Phase 7 for doctrine extension (FR-013).
   - (b) **Bundle/runtime migration authoring contract** — migration module shape, idempotency, test expectations.
   - (c) **Compatibility shim lifecycle** — canonical shim module shape (copy-paste template with 6 mandatory attributes), one-release deprecation window, extension mechanism (FR-003, FR-004).
   - (d) **Removal plans and registry contract** — registry schema summary, removal-PR contract (FR-005), `doctor shim-registry` usage.
3. Section 7: worked example mapping `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` to each rule family per R5 decision. If #610 already removed `specify_cli.charter`, document the "no-shim baseline case."
4. Cross-reference `architecture/2.x/05_ownership_map.md` per FR-014.

**Parallel opportunities**: T007 and T008 are independent files and can be written in parallel.
**Risks**: Worked example content must accurately reflect the state of the charter mission's artifacts at write time.
**Owned files**: `architecture/2.x/06_migration_and_shim_rules.md`, `architecture/2.x/shim-registry.yaml`

---

### WP05 — Architectural Tests (Schema + Scanner)

**Goal**: Add the two architectural pytest files that enforce the registry contract and detect unregistered shims.
**Priority**: High — these are the CI enforcement gates per FR-010 and FR-011.
**Estimated prompt size**: ~350 lines
**Dependencies**: WP01 (compat package), WP04 (registry file exists)

**Included subtasks**:
- [x] T009 Write `tests/architectural/test_shim_registry_schema.py` (FR-011 schema validation) (WP05)
- [x] T010 Write `tests/architectural/test_unregistered_shim_scanner.py` (FR-010 AST scanner) (WP05)

**Implementation sketch**:
1. `test_shim_registry_schema.py`:
   - Fixture: load `architecture/2.x/shim-registry.yaml` via `repo_root` (available from `tests/architectural/conftest.py`).
   - Parametrize: valid full entry, missing required field, wrong type for `grandfathered`, bad semver, invalid `tracker_issue`, `removal_target_release < introduced_in_release`.
   - Assert `validate_registry()` raises `RegistrySchemaError` with field name in message for each invalid case.
   - Assert the live registry (`shims: []`) passes validation.
2. `test_unregistered_shim_scanner.py`:
   - Walk `src/specify_cli/` for `.py` files; parse via `ast`, detect `__deprecated__ = True`.
   - Load registry; build set of `legacy_path` values.
   - Assert scanner-set ⊆ registry-set. On failure: print each unregistered path clearly.
   - Synthetic case (tmp_path): write a fake `__deprecated__ = True` module, assert scanner picks it up.

**Parallel opportunities**: T009 and T010 are independent test files; can be written in parallel.
**Risks**: AST scanner must handle both `__deprecated__ = True` and `__deprecated__: bool = True` annotation forms.
**Owned files**: `tests/architectural/test_shim_registry_schema.py`, `tests/architectural/test_unregistered_shim_scanner.py`

---

### WP06 — CLI Integration Tests and Changelog

**Goal**: Cover the `doctor shim-registry` CLI surface with integration tests and add the CHANGELOG entry.
**Priority**: Medium — polishes the delivery; tests WP03 end-to-end.
**Estimated prompt size**: ~330 lines
**Dependencies**: WP03 (CLI exists), WP04 (registry file exists)

**Included subtasks**:
- [x] T011 Write `tests/doctor/test_shim_registry.py` (FR-009 CLI integration) (WP06)
- [x] T012 Update `CHANGELOG.md` with Unreleased/Added entry (FR-015) (WP06)

**Implementation sketch**:
1. `test_shim_registry.py`: Use `typer.testing.CliRunner` (same pattern as `tests/doctor/test_identity_audit.py`). Scenarios:
   - Empty registry → exit 0, table header shown.
   - Pending entry (target > current version, shim file absent or present) → exit 0, status `pending`.
   - Overdue entry (target ≤ current version, shim file present) → exit 1, overdue block in output.
   - Grandfathered entry → exit 0, advisory text, never exit 1.
   - Removed entry (target ≤ current version, shim file absent) → exit 0, `removed` status.
   - Missing `pyproject.toml` → exit 2 with config-error message.
   - Missing `shim-registry.yaml` → exit 2 with config-error message.
   - `--json` flag: validate JSON keys match schema.
2. `CHANGELOG.md`: Under `## [Unreleased]` → `### Added`:
   - `architecture/2.x/06_migration_and_shim_rules.md` — compatibility shim lifecycle rulebook.
   - `architecture/2.x/shim-registry.yaml` — machine-readable shim registry.
   - `spec-kitty doctor shim-registry` — CI enforcement check for overdue shims.

**Parallel opportunities**: T012 (CHANGELOG) can be written in parallel with T011.
**Risks**: CLI runner tests must use `tmp_path` fixtures with synthetic `pyproject.toml` and registry files to avoid coupling tests to the live project version.
**Owned files**: `tests/doctor/test_shim_registry.py`, `CHANGELOG.md`
