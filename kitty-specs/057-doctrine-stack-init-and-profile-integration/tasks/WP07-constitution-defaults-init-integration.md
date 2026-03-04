---
work_package_id: WP07
title: Constitution Defaults File + Init Integration
lane: planned
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-015
- FR-020
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
phase: Phase C - Init-Time Doctrine
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-22T11:50:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP07 – Constitution Defaults File + Init Integration

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

Depends on **WP06** (Phase B gate). All Phase B WPs must be merged before starting Phase C.

```bash
spec-kitty implement WP07 --base WP06
```

---

## Objectives & Success Criteria

- `src/doctrine/constitution/defaults.yaml` exists with predefined doctrine selections.
- `spec-kitty init` offers "Accept defaults" and "Configure manually" choices for the doctrine stack.
- "Accept defaults" → constitution generated, `.kittify/constitution/constitution.md` exists.
- `spec-kitty init --non-interactive` → doctrine defaults applied automatically (NFR-001: ≤2s).
- Init skips doctrine step if constitution already exists (FR-004).
- Interrupted init checkpoints progress; next invocation offers resume/restart (FR-020).
- User journey document exists at `architecture/2.x/user_journey/init-doctrine-flow.md`.
- US-1 scenarios 1-3 and US-2 scenarios 1-4 pass.
- Requirements FR-001-FR-005, FR-015, FR-020, NFR-001, C-002 satisfied.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-C1
- **Spec**: US-1, US-2, FR-001-FR-005, FR-015, FR-020, NFR-001, C-002
- **Critical constraint C-002**: `spec-kitty constitution interview` and `spec-kitty constitution generate` must continue working independently. Init only orchestrates; it does NOT reimplement the interview or generation.
- **`init.py` is 1400 lines** — read the full function structure before editing. The doctrine step slots in after skeleton creation.
- **Checkpoint file location**: `.kittify/.init-checkpoint.yaml`
- **Atomic writes**: Use `from kernel.atomic import atomic_write` for checkpoint persistence.
- **Start command**: `spec-kitty implement WP07 --base WP06`

## Subtasks & Detailed Guidance

### Subtask T026 – Write ATDD acceptance tests (tests first)

- **Purpose**: 7 acceptance scenarios (US-1: 1-3, US-2: 1-4) must be red before implementation.
- **Files**: Create `tests/specify_cli/cli/commands/test_init_doctrine.py`.
- **Steps**:
  1. Read existing `tests/specify_cli/cli/commands/` for init test patterns. Find the test for `init.py`.
  2. Write test functions:
     **US-1 (Accept Defaults)**:
     - `test_init_accept_defaults_creates_constitution` — fresh project, simulate user selecting "accept defaults" → `.kittify/constitution/constitution.md` exists.
     - `test_init_non_interactive_applies_defaults` — `spec-kitty init --non-interactive` on fresh project → constitution generated without prompts.
     - `test_init_skips_doctrine_if_constitution_exists` — project with existing constitution, run init → doctrine step skipped with message.
     **US-2 (Configure Manually)**:
     - `test_init_configure_manually_asks_interview_depth` — user selects "configure manually" → asked for minimal/comprehensive depth.
     - `test_init_configure_manually_informs_user` — interview info shown before interview begins.
     - `test_init_configure_manually_generates_constitution` — complete the interview inline → constitution generated.
     - `test_init_resume_after_interrupt` — simulate interrupted init (checkpoint exists), run init again → offered resume/restart; selecting restart discards checkpoint.
  3. Run `pytest tests/specify_cli/cli/commands/test_init_doctrine.py -v` — all must FAIL.

### Subtask T027 – Create `src/doctrine/constitution/defaults.yaml`

- **Purpose**: The defaults file defines which doctrine selections are applied when the user chooses "accept defaults". It must be a complete, loadable selection set.
- **Files**: Create `src/doctrine/constitution/defaults.yaml`.
- **Steps**:
  1. Read `src/constitution/compiler.py` and `src/constitution/interview.py` to understand the input format expected by `constitution generate`.
  2. Study existing test fixtures or examples that show what a complete doctrine selection looks like.
  3. Create the defaults file with a minimal practical selection:
     ```yaml
     # Doctrine defaults for new projects (applied by spec-kitty init --non-interactive or "accept defaults")
     # Format must match the constitution compiler's expected input.
     paradigms:
       - test-first
     directives:
       - DIRECTIVE_001   # Architectural Integrity Standard
       - DIRECTIVE_010   # Specification Fidelity Requirement
       - DIRECTIVE_025   # Boy Scout Rule
       - DIRECTIVE_028   # Efficient Local Tooling
       - DIRECTIVE_030   # Test and Typecheck Quality Gate
       - DIRECTIVE_033   # Targeted Staging Policy
     tools:
       auto_commit: true
       preferred_shell: "bash"
     ```
  4. Validate the YAML parses: `python -c "import yaml; yaml.safe_load(open('src/doctrine/constitution/defaults.yaml'))"`.
  5. Adjust the format to match exactly what the compiler expects. This is the most important step — a mismatched format will fail T028.

### Subtask T028 – Add "Accept defaults" path to `init.py`

- **Purpose**: Wire the defaults.yaml into init so a user can get a fully configured constitution with one selection.
- **Files**: `src/specify_cli/cli/commands/init.py`
- **Steps**:
  1. Read `init.py` carefully. Identify where the `.kittify/constitution/` directory is created (line ~191) and where `copy_constitution_templates()` is called (line ~946). The doctrine step should be inserted after skeleton creation and before the final success message.
  2. Add a helper function `_run_doctrine_stack_init(project_path, non_interactive, console)`:
     ```python
     def _run_doctrine_stack_init(project_path: Path, non_interactive: bool, console) -> bool:
         """Run the doctrine stack setup step during init.
         Returns True if setup was performed or skipped, False if aborted.
         """
         constitution_path = project_path / ".kittify" / "constitution" / "constitution.md"
         if constitution_path.exists():
             console.print("[dim]Constitution already exists — skipping doctrine stack setup.[/dim]")
             return True

         if non_interactive:
             # Apply defaults automatically
             _apply_doctrine_defaults(project_path, console)
             return True

         choice = Prompt.ask(
             "\n[bold]Doctrine stack[/bold]: How would you like to configure your project governance?",
             choices=["defaults", "manual", "skip"],
             default="defaults",
         )
         if choice == "defaults":
             _apply_doctrine_defaults(project_path, console)
         elif choice == "manual":
             _run_inline_interview(project_path, console)
         # "skip" → no constitution generated
         return True
     ```
  3. Add `_apply_doctrine_defaults(project_path, console)`:
     - Load `src/doctrine/constitution/defaults.yaml`.
     - Call `spec-kitty constitution generate` via subprocess or internal API with the defaults as input.
     - Alternatively, call the Python API directly: `from specify_cli.constitution.generator import generate_constitution`.
  4. Insert a call to `_run_doctrine_stack_init()` in the `init()` function at the appropriate location.

### Subtask T029 – Add "Configure manually" path to `init.py`

- **Purpose**: Power users can run the full interview inline rather than accepting defaults.
- **Files**: `src/specify_cli/cli/commands/init.py`
- **Steps**:
  1. Implement `_run_inline_interview(project_path, console)`:
     - Ask interview depth: `Prompt.ask("Interview depth?", choices=["minimal", "comprehensive"], default="minimal")`
     - Inform the user: "This interview will configure your constitution — which paradigms, directives, and tool settings govern your project. You can customize further after init by running `spec-kitty constitution interview`."
     - Call the existing `constitution interview` flow — either via subprocess `spec-kitty constitution interview --depth {depth}` or internal Python API.
  2. Verify that C-002 is satisfied: `spec-kitty constitution interview` continues to work independently (no code was removed, only called from init).

### Subtask T030 – Implement skip-if-exists and `--non-interactive` paths

- **Purpose**: FR-004 and FR-005.
- **Files**: `src/specify_cli/cli/commands/init.py`
- **Steps**:
  1. Skip-if-exists is already handled in `_run_doctrine_stack_init()` (T028 step 1). Verify the check is in place.
  2. `--non-interactive` flag: check if `init.py` already has a `--non-interactive` flag. If so, pass it to `_run_doctrine_stack_init()`. If not, add it:
     ```python
     non_interactive: bool = typer.Option(False, "--non-interactive", help="Apply defaults without prompting")
     ```
  3. Test: run `spec-kitty init --non-interactive` on a fresh project (or with a test fixture) and verify constitution is generated in ≤2 seconds.

### Subtask T031 – Implement init resume/restart checkpoint

- **Purpose**: FR-020. Long interviews can be interrupted (Ctrl+C). The user should not lose progress.
- **Files**: `src/specify_cli/cli/commands/init.py`
- **Steps**:
  1. During the interview flow (T029's `_run_inline_interview()`), periodically persist progress to `.kittify/.init-checkpoint.yaml`:
     ```python
     from kernel.atomic import atomic_write
     import yaml

     checkpoint = {
         "phase": "interview",
         "depth": depth,
         "answers_so_far": interview_state,
         "started_at": datetime.utcnow().isoformat(),
     }
     checkpoint_path = project_path / ".kittify" / ".init-checkpoint.yaml"
     atomic_write(checkpoint_path, yaml.dump(checkpoint), mkdir=True)
     ```
  2. At the start of `_run_doctrine_stack_init()`, check for an existing checkpoint:
     ```python
     checkpoint_path = project_path / ".kittify" / ".init-checkpoint.yaml"
     if checkpoint_path.exists():
         choice = Prompt.ask(
             "A previous init session was interrupted. Resume it?",
             choices=["resume", "restart"],
             default="resume",
         )
         if choice == "restart":
             checkpoint_path.unlink()  # Discard checkpoint
         else:
             # Load checkpoint and resume from saved state
             _resume_from_checkpoint(checkpoint_path, project_path, console)
             return True
     ```
  3. Wrap the interview in a `try/except KeyboardInterrupt` to ensure checkpoint is written on Ctrl+C.
  4. Delete checkpoint after successful completion.

### Subtask T032 – Write init-doctrine user journey document

- **Purpose**: Architecture documentation deliverable. Captures the full init-doctrine flow for future maintainers and agents.
- **Files**: Create `architecture/2.x/user_journey/init-doctrine-flow.md`.
- **Steps**:
  1. Check if `architecture/2.x/user_journey/` directory exists; create it if not.
  2. Write a narrative + flow diagram covering all 5 paths:
     - **Accept defaults**: init → skeleton → doctrine step → load defaults.yaml → constitution generate → done
     - **Configure manually (minimal)**: init → skeleton → doctrine step → interview depth prompt → minimal interview → constitution generate → done
     - **Configure manually (comprehensive)**: same but comprehensive interview depth
     - **Skip (existing constitution)**: init → skeleton → doctrine step → constitution detected → skip → done
     - **Non-interactive**: init --non-interactive → skeleton → defaults applied → done
     - **Resume/restart**: init starts → interrupt → checkpoint saved → re-run init → resume/restart prompt → (resume) continue from checkpoint OR (restart) fresh start
  3. The document should include:
     - ASCII or Mermaid flow diagram
     - Description of each decision point
     - Notes on the checkpoint format and location
     - Reference to C-002 (existing constitution commands unaffected)

## Test Strategy

```bash
# ATDD acceptance tests
rtk test pytest tests/specify_cli/cli/commands/test_init_doctrine.py -v

# Full suite regression
rtk test pytest tests/ -x

# Coverage gate (90%+ on new modules — constitution requirement)
rtk test pytest tests/ --cov=specify_cli --cov=doctrine --cov=constitution --cov-fail-under=90 -q

# Type check
mypy --strict src/specify_cli/cli/commands/init.py src/doctrine/constitution/

# Lint
rtk ruff check src/specify_cli/cli/commands/init.py

# Performance spot check (≤2s for defaults path)
time spec-kitty init --non-interactive --project /tmp/test-project-$(date +%s)
```

## Risks & Mitigations

- **`init.py` complexity**: 1400 lines — read the full function before editing. The init function has many conditional branches; adding the doctrine step in the wrong place can cause double execution or missing execution.
- **Constitution generate API**: If `constitution generate` has no stable Python API, use subprocess with the CLI. Ensure the subprocess is invoked with the correct working directory.
- **Checkpoint atomicity**: Use `atomic_write` to prevent corrupt checkpoint files on Ctrl+C.
- **`--non-interactive` already exists**: Check if the flag is already defined in `init.py` before adding it; avoid duplicates.

## Review Guidance

- Run `spec-kitty init` on a temp directory interactively and choose each path (defaults, manual, skip).
- Run `spec-kitty init --non-interactive` and time it — must be ≤2 seconds for the doctrine step.
- Run init, interrupt mid-interview (Ctrl+C), verify checkpoint exists. Re-run init, choose resume, verify it continues. Re-run again, choose restart, verify checkpoint is deleted and fresh start.
- Verify `spec-kitty constitution interview` still works independently (C-002).

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
