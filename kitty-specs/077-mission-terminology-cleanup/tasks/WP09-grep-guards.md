---
work_package_id: WP09
title: CI Grep Guards
dependencies:
- WP02
requirement_refs:
- FR-012
- FR-022
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane workspace per execution lane (resolved by spec-kitty implement WP09)
subtasks:
- T036
- T037
- T038
- T039
- T040
- T041
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: tests/contract/test_terminology_guards.py
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- tests/contract/test_terminology_guards.py
priority: P0
tags: []
---

# WP09 — CI Grep Guards

## Objective

Implement `tests/contract/test_terminology_guards.py` per `contracts/grep_guards.md`. Nine guard test functions that prevent the canonical terminology drift from returning, scoped to live first-party surfaces only (FR-022) and respecting the historical-artifact exclusion (C-011).

These guards run in CI as part of the standard pytest suite. When a future PR re-introduces a forbidden pattern in a live surface, the guard fires and the build fails.

## Context

The guards are the **regression-prevention layer** for this entire mission. Without them, the cleanup will drift back the next time someone copy-pastes from an older command file.

The full guard contract is in `contracts/grep_guards.md`. There are **9 guards** total:

| # | Guard | Authority |
|---|---|---|
| 1 | `test_no_mission_run_alias_in_tracked_mission_selectors` | FR-002, FR-003 |
| 2 | `test_no_mission_run_slug_help_text_in_cli_commands` | FR-008 |
| 3 | `test_no_visible_feature_alias_in_cli_commands` | Charter §Terminology Canon, spec §11.1 |
| 4 | `test_no_mission_run_instructions_in_doctrine_skills` | FR-009 |
| 5 | `test_no_mission_run_instructions_in_agent_facing_docs` | FR-010, FR-022 |
| 5b | `test_no_feature_flag_in_live_top_level_docs` | FR-005, FR-022 |
| 6 | `test_no_mission_used_to_mean_mission_type_in_cli_commands` | FR-021 |
| 7 | `test_orchestrator_api_envelope_width_unchanged` | C-010 |
| 8 | `test_grep_guards_do_not_scan_historical_artifacts` (meta-guard) | FR-022, C-011 |

The envelope guard (Guard 7) **must** use the actual envelope keys at HEAD `35d43a25`: `contract_version`, `command`, `timestamp`, `correlation_id`, `success`, `error_code`, `data`. Using the wrong key set will cause a phantom regression hunt.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP09` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T036 — Create `tests/contract/test_terminology_guards.py` shell with helpers

**Purpose**: Set up the file with imports, helpers, scope constants, and the docstring that documents the FR-022/C-011 scope rule.

**Steps**:
1. Create `tests/contract/test_terminology_guards.py`:

   ```python
   """CI grep guards for canonical terminology drift.

   These guards prevent the Mission Type / Mission / Mission Run terminology
   boundary from drifting back to legacy selector vocabulary. They are scoped
   to LIVE first-party surfaces only.

   EXPLICITLY DOES NOT SCAN (per FR-022, C-011):
     - kitty-specs/** (historical mission artifacts)
     - architecture/** (historical ADRs and initiative records)
     - .kittify/** (runtime state)
     - tests/** (tests legitimately mention forbidden patterns)
     - docs/migration/** (migration docs explain the deprecation by name)
     - Historical version sections of CHANGELOG.md (below the first ## [x.y.z] heading)

   Authority:
     - kitty-specs/077-mission-terminology-cleanup/spec.md FR-022, C-010, C-011
     - kitty-specs/077-mission-terminology-cleanup/contracts/grep_guards.md
     - charter.md §Terminology Canon hyper-vigilance rules
   """
   from __future__ import annotations

   import re
   from pathlib import Path

   import pytest


   REPO_ROOT = Path(__file__).resolve().parents[2]


   def _glob(pattern: str) -> list[Path]:
       return list(REPO_ROOT.glob(pattern))


   def _read(path: Path) -> str:
       return path.read_text(encoding="utf-8")


   def _iter_typer_option_blocks(content: str):
       """Yield each typer.Option(...) call's text (best-effort, single-line and multi-line)."""
       # Match typer.Option(...) including balanced parentheses across lines
       pattern = re.compile(r"typer\.Option\((?:[^()]|\([^()]*\))*\)", re.DOTALL)
       for match in pattern.finditer(content):
           yield match.group(0)


   def _extract_help(option_block: str) -> str:
       """Extract the help= string from a typer.Option block, or empty string if absent."""
       match = re.search(r'help\s*=\s*"([^"]*)"', option_block)
       return match.group(1) if match else ""


   def _extract_changelog_unreleased(path: Path) -> str:
       """Return the portion of CHANGELOG.md above the first ## [<version>] heading.

       Historical version entries are excluded per FR-022.
       """
       content = _read(path)
       match = re.search(r"^## \[\d+\.\d+\.\d+", content, flags=re.MULTILINE)
       if match is None:
           return content
       return content[: match.start()]
   ```

2. Verify the file imports cleanly:
   ```bash
   uv run python -c "import tests.contract.test_terminology_guards"
   ```

### T037 — Implement guards 1-3 (CLI command file checks) [P]

**Purpose**: Implement the three guards that scan `src/specify_cli/cli/commands/**/*.py`.

**Steps**:
1. Add Guard 1 — `test_no_mission_run_alias_in_tracked_mission_selectors`. Find every `typer.Option` block that mentions `--mission-run` and verify the surrounding parameter is a runtime/session selector (function name or parameter name contains `runtime`, `session`, or `run_id`). If not, fail.

2. Add Guard 2 — `test_no_mission_run_slug_help_text_in_cli_commands`. Read each `.py` file under `src/specify_cli/cli/commands/`. Fail if `"Mission run slug"` appears.

3. Add Guard 3 — `test_no_visible_feature_alias_in_cli_commands`. For each `typer.Option` block in CLI command files, if the block contains `"--feature"` and does **not** contain `hidden=True`, fail with a message naming the file and offset. Note: tests must distinguish "hidden=True" inside the same Option block.

4. Refer to `contracts/grep_guards.md` for the exact pseudocode for each guard. Translate to runnable Python. The tests should be small and direct — no clever abstractions.

5. Run just these three:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py::test_no_mission_run_alias_in_tracked_mission_selectors tests/contract/test_terminology_guards.py::test_no_mission_run_slug_help_text_in_cli_commands tests/contract/test_terminology_guards.py::test_no_visible_feature_alias_in_cli_commands -v
   ```

   These should **fail** before WP03/WP04/WP05 land (because the drift sites still exist). They should **pass** after WP03/WP04/WP05 are complete.

### T038 — Implement guards 4-5 (doctrine skills + agent-facing docs) [P]

**Purpose**: Implement the two guards that scan markdown files.

**Steps**:
1. Add Guard 4 — `test_no_mission_run_instructions_in_doctrine_skills`. Scan `src/doctrine/skills/**/*.md`. Fail on any of the patterns from `contracts/grep_guards.md`:
   - `--mission-run\s+\d{3}` (e.g., `--mission-run 077-foo`)
   - `--mission-run\s+<slug>`
   - `--mission-run\s+<mission`

2. Add Guard 5 — `test_no_mission_run_instructions_in_agent_facing_docs`. Scan `docs/explanation/**/*.md`, `docs/reference/**/*.md`, `docs/tutorials/**/*.md`, top-level `README.md`, top-level `CONTRIBUTING.md`, and the Unreleased section of `CHANGELOG.md` (use `_extract_changelog_unreleased` from T036). **Do not** scan `docs/migration/**`.

3. The CHANGELOG handling is the tricky part:
   ```python
   for top_level in ["README.md", "CONTRIBUTING.md"]:
       path = REPO_ROOT / top_level
       if path.exists():
           scan_targets.append((path, _read(path)))

   changelog_path = REPO_ROOT / "CHANGELOG.md"
   if changelog_path.exists():
       scan_targets.append((changelog_path, _extract_changelog_unreleased(changelog_path)))
   ```

4. Run:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py::test_no_mission_run_instructions_in_doctrine_skills tests/contract/test_terminology_guards.py::test_no_mission_run_instructions_in_agent_facing_docs -v
   ```

### T039 — Implement guard 5b (top-level project docs) and guard 6 (inverse drift) [P]

**Purpose**: Implement the two guards that catch top-level docs drift and inverse-drift respectively.

**Steps**:
1. Add Guard 5b — `test_no_feature_flag_in_live_top_level_docs`. Scan top-level `README.md`, `CONTRIBUTING.md`, and the Unreleased section of `CHANGELOG.md` for raw `--feature` declarations. Patterns from `contracts/grep_guards.md`:
   - `--feature\s+<slug>`
   - `--feature\s+\d{3}`
   - `--feature\s+[a-z][a-z0-9-]*` (slug-like token)
   - `\|\s*\`--feature[\s|<>\`]` (markdown table cell)

2. Add Guard 6 — `test_no_mission_used_to_mean_mission_type_in_cli_commands`. For each `typer.Option` block in CLI command files: if it contains `"--mission"` (the literal flag) and the help text contains `"mission type"` or `"mission key"` (case-insensitive), and `"--mission-type"` is **not** also present in the same block, fail.

3. This guard catches the inverse-drift regression: if a future PR re-introduces a `--mission` parameter whose help string says "Mission type", the guard fires.

4. Run:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py::test_no_feature_flag_in_live_top_level_docs tests/contract/test_terminology_guards.py::test_no_mission_used_to_mean_mission_type_in_cli_commands -v
   ```

### T040 — Implement guards 7-8 (envelope width + meta-guard) [P]

**Purpose**: The two structural guards.

**Steps**:
1. Add Guard 7 — `test_orchestrator_api_envelope_width_unchanged`. **Critical: use the actual envelope keys verified at HEAD `35d43a25`:**
   ```python
   def test_orchestrator_api_envelope_width_unchanged():
       """The orchestrator-api 7-key envelope must not be widened by this or any future mission.

       Authority: C-010, spec §10.1 item 10.

       The expected key set is verified against the canonical implementation at
       src/specify_cli/orchestrator_api/envelope.py::make_envelope at HEAD 35d43a25.
       If make_envelope is intentionally changed in a future PR, this guard's
       expected_keys must be updated in the SAME PR after a documented C-010 amendment.
       """
       from specify_cli.orchestrator_api.envelope import make_envelope
       envelope = make_envelope("test-cmd", success=True, data={})
       expected_keys = {
           "contract_version",
           "command",
           "timestamp",
           "correlation_id",
           "success",
           "error_code",
           "data",
       }
       assert set(envelope.keys()) == expected_keys, (
           f"Orchestrator-api envelope keys must remain exactly {expected_keys}; "
           f"got {set(envelope.keys())}. C-010 forbids widening."
       )
       assert len(envelope) == 7, (
           f"Orchestrator-api envelope must remain exactly 7 keys; got {len(envelope)}."
       )
   ```

2. Add Guard 8 — `test_grep_guards_do_not_scan_historical_artifacts` (the meta-guard). This test introspects the other guards in this file to verify none of them resolve into forbidden roots:

   ```python
   def test_grep_guards_do_not_scan_historical_artifacts():
       """Verify no guard in this file scans kitty-specs/, architecture/, .kittify/, or historical CHANGELOG sections.

       Authority: FR-022, C-011.
       """
       forbidden_roots = ["kitty-specs/", "architecture/", ".kittify/"]
       this_file = Path(__file__).read_text(encoding="utf-8")
       for forbidden in forbidden_roots:
           # Find any string that looks like a glob pattern referencing the forbidden root
           pattern = rf'["\'].*{re.escape(forbidden)}'
           offending = re.findall(pattern, this_file)
           # Filter out the docstring mentions which are intentional
           offending = [o for o in offending if not o.startswith('"""') and "EXPLICITLY DOES NOT SCAN" not in this_file[max(0, this_file.find(o)-200):this_file.find(o)]]
           # The forbidden root may appear in docstrings/comments documenting the exclusion
           # but not in any actual scan target.
           # For a stricter version, parse the file and check only string literals passed to glob()/Path().
           # Heuristic version (good enough for CI):
           lines_with_match = [line for line in this_file.split("\n") if forbidden in line and "EXPLICITLY" not in line and "Authority" not in line and "doc" not in line.lower()]
           # Allow lines that are clearly comments or docstrings
           code_lines = [l for l in lines_with_match if not l.strip().startswith("#") and not l.strip().startswith('"""')]
           assert not code_lines, f"Guard file scans forbidden root '{forbidden}': {code_lines}"
   ```

   Note: the meta-guard implementation is intentionally heuristic. It catches the obvious mistake of accidentally adding `kitty-specs/**` to a glob. A stricter AST-based version is overkill.

3. Run:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py::test_orchestrator_api_envelope_width_unchanged tests/contract/test_terminology_guards.py::test_grep_guards_do_not_scan_historical_artifacts -v
   ```

### T041 — Run all 9 guards against current state and verify pass/fail behavior

**Purpose**: Confirm the guards work end-to-end.

**Steps**:
1. Run the full guard suite:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py -v
   ```

2. **Expected initial state** (before WP02-WP08 are all complete):
   - Guards 1, 2, 3, 4, 5, 5b: **fail** (drift still present in CLI files, doctrine skills, docs, README)
   - Guards 6, 7, 8: **pass** (no inverse-drift parameter declarations, envelope unchanged, meta-guard satisfied)

3. **Expected final state** (after WP02-WP08 are all complete and merged):
   - All 9 guards: **pass**

4. If any guard behaves unexpectedly, debug:
   - Guard fails when it should pass → fix the underlying drift
   - Guard passes when it should fail → strengthen the guard's pattern
   - Guard 7 fails on the canonical envelope → **stop and recheck the envelope keys**; do not change the envelope to match the guard

5. Document the WP09 completion in the WP10 acceptance evidence.

## Files Touched

| File | Action | Estimated lines |
|---|---|---|
| `tests/contract/test_terminology_guards.py` | CREATE | ~400 |

This is the only file owned by WP09. WP09 does not modify any other file (read-only verification of envelope.py, command files, doctrine skills, docs).

## Definition of Done

- [ ] `tests/contract/test_terminology_guards.py` exists with all 9 guard test functions
- [ ] All 9 guards run without import errors
- [ ] Guard 7 uses the actual envelope keys (`contract_version`, `command`, `timestamp`, `correlation_id`, `success`, `error_code`, `data`)
- [ ] Guard 8 (meta-guard) verifies no other guard scans forbidden roots
- [ ] Guards 1, 2, 3 fail before WP03/WP04 land (proving they detect drift) and pass after
- [ ] Guards 4, 5, 5b fail before WP06/WP07 land and pass after
- [ ] Guard 6 catches the inverse-drift regression (test by reverting one site temporarily)
- [ ] All guards pass after WP02-WP08 are complete and merged
- [ ] No file outside `tests/contract/test_terminology_guards.py` is modified

## Risks and Reviewer Guidance

**Risks**:
- The meta-guard (Guard 8) is the most fragile because it pattern-matches its own source code. A poorly written future addition might trigger false positives. Use a heuristic pattern that's resistant to comment changes.
- Guard 1 must allow runtime/session usages of `--mission-run`. Test that legitimate runtime/session command files don't fail this guard.
- Guard 7 must use the **canonical** envelope keys at HEAD `35d43a25`, not a guess. Verify by reading `src/specify_cli/orchestrator_api/envelope.py:66-74` directly before writing the guard.

**Reviewer checklist**:
- [ ] Guard 7 uses `contract_version`/`command`/`timestamp`/`correlation_id`/`success`/`error_code`/`data` (NOT `schema_version`/`build_id`)
- [ ] Guard 8 (meta-guard) is present and passes
- [ ] No guard scans `kitty-specs/`, `architecture/`, `.kittify/`, or historical CHANGELOG sections
- [ ] Guard 1 allows runtime/session contexts
- [ ] All guards have failure messages naming the file and citing the FR
- [ ] mypy --strict is clean on the new test file

## Implementation Command

```bash
spec-kitty implement WP09
```

This WP depends on WP02 (the helper must exist before guard 3 can verify against canonical state). After WP02 is merged, WP09 can run in parallel with WP03, WP04, WP05.

## References

- `contracts/grep_guards.md` — full guard contract with all 9 specifications
- Spec FR-022, C-010, C-011, NFR-005
- Charter §Terminology Canon hyper-vigilance rules
- `src/specify_cli/orchestrator_api/envelope.py:66-74` — canonical envelope keys
