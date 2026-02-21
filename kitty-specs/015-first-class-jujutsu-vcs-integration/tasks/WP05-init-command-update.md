---
work_package_id: "WP05"
title: "Init Command Update"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
phase: "Phase 2 - Command Updates"
lane: "done"
priority: "P1"
dependencies: ["WP02"]
assignee: "__AGENT__"
agent: "__AGENT__"
shell_pid: "90012"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Init Command Update

## Objectives & Success Criteria

**Goal**: Update `spec-kitty init` to detect jj, show recommendation message, store VCS preference.

**Success Criteria**:

- Running `spec-kitty init` with jj installed shows "jj detected" confirmation
- Running `spec-kitty init` without jj shows recommendation message to install it
- VCS preference stored in `.kittify/config.yaml`
- `--vcs=git|jj` flag overrides detection
- Message is informational, not blocking

**User Stories Addressed**: US1 (P1)
**Requirements**: FR-005, FR-008

## Context & Constraints

**Reference Documents**:

- `src/specify_cli/cli/commands/init.py` - Existing init command
- `kitty-specs/015-first-class-jujutsu-vcs-integration/data-model.md` - ProjectVCSConfig structure

**Architecture Decisions**:

- jj preferred when available (FR-003)
- Info message is non-blocking (per user requirement)
- Config stored in `.kittify/config.yaml` under `vcs:` section

**Constraints**:

- Must not break existing init workflow
- Message should be clear about what VCS will be used
- Config.yaml may not exist yet (create if needed)

## Subtasks & Detailed Guidance

### Subtask T026 – Import VCS detection in init.py

**Purpose**: Add VCS detection imports to init command.

**Steps**:

1. Open `src/specify_cli/cli/commands/init.py`
2. Add imports:

   ```python
   from specify_cli.core.vcs import (
       is_jj_available,
       is_git_available,
       VCSBackend,
   )
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/init.py`

---

### Subtask T027 – Add VCS detection to init workflow

**Purpose**: Detect available VCS tools during init.

**Steps**:

1. Add VCS detection after directory setup in init workflow
2. Determine default VCS based on availability:

   ```python
   def _detect_default_vcs() -> VCSBackend:
       if is_jj_available():
           return VCSBackend.JUJUTSU
       elif is_git_available():
           return VCSBackend.GIT
       else:
           raise VCSNotFoundError("Neither jj nor git is available")
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/init.py`

---

### Subtask T028 – Implement jj recommendation message

**Purpose**: Show informational message about VCS selection.

**Steps**:

1. Add message display after VCS detection:

   ```python
   from rich.console import Console
   console = Console()

   def _display_vcs_info(detected_vcs: VCSBackend) -> None:
       if detected_vcs == VCSBackend.JUJUTSU:
           console.print("[green]✓ jj detected[/green] - will be used for new features")
           console.print("  jj enables auto-rebase and parallel multi-agent development")
       else:
           console.print("[yellow]ℹ Using git[/yellow] for version control")
           console.print()
           console.print("[dim]RECOMMENDED: Install jj (jujutsu) for improved multi-agent workflows:[/dim]")
           console.print("[dim]  - Auto-rebase of dependent work packages[/dim]")
           console.print("[dim]  - Non-blocking conflict handling[/dim]")
           console.print("[dim]  - Operation log with full undo[/dim]")
           console.print("[dim]  Install: https://github.com/martinvonz/jj#installation[/dim]")
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/init.py`

**Notes**:

- Message is informational, not an error
- Use Rich formatting for visual distinction
- Include installation link for jj

---

### Subtask T029 – Store VCS preference in config.yaml

**Purpose**: Persist VCS preference in project configuration.

**Steps**:

1. Add VCS section to `.kittify/config.yaml`:

   ```yaml
   vcs:
     preferred: "auto"  # auto | jj | git
     jj:
       min_version: "0.20.0"
       colocate: true
   ```

2. Implement config update:

   ```python
   def _save_vcs_config(config_path: Path, detected_vcs: VCSBackend) -> None:
       # Load existing config or create new
       # Add/update vcs section
       # Write back
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/init.py`

**Notes**:

- Use ruamel.yaml for round-trip editing (preserve comments)
- Create config.yaml if it doesn't exist
- Default to "auto" for preferred (detect at runtime)

---

### Subtask T030 – Add --vcs flag to init command

**Purpose**: Allow explicit VCS override during init.

**Steps**:

1. Add CLI option:

   ```python
   @app.command()
   def init(
       path: Path = typer.Argument(...),
       vcs: Optional[str] = typer.Option(
           None,
           "--vcs",
           help="VCS to use: 'git' or 'jj'. Defaults to jj if available.",
       ),
   ):
   ```

2. Validate and use override:

   ```python
   if vcs:
       if vcs not in ("git", "jj"):
           raise typer.BadParameter("--vcs must be 'git' or 'jj'")
       selected_vcs = VCSBackend(vcs)
       # Validate tool is available
       if selected_vcs == VCSBackend.JUJUTSU and not is_jj_available():
           raise typer.BadParameter("jj is not installed")
   else:
       selected_vcs = _detect_default_vcs()
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/init.py`

---

### Subtask T031 – Update init command tests [P]

**Purpose**: Test VCS detection and messaging in init command.

**Steps**:

1. Add tests to existing init tests or create new file
2. Test scenarios:
   - Init with jj available → "jj detected" message
   - Init without jj → recommendation message
   - Init with `--vcs=git` → uses git explicitly
   - Init with `--vcs=jj` when jj unavailable → error
   - Config.yaml created with vcs section

**Files**:

- Modify or create: `tests/specify_cli/cli/commands/test_init.py`

**Test Examples**:

```python
def test_init_with_jj_shows_confirmation(tmp_path, capsys):
    # Mock jj as available
    with patch("specify_cli.core.vcs.is_jj_available", return_value=True):
        result = runner.invoke(app, ["init", str(tmp_path)])
    assert "jj detected" in result.output

def test_init_without_jj_shows_recommendation(tmp_path, capsys):
    with patch("specify_cli.core.vcs.is_jj_available", return_value=False):
        result = runner.invoke(app, ["init", str(tmp_path)])
    assert "RECOMMENDED: Install jj" in result.output

def test_init_creates_vcs_config(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    config = yaml.safe_load((tmp_path / ".kittify/config.yaml").read_text())
    assert "vcs" in config
```

**Parallel?**: Yes - can start once T026-T030 scaffolded

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing init | Run existing init tests to verify |
| Config.yaml corruption | Use ruamel.yaml for safe round-trip |
| User confusion | Clear messaging about what "auto" means |

## Definition of Done Checklist

- [ ] T026: VCS detection imports added to init.py
- [ ] T027: VCS detection integrated into init workflow
- [ ] T028: Info message displayed based on VCS availability
- [ ] T029: VCS preference saved to .kittify/config.yaml
- [ ] T030: --vcs flag working with validation
- [ ] T031: Init tests updated and passing
- [ ] Running `spec-kitty init` shows appropriate message
- [ ] Config.yaml has vcs section after init

## Review Guidance

**Key Checkpoints**:

1. Verify message is informational, not error/warning
2. Verify --vcs flag validates tool availability
3. Verify config.yaml is created/updated correctly
4. Verify existing init functionality preserved
5. Test with and without jj installed

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T12:12:57Z – claude-code – shell_pid=72657 – lane=doing – Started implementation via workflow command
- 2026-01-17T12:21:39Z – claude-code – shell_pid=72657 – lane=for_review – Ready for review: VCS detection and --vcs flag added to init command with 6 tests (822 total tests pass)
- 2026-01-17T12:27:34Z – **AGENT** – shell_pid=90012 – lane=doing – Started review via workflow command
- 2026-01-17T12:32:25Z – **AGENT** – shell_pid=90012 – lane=done – Review passed: All 6 subtasks implemented correctly - VCS detection imports (T026), workflow integration (T027), info messages (T028), config.yaml persistence (T029), --vcs flag with validation (T030), and 6 tests (T031). All 822 tests pass.
