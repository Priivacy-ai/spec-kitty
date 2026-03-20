---
work_package_id: WP05
title: Init Wiring
lane: "doing"
dependencies: [WP01, WP02, WP03, WP04]
base_branch: 042-agent-skills-installer-infrastructure-WP04
base_commit: 02040aa5810b7dde66c0e3394a7178d059c38ca9
created_at: '2026-03-20T17:40:58.895766+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
phase: Phase 3 - Integration
assignee: ''
agent: "coordinator"
shell_pid: "48589"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-022
---

# Work Package Prompt: WP05 – Init Wiring

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

Depends on WP01–WP04.

---

## Objectives & Success Criteria

1. `spec-kitty init --skills auto|native|shared|wrappers-only` creates the correct skill root directories.
2. Manifest is written after init with all managed files tracked.
3. Post-init verification runs and reports results.
4. Wrappers continue to be generated identically (no behavioral change for existing users).
5. `--skills wrappers-only` produces exact pre-Phase-0 behavior (no skill roots, no manifest skill roots, manifest still written for tracking).

## Context & Constraints

- **Spec**: FR-004 through FR-015, FR-022
- **Plan**: Section 6 (Init Modifications)
- **Current init code**: `src/specify_cli/cli/commands/init.py` — review lines 179–620
- **Insert point**: After wrapper generation (line ~495) and before git init (line ~528)
- **Tracker pattern**: Follow existing `tracker.add()`/`tracker.start()`/`tracker.complete()` pattern

## Subtasks & Detailed Guidance

### Subtask T021 – Add --skills flag to init signature

**Purpose**: New CLI option for skill distribution mode.

**Steps**:
1. In `src/specify_cli/cli/commands/init.py`, add parameter to the `init()` function:
   ```python
   skills_mode: str = typer.Option(
       "auto",
       "--skills",
       help="Skill distribution mode: auto, native, shared, or wrappers-only",
   ),
   ```
2. Add it after the existing `non_interactive` parameter.

**Files**: `src/specify_cli/cli/commands/init.py`

### Subtask T022 – Validate --skills flag value

**Purpose**: Fail early with a clear error on invalid mode.

**Steps**:
1. After agent selection and before template preparation, validate:
   ```python
   VALID_SKILLS_MODES = {"auto", "native", "shared", "wrappers-only"}
   if skills_mode not in VALID_SKILLS_MODES:
       _console.print(
           f"[red]Error:[/red] Invalid --skills value '{skills_mode}'. "
           f"Choose from: {', '.join(sorted(VALID_SKILLS_MODES))}"
       )
       raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/init.py`

### Subtask T023 – Add skill root resolution step

**Purpose**: Compute which skill roots to create after wrappers are generated.

**Steps**:
1. After the wrapper generation loop (around line 495, after the `for index, agent_key in enumerate(selected_agents)` block completes), add:
   ```python
   from specify_cli.skills.roots import resolve_skill_roots
   resolved_roots = resolve_skill_roots(selected_agents, mode=skills_mode)
   ```
2. Add tracker step:
   ```python
   tracker.add("skills-resolve", "Resolve skill roots")
   tracker.start("skills-resolve")
   if resolved_roots:
       tracker.complete("skills-resolve", f"{len(resolved_roots)} root(s)")
   else:
       tracker.complete("skills-resolve", "none needed")
   ```

**Files**: `src/specify_cli/cli/commands/init.py`

### Subtask T024 – Create skill root directories with .gitkeep

**Purpose**: Materialize the resolved roots on disk.

**Steps**:
1. After resolution, create directories:
   ```python
   tracker.add("skills-create", "Create skill directories")
   tracker.start("skills-create")
   for root in resolved_roots:
       root_path = project_path / root
       root_path.mkdir(parents=True, exist_ok=True)
       gitkeep = root_path / ".gitkeep"
       if not gitkeep.exists():
           gitkeep.write_text("", encoding="utf-8")
   tracker.complete("skills-create", f"{len(resolved_roots)} created")
   ```
2. Use `exist_ok=True` so existing directories (from non-Spec-Kitty sources) are not disturbed.

**Files**: `src/specify_cli/cli/commands/init.py`

### Subtask T025 – Write manifest

**Purpose**: Track all managed files (wrappers + skill root markers) in the manifest.

**Steps**:
1. After skill root creation, collect managed files:
   ```python
   from specify_cli.skills.manifest import (
       ManagedFile, SkillsManifest, compute_file_hash, write_manifest,
   )
   from datetime import datetime, timezone

   tracker.add("skills-manifest", "Write installation manifest")
   tracker.start("skills-manifest")

   managed_files: list[ManagedFile] = []

   # Collect skill root markers
   for root in resolved_roots:
       gitkeep = project_path / root / ".gitkeep"
       if gitkeep.exists():
           managed_files.append(ManagedFile(
               path=str(Path(root) / ".gitkeep"),
               sha256=compute_file_hash(gitkeep),
               file_type="skill_root_marker",
           ))

   # Collect wrapper files
   for agent_key in selected_agents:
       from specify_cli.core.agent_surface import get_agent_surface
       surface = get_agent_surface(agent_key)
       wrapper_dir = project_path / surface.wrapper.dir
       if wrapper_dir.exists():
           for wrapper_file in sorted(wrapper_dir.iterdir()):
               if wrapper_file.is_file() and wrapper_file.name.startswith("spec-kitty."):
                   managed_files.append(ManagedFile(
                       path=str(wrapper_file.relative_to(project_path)),
                       sha256=compute_file_hash(wrapper_file),
                       file_type="wrapper",
                   ))

   now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
   manifest = SkillsManifest(
       spec_kitty_version=__version__,  # import from specify_cli
       created_at=now_iso,
       updated_at=now_iso,
       skills_mode=skills_mode,
       selected_agents=list(selected_agents),
       installed_skill_roots=resolved_roots,
       managed_files=managed_files,
   )
   write_manifest(project_path, manifest)
   tracker.complete("skills-manifest", f"{len(managed_files)} files tracked")
   ```

2. Import `__version__` from the package root or use a version detection function if one exists.

**Files**: `src/specify_cli/cli/commands/init.py`

### Subtask T026 – Run verification

**Purpose**: Catch installation failures immediately.

**Steps**:
1. After manifest write:
   ```python
   from specify_cli.skills.verification import verify_installation

   tracker.add("skills-verify", "Verify installation")
   tracker.start("skills-verify")
   verification = verify_installation(project_path, selected_agents, manifest)
   if verification.passed:
       tracker.complete("skills-verify", "all checks passed")
   else:
       for error in verification.errors:
           _console.print(f"  [red]✗[/red] {error}")
       for warning in verification.warnings:
           _console.print(f"  [yellow]⚠[/yellow] {warning}")
       tracker.error("skills-verify", f"{len(verification.errors)} error(s)")
   ```

2. Verification failures should be reported as warnings (not crash init) — the installation partially succeeded and the user can repair with sync.

**Files**: `src/specify_cli/cli/commands/init.py`

### Subtask T027 – Integration tests

**Purpose**: Verify the full init flow with --skills flag.

**Steps**:
1. Create `tests/specify_cli/test_cli/test_init_skills.py`
2. Tests should use the init command programmatically or via `CliRunner`:

```python
# Test auto mode creates shared + native roots
def test_init_auto_mode(tmp_path):
    # Run init with claude + codex
    # Verify .agents/skills/ exists (for codex)
    # Verify .claude/skills/ exists (for claude)
    # Verify manifest exists and contains correct data
    # Verify wrappers generated for both agents

# Test wrappers-only mode creates no skill roots
def test_init_wrappers_only(tmp_path):
    # Run init with --skills wrappers-only
    # Verify no .agents/skills/ or .claude/skills/
    # Verify manifest exists with empty installed_skill_roots
    # Verify wrappers generated normally

# Test native mode prefers vendor roots
def test_init_native_mode(tmp_path):
    # Run init with copilot in native mode
    # Verify .github/skills/ exists (not just .agents/skills/)

# Test invalid --skills flag rejected
def test_init_invalid_skills_mode(tmp_path):
    # Run init with --skills invalid
    # Verify exit code 1 and error message
```

**Files**: `tests/specify_cli/test_cli/test_init_skills.py` (new, ~120 lines)

**Note**: These tests need the init command to be callable without interactive prompts. Use `--ai` and `--non-interactive` flags, and `--template-root` to point at the local source.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Init tracker ordering disrupted | Insert new steps between wrapper generation and git init — test the tracker output |
| __version__ import location | Check how existing code gets the version — likely `from specify_cli import __version__` |
| Wrapper file collection misses generated files | Test by comparing collected file count against expected template count |

## Review Guidance

1. Verify new steps are inserted **between** wrapper generation and git init (not before wrappers, not after git).
2. Verify `--skills wrappers-only` produces ZERO new directories beyond what pre-Phase-0 init created.
3. Verify manifest includes BOTH wrapper files AND skill root markers.
4. Verify verification failures are reported as warnings, not crashes.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T17:40:59Z – coordinator – shell_pid=48589 – lane=doing – Assigned agent via workflow command
