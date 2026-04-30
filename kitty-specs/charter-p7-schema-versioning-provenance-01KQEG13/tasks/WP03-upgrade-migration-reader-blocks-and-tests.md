---
work_package_id: WP03
title: Upgrade Migration, Reader Blocks, and Full Test Suite
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Integration
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
shell_pid: "69687"
history:
- at: '2026-04-30T06:23:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/upgrade/migrations/
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/charter_bundle.py
- tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py
- tests/specify_cli/cli/commands/test_charter_status_provenance.py
- tests/charter/synthesizer/test_schema_conformance.py
tags: []
task_type: implement
---

# Work Package Prompt: WP03 — Upgrade Migration, Reader Blocks, and Full Test Suite

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load reviewer-renata
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Complete the v1→v2 migration implementation in `versioning.py`, create the `CharterBundleV2Migration` upgrade step, add reader blocks to charter subcommands, and verify everything with integration tests covering: migration, incompatible-bundle blocking, and `charter status --provenance` regression.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` after WP01 and WP02 are merged; do not guess the worktree path

## Prerequisites

**WP01 must be merged first**: `src/doctrine/versioning.py` with stubs for `migrate_v1_to_v2()` and `run_migration()` must exist.

**WP02 must be merged first**: `ProvenanceEntry` with `schema_version: Literal["2"]` and all 5 new mandatory fields must exist; `SynthesisManifest` with `synthesizer_version` and `manifest_hash` must exist.

Start by confirming both preconditions:
```bash
python -c "from doctrine.versioning import run_migration, migrate_v1_to_v2; print('WP01 OK')"
python -c "from charter.synthesizer.synthesize_pipeline import ProvenanceEntry; p = ProvenanceEntry.__fields__; assert 'synthesizer_version' in p; print('WP02 OK')"
```
(Run from `src/`)

## Context

**Decision DM-01KQEG9HTZ8RSZW4D50CN8V6CJ (Option C)**: `spec-kitty upgrade` is the single migration entry point. Normal charter commands check `bundle_schema_version` and block with a "run `spec-kitty upgrade`" error if incompatible. No opportunistic mutation by charter commands.

**Reader block placement** (from plan.md):
- ✅ `status()` — when charter is `available` (has metadata.yaml)
- ✅ `charter_resynthesize()` — reads existing bundle
- ✅ `charter_bundle.py` → `validate()` — validates the doctrine bundle
- ❌ `charter sync` — operates on charter.md, not the doctrine bundle; no block
- ❌ Fresh `charter synthesize` (first run) — creates a new v2 bundle; not blocked

**Migration sentinel values** for v1 sidecars that lack v2 fields:
```
synthesizer_version: "(pre-phase7-migration)"
synthesis_run_id: "(pre-phase7-migration)"
produced_at: <file mtime in ISO 8601 UTC, or "(pre-phase7-migration)" if mtime unavailable>
source_input_ids: <copy of existing source_urns field>
corpus_snapshot_id: <existing value or "(none)" if was null>
```

**Sentinel values are valid strings — do not reject them in FR-006 validation**: Strings like `"(pre-phase7-migration)"` and `"(none)"` are syntactically valid, non-empty values. FR-006 ("fails closed on missing or malformed mandatory fields") triggers only when a mandatory field is absent or its Pydantic type is violated. A migrated sidecar with `synthesizer_version: "(pre-phase7-migration)"` satisfies `synthesizer_version: str` and WILL pass `ProvenanceEntry` validation. Do NOT add logic to reject sentinel strings; they are the intended post-migration state.

**All three WPs land in lane-a**: `lanes.json` assigns WP01, WP02, and WP03 to a single lane (`lane-a`) because WP03 depends on both earlier WPs. The implementing agent works sequentially within that one lane worktree.

**BaseMigration pattern**: Read `src/specify_cli/upgrade/migrations/base.py` to understand `detect()` / `apply()` signatures. Follow the exact same pattern as existing migrations (e.g., `m_3_2_5_*.py` if present).

**Working directory**: `src/` for mypy and imports; `cd src && pytest ../tests/specify_cli/upgrade/` for migration tests.

## Subtask Guidance

### T015 — Complete `migrate_v1_to_v2()` in `versioning.py`

**File**: `src/doctrine/versioning.py` (modifying the stub from WP01)

Replace the `NotImplementedError` stub with the full implementation. The function signature is:

```python
def migrate_v1_to_v2(bundle_root: Path, dry_run: bool = False) -> MigrationResult:
```

`bundle_root` is the path to the `.kittify/charter/` directory (the charter dir containing `metadata.yaml`, `provenance/`, `synthesis-manifest.yaml`).

**Algorithm**:

1. **Find all provenance sidecar files**: `list((bundle_root / "provenance").glob("*.yaml"))`. If the directory doesn't exist, skip sidecar migration.

2. **For each sidecar file**:
   - Load with ruamel.yaml.
   - If `schema_version == "2"`: skip (already migrated).
   - Add missing v2 fields:
     ```python
     data.setdefault("synthesizer_version", "(pre-phase7-migration)")
     data.setdefault("synthesis_run_id", "(pre-phase7-migration)")
     if "produced_at" not in data:
         try:
             mtime = sidecar_path.stat().st_mtime
             data["produced_at"] = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
         except OSError:
             data["produced_at"] = "(pre-phase7-migration)"
     if "source_input_ids" not in data:
         data["source_input_ids"] = list(data.get("source_urns", []))
     if data.get("corpus_snapshot_id") is None:
         data["corpus_snapshot_id"] = "(none)"
     data["schema_version"] = "2"
     ```
   - Write back with ruamel.yaml (preserve round-trip style).
   - Record `str(sidecar_path)` in `changes_made`.

3. **Migrate `synthesis-manifest.yaml`** (if it exists):
   - Load the manifest.
   - If `schema_version == "2"`: skip.
   - Set `schema_version = "2"`.
   - Set `synthesizer_version = "(pre-phase7-migration)"` if missing.
   - Compute `manifest_hash` from the manifest content (excluding the `manifest_hash` key):
     ```python
     fields_for_hash = {k: v for k, v in data.items() if k != "manifest_hash"}
     import hashlib
     from charter.synthesizer.synthesize_pipeline import canonical_yaml
     manifest_hash = hashlib.sha256(canonical_yaml(fields_for_hash)).hexdigest()
     data["manifest_hash"] = manifest_hash
     ```
   - Write back.
   - Record manifest path in `changes_made`.

4. **Update `metadata.yaml`**:
   - Load metadata.
   - Set `bundle_schema_version = 2`.
   - Write back.
   - Record metadata path in `changes_made`.

5. **Idempotency**: The "skip if already v2" checks on each file ensure running twice returns `changes_made=[]` on the second run.

6. **dry_run mode**: When `dry_run=True`, perform all reads and compute what would change, but do not write any files. Populate `changes_made` with what would change.

Run `mypy --strict src/doctrine/versioning.py` after.

### T016 — Create `CharterBundleV2Migration`

**File**: `src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py` (new file)

Read `src/specify_cli/upgrade/migrations/base.py` **first** to get the exact `BaseMigration` and `MigrationResult` interfaces. Then read an existing recent migration (e.g., `m_3_2_5_fix_prompt_file_workaround.py`) to see the decorator and registration pattern in use.

**Key interface facts** (verify against `base.py` before writing code):
- `MigrationResult` is a `@dataclass` with `success: bool` as the **first required field**, plus `changes_made`, `errors`, `warnings`, `manual_review_required`, `preserved_paths`
- `BaseMigration` has class-level string fields: `migration_id`, `target_version`, `description`
- `detect(self, project_path)` and `can_apply(self, project_path)` are instance methods (NOT classmethods)
- `can_apply()` returns `tuple[bool, str]`
- Migrations are registered via `@MigrationRegistry.register` decorator (import from `specify_cli.upgrade.migrations.registry`)

Create the migration class:

```python
from __future__ import annotations

from pathlib import Path

from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult
from specify_cli.upgrade.migrations.registry import MigrationRegistry
from doctrine.versioning import (
    get_bundle_schema_version,
    run_migration,
    CURRENT_BUNDLE_SCHEMA_VERSION,
)


@MigrationRegistry.register
class CharterBundleV2Migration(BaseMigration):
    """Upgrades charter doctrine bundles from v1 to v2 (Phase 7 hardening)."""

    migration_id: str = "3.2.6_charter_bundle_v2"
    target_version: str = "3.2.6"
    description: str = "Upgrade charter bundle schema from v1 to v2 (Phase 7 provenance hardening)"

    def detect(self, project_path: Path) -> bool:
        """Return True if the project has a charter bundle that needs migration."""
        charter_dir = project_path / ".kittify" / "charter"
        if not charter_dir.exists():
            return False
        bundle_version = get_bundle_schema_version(charter_dir)
        return bundle_version is None or bundle_version < CURRENT_BUNDLE_SCHEMA_VERSION

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        charter_dir = project_path / ".kittify" / "charter"
        if not charter_dir.exists():
            return False, "No charter directory found at .kittify/charter"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        charter_dir = project_path / ".kittify" / "charter"
        bundle_version = get_bundle_schema_version(charter_dir)
        if bundle_version is None:
            bundle_version = 1  # treat missing as v1

        if bundle_version >= CURRENT_BUNDLE_SCHEMA_VERSION:
            return MigrationResult(success=True, changes_made=[], errors=[])

        all_changes: list[str] = []
        all_errors: list[str] = []
        current = bundle_version
        while current < CURRENT_BUNDLE_SCHEMA_VERSION:
            result = run_migration(current, charter_dir, dry_run=dry_run)
            all_changes.extend(result.changes_made)
            all_errors.extend(result.errors)
            current += 1

        return MigrationResult(
            success=len(all_errors) == 0,
            changes_made=all_changes,
            errors=all_errors,
        )
```

**After writing the file**, verify the migration is picked up by the upgrade runner. Check `src/specify_cli/upgrade/runner.py` (or wherever migrations are discovered). If they are loaded by explicit import, add an import of `m_3_2_6_charter_bundle_v2` there.

Run `mypy --strict src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py`.

Also verify the migration is registered in the upgrade runner. Check `src/specify_cli/upgrade/runner.py` (or equivalent) to see how migrations are discovered. If they use a registry list, add the new migration there.

### T017 — Add `_assert_bundle_compatible()` to `charter.py`

**File**: `src/specify_cli/cli/commands/charter.py`

Read the full file first. Understand the structure: `status()`, `charter_resynthesize()`, and the `bundle validate` path.

Add a helper function:

```python
from pathlib import Path
from doctrine.versioning import get_bundle_schema_version, check_bundle_compatibility
from specify_cli.cli.errors import TaskCliError  # or the appropriate error class

def _assert_bundle_compatible(charter_dir: Path) -> None:
    """Raise TaskCliError if the bundle at charter_dir is not compatible with this CLI."""
    bundle_version = get_bundle_schema_version(charter_dir)
    result = check_bundle_compatibility(bundle_version)
    if not result.is_compatible:
        raise TaskCliError(result.message)
```

Then call `_assert_bundle_compatible(charter_dir)` at the start of:
1. `status()` — only when the charter `available` branch is reached (i.e., after the code confirms `metadata.yaml` exists)
2. `charter_resynthesize()` — before any bundle reads
3. The bundle validate handler — before running validation

**Important**: Check what error class is used by existing commands when they want to exit with code 1. It may be `typer.Exit(1)` with a `console.print(...)` call, or a custom `TaskCliError`. Match the existing pattern.

**Do NOT add the check to**:
- `charter sync` (operates on charter.md, not the bundle)
- Fresh `charter synthesize` (produces a new v2 bundle; would wrongly block first-time synthesis)

**Also update `charter_bundle.py` — provenance sidecar content validation (FR-006, FR-007)**:

Read `src/specify_cli/cli/commands/charter_bundle.py` in full. The current `validate()` function validates canonical bundle structure (tracked/derived files, gitignore entries) but does **NOT** parse or validate provenance sidecar content. You must add a provenance validation pass.

After the existing structure checks pass, add:

```python
from charter.synthesizer.synthesize_pipeline import ProvenanceEntry
from pydantic import ValidationError

provenance_dir = charter_dir / "provenance"
sidecar_errors: list[str] = []
if provenance_dir.exists():
    for sidecar_path in sorted(provenance_dir.glob("*.yaml")):
        raw = yaml.load(sidecar_path)
        if isinstance(raw, dict):
            try:
                ProvenanceEntry(**raw)
            except ValidationError as e:
                sidecar_errors.append(f"{sidecar_path.name}: {e}")

if sidecar_errors:
    for msg in sidecar_errors:
        console.print(f"[red]Provenance validation error:[/red] {msg}")
    raise typer.Exit(code=1)
```

Place `_assert_bundle_compatible(charter_dir)` BEFORE the structure checks, so an incompatible bundle fails fast with an upgrade prompt rather than a structure error.

Run `mypy --strict src/specify_cli/cli/commands/charter_bundle.py` after.

### T018 — Create `test_charter_bundle_v2_migration.py`

**File**: `tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py` (new file)

Ensure `tests/specify_cli/upgrade/__init__.py` exists.

Create a synthetic v1 bundle fixture using `tmp_path`. A minimal v1 bundle:
- `.kittify/charter/metadata.yaml` — no `bundle_schema_version` field (or `bundle_schema_version: null`)
- `.kittify/charter/provenance/directive-use-prs.yaml` — `schema_version: "1"`, no `synthesizer_version`, `corpus_snapshot_id: null`
- `.kittify/charter/synthesis-manifest.yaml` — `schema_version: "1"`, no `synthesizer_version`, no `manifest_hash`

Required test cases:

```python
def test_detect_v1_bundle_returns_true(tmp_path):
    _create_v1_bundle(tmp_path)
    assert CharterBundleV2Migration.detect(tmp_path) is True

def test_detect_v2_bundle_returns_false(tmp_path):
    _create_v2_bundle(tmp_path)
    assert CharterBundleV2Migration.detect(tmp_path) is False

def test_detect_no_charter_returns_false(tmp_path):
    assert CharterBundleV2Migration.detect(tmp_path) is False

def test_apply_migrates_sidecar_to_v2(tmp_path):
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    result = migration.apply(tmp_path)
    assert len(result.changes_made) > 0
    assert len(result.errors) == 0
    # Verify sidecar parses as ProvenanceEntry v2
    from charter.synthesizer.synthesize_pipeline import ProvenanceEntry
    sidecar = _load_yaml(tmp_path / ".kittify/charter/provenance/directive-use-prs.yaml")
    entry = ProvenanceEntry(**sidecar)
    assert entry.schema_version == "2"
    assert entry.synthesizer_version == "(pre-phase7-migration)"
    assert entry.corpus_snapshot_id == "(none)"

def test_apply_idempotent(tmp_path):
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    migration.apply(tmp_path)
    result2 = migration.apply(tmp_path)
    assert result2.changes_made == []

def test_apply_updates_metadata_yaml(tmp_path):
    _create_v1_bundle(tmp_path)
    CharterBundleV2Migration().apply(tmp_path)
    from doctrine.versioning import get_bundle_schema_version
    version = get_bundle_schema_version(tmp_path / ".kittify/charter")
    assert version == 2

def test_apply_manifest_gets_v2_fields(tmp_path):
    _create_v1_bundle(tmp_path)
    CharterBundleV2Migration().apply(tmp_path)
    manifest = _load_yaml(tmp_path / ".kittify/charter/synthesis-manifest.yaml")
    assert manifest["schema_version"] == "2"
    assert "synthesizer_version" in manifest
    assert len(manifest["manifest_hash"]) == 64

def test_apply_dry_run_makes_no_changes(tmp_path):
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    result = migration.apply(tmp_path, dry_run=True)
    assert len(result.changes_made) > 0  # reports what would change
    # But files unchanged:
    sidecar = _load_yaml(tmp_path / ".kittify/charter/provenance/directive-use-prs.yaml")
    assert sidecar.get("schema_version") == "1"  # not mutated
```

### T019 — Create `test_charter_status_provenance.py`

**File**: `tests/specify_cli/cli/commands/test_charter_status_provenance.py` (new file)

This covers FR-009 (incompatible bundle blocking) and FR-010 (regression: `charter status --provenance`).

Use `typer.testing.CliRunner` to invoke the CLI in-process. Study how existing tests in `tests/specify_cli/cli/commands/` call charter commands and build their fixture state.

Required test cases:

```python
def test_status_v1_bundle_exits_1_with_upgrade_message(tmp_path, monkeypatch):
    """FR-009: v1 bundle blocks with actionable error."""
    _setup_charter_v1_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "status"])
    assert result.exit_code == 1
    assert "spec-kitty upgrade" in result.output

def test_status_future_bundle_exits_1(tmp_path, monkeypatch):
    """FR-009: bundle too new for this CLI."""
    _setup_charter_project_with_version(tmp_path, bundle_schema_version=99)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "status"])
    assert result.exit_code == 1

def test_status_v2_bundle_exits_0(tmp_path, monkeypatch):
    """FR-011: fully-migrated Phase 7 bundle is accepted."""
    _setup_charter_v2_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "status"])
    assert result.exit_code == 0

def test_status_provenance_json_includes_synthesizer_version(tmp_path, monkeypatch):
    """FR-010: regression guard — synthesizer_version present in --json --provenance output."""
    _setup_charter_v2_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "status", "--provenance", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # charter status --json --provenance returns either a dict with a "provenance" list
    # or a list of provenance entries directly; read charter.py to confirm the exact shape.
    provenance_entries = data.get("provenance", data) if isinstance(data, dict) else data
    assert isinstance(provenance_entries, list), "Expected a list of provenance entries"
    assert any(
        "synthesizer_version" in entry for entry in provenance_entries
    ), "synthesizer_version not found in any provenance entry"

def test_status_provenance_json_includes_produced_at(tmp_path, monkeypatch):
    """FR-010: regression guard — produced_at present in --json --provenance output."""
    _setup_charter_v2_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "status", "--provenance", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    provenance_entries = data.get("provenance", data) if isinstance(data, dict) else data
    assert isinstance(provenance_entries, list), "Expected a list of provenance entries"
    assert any(
        "produced_at" in entry for entry in provenance_entries
    ), "produced_at not found in any provenance entry"

def test_bundle_validate_fails_on_missing_synthesizer_version(tmp_path, monkeypatch):
    """FR-006: validation fails closed on incomplete provenance."""
    _setup_charter_v2_project_missing_field(tmp_path, remove_field="synthesizer_version")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "bundle", "validate"])
    assert result.exit_code == 1
    assert "synthesizer_version" in result.output

def test_bundle_validate_passes_complete_v2_bundle(tmp_path, monkeypatch):
    """FR-011: complete v2 bundle validates successfully."""
    _setup_charter_v2_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["charter", "bundle", "validate"])
    assert result.exit_code == 0
```

Implement `_setup_charter_v1_project()`, `_setup_charter_v2_project()`, `_setup_charter_project_with_version()`, and `_setup_charter_v2_project_missing_field()` as private helpers in the test file. They create minimal synthetic bundles directly on the filesystem (`tmp_path`).

Study the `charter status --provenance` code path from WP7.4 to understand what fields are expected in the output. The key regression guard is that the command exits 0 and includes `synthesizer_version` and `produced_at` in its output.

### T020 — Update `test_schema_conformance.py`

**File**: `tests/charter/synthesizer/test_schema_conformance.py`

Read the file. Find any assertions on `schema_version` values for `ProvenanceEntry` and `SynthesisManifest`. Update from `"1"` to `"2"`.

Also add assertions for the new v2 fields if the conformance tests validate field presence:
- `ProvenanceEntry` must have `synthesizer_version`, `source_input_ids`, `produced_at`, `synthesis_run_id` in its schema
- `SynthesisManifest` must have `synthesizer_version`, `manifest_hash` in its schema

Run:
```bash
cd src && pytest ../tests/charter/synthesizer/test_schema_conformance.py -v
```

## Definition of Done

- [ ] `migrate_v1_to_v2()` fully implemented; replaces `NotImplementedError` stub; uses `canonical_yaml(data)` directly (no `.encode()`)
- [ ] `CharterBundleV2Migration` created with `@MigrationRegistry.register`, correct `migration_id`/`target_version`/`can_apply()` fields, and `MigrationResult(success=..., ...)` return type; registered in upgrade runner
- [ ] `_assert_bundle_compatible()` added to `charter.py`; called from `status`, `resynthesize`, and `bundle validate`
- [ ] `charter_bundle.py` `validate()` iterates provenance sidecars, parses each as `ProvenanceEntry`, exits 1 on `ValidationError` (FR-006/FR-007)
- [ ] `test_charter_bundle_v2_migration.py` passes (migration, detect, idempotency, dry_run, metadata stamp)
- [ ] `test_charter_status_provenance.py` passes (v1 block, future-version block, v2 passes, `--json --provenance` regression assertions)
- [ ] `test_schema_conformance.py` passes with v2 assertions
- [ ] `mypy --strict` passes on all new/modified source files
- [ ] No changes to any file outside `owned_files`

## Risks

- **BaseMigration interface mismatch**: Read `base.py` carefully before writing the class. The `apply()` return type and field names may differ from the pseudocode above.
- **Migration registration discovery**: If the upgrade runner discovers migrations by class scanning or an explicit list, you must register `CharterBundleV2Migration`. Check how other `m_3_2_*.py` migrations are discovered.
- **`_assert_bundle_compatible` for fresh synthesize**: The check MUST NOT run before a first-ever synthesis (when `metadata.yaml` doesn't exist yet). Only add the check inside branches where `metadata.yaml` is known to exist.
- **CliRunner output format**: `charter status --provenance` output may be a table (Rich). The regression test checks for field name presence as a string in the output — this works for Rich table headers. If it outputs JSON, parse it instead.
- **import `canonical_yaml` from within versioning.py**: The `migrate_v1_to_v2` function needs `canonical_yaml` (from `charter.synthesizer.synthesize_pipeline`). This creates a `doctrine → charter` import — which is the WRONG direction per the constraint. Use a local alternative: serialize to YAML via ruamel.yaml with sorted keys, or inline the canonical serialization logic. Do NOT import from `charter.*` in `versioning.py`. One clean option: extract `canonical_yaml` to a shared utility module (e.g., `src/doctrine/yaml_utils.py`) and import from there in both `versioning.py` and `synthesize_pipeline.py`. Ask the user if the right approach is unclear.

## Activity Log

- 2026-04-30T07:30:08Z – claude:sonnet-4-6:implementer:implementer – shell_pid=68505 – Started implementation via action command
- 2026-04-30T07:40:04Z – claude:sonnet-4-6:implementer:implementer – shell_pid=68505 – Ready for review: migrate_v1_to_v2 implemented, CharterBundleV2Migration registered, reader blocks in charter status/resynthesize/bundle validate, 41 tests passing
- 2026-04-30T07:40:42Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=69687 – Started review via action command
