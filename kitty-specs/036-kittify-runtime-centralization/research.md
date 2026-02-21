# Research: ~/.kittify Runtime Centralization

**Feature**: 036-kittify-runtime-centralization
**Date**: 2026-02-09

## R1: File Locking Approach for ensure_runtime()

**Decision**: Use `fcntl.flock()` on Unix and `msvcrt.locking()` on Windows via stdlib.

**Rationale**: Both are available in Python's standard library. `fcntl.flock()` provides advisory file locking on Unix systems (macOS, Linux). `msvcrt.locking()` provides mandatory file locking on Windows. No third-party dependency needed. The `filelock` package was considered but rejected to avoid adding a new dependency for a simple use case.

**Alternatives considered**:

- `filelock` PyPI package: Cross-platform, well-tested, but adds a new dependency. Rejected per "no new dependencies" constraint.
- `os.open()` with `O_EXCL`: Atomic file creation, but doesn't handle waiting for another process. Rejected because waiting behavior is required.
- `fcntl.lockf()`: Similar to `flock()` but uses record locks. Rejected because `flock()` is simpler for whole-file locking.

## R2: Existing Template Resolution in Codebase

**Decision**: Create new resolver in `runtime/resolver.py` and update existing call sites.

**Rationale**: Current template resolution is scattered across:

- `mission.py` lines 269-294: `Mission.get_command_template()` — resolves from mission's `command-templates/` directory
- `init.py` lines 619-630: Template preparation during init — copies from package or local source
- `agent_utils/directories.py`: Agent directory detection and config-aware processing

The new resolver provides a unified 4-tier resolution function that these call sites will use. The resolver is a standalone function, not tied to any class, making it easy to integrate.

**Call sites to update**:

1. `Mission.get_command_template()` → Use resolver for mission command templates
2. `init.py` template preparation → Use resolver for init templates
3. Any `discover_missions()` callers → Use resolver for mission YAML files

## R3: Cross-Platform Path Resolution

**Decision**: `~/.kittify/` on macOS/Linux via `Path.home()`, `%LOCALAPPDATA%\kittify\` on Windows via `platformdirs.user_data_dir("kittify")`. Override via `SPEC_KITTY_HOME` env var on all platforms.

**Rationale**: `platformdirs` is already a dependency (pyproject.toml line 55). Using `Path.home() / ".kittify"` on Unix follows the convention for CLI tool config (`.config/`, `.cache/`, etc. are alternatives but `.kittify/` is simpler and established). On Windows, `%LOCALAPPDATA%` is the standard location per Windows guidelines.

**Alternatives considered**:

- XDG spec on Linux (`~/.config/kittify/`, `~/.cache/kittify/`): More spec-compliant but inconsistent with the `.kittify` project directory naming. Rejected for user recognition.
- `platformdirs` on all platforms: Would put files in `~/.local/share/kittify/` on Linux, which is less discoverable. Rejected for discoverability.
- `~/.kittify/` on all platforms including Windows: Windows users expect AppData paths. Rejected for platform convention compliance.

## R4: Migration File Classification

**Decision**: Use `filecmp.cmp()` (shallow=False) for byte-identical comparison between local and global files.

**Rationale**: `filecmp.cmp(shallow=False)` does a full byte-by-byte comparison, which is the most reliable way to detect customization. Files that are byte-identical to the global version are safe to remove. Files that differ are customized and must be preserved in `overrides/`.

**Classification categories**:

- **Shared asset, identical**: File exists at legacy path AND byte-identical to global → remove (safe to resolve from global)
- **Shared asset, customized**: File exists at legacy path AND differs from global → move to `.kittify/overrides/`
- **Project-specific**: File at project-specific path (config.yaml, metadata.yaml, memory/, workspaces/, logs/) → keep unchanged
- **Unknown**: File not in any known category → keep unchanged and warn

## R5: ensure_runtime() Integration with CLI Entry Points

**Decision**: Call `ensure_runtime()` from the Typer `app.callback()` in the main CLI entry point, before any command handler runs.

**Rationale**: This ensures every CLI invocation checks the global runtime. The callback runs before any subcommand, making it the natural integration point. The fast path (<100ms) means negligible overhead for version-match cases.

**Integration point**: `src/specify_cli/cli/app.py` or equivalent main CLI module — the Typer app callback.

## R6: Package Asset Source Discovery

**Decision**: Use `importlib.resources` to locate package-bundled mission assets for populating `~/.kittify/`.

**Rationale**: The existing migration `m_0_6_7_ensure_missions.py` already uses `importlib.resources.files()` with fallbacks to `specify_cli.__file__` location and `SPEC_KITTY_TEMPLATE_ROOT` env var. The `ensure_runtime()` bootstrap uses the same pattern for consistency.

**Asset source hierarchy** (for populating `~/.kittify/` from package):

1. `importlib.resources.files("specify_cli") / "missions"` — standard package location
2. `Path(specify_cli.__file__).parent / "missions"` — development layout
3. `SPEC_KITTY_TEMPLATE_ROOT` env var — CI/testing override
