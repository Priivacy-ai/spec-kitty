# Phase 0 Research — Migration and Shim Ownership Rules

**Mission**: `migration-shim-ownership-rules-01KPDYDW`
**Date**: 2026-04-17
**Spec refs**: FR-001..FR-015, C-001..C-007, NFR-001..NFR-005

---

## R1. Semver comparator for `removal_target_release` checks

**Decision**: Use `packaging.version.Version` for all semver comparisons in the doctor subcommand and schema test.

**Rationale**:
- `packaging` is battle-tested (official PyPA tooling) and handles pre-release suffixes (`3.2.0a3`, `3.3.0rc1`) correctly — critical because the current project version (per `pyproject.toml`) today is `3.1.2a3`.
- `Version("3.3.0") >= Version("3.2.0")` returns `True`; `Version("3.3.0") >= Version("3.3.0a1")` also returns `True` (stable ≥ pre-release) — matches intended semantics: once a stable release reaches the removal target, the shim must go.
- No hand-rolled regex required for comparison; semver-shape *validation* is a separate concern (see R3).

**Alternatives considered**:
- **Hand-rolled tuple parser** — rejected: risks bugs on pre-release suffixes; reinvents what `packaging` already solves.
- **String comparison** — rejected: wrong for `3.10.0` vs `3.2.0`.

**Availability**: `packaging` is a transitive dep (pulled in by `build`, `pip`, most packaging-adjacent libs). Phase 1 contract/task WP will confirm via `python -c "import packaging.version"` and add it as an explicit `pyproject.toml` dependency if not already declared there — this is a defensive step to avoid relying on transitive availability.

---

## R2. Reading `pyproject.toml` version

**Decision**: Use stdlib `tomllib` (Python 3.11+) to read `[project].version` from `pyproject.toml` at the repo root.

**Pattern**:
```python
import tomllib
from pathlib import Path

def read_project_version(repo_root: Path) -> str:
    pyproject = repo_root / "pyproject.toml"
    with pyproject.open("rb") as fp:
        data = tomllib.load(fp)
    return data["project"]["version"]
```

**Rationale**: Python 3.11+ is the spec-kitty baseline (Technical Context). `tomllib` is stdlib — no dep to add.

**Edge case**: `pyproject.toml` missing OR `[project].version` absent → the doctor subcommand exits with code 2 (configuration error, distinct from code 1 which means "overdue shim found"). Error message names the missing file/key.

**Alternatives considered**:
- **Runtime introspection of `specify_cli.__version__`** — rejected: tightly couples doctor check to import-time module state; fails if there is a pre-install or editable-install quirk.
- **Separate VERSION file** — rejected: `pyproject.toml` is the canonical source per the project's own release process documented in `CLAUDE.md`.

---

## R3. Registry YAML schema validation approach

**Decision**: Manual schema validation in `src/specify_cli/architecture/shim_registry.py`. No new dependency.

**Approach**:
1. Parse YAML with `ruamel.yaml` safe loader (already a project dep).
2. Assert top-level shape: `{"shims": list}`.
3. Iterate entries; for each entry assert:
   - Required keys present: `legacy_path`, `canonical_import`, `introduced_in_release`, `removal_target_release`, `tracker_issue`, `grandfathered`.
   - Types: strings except `canonical_import` (string or list[string]), and `grandfathered` (bool).
   - `introduced_in_release` and `removal_target_release` match semver regex: `^\d+\.\d+\.\d+(?:[a-z]\d+)?$` (accepts `3.2.0`, `3.2.0a3`, `3.2.0rc1`).
   - `tracker_issue` matches either `^#\d+$` or `^https?://` URL.
   - If `extension_rationale` is set, value is a non-empty string.
   - `notes` is optional; type string if present.
4. Collect all validation errors and raise a `RegistrySchemaError` with the accumulated list (no short-circuit).

**Rationale**:
- Avoids pulling in `cerberus` or `jsonschema` (each ~few hundred KB, non-trivial test suite impact).
- NFR-002 (`≤500 ms`) is easy to meet with manual iteration over ≤50 entries.
- The resulting validator is trivially readable and grep-friendly.

**Alternatives considered**:
- **`jsonschema` + YAML-to-dict** — rejected: new dep, overkill for a file that will hold ≤10 entries (A4).
- **`pydantic` model** — rejected: same new-dep objection; current codebase does not force pydantic adoption here.

---

## R4. Existing `tests/architectural/` fixtures

**Decision**: Reuse whatever `tests/architectural/conftest.py` provides for project-root discovery; if no such fixture exists, implement a local `repo_root` fixture in each new test file.

**Action item for Phase 1**: Read `tests/architectural/conftest.py` during WP implementation and document (in the test files themselves) any fixtures reused.

**Pattern (fallback if no shared fixture)**:
```python
import pytest
from pathlib import Path

@pytest.fixture
def repo_root() -> Path:
    # tests/architectural/test_X.py -> repo root is two parents up
    return Path(__file__).resolve().parents[2]
```

---

## R5. Worked example content (FR-012)

**Decision**: The rulebook's worked example section cites `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` by slug and mission_id (`01KPD880…`) and maps each of the four rule families to specific artefacts produced by that mission.

**Mapping plan** (to be filled during WP that writes the rulebook):

| Rule family | Artefact in charter mission |
|-------------|-----------------------------|
| (a) schema/version gating | Charter bundle schema version marker (file path TBD from #610 outputs) |
| (b) migration authoring | Charter bundle migration module (path TBD) |
| (c) shim lifecycle | The `specify_cli.charter` shim (if present) or the "shim intentionally not introduced" note (if #610 merged the deletion) |
| (d) removal plans | Registry entry for `specify_cli.charter` or explicit "pre-removed" note |

**Note**: By the time this mission executes, #610 may already have deleted `specify_cli.charter`. In that case, the worked example explicitly documents "the charter mission demonstrates rule family (c) by *not* introducing a shim because the canonical package had no external importers; this exception is registered as the empty/baseline case in the registry." Either way, the worked example stays concrete.

---

## R6. Shim-file existence probe

**Decision**: Given a `legacy_path = "specify_cli.charter"`, probe in order:
1. `src/specify_cli/charter.py` (single-module shim)
2. `src/specify_cli/charter/__init__.py` (package shim)

First match counts as "exists." If neither exists, status is `removed`.

**Rationale**: Covers both shim module shapes. The shim module shape mandated by FR-003 can be realized either way — a single `charter.py` file that re-exports, or an `__init__.py` inside a `charter/` package directory.

---

## R7. Open items deferred to implementation (not blocking plan)

- **Decision on `packaging` as explicit dep vs. transitive**: checked during first WP; update `pyproject.toml` if not already pinned.
- **Exact wording of `DeprecationWarning` template in rulebook**: the rulebook will provide a copy-paste template; the `stacklevel=2` requirement (FR-003) is already pinned.
- **CHANGELOG.md exact text**: standard `- Added: architecture/2.x/06_migration_and_shim_rules.md rulebook, architecture/2.x/shim-registry.yaml registry, and spec-kitty doctor shim-registry CI check.` (FR-015).

## Summary

All NEEDS CLARIFICATION items from the spec's Open Questions are resolved in `plan.md`. This research document documents the how/why for the chosen comparator (R1), version reader (R2), schema validator (R3), test fixtures (R4), worked-example strategy (R5), and file-existence probe (R6). No blockers for Phase 1 design.
