---
work_package_id: WP03
title: Sync, Hashing, and CLI Commands
lane: "done"
dependencies: [WP02]
base_branch: develop
base_commit: 12d1f5adbae614f3a4df524db5cc5d2fe23ef0d4
created_at: '2026-02-15T23:00:54.146328+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Core Features
assignee: ''
agent: claude
shell_pid: '547518'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T22:11:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Sync, Hashing, and CLI Commands

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Implement SHA-256 content hashing with whitespace normalization
- Implement staleness detection (compare constitution hash vs metadata.yaml hash)
- Implement `sync()` orchestration function (read → parse → extract → write YAML → update metadata)
- Implement `spec-kitty constitution sync` CLI command
- Implement `spec-kitty constitution status` CLI command with Rich output
- Register `constitution` subcommand in CLI app
- **All tests pass**, **mypy --strict clean**, **ruff clean**

**Success metrics**:
- `spec-kitty constitution sync` produces correct YAML files from constitution
- `spec-kitty constitution status` shows correct sync state and file listing
- Sync is idempotent — running twice produces identical output
- Stale detection works correctly when constitution is modified

## Context & Constraints

- **Spec**: `kitty-specs/045-constitution-doctrine-config-sync/spec.md` — FR-1.1, FR-1.6, FR-1.7, FR-5.1–5.4
- **Plan**: `kitty-specs/045-constitution-doctrine-config-sync/plan.md` — AD-1, AD-2
- **Research**: `kitty-specs/045-constitution-doctrine-config-sync/research.md` — RQ-3 (hashing)
- **Quickstart**: `kitty-specs/045-constitution-doctrine-config-sync/quickstart.md` — CLI command usage examples
- **Depends on WP02**: `Extractor`, `ExtractionResult`, `write_extraction_result()`
- **Codebase pattern**: Follow `src/specify_cli/cli/commands/agent/telemetry.py` for CLI command structure

**Implementation command**: `spec-kitty implement WP03 --base WP02`

## Subtasks & Detailed Guidance

### Subtask T019 – Implement SHA-256 Content Hashing

**Purpose**: Generate a content hash of constitution.md for staleness detection (FR-1.7).

**Steps**:
1. Create `src/specify_cli/constitution/hasher.py`:
   ```python
   import hashlib

   def hash_constitution(content: str) -> str:
       """Compute SHA-256 hash of constitution content with normalized whitespace.

       Returns hash in format: "sha256:{hexdigest}"
       """
       normalized = content.strip()
       digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
       return f"sha256:{digest}"
   ```

2. Add `parse_hash(hash_string: str) -> str` utility:
   - Parse `"sha256:abc123"` → `"abc123"`
   - Validate format

**Files**:
- `src/specify_cli/constitution/hasher.py`

**Notes**:
- Whitespace normalization: `.strip()` only — preserve internal formatting
- Must be deterministic for idempotency (FR-1.6)

### Subtask T020 – Implement Staleness Detection

**Purpose**: Compare current constitution hash against the hash stored in metadata.yaml (FR-5.1, FR-5.2).

**Steps**:
1. In `hasher.py`, add:
   ```python
   def is_stale(constitution_path: Path, metadata_path: Path) -> tuple[bool, str, str]:
       """Check if constitution has changed since last sync.

       Returns:
           (is_stale, current_hash, stored_hash)
       """
       content = constitution_path.read_text("utf-8")
       current_hash = hash_constitution(content)

       if not metadata_path.exists():
           return True, current_hash, ""

       yaml = YAML()
       metadata = yaml.load(metadata_path)
       stored_hash = metadata.get("constitution_hash", "")

       return current_hash != stored_hash, current_hash, stored_hash
   ```

**Files**:
- `src/specify_cli/constitution/hasher.py`

**Notes**:
- If metadata.yaml doesn't exist → always stale (first run)
- Never block on staleness — always informational (FR-5.4)

### Subtask T021 – Implement `sync()` Orchestration Function

**Purpose**: Single entry point for constitution → YAML extraction (FR-1.1).

**Steps**:
1. Create `src/specify_cli/constitution/sync.py`:
   ```python
   from pathlib import Path
   from datetime import datetime, timezone

   def sync(
       constitution_path: Path,
       output_dir: Path | None = None,
       force: bool = False,
   ) -> SyncResult:
       """Sync constitution.md → structured YAML files.

       Args:
           constitution_path: Path to constitution.md
           output_dir: Directory for YAML output (default: same as constitution_path.parent)
           force: If True, extract even if not stale

       Returns:
           SyncResult with status and file paths
       """
   ```

2. Define `SyncResult` dataclass:
   ```python
   @dataclass
   class SyncResult:
       synced: bool           # True if extraction ran
       stale_before: bool     # True if constitution was stale before sync
       files_written: list[str]  # List of YAML file names written
       extraction_mode: str   # "deterministic" | "hybrid"
       error: str | None = None
   ```

3. Orchestration flow:
   - Read constitution content
   - Check staleness (skip if not stale and not force)
   - Run `Extractor.extract(content)`
   - Write YAML files via `write_extraction_result()`
   - Update metadata with current hash and timestamp
   - Return `SyncResult`

**Files**:
- `src/specify_cli/constitution/sync.py`

**Notes**:
- Idempotent: skip if constitution unchanged (unless `--force`)
- Exception handling: catch extraction errors, return SyncResult with error field
- The `output_dir` defaults to `constitution_path.parent` (`.kittify/constitution/`)

### Subtask T022 – Implement `spec-kitty constitution sync` CLI Command

**Purpose**: User-facing CLI command for explicit sync (FR-1.1).

**Steps**:
1. Create `src/specify_cli/cli/commands/constitution.py`:
   ```python
   import typer
   from rich.console import Console

   app = typer.Typer(help="Constitution management commands")
   console = Console()

   @app.command()
   def sync(
       force: bool = typer.Option(False, "--force", "-f", help="Force sync even if not stale"),
       json_output: bool = typer.Option(False, "--json", help="Output JSON"),
   ) -> None:
       """Sync constitution.md to structured YAML config files."""
   ```

2. Implementation:
   - Detect repo root (use existing `find_repo_root()` or similar)
   - Construct constitution path: `repo_root / ".kittify" / "constitution" / "constitution.md"`
   - Fall back to old path: `repo_root / ".kittify" / "memory" / "constitution.md"` (pre-migration)
   - Call `sync()` function
   - Display results with Rich:
     - `✅ Constitution synced successfully` (green)
     - `ℹ️ Constitution already in sync (use --force to re-extract)` (blue)
     - `❌ Error: {message}` (red)
   - List files written

**Files**:
- `src/specify_cli/cli/commands/constitution.py` (new)

**Notes**:
- Follow existing CLI patterns (see `telemetry.py` for reference)
- Support both `--json` and human-readable output
- Handle missing constitution file gracefully (error message, exit code 1)

### Subtask T023 – Implement `spec-kitty constitution status` CLI Command

**Purpose**: Display sync status, staleness, and file listing (FR-5.3).

**Steps**:
1. Add `status` command to `src/specify_cli/cli/commands/constitution.py`:
   ```python
   @app.command()
   def status(
       json_output: bool = typer.Option(False, "--json", help="Output JSON"),
   ) -> None:
       """Display constitution sync status."""
   ```

2. Output format (Rich):
   ```
   Constitution: .kittify/constitution/constitution.md
   Status: ✅ SYNCED | ⚠️ STALE
   Last sync: 2026-02-15T21:00:00+00:00
   Hash: sha256:abc123...

   Extracted files:
     ✓ governance.yaml (1.2 KB)
     ✓ agents.yaml (0.4 KB)
     ✓ directives.yaml (0.3 KB)
     ✓ metadata.yaml (0.2 KB)
   ```

3. If stale:
   ```
   Status: ⚠️ STALE (modified since last sync)
   Expected hash: sha256:abc123...
   Current hash:  sha256:def456...
   Run: spec-kitty constitution sync
   ```

**Files**:
- `src/specify_cli/cli/commands/constitution.py`

### Subtask T024 – Register Constitution Subcommand in CLI App

**Purpose**: Wire the `constitution` subcommand into the main CLI entry point.

**Steps**:
1. Find the main CLI app registration (likely `src/specify_cli/cli/app.py` or `src/specify_cli/cli/__init__.py`)
2. Import the constitution app: `from specify_cli.cli.commands.constitution import app as constitution_app`
3. Register: `main_app.add_typer(constitution_app, name="constitution")`

**Files**:
- `src/specify_cli/cli/app.py` or equivalent main CLI module

**Notes**:
- Follow the pattern used for `agent` and `telemetry` subcommands
- Verify with `spec-kitty constitution --help`

### Subtask T025 – Write Sync, Hashing, and CLI Tests

**Purpose**: Comprehensive test coverage for sync orchestration, hashing, and CLI commands.

**Steps**:
1. Create `tests/specify_cli/constitution/test_hasher.py`:
   - Test `hash_constitution()` produces consistent output
   - Test whitespace normalization (trailing newlines don't change hash)
   - Test `is_stale()` with matching/mismatching hashes
   - Test `is_stale()` with missing metadata.yaml

2. Create `tests/specify_cli/constitution/test_sync.py`:
   - Test sync with fresh constitution (no prior extraction)
   - Test sync with unchanged constitution (should skip)
   - Test sync with `--force` (should extract even if unchanged)
   - Test sync with modified constitution (should extract)
   - Test idempotency: sync twice → same output

3. Create `tests/specify_cli/cli/commands/test_constitution_cli.py`:
   - Test `sync` command with valid constitution
   - Test `sync` command with missing constitution
   - Test `sync --force` flag
   - Test `sync --json` output format
   - Test `status` command with synced state
   - Test `status` command with stale state
   - Test `status` command with no constitution

**Files**:
- `tests/specify_cli/constitution/test_hasher.py`
- `tests/specify_cli/constitution/test_sync.py`
- `tests/specify_cli/cli/commands/test_constitution_cli.py`

**Target**: 18-22 tests covering all sync/hash/CLI functionality.

## Test Strategy

- **Unit tests**: Hashing, staleness detection tested with controlled fixtures
- **Integration tests**: Full sync pipeline with real constitution
- **CLI tests**: Use Typer `CliRunner` (same pattern as telemetry CLI tests)
- **Run**: `pytest tests/specify_cli/constitution/ tests/specify_cli/cli/commands/test_constitution_cli.py -v`
- **Type check**: `mypy --strict src/specify_cli/constitution/hasher.py src/specify_cli/constitution/sync.py src/specify_cli/cli/commands/constitution.py`

## Risks & Mitigations

- **Risk**: Hash collision on normalized content → SHA-256 is collision-resistant, minimal risk
- **Risk**: CLI registration conflicts with existing commands → Check for name collisions before registering
- **Risk**: Sync fails silently → Return SyncResult with explicit error field, CLI displays error

## Review Guidance

- Verify hashing is deterministic (same content → same hash, always)
- Check sync correctly skips when not stale (efficiency)
- Ensure CLI output matches quickstart.md examples
- Verify error handling for missing constitution file
- Test `--json` output is valid JSON

## Activity Log

- 2026-02-15T22:11:29Z – system – lane=planned – Prompt created.
- 2026-02-15T23:00:54Z – claude – shell_pid=547518 – lane=doing – Assigned agent via workflow command
- 2026-02-15T23:17:56Z – claude – shell_pid=547518 – lane=for_review – TOCTOU race fixed, 122 tests pass
- 2026-02-15T23:17:57Z – claude – shell_pid=547518 – lane=done – All tests pass, mypy/ruff clean
