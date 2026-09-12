---
work_package_id: WP02
title: Slash-command reference gate + backfill
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: docs/3253-docs-gaps
merge_target_branch: docs/3253-docs-gaps
branch_strategy: Planning artifacts for this mission were generated on docs/3253-docs-gaps. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/3253-docs-gaps unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
history:
- at: '2026-08-08T10:45:09Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/check_slash_command_freshness.py
create_intent:
- scripts/docs/check_slash_command_freshness.py
- tests/docs/test_check_slash_command_freshness.py
execution_mode: code_change
owned_files:
- scripts/docs/check_slash_command_freshness.py
- docs/api/slash-commands.md
- tests/docs/test_check_slash_command_freshness.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else:

```
/ad-hoc-profile-load python-pedro
```

Confirm which initialization/boundaries/directives you applied (TDD/red-first; run
pytest+ruff+mypy before handoff; Python-implementation lane). The doc-backfill subtask
(T009) is prose — apply the charter's active writing doctrine (`professional-communications`,
`plain-language`, DIRECTIVE_047 audience-oriented, Terminology Canon `<mission>` not
`<feature>`) when authoring it. Then proceed.

## Objective

Stop `docs/api/slash-commands.md` from silently drifting from the command registry
(FR-001), and backfill the three consumer commands it is missing so it mirrors
`CONSUMER_SKILLS` (FR-002). The gate is **check-only** (no generator) and **bidirectional**.

## Context

- **Authority (C-001)**: `CONSUMER_SKILLS` in `src/specify_cli/shims/registry.py` — a
  frozenset of 15 consumer commands, import-asserted equal to
  `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS` (`registry.py:87`). Import it directly;
  do NOT fork or re-parse a second command set.
- The doc documents **12** commands today via `## /spec-kitty.<name>` headings; missing:
  `tasks-outline`, `tasks-packages`, `tasks-finalize`.
- **Mirror the shape, not the regex**: `scripts/docs/check_cli_reference_freshness.py`
  is the pattern to follow (parse headings → diff → emit → non-zero exit) and
  `tests/docs/test_check_cli_reference_freshness.py` is the test-harness template — but its
  `_HEADING_RE` matches the **space** form `spec-kitty foo` and will NOT match the
  slash+dot form. Author a **new** extractor.
- **NFR-004**: pure in-process — no subprocess, no network. Importing `CONSUMER_SKILLS`
  transitively initializes the `specify_cli` package (~140ms) — acceptable.

## Subtasks

### T008 — Author `check_slash_command_freshness.py`
**Purpose**: The bidirectional gate.
**Steps**:
1. New file `scripts/docs/check_slash_command_freshness.py`.
2. Extract the documented set with a new regex, e.g. `^##\s+/spec-kitty\.([a-z0-9-]+)\s*$` (top-level heading only; ignore prose sections like `## Getting Started`).
3. Import `CONSUMER_SKILLS`; compute symmetric difference:
   - `MISSING` = `CONSUMER_SKILLS - documented` (in registry, undocumented).
   - `EXTRA` = `documented - CONSUMER_SKILLS` (documented, retired/unknown).
4. Print one line per offender under a clear header; exit non-zero if either set is non-empty, exit 0 otherwise.
5. Keep it a pure set-diff: no subprocess/network; functions ≤15 complexity.
**Validation**: run it against today's doc → exit 1 listing the 3 MISSING; covered by T010.

### T009 — Backfill the three missing sections
**Purpose**: Make the doc mirror the registry (turns FR-001 green).
**Steps**:
1. In `docs/api/slash-commands.md`, add `## /spec-kitty.tasks-outline`, `## /spec-kitty.tasks-packages`, `## /spec-kitty.tasks-finalize` sections.
2. Match the existing per-command section structure (purpose, usage, arguments/paths as the neighbouring sections do). Consult the mission-system / tasks docs and the command templates for accurate content — do not invent behavior.
3. Use `<mission>` placeholders (never `<feature>`) in any example paths (C-004).
4. Keep edits scoped to the three new sections — do NOT sweep the file's other `<feature>` occurrences (that is OUT per C-005 / a separate follow-up).
**Validation**: `check_slash_command_freshness.py` exits 0; terminology guard passes.

### T010 — Committed negative test (both directions) + green-after-backfill
**Steps**:
1. New file `tests/docs/test_check_slash_command_freshness.py` (mirror `test_check_cli_reference_freshness.py`).
2. Test MISSING: a fixture doc missing a command → gate exits non-zero naming it.
3. Test EXTRA: a fixture doc with a `## /spec-kitty.<retired>` heading not in `CONSUMER_SKILLS` → gate exits non-zero naming it.
4. Test GREEN: the real (backfilled) doc → exit 0.
**Validation**: committed, non-vacuous (fails on both mutated fixtures).

## Branch Strategy

- **Planning/base branch**: `docs/3253-docs-gaps`. **Final merge target**: `docs/3253-docs-gaps`.
- Execution worktree allocated per computed lane from `lanes.json`; enter what `spec-kitty implement WP02` resolves. WP02 starts Lane B; **WP03 depends on WP02** (it wires this gate into CI after the doc is backfilled).

## Test Strategy (ATDD, C-006)

Red-first for FR-002 is genuine: on the base branch the doc is 12/15, so the gate is RED
before T009 and GREEN after. Commit the gate+test first (T008/T010), demonstrate the RED,
then backfill (T009) → GREEN. Targeted: `pytest tests/docs/test_check_slash_command_freshness.py`.
ruff + mypy clean.

## Definition of Done

- `check_slash_command_freshness.py` exists; fails on both drift directions; exits 0 on the backfilled doc (SC-001, SC-002).
- The doc documents all 15 consumer commands; new sections use `<mission>` and match house style.
- Committed negative test (MISSING + EXTRA) is non-vacuous (NFR-001).
- Does NOT modify `docs-freshness.yml` (that is WP03).

## Risks / Reviewer guidance

- **Reviewer**: confirm the gate imports `CONSUMER_SKILLS` (not a hand-list), checks
  **both** directions, and defines "documented" as a `## /spec-kitty.<name>` heading. Confirm
  the backfill matches house style, uses `<mission>`, and did not sweep unrelated
  `<feature>` occurrences. Confirm WP02 leaves `docs-freshness.yml` untouched.
