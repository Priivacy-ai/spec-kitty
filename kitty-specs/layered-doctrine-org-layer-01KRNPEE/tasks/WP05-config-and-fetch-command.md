---
work_package_id: WP05
title: Config Model and doctrine fetch Command
dependencies:
- WP03
- WP04
requirement_refs:
- C-001
- C-002
- C-004
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-020
- NFR-006
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "597832"
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/config.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/config.py
- src/specify_cli/cli/commands/doctrine.py
- tests/specify_cli/doctrine/test_config.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Implement `DoctrineOrgConfig` (Pydantic model for the `doctrine.org` config block), wire it
into `DoctrineService` factory call sites, and create the `spec-kitty doctrine` CLI command
group with `fetch`, `pack validate` (stub), and `pack assemble` (stub).

---

## Context

`.kittify/config.yaml` is already loaded by multiple parts of `specify_cli`. This WP adds
a `doctrine.org` block to that schema without breaking any existing reader. The Pydantic
model validates the block and provides typed access.

The `doctrine.py` CLI file is new — it creates the `doctrine` subcommand group and registers
the `fetch` subcommand. The `pack validate` and `pack assemble` stubs are wired to their
implementation functions (which are created in WP06); the stubs raise `NotImplementedError`
until WP06 fills them in.

See `contracts/config-schema.yaml` for the normative config schema.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP05 --agent claude:sonnet-4-6`

---

## Subtask T022 — Implement `OrgPackConfig`, `PackRegistry`, and load/save functions

**File**: `src/specify_cli/doctrine/config.py`

```python
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, field_validator, model_validator
from typing import Literal

class OrgPackConfig(BaseModel):
    """Single named org doctrine pack entry."""
    name: str
    local_path: Path
    source_type: Literal["git", "https", "api"] | None = None
    url: str | None = None
    ref: str | None = None

    @field_validator("local_path", mode="before")
    @classmethod
    def expand_tilde(cls, v: str | Path) -> Path:
        return Path(str(v)).expanduser()

class PackRegistry(BaseModel):
    """Ordered list of configured org doctrine packs."""
    packs: list[OrgPackConfig] = []

    @model_validator(mode="after")
    def validate_unique_names(self) -> "PackRegistry":
        names = [p.name for p in self.packs]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(f"Duplicate pack names in doctrine.org.packs: {dupes}")
        return self

def load_pack_registry(repo_root: Path) -> PackRegistry:
    """Read doctrine.org from .kittify/config.yaml; return empty registry if absent.

    Handles both forms:
    - Multi-pack: doctrine.org.packs list → PackRegistry
    - Legacy single: doctrine.org.local_path → PackRegistry with one anonymous pack
    """
    ...

def save_pack_registry(repo_root: Path, registry: PackRegistry) -> None:
    """Write doctrine.org.packs block to .kittify/config.yaml (merge, preserve other keys)."""
    ...
```

**Implementation notes for `load_pack_registry()`**:
1. Locate `.kittify/config.yaml` from `repo_root`. If absent, return `PackRegistry()` (empty).
2. Load YAML; navigate `data.get("doctrine", {}).get("org")`. If absent, return `PackRegistry()`.
3. If the `org` block has a `packs` key: validate as `PackRegistry.model_validate({"packs": org["packs"]})`.
4. If the `org` block has a `local_path` key (legacy single-pack form): construct one
   anonymous `OrgPackConfig` with `name="default"` and the given fields.
5. On `ValidationError` (including duplicate name): emit `warnings.warn` and return `PackRegistry()`.

---

## Subtask T023 — Wire `PackRegistry` into `DoctrineService` factory sites

Search for all instantiation sites of `DoctrineService(` in `src/` using
`grep -rn "DoctrineService(" src/`. For each site where `repo_root` is in scope:

```python
from specify_cli.doctrine.config import load_pack_registry
registry = load_pack_registry(repo_root)
org_roots = [pack.local_path for pack in registry.packs]
# then pass org_roots=org_roots to DoctrineService(...)
```

If `repo_root` is not in scope: pass `org_roots=[]` with a `# TODO: wire org_roots` comment.

WP07 owns `context.py` and wires that site. This WP updates any other factory sites not
owned by WP07.

---

## Subtask T024 — Implement `spec-kitty doctrine` command group and `fetch` subcommand

**File**: `src/specify_cli/cli/commands/doctrine.py` (new file)

The `fetch` command supports an optional `--pack <name>` flag (FR-020). Without it, all
configured packs are fetched in declaration order. With it, only the named pack is fetched.

```python
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

app = typer.Typer(name="doctrine", help="Manage org-layer doctrine packs")
console = Console()

@app.command(name="fetch")
def fetch(
    pack_name: Optional[str] = typer.Option(None, "--pack", help="Fetch only this named pack"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fetched"),
) -> None:
    """Fetch org doctrine pack(s) from their configured remote sources."""
    from specify_cli.core.paths import locate_project_root
    from specify_cli.doctrine.config import load_pack_registry
    from specify_cli.doctrine.snapshot import fetch_pack

    repo_root = locate_project_root()
    registry = load_pack_registry(repo_root)

    if not registry.packs:
        console.print("[red]No org doctrine packs configured.[/red]")
        console.print("Add 'doctrine.org.packs' to .kittify/config.yaml")
        raise typer.Exit(1)

    target_packs = registry.packs
    if pack_name is not None:
        target_packs = [p for p in registry.packs if p.name == pack_name]
        if not target_packs:
            names = ", ".join(p.name for p in registry.packs)
            console.print(f"[red]Pack '{pack_name}' not found. Configured: {names}[/red]")
            raise typer.Exit(1)

    if dry_run:
        for pack in target_packs:
            console.print(f"Would fetch pack '{pack.name}' from {pack.url or pack.local_path}")
        return

    any_failed = False
    for pack in target_packs:
        result = fetch_pack(pack)
        if result.ok:
            console.print(f"[green]Pack '{pack.name}': {result.artifacts_written} artifacts[/green]")
            if result.pack_version:
                console.print(f"  Version: {result.pack_version}")
        else:
            console.print(f"[red]Pack '{pack.name}' failed:[/red]")
            for err in result.errors:
                console.print(f"  {err}")
            any_failed = True

    if any_failed:
        raise typer.Exit(1)
```

Add `fetch_pack(pack: OrgPackConfig) -> FetchResult` in `snapshot.py` — the single-pack
fetch entry point:

```python
def fetch_pack(pack: OrgPackConfig) -> FetchResult:
    """Fetch a single configured pack using its declared source type."""
    source = _build_source(pack)
    if isinstance(source, GitSource):
        return source.fetch(pack.local_path)   # GitSource manages its own dir
    return write_snapshot(source, pack.local_path, source_url=pack.url or "")
```

Add `_build_source(pack: OrgPackConfig) -> OrgDoctrineSource` in `snapshot.py`:

```python
def _build_source(config) -> OrgDoctrineSource:
    if config.source_type == "git":
        from specify_cli.doctrine.sources.git_source import GitSource
        return GitSource(url=config.url, ref=config.ref)
    elif pack.source_type == "https":
        from specify_cli.doctrine.sources.https_source import HttpsBundleSource
        return HttpsBundleSource(url=pack.url, ref=pack.ref)
    elif pack.source_type == "api":
        from specify_cli.doctrine.sources.api_source import ApiSource
        return ApiSource(url=pack.url, ref=pack.ref)
    raise ValueError(f"Unknown source_type: {pack.source_type!r} for pack '{pack.name}'")
```

Register `doctrine.app` in the main CLI app (find where other command groups like `charter`
and `doctor` are registered and add `doctrine`).

---

## Subtask T025 — Add `pack validate` and `pack assemble` CLI stubs

**File**: `src/specify_cli/cli/commands/doctrine.py`

Add two sub-app groups under `doctrine`:

```python
pack_app = typer.Typer(name="pack", help="Manage doctrine packs")
app.add_typer(pack_app)

@pack_app.command(name="validate")
def pack_validate(
    pack_path: Path = typer.Argument(..., help="Path to the doctrine pack directory"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Validate a doctrine pack against schema and DRG constraints."""
    from specify_cli.doctrine.pack_validator import validate_pack
    result = validate_pack(pack_path)
    _render_validation_result(result, json_output)

@pack_app.command(name="assemble")
def pack_assemble(
    output_path: Path = typer.Argument(..., help="Output directory for assembled pack"),
    input_packs: list[Path] = typer.Argument(..., help="Input pack directories"),
    conflicts_out: Path = typer.Option(None, "--conflicts-out"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Assemble multiple doctrine packs into a single distributable."""
    from specify_cli.doctrine.pack_assembler import assemble_pack
    result = assemble_pack(input_packs, output_path)
    _render_assembly_result(result, conflicts_out, json_output)
```

`_render_validation_result()` and `_render_assembly_result()` are helper functions in this
file. They use `rich` for human output and `json.dumps()` for `--json`. Both are stubs that
show a "not yet implemented" message until WP06 fills in `pack_validator.py` and
`pack_assembler.py`.

---

## Subtask T026 — Integration tests for config and `doctrine fetch`

**File**: `tests/specify_cli/doctrine/test_config.py`

| Test | Expected |
|---|---|
| `test_load_packs_list` | Config with `doctrine.org.packs` list → `PackRegistry` with all entries |
| `test_load_legacy_single_pack` | Config with `doctrine.org.local_path` → `PackRegistry` with one anonymous pack |
| `test_load_config_absent_key` | Config without `doctrine` key → empty `PackRegistry` |
| `test_load_config_no_file` | No `.kittify/config.yaml` → empty `PackRegistry` |
| `test_duplicate_pack_names` | Two packs with same `name` → warning emitted, empty registry |
| `test_save_config_new_block` | No existing `doctrine` → `packs` block added |
| `test_save_config_merge` | Existing `doctrine` with `vcs`/`agents` keys → `org.packs` added, others preserved |
| `test_tilde_expansion` | `local_path: "~/.kittify/org/security/"` → `Path.expanduser()` applied |
| `test_fetch_all_packs` | 2 packs configured; mock fetch for each | Both packs fetched, success output per pack |
| `test_fetch_single_pack_flag` | 2 packs; `--pack security` | Only security pack fetched |
| `test_fetch_unknown_pack_flag` | `--pack nonexistent` | Exit 1 with available pack names |
| `test_fetch_no_config` | Empty registry | Exit 1 with configuration hint |

---

## Definition of Done

- [ ] `OrgPackConfig` model validates `name`, `local_path`, `source_type`, `url`, `ref`; tilde expanded in `local_path`
- [ ] `PackRegistry` validates duplicate names at load time; emits warning and returns empty on error
- [ ] `load_pack_registry()` handles multi-pack list and legacy single-`local_path` forms; returns empty registry (not None) on missing config
- [ ] `save_pack_registry()` merges without clobbering existing config keys
- [ ] `doctrine fetch` fetches all packs when no `--pack` flag; fetches one when flag given
- [ ] `doctrine fetch --pack <unknown>` exits 1 with list of valid pack names
- [ ] `spec-kitty doctrine pack validate` and `pack assemble` stubs registered
- [ ] All tests in `test_config.py` pass
- [ ] `spec-kitty doctrine --help` shows all subcommands

## Risks

- Adding `doctrine` to the CLI app must not conflict with any existing subcommand name.
  Run `spec-kitty --help` before and after to confirm.
- Config save must be non-destructive; test with a config that has existing `vcs`, `agents`,
  `merge` keys to confirm none are lost.

## Reviewer Guidance

1. Confirm tilde expansion happens at validation time (not read time).
2. Confirm the CLI stubs exit gracefully with a message when the implementation module is
   missing (WP06 not yet merged).
3. Verify `_build_source()` error on unknown `source_type` is user-friendly.

## Activity Log

- 2026-05-15T13:49:04Z – claude:opus-4-7:python-pedro:implementer – shell_pid=597832 – Started implementation via action command
