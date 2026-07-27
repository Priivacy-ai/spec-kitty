# Implementation Plan: Specify Brief Intake Mode

**Branch**: `main` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Mission**: `specify-brief-intake-mode-01KPMXQB` (`01KPMXQBM67RJQTCWB31SC6PGM`)
**Input**: Feature specification from `kitty-specs/specify-brief-intake-mode-01KPMXQB/spec.md`

---

## Summary

Add a `spec-kitty intake <path>` root-level CLI command that ingests any Markdown plan document into `.kittify/mission-brief.md` (with provenance header) and `.kittify/brief-source.yaml` (SHA-256 fingerprint + metadata). Both files are gitignored transient artifacts. In parallel, extend the specify source template with a "Brief Context Detection" section that detects these brief files before the Discovery Gate and enters a short-circuit extraction mode, reducing discovery to 0–2 gap-filling questions for comprehensive plans.

---

## Technical Context

**Language/Version**: Python 3.11+
**CLI Framework**: typer (existing project dependency)
**Console Output**: rich (existing project dependency)
**YAML I/O**: ruamel.yaml for brief-source.yaml (existing project dependency); stdlib `hashlib` for SHA-256
**Storage**: Filesystem only — `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` (gitignored, local-only)
**Testing**: pytest with ≥ 90% line coverage; integration tests for the CLI command; mypy --strict on all new modules
**Target Platform**: macOS / Linux (same as existing spec-kitty targets)
**Performance Goals**: `spec-kitty intake` completes within 3 seconds for plan files up to 1 MB
**Constraints**: No new runtime dependencies; no changes to `ticket_context.py`; `spec-kitty plan` command is untouched

---

## Charter Check

*GATE: Must pass before implementation. Re-evaluated after Phase 1 design.*

| Charter Requirement | This Feature | Status |
|--------------------|-------------|--------|
| typer for CLI | `intake.py` uses typer | ✅ PASS |
| rich for console output | CLI uses rich for error/success output | ✅ PASS |
| ruamel.yaml for YAML | `brief-source.yaml` written via ruamel.yaml | ✅ PASS |
| pytest + ≥ 90% coverage | Unit + integration tests planned | ✅ PASS |
| mypy --strict | All new modules annotated; no Any escapes planned | ✅ PASS |
| Integration tests for CLI commands | `test_intake.py` tests the CLI entry point end-to-end | ✅ PASS |

No violations. No complexity justification required.

---

## Phase 0: Research

**Research verdict: not required.** All implementation patterns are already established in the codebase:

- **Brief file write/read/clear pattern**: `src/specify_cli/tracker/ticket_context.py` — verbatim reference; `mission_brief.py` follows the same structure (write/read/clear helpers, no auth credentials, plain YAML for metadata)
- **CLI command registration**: `src/specify_cli/cli/commands/__init__.py` line 55 registers `lifecycle_module.plan` as a standalone root-level command via `app.command()(fn)` — `intake` uses the same pattern
- **Stdin handling**: stdlib `sys.stdin.read()` — no research needed
- **SHA-256**: stdlib `hashlib.sha256()` — no research needed
- **Template modification and upgrade propagation**: existing `spec-kitty upgrade` mechanism handles this; no new code needed in the migration layer

No `research.md` generated.

---

## Phase 1: Design

### File Format Specifications

#### `.kittify/mission-brief.md`

```
<!-- spec-kitty intake: ingested from <source_file> at <ingested_at> -->
<!-- brief_hash: <sha256_hex> -->

<verbatim plan content>
```

The provenance header is two HTML comment lines prepended to the original content. The rest of the file is the plan document exactly as received (no normalisation, no stripping).

#### `.kittify/brief-source.yaml`

```yaml
source_file: PLAN.md          # "stdin" when read from stdin
ingested_at: "2026-04-20T07:47:00+00:00"   # ISO 8601 UTC
brief_hash: "abc123..."        # SHA-256 hex digest of raw plan content (pre-header)
```

SHA-256 is computed on the raw plan content *before* the provenance header is prepended, so the hash describes the source document, not the stored artifact.

### `spec-kitty intake` Behaviour Contract

| Invocation | Action |
|-----------|--------|
| `spec-kitty intake PLAN.md` | Read file, write brief + source, exit 0 |
| `spec-kitty intake -` | Read stdin, write brief + source, exit 0 |
| `spec-kitty intake PLAN.md` (brief exists) | Exit 1: "Brief already exists … Use --force" |
| `spec-kitty intake PLAN.md --force` | Overwrite brief + source, exit 0 |
| `spec-kitty intake --show` (brief exists) | Print brief + provenance, exit 0 |
| `spec-kitty intake --show` (no brief) | Exit 1: "No brief found at .kittify/mission-brief.md" |

### Specify Template: Brief Context Detection Section

Inserted immediately after the **"Charter Context Bootstrap"** section heading block and before the **"Discovery Gate"** heading in `src/specify_cli/missions/software-dev/command-templates/specify.md`.

Content contract (prose instructions for the agent):

1. **Check** (in priority order):
   - `ls .kittify/mission-brief.md` → `MISSION_BRIEF_FOUND`
   - `ls .kittify/ticket-context.md` → `TICKET_CONTEXT_FOUND`
2. **If found** → enter brief-intake mode:
   - Read the full brief
   - Print: `BRIEF DETECTED: <filename> (source: <source_file>)`
   - Present one-paragraph summary to user
   - Extract FR-###, NFR-###, C-### from brief content directly
   - Ask gap-filling questions only (0–2 for comprehensive brief, up to 5 for sparse)
   - Present extracted requirement set for one-round confirmation
   - After spec.md committed, delete `.kittify/mission-brief.md`, `.kittify/brief-source.yaml`, `.kittify/ticket-context.md`, `.kittify/pending-origin.yaml` (each only if present)
3. **If not found** → proceed with normal Discovery Gate (no change)

The section also includes the **Brief Quality → Discovery Scope** table from the spec (FR-013):

| Brief quality | Discovery questions |
|---------------|---------------------|
| Comprehensive (objective + constraints + approach + ACs) | 0–1 gap-filling questions |
| Good (objective + constraints, no ACs) | 2–3 questions |
| Partial (goal statement only) | 4–5 questions |
| Empty / missing | Full Discovery Gate (current behaviour) |

### Source Structure

```
src/specify_cli/
├── mission_brief.py                          # NEW — write/read/clear for brief artifacts
└── cli/
    └── commands/
        ├── __init__.py                       # MODIFY — register intake command
        └── intake.py                         # NEW — spec-kitty intake CLI command

src/specify_cli/missions/software-dev/command-templates/
└── specify.md                                # MODIFY — add Brief Context Detection section

tests/specify_cli/
├── test_mission_brief.py                     # NEW — unit tests for mission_brief.py
└── cli/
    └── commands/
        └── test_intake.py                    # NEW — integration tests for CLI

.gitignore                                    # MODIFY — add .kittify/mission-brief.md,
                                              #           .kittify/brief-source.yaml
```

### Module Design: `src/specify_cli/mission_brief.py`

Mirrors `ticket_context.py` exactly in structure:

```python
MISSION_BRIEF_FILENAME = "mission-brief.md"
BRIEF_SOURCE_FILENAME = "brief-source.yaml"

def write_mission_brief(repo_root: Path, content: str, source_file: str) -> tuple[Path, Path]:
    """Write .kittify/mission-brief.md and .kittify/brief-source.yaml."""
    ...

def read_mission_brief(repo_root: Path) -> str | None:
    """Return brief content (with header) or None if absent."""
    ...

def read_brief_source(repo_root: Path) -> dict[str, Any] | None:
    """Return brief-source.yaml as dict or None if absent."""
    ...

def clear_mission_brief(repo_root: Path) -> None:
    """Remove mission-brief.md and brief-source.yaml."""
    ...
```

### Module Design: `src/specify_cli/cli/commands/intake.py`

```python
import typer
from specify_cli.mission_brief import write_mission_brief, read_mission_brief, read_brief_source, clear_mission_brief

def intake(
    path: str = typer.Argument(..., help="Plan file path, or '-' to read from stdin"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing brief"),
    show: bool = typer.Option(False, "--show", help="Print current brief and exit"),
) -> None:
    """Ingest a plan document as a mission brief for /spec-kitty.specify."""
    ...
```

Registration in `__init__.py` (alongside existing `app.command()(lifecycle_module.plan)`):
```python
from . import intake as intake_module
app.command()(intake_module.intake)
```

### Quickstart

See `quickstart.md` (generated separately).

---

## Work Packages

Two independent work packages; either order or parallel execution is valid.

### WP01 — `spec-kitty intake` CLI command

**Delivers**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-001, NFR-002, NFR-003, C-001

**Files**:
- `src/specify_cli/mission_brief.py` ← create
- `src/specify_cli/cli/commands/intake.py` ← create
- `src/specify_cli/cli/commands/__init__.py` ← modify (register intake)
- `.gitignore` ← modify (add two entries)
- `tests/specify_cli/test_mission_brief.py` ← create
- `tests/specify_cli/cli/commands/test_intake.py` ← create

**Acceptance**:
- `spec-kitty intake PLAN.md` writes both artifact files
- `spec-kitty intake -` reads stdin correctly
- `--force` overwrites; without it exits 1 on existing brief
- `--show` prints brief + provenance; exits 1 if absent
- `.gitignore` contains both new entries
- `pytest tests/specify_cli/test_mission_brief.py tests/specify_cli/cli/commands/test_intake.py -v` passes
- `mypy --strict src/specify_cli/mission_brief.py src/specify_cli/cli/commands/intake.py` passes

**Dependencies**: none

---

### WP02 — Specify template: Brief Context Detection

**Delivers**: FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, NFR-004, C-002, C-003, C-004, C-005, C-006, C-007

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/specify.md` ← modify (insert section)
- All 13 agent directories updated by `spec-kitty upgrade` ← runtime step

**Acceptance**:
- New "Brief Context Detection" section appears after "Charter Context Bootstrap" and before "Discovery Gate" in the source template
- `spec-kitty upgrade` exits 0 and the section is present in `.claude/commands/spec-kitty.specify.md` (spot-check)
- Running `/spec-kitty.specify` without brief files → behaviour unchanged (manual test)

**Dependencies**: none (independent of WP01)

---

## Branch Contract (repeated per mandate)

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Merge target for completed changes**: `main`
- **`branch_matches_target`**: `true`
