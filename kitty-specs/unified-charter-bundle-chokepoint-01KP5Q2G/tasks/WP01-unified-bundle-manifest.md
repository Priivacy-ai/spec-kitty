---
work_package_id: WP01
title: Unified bundle manifest, architecture doc, and bundle CLI
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-015
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
history:
- at: '2026-04-14T11:16:00Z'
  actor: claude
  event: created
authoritative_surface: src/charter/bundle.py
execution_mode: code_change
owned_files:
- src/charter/bundle.py
- src/charter/__init__.py
- src/specify_cli/cli/commands/charter_bundle.py
- architecture/2.x/06_unified_charter_bundle.md
- tests/charter/test_bundle_manifest_model.py
- tests/charter/test_bundle_validate_cli.py
- kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP01.yaml
- kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml
tags: []
---

# WP01 — Unified bundle manifest, architecture doc, and bundle CLI

**Tracks**: [Priivacy-ai/spec-kitty#478](https://github.com/Priivacy-ai/spec-kitty/issues/478)
**Depends on**: — (first WP in the Phase 2 tranche)
**Merges to**: `main`

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP01 --agent <name> --mission unified-charter-bundle-chokepoint-01KP5Q2G` to resolve the actual workspace path and branch. Do NOT reconstruct the path by hand.

---

## Objective

Establish the v1.0.0 typed bundle manifest as the authoritative declaration of which files `src/charter/sync.py :: sync()` materializes, publish the architecture §6 doc that describes the unified bundle contract and the canonical-root semantics, and ship a self-contained `spec-kitty charter bundle validate` Typer sub-app. WP01 is pure additive work: no existing source code is refactored, no readers are flipped, no worktrees are touched. WP03 will register the sub-app into the `charter` CLI root; WP02 will replace WP01's temporary `git rev-parse --show-toplevel` wrapper with the proper `resolve_canonical_repo_root()`.

**No fallback. No deprecation shim. No expansion of v1.0.0 scope.** Per spec C-001 and C-012.

## Context

- EPIC: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
- Phase 2 tracking: [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)
- WP tracking issue: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478)
- Guardrail reference: [#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) — occurrence-classification pattern
- v1.0.0 manifest scope: exactly the three files `_SYNC_OUTPUT_FILES` declares at `src/charter/sync.py:32-36` — `governance.yaml`, `directives.yaml`, `metadata.yaml`. `references.yaml` and `context-state.json` are OUT OF SCOPE.

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-001, FR-002, FR-005, FR-015; C-001, C-002, C-006, C-007, C-012
- [plan.md](../plan.md) — WP2.1 section + D-1 (manifest module location), D-4 (bundle CLI), D-12 (gitignore policy), D-13 (v1.0.0 scope)
- [data-model.md](../data-model.md) — `CharterBundleManifest` entity
- [research.md](../research.md) — R-1 (reader inventory — read-only scope info)
- [contracts/bundle-manifest.schema.yaml](../contracts/bundle-manifest.schema.yaml) — JSON Schema for `CharterBundleManifest`
- [contracts/bundle-validate-cli.contract.md](../contracts/bundle-validate-cli.contract.md) — CLI contract
- [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml) — occurrence artifact schema
- [quickstart.md](../quickstart.md) — smoke-check commands for WP01

---

## Subtask details

### T001 — Create `src/charter/bundle.py` with `CharterBundleManifest` + `CANONICAL_MANIFEST`

**Purpose**: Establish the typed bundle manifest contract as the single authority for "which files constitute the v1.0.0 bundle".

**Steps**:

1. Create `src/charter/bundle.py` with the following structure (follow the exact schema from [contracts/bundle-manifest.schema.yaml](../contracts/bundle-manifest.schema.yaml)):

   ```python
   """Unified charter bundle manifest (v1.0.0).

   Declares the files src/charter/sync.py :: sync() materializes as the
   project's governance bundle. v1.0.0 scope is limited to the three
   sync-produced derivatives. See architecture/2.x/06_unified_charter_bundle.md
   for the full contract.
   """
   from __future__ import annotations

   from pathlib import Path
   from pydantic import BaseModel, Field, model_validator

   SCHEMA_VERSION: str = "1.0.0"


   class CharterBundleManifest(BaseModel):
       schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
       tracked_files: list[Path] = Field(min_length=1)
       derived_files: list[Path]
       derivation_sources: dict[Path, Path]
       gitignore_required_entries: list[str]

       model_config = {"frozen": True}

       @model_validator(mode="after")
       def _validate(self) -> "CharterBundleManifest":
           # No path may appear in both tracked and derived.
           tracked = set(self.tracked_files)
           derived = set(self.derived_files)
           overlap = tracked & derived
           if overlap:
               raise ValueError(f"Paths appear in both tracked and derived: {sorted(overlap)}")
           # Every key in derivation_sources must appear in derived_files.
           missing_keys = set(self.derivation_sources.keys()) - derived
           if missing_keys:
               raise ValueError(f"derivation_sources keys not in derived_files: {sorted(missing_keys)}")
           # Every value in derivation_sources must appear in tracked_files.
           missing_values = set(self.derivation_sources.values()) - tracked
           if missing_values:
               raise ValueError(f"derivation_sources values not in tracked_files: {sorted(missing_values)}")
           return self


   CANONICAL_MANIFEST: CharterBundleManifest = CharterBundleManifest(
       schema_version=SCHEMA_VERSION,
       tracked_files=[Path(".kittify/charter/charter.md")],
       derived_files=[
           Path(".kittify/charter/governance.yaml"),
           Path(".kittify/charter/directives.yaml"),
           Path(".kittify/charter/metadata.yaml"),
       ],
       derivation_sources={
           Path(".kittify/charter/governance.yaml"): Path(".kittify/charter/charter.md"),
           Path(".kittify/charter/directives.yaml"): Path(".kittify/charter/charter.md"),
           Path(".kittify/charter/metadata.yaml"):   Path(".kittify/charter/charter.md"),
       },
       gitignore_required_entries=[
           ".kittify/charter/directives.yaml",
           ".kittify/charter/governance.yaml",
           ".kittify/charter/metadata.yaml",
       ],
   )
   ```

2. The `CANONICAL_MANIFEST.derived_files` list must match `_SYNC_OUTPUT_FILES` at `src/charter/sync.py:32-36` exactly — same three files. Do NOT add `references.yaml` or `context-state.json`.

**Files**:
- `src/charter/bundle.py` (new, ~70 lines)

**Validation**:
- [ ] `python -c "from charter.bundle import CANONICAL_MANIFEST; print(CANONICAL_MANIFEST.schema_version)"` prints `1.0.0`.
- [ ] `len(CANONICAL_MANIFEST.derived_files) == 3`.
- [ ] Constructing a `CharterBundleManifest` with a path in both `tracked_files` and `derived_files` raises `ValidationError`.

---

### T002 — Write `architecture/2.x/06_unified_charter_bundle.md`

**Purpose**: The manifest is a typed contract; this file is its narrative source of truth.

**Steps**:

1. Create `architecture/2.x/06_unified_charter_bundle.md` (new file, ~100 lines) covering:
   - Purpose and relationship to architecture §6 (unified emergent bundle).
   - **v1.0.0 scope** explicitly: the three `sync()`-produced files; explicit out-of-scope list for `references.yaml` (compiler pipeline at `src/charter/compiler.py:169-196`) and `context-state.json` (runtime state at `src/charter/context.py:385-398`).
   - Tracked vs. derived classification and why the split exists.
   - Canonical-root contract (forward-reference to `contracts/canonical-root-resolver.contract.md`, which WP02 finalizes).
   - Staleness semantics: hash comparison between `charter.md` and `metadata.yaml`.
   - Gitignore policy: "MUST-INCLUDE" semantics. The project `.gitignore` MAY carry additional entries for out-of-scope files; the manifest does not forbid them.
   - Schema versioning policy: independent semver (not tied to `spec-kitty` package version). Future manifest versions bump the schema and ship with their own migration.

2. Cite the manifest module location (`src/charter/bundle.py`) and the JSON Schema (`kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/bundle-manifest.schema.yaml`).

**Files**:
- `architecture/2.x/06_unified_charter_bundle.md` (new, ~100 lines)

**Validation**:
- [ ] File exists and is committed.
- [ ] File explicitly lists the three v1.0.0 derived files.
- [ ] File explicitly notes `references.yaml` and `context-state.json` as out-of-scope.

---

### T003 — Create `src/specify_cli/cli/commands/charter_bundle.py` Typer sub-app

**Purpose**: Ship the `bundle validate` CLI surface as a self-contained Typer sub-app. WP03 will register it into the `charter` CLI root; WP02 will replace the temporary resolver wrapper.

**Steps**:

1. Create `src/specify_cli/cli/commands/charter_bundle.py` (new, ~150 lines):

   ```python
   """spec-kitty charter bundle - Typer sub-app for bundle validation.

   This module is self-contained. WP03 will register it into the main
   `charter` CLI as a sub-command group. A temporary canonical-root
   resolver wrapper is used here until WP02 replaces it with
   charter.resolution.resolve_canonical_repo_root.
   """
   from __future__ import annotations

   import json as _json
   import subprocess
   import sys
   from pathlib import Path

   import typer
   from rich.console import Console

   from charter.bundle import CANONICAL_MANIFEST

   app = typer.Typer(help="Charter bundle validation commands.", no_args_is_help=True)


   # TODO(WP02): replace with charter.resolution.resolve_canonical_repo_root
   # when WP02 lands. This temporary wrapper uses --show-toplevel which is
   # NOT correct under worktrees (it returns the worktree path, not the
   # main checkout). WP02 will fix this.
   def _resolve_canonical_root_TEMP(path: Path) -> Path:
       """Temporary resolver. See TODO."""
       result = subprocess.run(
           ["git", "rev-parse", "--show-toplevel"],
           cwd=path, capture_output=True, text=True, check=False,
       )
       if result.returncode != 0:
           raise RuntimeError(f"Not inside a git repository: {path!r}")
       return Path(result.stdout.strip())


   @app.command("validate")
   def validate(
       json_output: bool = typer.Option(False, "--json", help="Emit structured JSON."),
   ) -> None:
       """Validate the charter bundle against CharterBundleManifest v1.0.0."""
       console = Console()
       try:
           canonical_root = _resolve_canonical_root_TEMP(Path.cwd())
       except RuntimeError as exc:
           console.print(f"[red]Error:[/red] {exc}", style="red")
           sys.exit(2)

       # Implement validation per contracts/bundle-validate-cli.contract.md:
       # - Check tracked_files exist at canonical_root / path.
       # - Check derived_files exist (or are absent in fresh-clone state).
       # - Check gitignore_required_entries are present in canonical_root / ".gitignore".
       # - Enumerate out-of-scope files as informational warnings.
       # ...
       # (The implementer fills in the body per the contract.)
   ```

2. Behavior must match [contracts/bundle-validate-cli.contract.md](../contracts/bundle-validate-cli.contract.md) exactly:
   - Exit 0 on compliant bundle; exit 1 on non-compliant; exit 2 on resolver failure.
   - `--json` emits the exact JSON shape in the contract.
   - Out-of-scope files (`references.yaml`, `context-state.json`, `interview/answers.yaml`, `library/*.md`) surface as informational warnings, not failures.

3. The `TODO(WP02)` comment is **required** — it is a tracking anchor for the WP03 occurrence artifact (marked `action: rewrite`).

**Files**:
- `src/specify_cli/cli/commands/charter_bundle.py` (new, ~150 lines)

**Validation**:
- [ ] `python -c "from specify_cli.cli.commands.charter_bundle import app; print(app.info.name)"` runs without ImportError.
- [ ] `mypy --strict src/specify_cli/cli/commands/charter_bundle.py` passes.
- [ ] `grep -n "TODO(WP02)" src/specify_cli/cli/commands/charter_bundle.py` finds the rewrite anchor.

---

### T004 — Re-export `CharterBundleManifest` from `src/charter/__init__.py`

**Purpose**: Provide a single canonical import path (`from charter import CharterBundleManifest`) for downstream readers.

**Steps**:

1. Add to `src/charter/__init__.py`:

   ```python
   from charter.bundle import (
       CANONICAL_MANIFEST,
       CharterBundleManifest,
       SCHEMA_VERSION,
   )

   __all__ = [
       # ... existing entries ...
       "CANONICAL_MANIFEST",
       "CharterBundleManifest",
       "SCHEMA_VERSION",
   ]
   ```

2. Preserve all existing exports. Do NOT remove anything.

**Files**:
- `src/charter/__init__.py` (modified, +5 lines)

**Validation**:
- [ ] `python -c "from charter import CharterBundleManifest; print(CharterBundleManifest)"` succeeds.
- [ ] `grep -n "CharterBundleManifest" src/charter/__init__.py` shows the re-export.

---

### T005 — Write `tests/charter/test_bundle_manifest_model.py`

**Purpose**: Pin the v1.0.0 manifest contract with tests so regressions are caught immediately.

**Steps**:

1. Create `tests/charter/test_bundle_manifest_model.py` (new, ~80 lines) with these test cases:

   ```python
   """Tests for CharterBundleManifest v1.0.0."""
   from pathlib import Path
   import pytest
   from pydantic import ValidationError

   from charter.bundle import CANONICAL_MANIFEST, CharterBundleManifest, SCHEMA_VERSION


   def test_schema_version_is_1_0_0() -> None:
       assert SCHEMA_VERSION == "1.0.0"
       assert CANONICAL_MANIFEST.schema_version == "1.0.0"


   def test_canonical_manifest_has_exactly_three_derived_files() -> None:
       assert len(CANONICAL_MANIFEST.derived_files) == 3
       names = {p.name for p in CANONICAL_MANIFEST.derived_files}
       assert names == {"governance.yaml", "directives.yaml", "metadata.yaml"}


   def test_canonical_manifest_excludes_references_and_context_state() -> None:
       names = {p.name for p in CANONICAL_MANIFEST.derived_files}
       assert "references.yaml" not in names  # C-012
       assert "context-state.json" not in names  # C-012


   def test_every_derived_file_has_a_derivation_source() -> None:
       for d in CANONICAL_MANIFEST.derived_files:
           assert d in CANONICAL_MANIFEST.derivation_sources


   def test_every_derivation_source_is_tracked() -> None:
       for src in CANONICAL_MANIFEST.derivation_sources.values():
           assert src in CANONICAL_MANIFEST.tracked_files


   def test_validator_rejects_overlap() -> None:
       with pytest.raises(ValidationError):
           CharterBundleManifest(
               schema_version="1.0.0",
               tracked_files=[Path("a")],
               derived_files=[Path("a")],
               derivation_sources={},
               gitignore_required_entries=[],
           )


   def test_validator_rejects_orphan_derivation_source() -> None:
       with pytest.raises(ValidationError):
           CharterBundleManifest(
               schema_version="1.0.0",
               tracked_files=[Path("src.md")],
               derived_files=[Path("out.yaml")],
               derivation_sources={Path("out.yaml"): Path("missing.md")},
               gitignore_required_entries=[],
           )


   def test_schema_version_regex_enforced() -> None:
       with pytest.raises(ValidationError):
           CharterBundleManifest(
               schema_version="not-semver",
               tracked_files=[Path("a.md")],
               derived_files=[],
               derivation_sources={},
               gitignore_required_entries=[],
           )


   def test_gitignore_required_entries_is_must_include_not_exclusive() -> None:
       # Documentary test: the manifest's set is MUST-INCLUDE, not "only these".
       # Additional .gitignore entries (e.g., for out-of-scope files) are allowed.
       entries = set(CANONICAL_MANIFEST.gitignore_required_entries)
       assert ".kittify/charter/governance.yaml" in entries
       assert ".kittify/charter/directives.yaml" in entries
       assert ".kittify/charter/metadata.yaml" in entries
   ```

**Files**:
- `tests/charter/test_bundle_manifest_model.py` (new, ~80 lines)

**Validation**:
- [ ] `pytest tests/charter/test_bundle_manifest_model.py` passes (9 tests).

---

### T006 — Write `tests/charter/test_bundle_validate_cli.py`

**Purpose**: Integration test for the `bundle validate` CLI using Typer's test runner against the sub-app directly (full CLI registration comes in WP03).

**Steps**:

1. Create `tests/charter/test_bundle_validate_cli.py` (new, ~120 lines) with:

   - A fixture that creates a tmp git repo with a populated `.kittify/charter/charter.md` + the three derived files.
   - A fixture for a "fresh clone" repo (charter.md present, derivatives absent).
   - A fixture for a non-repo path.
   - Test cases:
     - `test_validate_passes_on_compliant_bundle()` — exit 0, `bundle_compliant: true`.
     - `test_validate_reports_out_of_scope_files_as_warnings()` — create a `references.yaml` or `context-state.json` in the fixture; assert `out_of_scope_files` is non-empty and `bundle_compliant` is still `true`.
     - `test_validate_fails_on_missing_tracked_file()` — delete `charter.md` from fixture; exit 1; `missing` list includes it.
     - `test_validate_fails_on_missing_gitignore_entry()` — remove a gitignore entry; exit 1; `missing_entries` non-empty.
     - `test_validate_exits_2_on_non_repo_path()` — invoke with `cwd` outside any repo; exit 2.
     - `test_validate_json_shape_matches_contract()` — parse JSON output; assert required keys match `contracts/bundle-validate-cli.contract.md`.

   Use `typer.testing.CliRunner().invoke(charter_bundle.app, ["validate", "--json"])` for invocation.

**Files**:
- `tests/charter/test_bundle_validate_cli.py` (new, ~120 lines)

**Validation**:
- [ ] `pytest tests/charter/test_bundle_validate_cli.py` passes (6 tests).

---

### T007 — Author `occurrences/WP01.yaml` and seed `index.yaml`

**Purpose**: Establish the #393 occurrence-classification artifact for WP01 and seed the mission-level aggregate.

**Steps**:

1. Create `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/` directory.

2. Author `occurrences/WP01.yaml` per [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml):

   ```yaml
   wp_id: WP01
   mission_slug: unified-charter-bundle-chokepoint-01KP5Q2G
   requires_merged: []
   categories:
     filesystem_path_literal:
       description: New v1.0.0 bundle manifest file paths introduced by WP01.
       include: ["src/charter/**", "src/specify_cli/cli/commands/**", "architecture/**"]
       exclude: []
       occurrences:
         - path: src/charter/bundle.py
           pattern: ".kittify/charter/governance.yaml"
           action: leave
           rationale: Manifest declaration; canonical carve-out per mission index.
         - path: src/charter/bundle.py
           pattern: ".kittify/charter/directives.yaml"
           action: leave
           rationale: Manifest declaration.
         - path: src/charter/bundle.py
           pattern: ".kittify/charter/metadata.yaml"
           action: leave
           rationale: Manifest declaration.
     symbol_name:
       description: New exported symbols.
       include: ["src/**", "tests/**"]
       exclude: []
       occurrences:
         - path: src/charter/bundle.py
           pattern: "CharterBundleManifest"
           action: leave
           rationale: New public symbol.
         - path: src/charter/bundle.py
           pattern: "CANONICAL_MANIFEST"
           action: leave
           rationale: New module-level instance.
         - path: src/charter/bundle.py
           pattern: "SCHEMA_VERSION"
           action: leave
           rationale: New constant.
     docstring_comment:
       description: Temporary TODO marker for WP02 replacement.
       include: ["src/specify_cli/cli/commands/charter_bundle.py"]
       exclude: []
       occurrences:
         - path: src/specify_cli/cli/commands/charter_bundle.py
           pattern: "TODO(WP02)"
           action: rewrite
           rewrite_to: "from charter.resolution import resolve_canonical_repo_root  (done by WP02)"
           rationale: Temporary resolver wrapper replaced by WP02.
   carve_outs: []
   must_be_zero_after:
     - "CharterBundleManifestV2"  # placeholder - no v2 symbol should appear yet
   verification_notes: "WP01 adds new files only; no existing code refactored."
   ```

3. Seed `occurrences/index.yaml` with mission-level scaffold:

   ```yaml
   mission_slug: unified-charter-bundle-chokepoint-01KP5Q2G
   wps:
     - WP01
   # WP02, WP03, WP04 append their entries as they merge.
   must_be_zero_after:
     - "direct_read_of_governance_yaml_bypassing_chokepoint"
     - "direct_read_of_directives_yaml_bypassing_chokepoint"
     - "direct_read_of_metadata_yaml_bypassing_chokepoint"
     - "fr004_reader_missing_ensure_charter_bundle_fresh_call"
   carve_outs:
     - path: src/charter/sync.py
       reason: "Chokepoint performs the authoritative read."
     - path: src/charter/bundle.py
       reason: "Manifest declaration; carve-out C-012."
     - path: src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py
       reason: "Migration performs bundle validation; WP04 adds this file."
     - path: src/specify_cli/core/worktree.py
       reason: "C-011: memory/AGENTS sharing is documented-intentional and out of scope."
     - path: src/charter/compiler.py
       reason: "C-012: compiler pipeline owns references.yaml."
     - path: src/charter/context.py
       reason: "C-012: context-state.json write path at lines 385-398 is runtime-state, out of v1.0.0 scope."
   ```

**Files**:
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP01.yaml` (new)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml` (new, seed state)

**Validation**:
- [ ] `python scripts/verify_occurrences.py kitty-specs/.../occurrences/WP01.yaml` exits 0 (to-change set is empty — WP01 only adds files).
- [ ] YAML round-trips cleanly.

---

## Definition of Done

- [ ] T001–T007 all complete.
- [ ] `pytest tests/charter/test_bundle_manifest_model.py tests/charter/test_bundle_validate_cli.py` green.
- [ ] `mypy --strict src/charter/bundle.py src/specify_cli/cli/commands/charter_bundle.py` green.
- [ ] Verifier green against `WP01.yaml`.
- [ ] No edits to `src/specify_cli/core/worktree.py:478-532` (C-011).
- [ ] No edits to `src/charter/compiler.py` or `src/charter/context.py:385-398` (C-012).
- [ ] No edits to existing reader sites (reserved for WP03).
- [ ] The temporary resolver wrapper remains in place with its TODO marker; no attempt is made to use the real canonical-root resolver (that is a downstream WP concern).

## Risks

- **Cross-region charter.py ownership tension**. `charter_bundle.py` is a self-contained sub-app; it will be registered into the main `charter` CLI by WP03. Do NOT register it in WP01 — that would conflict with WP03's ownership of `charter.py`.
- **Temporary resolver wrapper drift**. The `_resolve_canonical_root_TEMP` function MUST be flagged with `TODO(WP02)` so WP03 finds and replaces it when WP02's `resolve_canonical_repo_root` is available.
- **Scope creep into v1.1.0**. Do NOT add `references.yaml` or `context-state.json` to the manifest. Anyone suggesting that change is fighting C-012.

## Reviewer guidance

- Verify `CANONICAL_MANIFEST.derived_files` matches `_SYNC_OUTPUT_FILES` at `src/charter/sync.py:32-36` exactly (three entries, same filenames).
- Run `diff <(python -c "from charter.bundle import CANONICAL_MANIFEST; print('\n'.join(sorted(str(p) for p in CANONICAL_MANIFEST.derived_files)))") <(python -c "from charter.sync import _SYNC_OUTPUT_FILES; print('\n'.join(sorted('.kittify/charter/' + f for f in _SYNC_OUTPUT_FILES)))")` — expect empty diff.
- Verify the TODO marker is present and occurrence artifact records it.
- Verify no edits to carve-out files.
