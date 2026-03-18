---
work_package_id: WP03
title: Doctor State-Roots Command
lane: planned
dependencies:
- WP01
base_branch: 050-state-model-cleanup-foundations-WP01
base_commit: 224fc89984e7bba1aac90032c254569380e6091d
created_at: '2026-03-18T19:21:19.200369+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Diagnostics
assignee: ''
agent: coordinator
shell_pid: '28963'
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://050-state-model-cleanup-foundations/WP03/20260318T193454Z-1e796431.md
history:
- timestamp: '2026-03-18T18:52:42Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-008
- FR-009
- NFR-002
---

# Work Package Prompt: WP03 – Doctor State-Roots Command

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

> **Reference-only section** – Canonical review feedback is stored via frontmatter `review_feedback` (`feedback://...`).

---

## Objectives & Success Criteria

- New `spec-kitty doctor` top-level command group exists with `state-roots` as its first subcommand.
- `spec-kitty doctor state-roots` prints:
  - The three state roots with resolved paths and existence status.
  - A table of all registered surfaces grouped by root, showing authority class, Git class, and on-disk presence.
  - Warnings for any repo-local runtime surfaces not covered by `.gitignore`.
- `--json` flag outputs machine-readable JSON matching `StateRootsReport.to_dict()`.
- Tests validate output for various filesystem states (surfaces present/absent, git repo/not-git-repo).

## Context & Constraints

- **Spec**: FR-008 (doctor command), FR-009 (--json output), NFR-002 (< 2s)
- **Plan**: Design decision D1 (top-level doctor group), Module Interfaces section
- **Data Model**: `StateRootInfo`, `SurfaceCheckResult`, `StateRootsReport` dataclasses
- **Research**: R6 (use `git check-ignore` for gitignore coverage)
- **Existing patterns**: `src/specify_cli/runtime/doctor.py` uses `DoctorCheck` dataclass — this command uses its own `StateRootsReport` since the structure is different.
- **Root resolution**:
  - Project: `locate_project_root()` from `specify_cli.core.paths`
  - Global runtime: `get_kittify_home()` from `specify_cli.runtime.home`
  - Global sync: `Path.home() / '.spec-kitty'` (hardcoded, matching `sync/config.py`)

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T010 – Create `state/` Package

- **Purpose**: Establish a new subpackage for state-model diagnostics, separate from the existing `status/` package (which is feature-scoped).
- **Files**:
  - `src/specify_cli/state/__init__.py` (new)
  - `src/specify_cli/state/doctor.py` (new, created in T011)
- **Steps**:
  1. Create `src/specify_cli/state/` directory.
  2. Create `src/specify_cli/state/__init__.py` with:
     ```python
     """State model diagnostics for spec-kitty CLI.

     This package provides project-scoped state health checks,
     distinct from the feature-scoped status checks in specify_cli.status.
     """
     ```
- **Notes**: Keep the `__init__.py` minimal. Public API exports will be added once `doctor.py` is implemented.

### Subtask T011 – Implement `check_state_roots()`

- **Purpose**: Core diagnostic logic that resolves state roots, checks surface presence, and validates gitignore coverage.
- **File**: `src/specify_cli/state/doctor.py` (new)
- **Steps**:
  1. Define dataclasses (from data-model.md):
     ```python
     from __future__ import annotations
     from dataclasses import dataclass, field
     from pathlib import Path
     import subprocess
     import logging

     from specify_cli.state_contract import (
         STATE_SURFACES,
         StateSurface,
         StateRoot,
         GitClass,
         AuthorityClass,
         get_surfaces_by_root,
     )

     logger = logging.getLogger(__name__)

     @dataclass
     class StateRootInfo:
         name: str
         label: str
         resolved_path: Path
         exists: bool

     @dataclass
     class SurfaceCheckResult:
         surface: StateSurface
         present: bool
         gitignore_covered: bool
         warning: str | None = None

     @dataclass
     class StateRootsReport:
         roots: list[StateRootInfo] = field(default_factory=list)
         surfaces: list[SurfaceCheckResult] = field(default_factory=list)
         warnings: list[str] = field(default_factory=list)

         @property
         def healthy(self) -> bool:
             return len(self.warnings) == 0

         def to_dict(self) -> dict:
             return {
                 "healthy": self.healthy,
                 "roots": [
                     {"name": r.name, "label": r.label,
                      "resolved_path": str(r.resolved_path), "exists": r.exists}
                     for r in self.roots
                 ],
                 "surfaces": [
                     {"name": s.surface.name, "path_pattern": s.surface.path_pattern,
                      "root": s.surface.root.value, "authority": s.surface.authority.value,
                      "git_class": s.surface.git_class.value, "present": s.present,
                      "gitignore_covered": s.gitignore_covered, "warning": s.warning}
                     for s in self.surfaces
                 ],
                 "warnings": self.warnings,
             }
     ```

  2. Implement gitignore check helper:
     ```python
     def _is_gitignore_covered(repo_root: Path, path: str) -> bool | None:
         """Check if a path is covered by .gitignore rules.

         Returns True if ignored, False if not ignored, None if git is unavailable.
         """
         try:
             result = subprocess.run(
                 ["git", "check-ignore", "-q", path],
                 cwd=str(repo_root),
                 capture_output=True,
                 timeout=5,
             )
             return result.returncode == 0
         except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
             return None
     ```

  3. Implement `check_state_roots()`:
     ```python
     def check_state_roots(repo_root: Path) -> StateRootsReport:
         from specify_cli.runtime.home import get_kittify_home

         report = StateRootsReport()

         # Resolve roots
         project_root = repo_root / ".kittify"
         global_runtime = get_kittify_home()
         global_sync = Path.home() / ".spec-kitty"

         report.roots = [
             StateRootInfo("project", "Project-local state", project_root, project_root.is_dir()),
             StateRootInfo("global_runtime", "Global runtime home", global_runtime, global_runtime.is_dir()),
             StateRootInfo("global_sync", "Global sync/auth home", global_sync, global_sync.is_dir()),
         ]

         # Check each surface
         for surface in STATE_SURFACES:
             present = _check_surface_present(repo_root, surface)
             gitignore_covered = _check_gitignore(repo_root, surface)
             warning = _generate_warning(surface, present, gitignore_covered)

             result = SurfaceCheckResult(
                 surface=surface,
                 present=present,
                 gitignore_covered=gitignore_covered,
                 warning=warning,
             )
             report.surfaces.append(result)

             if warning:
                 report.warnings.append(warning)

         return report
     ```

  4. Implement helper functions:
     ```python
     def _check_surface_present(repo_root: Path, surface: StateSurface) -> bool:
         """Check if a surface exists on disk."""
         if surface.root == StateRoot.PROJECT:
             path = repo_root / surface.path_pattern
         elif surface.root == StateRoot.FEATURE:
             # Feature surfaces use wildcards — check if any match exists
             # For now, skip presence check for wildcard paths
             return False  # Can't check without a specific feature
         elif surface.root == StateRoot.GLOBAL_RUNTIME:
             from specify_cli.runtime.home import get_kittify_home
             # Strip leading ~/ prefix for resolution
             relative = surface.path_pattern.replace("~/.kittify/", "")
             path = get_kittify_home() / relative
         elif surface.root == StateRoot.GLOBAL_SYNC:
             relative = surface.path_pattern.replace("~/.spec-kitty/", "")
             path = Path.home() / ".spec-kitty" / relative
         elif surface.root == StateRoot.GIT_INTERNAL:
             # Check under .git/
             relative = surface.path_pattern.replace(".git/", "")
             path = repo_root / ".git" / relative
         else:
             return False

         # Handle wildcard patterns — check if parent dir exists
         if "<" in str(path) or "*" in str(path):
             # Can't check parameterized paths; check parent dir instead
             parent = path.parent
             while "<" in str(parent) or "*" in str(parent):
                 parent = parent.parent
             return parent.is_dir()

         return path.exists()

     def _check_gitignore(repo_root: Path, surface: StateSurface) -> bool:
         """Check gitignore coverage for repo-local surfaces."""
         if surface.root not in (StateRoot.PROJECT,):
             return True  # Non-repo surfaces don't need gitignore
         if surface.git_class in (GitClass.TRACKED, GitClass.OUTSIDE_REPO, GitClass.GIT_INTERNAL):
             return True  # Tracked or external surfaces don't need gitignore

         result = _is_gitignore_covered(repo_root, surface.path_pattern)
         if result is None:
             return True  # Can't verify, don't warn
         return result

     def _generate_warning(
         surface: StateSurface, present: bool, gitignore_covered: bool
     ) -> str | None:
         """Generate a warning if a runtime surface is present but not ignored."""
         if surface.root != StateRoot.PROJECT:
             return None
         if surface.git_class in (GitClass.TRACKED, GitClass.OUTSIDE_REPO, GitClass.GIT_INTERNAL):
             return None
         if surface.authority not in (AuthorityClass.LOCAL_RUNTIME, AuthorityClass.DERIVED):
             return None
         if not present:
             return None
         if gitignore_covered:
             return None

         return (
             f"{surface.name} ({surface.path_pattern}) is present but not gitignored. "
             f"Authority: {surface.authority.value}. Risk: accidental commit."
         )
     ```

- **Notes**:
  - Feature surfaces (`kitty-specs/<feature>/...`) use parameterized paths — the doctor checks the parent directory existence, not individual features.
  - Global surfaces (`~/.kittify/`, `~/.spec-kitty/`) are always "covered" from a gitignore perspective since they're outside the repo.
  - The `_is_gitignore_covered()` function uses `git check-ignore -q` which handles all gitignore rule complexity (negation, nested files, etc.).

### Subtask T012 – Create Doctor CLI Command

- **Purpose**: Wire the diagnostic logic into a new top-level `spec-kitty doctor` command group.
- **File**: `src/specify_cli/cli/commands/doctor.py` (new)
- **Steps**:
  1. Create the Typer app and `state-roots` subcommand:
     ```python
     """Top-level doctor command group for project health diagnostics."""
     from __future__ import annotations

     import json
     from typing import Optional

     import typer
     from rich.console import Console
     from rich.table import Table
     from typing_extensions import Annotated

     from specify_cli.core.paths import locate_project_root

     app = typer.Typer(name="doctor", help="Project health diagnostics")
     console = Console()

     @app.command(name="state-roots")
     def state_roots(
         json_output: Annotated[
             bool,
             typer.Option("--json", help="Machine-readable JSON output"),
         ] = False,
     ) -> None:
         """Show state roots, surface classification, and safety warnings.

         Displays the three state roots with resolved paths, all registered
         state surfaces grouped by root with authority and Git classification,
         and warnings for any runtime surfaces not covered by .gitignore.

         Examples:
             spec-kitty doctor state-roots
             spec-kitty doctor state-roots --json
         """
         from specify_cli.state.doctor import check_state_roots
         from specify_cli.state_contract import StateRoot

         try:
             repo_root = locate_project_root()
         except Exception:
             console.print("[red]Error:[/red] Not in a spec-kitty project")
             raise typer.Exit(1)

         report = check_state_roots(repo_root)

         if json_output:
             console.print_json(json.dumps(report.to_dict(), indent=2))
             raise typer.Exit(0 if report.healthy else 1)

         # Human-readable output
         # 1. State roots table
         console.print("\n[bold]State Roots[/bold]")
         roots_table = Table(show_header=False, box=None, padding=(0, 2))
         for root_info in report.roots:
             status = "[green]✓ exists[/green]" if root_info.exists else "[dim]✗ absent[/dim]"
             console.print(f"  {root_info.name:<20} {root_info.resolved_path}  {status}")

         # 2. Surfaces by root
         console.print()
         root_order = [StateRoot.PROJECT, StateRoot.FEATURE, StateRoot.GLOBAL_RUNTIME, StateRoot.GLOBAL_SYNC, StateRoot.GIT_INTERNAL]
         root_labels = {
             StateRoot.PROJECT: "Project Surfaces (.kittify/)",
             StateRoot.FEATURE: "Feature Surfaces (kitty-specs/)",
             StateRoot.GLOBAL_RUNTIME: "Global Runtime (~/.kittify/)",
             StateRoot.GLOBAL_SYNC: "Global Sync (~/.spec-kitty/)",
             StateRoot.GIT_INTERNAL: "Git-Internal (.git/spec-kitty/)",
         }

         for root in root_order:
             root_surfaces = [s for s in report.surfaces if s.surface.root == root]
             if not root_surfaces:
                 continue

             console.print(f"[bold]{root_labels.get(root, root.value)}[/bold]")
             table = Table(box=None, padding=(0, 2), show_edge=False)
             table.add_column("Name", style="cyan", min_width=28)
             table.add_column("Authority", min_width=16)
             table.add_column("Git Policy", min_width=22)
             table.add_column("Present", justify="center", min_width=8)

             for check in root_surfaces:
                 present_icon = "[green]✓[/green]" if check.present else "[dim]✗[/dim]"
                 authority = check.surface.authority.value
                 git_class = check.surface.git_class.value
                 if check.warning:
                     authority = f"[yellow]{authority}[/yellow]"
                     git_class = f"[yellow]{git_class}[/yellow]"
                 table.add_row(check.surface.name, authority, git_class, present_icon)

             console.print(table)
             console.print()

         # 3. Warnings
         if report.warnings:
             console.print("[bold yellow]Warnings[/bold yellow]")
             for w in report.warnings:
                 console.print(f"  [yellow]⚠[/yellow] {w}")
         else:
             console.print("[green]No warnings — all runtime surfaces are properly covered.[/green]")

         console.print()
         raise typer.Exit(0 if report.healthy else 1)
     ```
- **Notes**: Uses `raise typer.Exit()` for clean exit codes (0 = healthy, 1 = issues). Lazy imports for `check_state_roots` and `StateRoot` to avoid import-time side effects.

### Subtask T013 – Register Doctor Command Group

- **Purpose**: Wire the new doctor command group into the CLI's command registration.
- **File**: `src/specify_cli/cli/commands/__init__.py`
- **Steps**:
  1. Add import at top:
     ```python
     from . import doctor as doctor_module
     ```
  2. Add registration in `register_commands()`:
     ```python
     app.add_typer(doctor_module.app, name="doctor", help="Project health diagnostics")
     ```
  3. Place the registration alphabetically among existing registrations (after `dashboard`, before `glossary`).
- **Notes**: This creates `spec-kitty doctor state-roots`. The existing `spec-kitty agent status doctor` is unchanged.

### Subtask T014 – Write Doctor Tests

- **Purpose**: Validate doctor output for various filesystem states.
- **File**: `tests/specify_cli/test_state_doctor.py` (new)
- **Steps**:
  1. **Test: roots are resolved correctly**:
     ```python
     def test_roots_resolved(tmp_path):
         """check_state_roots resolves three roots with correct names."""
         (tmp_path / ".kittify").mkdir()
         report = check_state_roots(tmp_path)
         root_names = [r.name for r in report.roots]
         assert "project" in root_names
         assert "global_runtime" in root_names
         assert "global_sync" in root_names
     ```

  2. **Test: project root existence detected**:
     ```python
     def test_project_root_exists(tmp_path):
         (tmp_path / ".kittify").mkdir()
         report = check_state_roots(tmp_path)
         project = next(r for r in report.roots if r.name == "project")
         assert project.exists is True

     def test_project_root_absent(tmp_path):
         report = check_state_roots(tmp_path)
         project = next(r for r in report.roots if r.name == "project")
         assert project.exists is False
     ```

  3. **Test: present surfaces detected**:
     ```python
     def test_surface_present(tmp_path):
         (tmp_path / ".kittify").mkdir()
         (tmp_path / ".kittify" / "config.yaml").write_text("agents: {}")
         report = check_state_roots(tmp_path)
         config_check = next(
             (s for s in report.surfaces if s.surface.name == "project_config"),
             None,
         )
         assert config_check is not None
         assert config_check.present is True
     ```

  4. **Test: absent surfaces not flagged as warnings**:
     ```python
     def test_absent_runtime_no_warning(tmp_path):
         """Absent runtime surfaces are not warnings (lazily created)."""
         (tmp_path / ".kittify").mkdir()
         report = check_state_roots(tmp_path)
         runtime_checks = [
             s for s in report.surfaces
             if s.surface.name == "runtime_feature_index"
         ]
         for check in runtime_checks:
             assert check.warning is None  # Absent = no warning
     ```

  5. **Test: report to_dict is JSON-serializable**:
     ```python
     def test_report_to_dict_serializable(tmp_path):
         report = check_state_roots(tmp_path)
         d = report.to_dict()
         import json
         json.dumps(d)  # Must not raise
         assert "healthy" in d
         assert "roots" in d
         assert "surfaces" in d
         assert "warnings" in d
     ```

  6. **Test: healthy property**:
     ```python
     def test_healthy_when_no_warnings(tmp_path):
         report = check_state_roots(tmp_path)
         # With no runtime surfaces on disk, no warnings expected
         assert report.healthy is True
     ```

  7. **Test: gitignore coverage (mock git check-ignore)**:
     ```python
     def test_warning_for_unignored_runtime(tmp_path, monkeypatch):
         """Present runtime surface not covered by gitignore produces warning."""
         (tmp_path / ".kittify").mkdir()
         (tmp_path / ".kittify" / "merge-state.json").write_text("{}")

         # Mock _is_gitignore_covered to return False
         from specify_cli.state import doctor as doctor_mod
         monkeypatch.setattr(doctor_mod, "_is_gitignore_covered", lambda *a: False)

         report = check_state_roots(tmp_path)
         merge_check = next(
             (s for s in report.surfaces if s.surface.name == "merge_resume_state"),
             None,
         )
         assert merge_check is not None
         assert merge_check.warning is not None
         assert "merge-state.json" in merge_check.warning
         assert not report.healthy
     ```

## Test Strategy

Run tests with:
```bash
pytest tests/specify_cli/test_state_doctor.py -v
```

Most tests use `tmp_path` fixture and mock `_is_gitignore_covered` to avoid git subprocess dependency. One integration-style test can exercise the real `git check-ignore` if run inside the spec-kitty repo.

## Risks & Mitigations

- **Risk**: `git check-ignore` not available. **Mitigation**: `_is_gitignore_covered` returns `None` on failure; the doctor treats `None` as "can't verify, don't warn".
- **Risk**: Performance with many surfaces. **Mitigation**: Each `git check-ignore` call is lightweight (~1ms). With ~35 surfaces, total < 100ms. Well under 2s NFR.
- **Risk**: `locate_project_root()` raises outside spec-kitty projects. **Mitigation**: Catch exception and print a user-friendly error with exit code 1.

## Review Guidance

- Verify `spec-kitty doctor state-roots` runs without error in the repo.
- Verify `--json` output is valid JSON with all required fields.
- Verify warnings appear only for present runtime surfaces that are not gitignored.
- Verify the command does NOT interfere with the existing `spec-kitty agent status doctor`.
- Verify absent surfaces are shown but not flagged as warnings (lazy creation is expected).

## Activity Log

- 2026-03-18T18:52:42Z – system – lane=planned – Prompt created.
- 2026-03-18T19:21:19Z – coordinator – shell_pid=21718 – lane=doing – Assigned agent via workflow command
- 2026-03-18T19:25:50Z – coordinator – shell_pid=21718 – lane=for_review – Doctor state-roots command complete: state/ package, check_state_roots() logic, CLI command with --json flag, registered in CLI, 11 tests passing
- 2026-03-18T19:26:11Z – codex – shell_pid=24774 – lane=doing – Started review via workflow command
- 2026-03-18T19:34:55Z – codex – shell_pid=24774 – lane=planned – Codex review: 2 findings - feature surfaces always absent, staging dirs path resolution
- 2026-03-18T19:35:03Z – coordinator – shell_pid=28963 – lane=doing – Started implementation via workflow command
