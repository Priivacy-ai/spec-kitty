---
work_package_id: WP02
title: Preserve encoding normalization on spec-kitty accept
dependencies:
- WP01
requirement_refs:
- FR-005
- NFR-004
tracker_refs: []
planning_base_branch: mission/retire-standalone-tasks-cli
merge_target_branch: mission/retire-standalone-tasks-cli
branch_strategy: Planning artifacts for this mission were generated on mission/retire-standalone-tasks-cli. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/retire-standalone-tasks-cli unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
phase: Phase 2 - Preserve capability
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "790104"
history:
- at: '2026-06-29T22:08:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/accept.py
create_intent:
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/cli/commands/test_accept_normalize_encoding.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/cli/commands/test_accept_normalize_encoding.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Preserve encoding normalization on `spec-kitty accept`

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Preserve the standalone tasks CLI's one genuinely-unique capability — opt-in acceptance-artifact encoding normalization — on the **supported** `spec-kitty accept` command, before the standalone surface is deleted. Add an opt-in `--normalize-encoding` flag that, on an encoding failure, repairs artifacts by delegating to the **canonical** `specify_cli.acceptance.normalize_feature_encoding` (C-003 — reuse canonical, copy no standalone logic).

**Test taxonomy (read before writing tests):** the new behavior is ONLY the repair path. So **T006 is the red-first wiring test** — write it first; it must fail before T004/T005 (the `--normalize-encoding` option does not exist yet) and pass after. **T007 and T008 are regression pins** for *pre-existing* behavior (the real `accept` already does no-rewrite-by-default and already raises `ArtifactEncodingError` → exit 1); they pass with or without the FR-005 wiring, so each must be written to fail only if *its own* default behavior is later changed — they are NOT proof the wiring works.

## Context (verified at plan time — confirm live)

- The real `spec-kitty accept` has **no** encoding handling today (`grep -ni "normalize\|encoding" src/specify_cli/cli/commands/accept.py` → empty).
- The without-flag error path **already exists**: `collect_feature_summary` reads via `_read_text_strict` (`acceptance/__init__.py:474-479`), which raises `ArtifactEncodingError` (subclass of `AcceptanceError`, `:210`) whose message at `:216` already says *"… Run with --normalize-encoding to fix automatically."*; `accept.py:318 except AcceptanceError` → prints `Error:` + `raise typer.Exit(1)` (`:326`), writing nothing. **Do not change this default path** — just assert it in T008.
- Canonical repair function: `specify_cli.acceptance.normalize_feature_encoding(repo_root: Path, feature: str) -> list[Path]` (`acceptance/__init__.py:600`) — returns the list of files it repaired. This is the C-003 delegation target. It only rewrites `PRIMARY_ARTIFACT_FILES` that actually fail UTF-8 decode (gate-time byte-recovery — distinct from `validate-encoding`'s proactive cleanup; see plan's Encoding-authority boundary, do not conflate them).
- Reference control flow to mirror (do NOT copy): the standalone `scripts/tasks/tasks_cli.py:156-205` (`_collect_summary_with_encoding` / `_handle_encoding_failure`): collect → on `ArtifactEncodingError`, if flag off re-raise, else `normalize_feature_encoding(...)`, print repaired paths to stderr, re-collect, proceed.

## Subtasks

### T004 — Add the flag (red-first scaffolding)
Add a typer option to the `accept` command in `src/specify_cli/cli/commands/accept.py`:
```python
normalize_encoding: bool = typer.Option(
    False,
    "--normalize-encoding/--no-normalize-encoding",
    help="Repair acceptance-artifact encoding (Windows-1252/Latin-1 -> UTF-8) before validating.",
),
```
Match the existing option style in the command signature. Default **off**.

### T005 — Wire the repair path
Locate where `accept` calls `collect_feature_summary` (≈`accept.py:293`). Wrap it so that, when `normalize_encoding` is True and an `ArtifactEncodingError` is raised, it:
1. calls `from specify_cli.acceptance import normalize_feature_encoding` and runs `repaired = normalize_feature_encoding(repo_root, feature)`,
2. reports the repaired paths (stderr / console, matching the command's existing reporting idiom),
3. re-collects (`collect_feature_summary(...)`) and proceeds.
When `normalize_encoding` is False, do nothing new — let the existing `except AcceptanceError` (`:318`) handle it (exit 1). Keep the change minimal (~20–30 lines). Resolve `repo_root`/`feature` from the values the command already has in scope. Do not import or reference anything under `specify_cli.scripts.tasks`.

### T006 — Test: repair-with-flag `[P]`
In `tests/specify_cli/cli/commands/test_accept_normalize_encoding.py` (new), build a mission repo whose acceptance artifact contains invalid UTF-8 (e.g. a Windows-1252 smart quote byte `0x92`). Invoke `spec-kitty accept ... --normalize-encoding` via `CliRunner`/`cli_app`. Assert: the artifact is rewritten to valid UTF-8, the repaired path is reported, and acceptance proceeds (no `ArtifactEncodingError`). Reuse existing acceptance test fixtures/helpers where available rather than hand-rolling repo setup.

### T007 — Test: default-off no rewrite `[P]`
Same malformed artifact; invoke `accept` **without** the flag. Assert the file bytes are **unchanged** (no rewrite) and the command surfaces the encoding error (T008 asserts the exact surface).

### T008 — Test: error-without-flag clean exit `[P]`
Assert that without `--normalize-encoding`, the malformed artifact yields exit code 1 and an error message containing `Invalid UTF-8` and `--normalize-encoding` (the existing `ArtifactEncodingError` message). This pins the existing default behavior so a later change cannot silently regress it.

## Definition of Done
- `spec-kitty accept --normalize-encoding` repairs mojibake artifacts via canonical `normalize_feature_encoding`; default-off leaves bytes untouched; without-flag malformed input → exit 1 referencing the flag.
- **T006 is non-vacuous**: it fails when T005's wiring is reverted (verify by reverting locally — it must red). T007/T008 are regression pins for the pre-existing default path (they are not expected to red on a wiring revert).
- No reference to `specify_cli.scripts.tasks` anywhere in the diff.
- `ruff` + `mypy` clean on `accept.py` and the new test.

## Risks
- **Re-collect loop**: ensure the repair path re-collects exactly once; if normalization repairs nothing (no files needed fixing) it must not loop. Mitigation: the standalone reference handled this — re-collect once and let any *second* failure propagate.
- **Dual-authority confusion**: delegate to `acceptance.normalize_feature_encoding`, NOT `text_sanitization` / `validate-encoding`. The plan records why; do not "unify" them.

## Reviewer guidance
Verify: opt-in default off, delegation to canonical `normalize_feature_encoding`, the three tests are non-vacuous (each fails if the corresponding behavior is removed), and the default error path is unchanged. Reject any copied standalone logic or any `text_sanitization` substitution.

## Activity Log

- 2026-06-29T23:50:25Z – claude:sonnet:python-pedro:implementer – shell_pid=776453 – Assigned agent via action command
- 2026-06-30T00:01:04Z – claude:sonnet:python-pedro:implementer – shell_pid=776453 – FR-005 complete: opt-in accept --normalize-encoding delegates to canonical normalize_feature_encoding; 3 tests pass; T006 non-vacuous (red on revert); T007/T008 regression pins; ruff+mypy clean. commit 4dc5fd83b.
- 2026-06-30T00:01:08Z – user – shell_pid=776453 – FR-005 complete (force past charter-synthesis churn; deliverable committed 4dc5fd83b).
- 2026-06-30T00:01:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=790104 – Started review via action command
- 2026-06-30T00:04:20Z – user – shell_pid=790104 – Review passed (reviewer-renata): opt-in default-off; canonical delegation (C-003); re-collects once; T006 non-vacuous (reproven red-on-revert); ruff+mypy clean.
