# Research: Intake Auto-Detect from Harness Plan Artifacts

**Mission**: intake-auto-detect-01KPNGCX  
**Phase**: 0 — Implementation unknowns

---

## 1. Typer Mutual Exclusion

**Decision**: Handle `--auto` + positional path mutual exclusion in the function body, not via Typer decorators.

**Rationale**: Typer has no built-in `mutually_exclusive` group. The standard pattern in this codebase is to check conflicting arguments at the top of the command function, print an error message via `err_console`, and `raise typer.Exit(1)`. This is already done for the `--show` + `path` conflict in the existing `intake()` function (`if show` guard block). Consistent with existing style.

**Implementation**:
```python
if path and auto:
    err_console.print("[red]--auto cannot be combined with a positional path argument.[/red]")
    raise typer.Exit(1)
```

---

## 2. TTY Detection

**Decision**: Use `sys.stdin.isatty()` for interactive vs. non-interactive detection.

**Rationale**: Standard Python approach, no additional dependency. Works consistently across macOS, Linux, and CI pipelines (CI stdin is typically a pipe → not a TTY). `typer.testing.CliRunner` invokes with stdin as a `StringIO`, which returns `False` for `isatty()`, making non-TTY behavior the default in tests — no special mocking needed for non-TTY paths. For TTY paths, mock `sys.stdin.isatty` → `True`.

---

## 3. YAML Field Omission (`source_agent`)

**Decision**: Build `source_data` dict conditionally; do not set `source_agent: None`.

**Rationale**: `yaml.safe_dump({'source_agent': None})` writes `source_agent: null`. The spec requires the key to be absent entirely for manual intake. The correct pattern is:
```python
source_data: dict[str, str] = {
    "source_file": source_file,
    "ingested_at": ingested_at,
    "brief_hash": brief_hash,
}
if source_agent is not None:
    source_data["source_agent"] = source_agent
```
This is the same pattern used in `tracker/ticket_context.py` for optional fields.

---

## 4. `write_mission_brief()` Backward Compatibility

**Decision**: Add `source_agent: str | None = None` as a keyword-only argument with a default of `None`.

**Rationale**: All existing callers (`intake.py`) pass positional `repo_root, content, source_file` and no `source_agent`. The new default means existing call sites require zero changes. The function signature becomes:
```python
def write_mission_brief(
    repo_root: Path,
    content: str,
    source_file: str,
    *,
    source_agent: str | None = None,
) -> tuple[Path, Path]:
```

---

## 5. `scan_for_plans()` Function Design

**Decision**: Separate `scan_for_plans(cwd)` function in `intake_sources.py`; returns a flat list of `(Path, harness_key, source_agent_value)` tuples.

**Rationale**: Separating scan logic from CLI logic allows unit testing scan behavior without invoking the CLI runner. The function iterates `HARNESS_PLAN_SOURCES` in order and appends matches. Order matters: declaration order in `HARNESS_PLAN_SOURCES` is the priority order.

**Return type**: `list[tuple[Path, str, str | None]]` — `(absolute_path, harness_key, source_agent_value)`. An empty list means no matches.

**Directory expansion (post-mission-review correction)**: The original plan spec said "use `is_file()` — directories at candidate paths are silently skipped." This was revised during implementation because all 4 active `HARNESS_PLAN_SOURCES` entries are *directories* (harnesses write timestamped or slug-named files into a well-known directory, not a predictable filename). The actual behavior is:

- If the candidate path is a file → include it directly.
- If the candidate path is a directory → include all `*.md` files inside it (non-recursive, `sorted()` order).
- If the candidate path does not exist → skip silently.
- `PermissionError` / `OSError` at any level → skip silently.

This is the intended design. The "skip directories" instruction in the WP01 prompt was an error and should not be reinstated.

---

## 6. Test Infrastructure

**Decision**: Use `typer.testing.CliRunner` + `tmp_path` for all CLI tests; use direct function calls for `scan_for_plans` unit tests.

**Rationale**: Consistent with all other CLI tests in the codebase (e.g., `tests/init/test_init_next_steps.py`). `CliRunner` isolates filesystem state via `tmp_path`. For `scan_for_plans`, call it directly with a `tmp_path`-rooted CWD to avoid CLI overhead.

**Pattern for `--auto` tests**: Patch `specify_cli.cli.commands.intake.scan_for_plans` to return controlled results, or create real files in `tmp_path` and let the real scan run. Both are valid; real-file approach is preferred for the single-match happy path since it exercises the full stack.

---

## 7. Research Deliverable Methodology (for WP01 implementer)

The implementing agent for WP01 must produce `docs/reference/agent-plan-artifacts.md`. Recommended research order:

1. **Official documentation**: Check each harness's official docs/changelog for plan-mode documentation.
2. **GitHub source**: Search the harness's GitHub repository for file creation logic in plan-mode code paths.
3. **Empirical test**: For harnesses available on the machine (check `which claude`, `which cursor`, `which codex`, etc.), invoke plan mode in an empty temp directory and observe what files are created.
4. **Community sources**: Search developer forums, blog posts, or issue trackers.

For the **empirical test** of Claude Code specifically, the plan mode in Claude Code is the `/plan` mode or the built-in planning toggle — the implementing agent should test by creating a temp project and observing output. Known candidate paths to check: `PLAN.md`, `.claude/PLAN.md`, `CLAUDE_PLAN.md`.

**Confidence threshold**: Only entries confirmed by steps 1 or 2 (Verified-docs) or step 3 (Verified-empirical) go into active `HARNESS_PLAN_SOURCES` entries. Anything else goes in commented TODO blocks.
