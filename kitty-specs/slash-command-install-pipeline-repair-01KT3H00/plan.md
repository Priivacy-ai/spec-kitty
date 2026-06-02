# Implementation Plan: Slash Command Install Pipeline Repair

**Mission**: slash-command-install-pipeline-repair-01KT3H00  
**Branch**: kitty/mission-slash-command-install-pipeline-repair-01KT3H00  
**Merge target**: main  
**GitHub issues**: #1608, #1609, #1610

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `doctrine` package (internal), `typer`, `rich`, `uv`  
**Build/Package**: hatchling, editable install via `pip install -e .`  
**Test Framework**: pytest, mypy --strict, ruff  
**Key Files**: `src/specify_cli/runtime/agent_commands.py`, `src/specify_cli/cli/commands/doctor.py`, `src/specify_cli/core/config.py`, `pyproject.toml`  
**Precedent**: `src/specify_cli/skills/command_installer.py` → `_package_templates_dir()` uses `doctrine.__file__` for template resolution (exact pattern to replicate)

---

## Charter Check

Charter is present. Relevant directives:
- **DIR-001**: Cross-platform (Linux, macOS, Windows 10+) — bootstrap approach must not require `make` for end-user installs (C-003 compliant: layered; `make dev-setup` is dev-only, CLI-startup auto-repair is cross-platform)
- **DIR-005**: Tests added for all new functionality — all three fix branches require test coverage
- **DIR-006**: mypy --strict passes — all new code fully annotated
- **C-011 (ATDD-First)**: Each implementation WP (WP01, WP02) must commit a minimal failing ATDD test as its very first commit before any implementation commit. WP04 and WP05 expand these stubs into the full test suite.
- **C-004 (Burn-down)**: Close issues #1608, #1609, #1610 in this mission
- **Performance exception**: NFR-001 (≤5s) and NFR-002 (≤3s) apply to the slow-path / first-run scenarios. The fast path (lock current) and warm-filesystem doctor run remain within the charter's blanket < 2-second budget. This distinction is documented in spec.md NFR-001/002.

No conflicts with charter.

---

## Engineering Alignment

Three independent repairs with a hard dependency order: **#1608 → #1609, #1610**.

### Fix 1 — Resolver + Renderer (#1608)

**Root cause**: `_get_command_templates_dir()` checks two stale locations — both deleted when templates moved to the doctrine layer. Returns `None`, silently aborting all 8 prompt-driven command installs on every CLI startup.

**Precedent pattern** (already in `src/specify_cli/skills/command_installer.py`):
```python
def _package_templates_dir(mission_type: str = "software-dev") -> Path:
    import doctrine
    return Path(doctrine.__file__).parent / "missions" / "mission-steps" / mission_type
```

**Fix**:
1. Replace `_get_command_templates_dir()` body to use the same `doctrine.__file__`-based resolution — returns `Path(doctrine.__file__).parent / "missions" / "mission-steps" / "software-dev"` (always present, no optional/fallback needed; return type changes from `Path | None` to `Path`).
2. Update `_sync_agent_commands()` iteration from flat `templates_dir.glob("*.md")` to per-step subdirectory: iterate `sorted(templates_dir.iterdir())`, for each step dir read `step_dir / "prompt.md"`. Filter by `PROMPT_DRIVEN_COMMANDS` on `step_dir.name`; skip missing `prompt.md` gracefully.
3. Version lock (`agent-commands.lock`) written only after `_sync_agent_commands()` completes for all configured agents without unhandled exception — fixes the stuck-lock-at-rc30 performance bug.

### Fix 2 — Doctor Slash-Command Audit (#1609)

**Root cause**: `doctor skills` intersection `set(config.available) & SUPPORTED_AGENTS` silently drops claude and all 12 other slash-command agents. Doctor has no visibility into `~/.claude/commands/` or any global slash-command path.

**Fix**:
Add a slash-command health check path to `doctor skills`, running alongside (not replacing) the existing Agent Skills audit:
1. Compute configured slash-command agents: `set(config.available) ∩ set(AGENT_COMMAND_CONFIG.keys())`.
2. For each, call `get_global_command_dir(agent_key)` and verify all `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS` filenames are present.
3. Missing/stale files reported in a new "Slash Commands" section in `doctor skills` output.
4. `--fix` calls `ensure_global_agent_commands()` for configured agents only.
5. Scope guard: never touch agents not in `config.available`.

### Fix 3 — Layered Dev Bootstrap (#1610)

Three layers (all required, all idempotent):

| Layer | Mechanism | Audience |
|-------|-----------|---------|
| A — Doctor repair | `doctor skills --fix` (Fix 2) | Any operator/dev |
| B — Contributor script | `Makefile` with `dev-setup` target | Dev repo contributors |
| C — CLI startup auto-repair | Fix 1 unblocks `ensure_global_agent_commands()` at every startup | All installs |

**Layer B** — new `Makefile`:
```makefile
dev-setup:
	uv sync --frozen --all-extras
	uv run spec-kitty doctor skills --fix
```

**Layer C** — no additional post-install hook. Fix 1 makes `ensure_global_agent_commands()` work correctly; it already runs on every CLI startup. First `spec-kitty` invocation after editable install writes all missing files automatically. This avoids fragile post-install hooks and satisfies FR-009 (approved substitute per spec amendment) and C-003. **Known limitation**: a developer who goes directly from `pip install -e .` into Claude Code without invoking `spec-kitty` will not have commands until their first CLI call — `make dev-setup` eliminates this gap by running `spec-kitty doctor skills --fix` explicitly.

---

## Phase 0: Research

No open unknowns requiring external research. All technical facts confirmed from codebase inspection:

- Template resolver pattern: `doctrine.__file__`-based (precedent confirmed in `command_installer.py:_package_templates_dir()`)
- Doctrine layout: `src/doctrine/missions/mission-steps/software-dev/{step}/prompt.md` (verified by `ls`)
- Slash-command agents: all keys in `AGENT_COMMAND_CONFIG` excluding `("codex","vibe","pi","letta")`
- Version lock: `~/.kittify/cache/agent-commands.lock` — plain version string

`research.md` not required for this mission.

---

## Phase 1: Design & Contracts

### Code change boundaries

| Module | Change |
|--------|--------|
| `src/specify_cli/runtime/agent_commands.py` | Replace `_get_command_templates_dir()` (return type `Path`, not `Path \| None`); update `_sync_agent_commands()` glob; reposition lock write |
| `src/specify_cli/cli/commands/doctor.py` | Add `_load_slash_command_state()`, `_repair_slash_command_state()`, extend `skills` output and `--fix` |
| `Makefile` (new) | `dev-setup` target |
| `tests/specify_cli/runtime/test_agent_commands.py` | New: cover resolver, per-step iteration, lock write position |
| `tests/specify_cli/cli/commands/test_doctor_slash_commands.py` | New: cover audit, false-positive prevention, `--fix` repair, scope guard, NFR-003 regression |

### Internal contract: template resolution

After Fix 1:
- `_get_command_templates_dir()` returns `Path` (never `None`)
- Returned path is the `software-dev` mission-steps root
- Each child directory is a step name; each step contains `prompt.md`
- `_sync_agent_commands()` iterates step dirs, skips non-directories and missing `prompt.md`, filters by `PROMPT_DRIVEN_COMMANDS`

Formalised in `contracts/template-resolver.md`.

### Internal contract: doctor slash-command audit

- **Input**: `config.available`, `AGENT_COMMAND_CONFIG`, `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS`
- **Output**: list of `(agent_key, command, status)` tuples where status ∈ {missing, stale, ok}
- **Staleness definition**: A file is *stale* when its first `_VERSION_MARKER_HEAD_LINES` lines do not contain `"{_VERSION_MARKER_PREFIX} {current_version}"`. A file is *missing* when it does not exist on disk. Both are gaps.
- **Scope**: only `config.available ∩ AGENT_COMMAND_CONFIG.keys()`
- **`--fix`**: calls `ensure_global_agent_commands()` scoped to configured agents; idempotent

Formalised in `contracts/doctor-slash-audit.md`.

---

## Work Package Sketch (finalized 5-WP structure)

| WP | Scope | Depends on |
|----|-------|-----------|
| WP01 | All `agent_commands.py` fixes — doctrine-based resolver (`Path` return), per-step renderer, post-sync lock write. **First commit: failing ATDD stub (C-011).** | — |
| WP02 | `doctor.py` slash-command audit + `--fix` repair; `ensure_global_agent_commands()` `agent_keys` extension. **First commit: failing ATDD stub (C-011).** | WP01 |
| WP03 | `Makefile` `dev-setup` target + `CONTRIBUTING.md` developer setup section | WP02 |
| WP04 | Full runtime test suite for `agent_commands.py` fixes (expands WP01 ATDD stubs) | WP01 |
| WP05 | Full doctor test suite + mypy sign-off + NFR-003 regression tests (expands WP02 ATDD stubs) | WP02 |

Parallelization: `WP01 → WP02 → WP03` and `WP01 → WP04`, `WP02 → WP05`. WP04 and WP02 can run concurrently after WP01.
