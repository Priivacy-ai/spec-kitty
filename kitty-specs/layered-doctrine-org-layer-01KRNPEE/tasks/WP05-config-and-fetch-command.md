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
- NFR-006
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: All planning and implementation targets feat/org-doctrine-layer. Worktree branch allocated by finalize-tasks lane computation.
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: codex
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
- **Implement command**: `spec-kitty agent action implement WP05 --agent codex`

---

## Subtask T022 — Implement `DoctrineOrgConfig` and load/save functions

**File**: `src/specify_cli/doctrine/config.py`

```python
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import Literal

class DoctrineOrgConfig(BaseModel):
    local_path: Path
    source_type: Literal["git", "https", "api"] | None = None
    url: str | None = None
    ref: str | None = None

    @field_validator("local_path", mode="before")
    @classmethod
    def expand_tilde(cls, v: str | Path) -> Path:
        return Path(str(v)).expanduser()

def load_doctrine_org_config(repo_root: Path) -> DoctrineOrgConfig | None:
    """Read doctrine.org from .kittify/config.yaml; return None if absent."""
    ...

def save_doctrine_org_config(repo_root: Path, config: DoctrineOrgConfig) -> None:
    """Write doctrine.org block to .kittify/config.yaml (merge, don't overwrite)."""
    ...
```

**Implementation notes for `load_doctrine_org_config()`**:
1. Locate `.kittify/config.yaml` from `repo_root`. If absent, return `None`.
2. Load YAML with `ruamel.yaml` (consistent with existing config loaders).
3. Navigate `data.get("doctrine", {}).get("org")`. If absent, return `None`.
4. Validate with `DoctrineOrgConfig.model_validate(org_block)`.
5. On `ValidationError`: emit a `warnings.warn` and return `None`.

**Implementation notes for `save_doctrine_org_config()`**:
1. Load existing config YAML (or start with empty dict).
2. Set `data.setdefault("doctrine", {})["org"] = config.model_dump(exclude_none=True)`.
3. Serialize `local_path` back to string (keep tilde if the path starts with home dir).
4. Write back atomically.

---

## Subtask T023 — Wire config into `DoctrineService` factory sites

Search for all instantiation sites of `DoctrineService(` in `src/` using
`grep -rn "DoctrineService(" src/`. For each site, check if `repo_root` is available
in scope:

- If `repo_root` is available: import `load_doctrine_org_config` and pass
  `org_roots=[config.local_path] if (config := load_doctrine_org_config(repo_root)) else []`.
- If `repo_root` is not available: pass `org_roots=[]` and add a TODO comment.

The primary instantiation site is likely in `charter/context.py` (owned by WP07) and in
a factory function or command callback — identify those and update the ones this WP owns.

This WP specifically owns the wiring in files listed in `owned_files`. WP07 will update
`context.py`. Update any other factory sites not owned by WP07.

---

## Subtask T024 — Implement `spec-kitty doctrine` command group and `fetch` subcommand

**File**: `src/specify_cli/cli/commands/doctrine.py` (new file)

```python
import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(name="doctrine", help="Manage org-layer doctrine packs")
console = Console()

@app.command(name="fetch")
def fetch(
    config_path: Path = typer.Option(None, "--config", help="Path to .kittify/config.yaml"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fetched"),
) -> None:
    """Fetch org doctrine pack from the configured remote source."""
    from specify_cli.core.paths import locate_project_root
    from specify_cli.doctrine.config import load_doctrine_org_config
    from specify_cli.doctrine.sources.protocol import OrgDoctrineSource
    from specify_cli.doctrine.snapshot import write_snapshot, _build_source

    repo_root = locate_project_root()
    config = load_doctrine_org_config(repo_root)
    if config is None:
        console.print("[red]No org doctrine source configured.[/red]")
        console.print("Add a 'doctrine.org' block to .kittify/config.yaml")
        raise typer.Exit(1)

    if dry_run:
        console.print(f"Would fetch from: {config.url or config.local_path}")
        console.print(f"Target: {config.local_path}")
        return

    source = _build_source(config)
    result = write_snapshot(source, config.local_path, source_url=config.url or "")

    if result.ok:
        console.print(f"[green]Fetched {result.artifacts_written} artifacts[/green]")
        if result.pack_version:
            console.print(f"Version: {result.pack_version}")
    else:
        for err in result.errors:
            console.print(f"[red]Error: {err}[/red]")
        raise typer.Exit(1)
```

Add `_build_source(config: DoctrineOrgConfig) -> OrgDoctrineSource` in `snapshot.py`:

```python
def _build_source(config) -> OrgDoctrineSource:
    if config.source_type == "git":
        from specify_cli.doctrine.sources.git_source import GitSource
        return GitSource(url=config.url, ref=config.ref)
    elif config.source_type == "https":
        from specify_cli.doctrine.sources.https_source import HttpsBundleSource
        return HttpsBundleSource(url=config.url, ref=config.ref)
    elif config.source_type == "api":
        from specify_cli.doctrine.sources.api_source import ApiSource
        return ApiSource(url=config.url, ref=config.ref)
    raise ValueError(f"Unknown source_type: {config.source_type!r}")
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
| `test_load_config_present` | Config with `doctrine.org` block → `DoctrineOrgConfig` returned |
| `test_load_config_absent_key` | Config without `doctrine` key → `None` |
| `test_load_config_no_file` | No `.kittify/config.yaml` → `None` |
| `test_load_config_validation_error` | Invalid `source_type` → warning emitted, `None` returned |
| `test_save_config_new_block` | No existing `doctrine` → block added |
| `test_save_config_merge` | Existing `doctrine` with other keys → `org` key added, others preserved |
| `test_tilde_expansion` | `local_path: "~/.kittify/org/"` → `Path.expanduser()` applied |
| `test_fetch_command_git_mocked` | Invoke CLI `doctrine fetch` with mocked `GitSource` → success output |
| `test_fetch_command_no_config` | Invoke `doctrine fetch` with no config → exit 1 |

---

## Definition of Done

- [ ] `DoctrineOrgConfig` model validates `local_path`, `source_type`, `url`, `ref`
- [ ] `load_doctrine_org_config()` returns `None` on missing config or invalid block
- [ ] `save_doctrine_org_config()` merges without clobbering existing config keys
- [ ] `spec-kitty doctrine fetch` command registered in main CLI
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
