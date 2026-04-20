---
work_package_id: WP01
title: Research Deliverable & Scan Module
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Feature branch from main; merge back to main when WP01 is approved.
subtasks:
- T001
- T002
- T003
- T004
history:
- date: '2026-04-20'
  author: spec-kitty.tasks
  note: Initial WP created
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- docs/reference/agent-plan-artifacts.md
- src/specify_cli/intake_sources.py
tags: []
---

# WP01 — Research Deliverable & Scan Module

**Mission**: intake-auto-detect-01KPNGCX  
**Issue**: Priivacy-ai/spec-kitty#703  
**Depends on**: (none — first WP)  
**Gates**: WP02 cannot start until this WP is approved

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- Execution worktree is allocated per computed lane from `lanes.json` after `finalize-tasks`.
- Enter your workspace with: `spec-kitty agent action implement WP01 --agent <name>`

## Objective

Produce two deliverables that together define the `--auto` scan surface:

1. **`docs/reference/agent-plan-artifacts.md`** — canonical reference for all 13 harnesses: plan mode status, artifact paths, confidence levels, sources, and source_agent mapping values.
2. **`src/specify_cli/intake_sources.py`** — new module with `HARNESS_PLAN_SOURCES` list and `scan_for_plans()` function. Only Verified-* confidence entries are active; lower-confidence entries exist as commented TODO blocks.

## Context

`spec-kitty intake --auto` (WP02) needs a reliable, documented scan list. The scan list must be derived from verified knowledge, not guesswork — a wrong path causes silent misses; a wrong file causes incorrect ingestion. This WP establishes the ground truth.

The 13 supported harnesses are: Claude Code, GitHub Copilot, Google Gemini, Cursor, Qwen Code, OpenCode, Windsurf, Kilocode, Augment Code, Roo Cline, Amazon Q / Kiro, Google Antigravity, Mistral Vibe.

Current known confidence for all harnesses: Low or Unknown. This WP must improve that by doing actual research.

---

## Subtask T001 — Research Plan-Mode Behavior for All 13 Harnesses

**Purpose**: Determine, for each harness, whether it has a plan mode and where it saves plan artifacts.

**Research priority order** (for each harness):
1. **Official documentation / changelog** — check the harness's official docs site, release notes, and any "plan mode" documentation.
2. **GitHub source** — search the harness's GitHub repository for file creation logic (`os.makedirs`, `Path.write_text`, etc.) in plan-mode code paths.
3. **Empirical test** — for harnesses available on this machine (check with `which claude`, `which cursor`, `which codex`, `which windsurf`, etc.), invoke plan mode in a temporary empty directory and observe what files are created.
4. **Community sources** — developer forums, blog posts, GitHub issue discussions.

**For empirical testing**:
```bash
# Check which harnesses are installed
which claude cursor codex windsurf 2>/dev/null

# For each installed harness, test in a temp directory:
tmp=$(mktemp -d)
cd "$tmp"
# Invoke plan mode per harness-specific invocation
find . -type f  # Observe what was created
```

**Questions to answer per harness**:
1. Does it have a plan mode? (Yes / No / Unclear)
2. What is the canonical artifact path, relative to project root?
3. What is the artifact named? (filename, extension)
4. Is the location user-configurable? (and if so, how)
5. Confidence level: Verified-docs | Verified-empirical | Inferred | Unknown

**Files**: No files created in this subtask — it's pure research input for T002.

**Validation**: For each of the 13 harnesses, you have an answer to all 5 questions with a documented source.

---

## Subtask T002 — Produce `docs/reference/agent-plan-artifacts.md`

**Purpose**: Write the canonical reference document from T001 research findings.

**File location**: `docs/reference/agent-plan-artifacts.md` (create `docs/reference/` if it doesn't exist)

**Document structure**:

```markdown
# Agent Plan-Mode Artifact Reference

<!-- intro paragraph: purpose, how to update, how it feeds intake_sources.py -->

## Harness Entries

### Claude Code (`claude`)

| Field | Value |
|-------|-------|
| Plan mode | Yes / No / Unclear |
| Artifact path(s) | `PLAN.md`, `.claude/PLAN.md`, ... |
| Filename pattern | `*.md` |
| User-configurable | Yes (settings key: X) / No |
| Confidence | Verified-docs / Verified-empirical / Inferred / Unknown |
| Source | [URL or "empirical test on version X.Y.Z on 2026-04-20"] |

**Notes**: Any caveats, version differences, format details.

---

### GitHub Copilot (`copilot`)
<!-- repeat pattern for all 13 harnesses -->

## source_agent Mapping

| Harness | Config key | source_agent value |
|---------|------------|-------------------|
| Claude Code | claude | claude-code |
| GitHub Copilot | copilot | copilot |
| Google Gemini | gemini | gemini |
| Cursor | cursor | cursor |
| Qwen Code | qwen | qwen |
| OpenCode | opencode | opencode |
| Windsurf | windsurf | windsurf |
| Kilocode | kilocode | kilocode |
| Augment Code | auggie | augment |
| Roo Cline | roo | roo |
| Amazon Q / Kiro | q / kiro | amazon-q |
| Google Antigravity | antigravity | antigravity |
| Mistral Vibe | vibe | vibe |

## How to Update This Document

<!-- instructions for adding a new harness or updating confidence -->
```

**All 13 harnesses must have an entry**, even if confidence is Unknown. The entry for Unknown harnesses should state why it's unknown and what further research would be needed.

**Validation**:
- [ ] All 13 harnesses have a section
- [ ] Every section has all 5 fields populated (with "Unclear" / "Unknown" as valid values)
- [ ] source_agent mapping table is complete
- [ ] Document builds cleanly (no broken links)

---

## Subtask T003 — Create `src/specify_cli/intake_sources.py` with `HARNESS_PLAN_SOURCES`

**Purpose**: Create the module that defines the priority-ordered scan list.

**File**: `src/specify_cli/intake_sources.py` (new file)

**Module structure**:

```python
"""Harness plan-artifact scan list for ``spec-kitty intake --auto``.

Each entry is a tuple of:
  (harness_key, source_agent_value, candidate_paths)

where:
  harness_key        – human-readable harness name (e.g. "claude-code")
  source_agent_value – value written to brief-source.yaml source_agent field
                       (None for generic/fallback entries)
  candidate_paths    – list of paths relative to CWD to check, in priority order

Only Verified-docs or Verified-empirical entries appear as active tuples.
Inferred or Unknown entries are commented out as TODO blocks.

Source: docs/reference/agent-plan-artifacts.md
Last updated: 2026-04-20
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Harness scan list
# ---------------------------------------------------------------------------

HARNESS_PLAN_SOURCES: list[tuple[str, str | None, list[str]]] = [
    # --- Verified-docs entries ---
    # ("claude-code", "claude-code", [".claude/PLAN.md", "PLAN.md"]),  # example

    # --- Generic fallback (no harness attribution) ---
    # ("generic", None, ["plan.md", "BRIEF.md"]),

    # --- TODO: Verify and promote these entries ---
    # Claude Code: Inferred — likely PLAN.md or .claude/PLAN.md (needs verification)
    # ("claude-code", "claude-code", ["PLAN.md", ".claude/PLAN.md"]),

    # Cursor: Inferred — Composer plan mode artifact path unknown
    # ("cursor", "cursor", [".cursor/PLAN.md"]),

    # ... (add remaining harnesses per research findings)
]
```

**Important**: Populate `HARNESS_PLAN_SOURCES` based on what T001/T002 research established at Verified-docs or Verified-empirical confidence. If all entries are still Inferred/Unknown after research, the active list must be empty — commented-out TODO blocks are the correct representation. The module is still valid and shippable with an empty active list.

**Ordering rule**: Most harness-specific paths (hidden dirs like `.claude/`, `.cursor/`) before generic root-level names (`PLAN.md`). Within a harness, more specific paths before more generic ones.

**Validation**:
- [ ] `ruff check src/specify_cli/intake_sources.py` passes
- [ ] `ruff format --check src/specify_cli/intake_sources.py` passes
- [ ] Module is importable: `python -c "from specify_cli.intake_sources import HARNESS_PLAN_SOURCES; print(len(HARNESS_PLAN_SOURCES))"`
- [ ] Every active entry has `harness_key` and `source_agent_value` as non-empty strings, and `candidate_paths` as a non-empty list

---

## Subtask T004 — Implement `scan_for_plans(cwd)` in `intake_sources.py`

**Purpose**: Add the function that does the actual filesystem scan against `HARNESS_PLAN_SOURCES`.

**Function signature**:
```python
def scan_for_plans(cwd: Path) -> list[tuple[Path, str, str | None]]:
    """Scan known harness plan locations under ``cwd``.

    Returns a list of ``(absolute_path, harness_key, source_agent_value)`` tuples
    for every candidate path that exists as a regular file, in declaration order.
    Silently skips paths that do not exist, are directories, or are unreadable.
    """
```

**Implementation**:
```python
def scan_for_plans(cwd: Path) -> list[tuple[Path, str, str | None]]:
    results: list[tuple[Path, str, str | None]] = []
    for harness_key, source_agent_value, candidate_paths in HARNESS_PLAN_SOURCES:
        for rel_path in candidate_paths:
            abs_path = cwd / rel_path
            try:
                if abs_path.is_file():
                    results.append((abs_path, harness_key, source_agent_value))
            except (PermissionError, OSError):
                pass  # silently skip unreadable paths
    return results
```

**Key behaviors**:
- Uses `is_file()` not `exists()` — directories at candidate paths are silently skipped
- Catches `PermissionError` and `OSError` — unreadable paths are silently skipped
- Returns in declaration order from `HARNESS_PLAN_SOURCES` — deterministic, matches stated priority
- Does NOT deduplicate — if the same physical file matches multiple entries (edge case), it appears multiple times; the CLI handles disambiguation

**Validation**:
- [ ] `scan_for_plans(Path("/nonexistent"))` returns `[]` without exception
- [ ] `scan_for_plans(Path("/tmp/empty-dir"))` returns `[]` without exception  
- [ ] Creates a real file at a candidate path → appears in results
- [ ] Directory at candidate path → not in results
- [ ] `ruff check` passes on the updated module

---

## Definition of Done

- [ ] `docs/reference/agent-plan-artifacts.md` exists and covers all 13 harnesses
- [ ] `src/specify_cli/intake_sources.py` exists and is importable
- [ ] `HARNESS_PLAN_SOURCES` active entries (if any) are Verified-docs or Verified-empirical only
- [ ] `scan_for_plans()` is implemented and handles all edge cases
- [ ] `ruff check src/specify_cli/intake_sources.py` passes
- [ ] No changes to any file outside `owned_files`

## Risks

| Risk | Mitigation |
|------|-----------|
| All 13 harnesses remain Inferred/Unknown | Empty active list is valid; ship with TODO comments; future PRs add entries as confidence improves |
| Harness plan mode saves to non-deterministic path | Document as Inferred/Unknown; do not add to active list |
| Empirical test invokes harness unexpectedly | Test in a temp directory; `rm -rf` the temp dir after |

## Reviewer Guidance

- Verify `agent-plan-artifacts.md` has explicit confidence levels — "Low" is not a valid confidence value (must be one of: Verified-docs, Verified-empirical, Inferred, Unknown)
- Verify no active `HARNESS_PLAN_SOURCES` entry has confidence below Verified-*
- Check `scan_for_plans()` handles the permission-error case — look for the try/except
- Check `ruff check` passes before approving
