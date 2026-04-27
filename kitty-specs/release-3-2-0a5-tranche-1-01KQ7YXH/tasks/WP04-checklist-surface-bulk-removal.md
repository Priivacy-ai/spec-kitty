---
work_package_id: WP04
title: FR-003 + FR-004 /spec-kitty.checklist bulk removal
dependencies: []
requirement_refs:
- C-003
- C-008
- FR-003
- FR-004
- NFR-003
- NFR-009
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "78401"
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- src/specify_cli/missions/software-dev/command-templates/checklist.md
- .kittify/overrides/missions/software-dev/command-templates/checklist.md
- .kittify/command-skills-manifest.json
- src/specify_cli/upgrade/migrations/_legacy_codex_hashes.py
- tests/specify_cli/skills/__snapshots__/codex/checklist.SKILL.md
- tests/specify_cli/skills/__snapshots__/vibe/checklist.SKILL.md
- tests/specify_cli/regression/_twelve_agent_baseline/**/checklist*
- tests/specify_cli/upgrade/fixtures/codex_legacy/**/spec-kitty.checklist.md
- tests/specify_cli/skills/test_registry.py
- tests/specify_cli/skills/test_command_renderer.py
- tests/specify_cli/skills/test_installer.py
- tests/missions/test_command_templates_canonical_path.py
- tests/specify_cli/test_no_checklist_surface.py
- tests/missions/test_specify_creates_requirements_checklist.py
- README.md
- docs/reference/slash-commands.md
- docs/reference/file-structure.md
- docs/reference/supported-agents.md
role: implementer
tags:
- bulk-edit
- removal
---

# WP04 — FR-003 + FR-004 `/spec-kitty.checklist` bulk removal

## ⚡ Do This First: Load Agent Profile AND Bulk-Edit Skill

Before reading further or making any edits, do BOTH of these:

1. Invoke the `/ad-hoc-profile-load` skill with:
   - **Profile**: `implementer-ivan`
   - **Role**: `implementer`
2. Load the `spec-kitty-bulk-edit-classification` skill. This WP is bulk-edit-classified (`meta.json::change_mode == "bulk_edit"`) and the skill carries the workflow that prevents DIRECTIVE_035 violations. **Do not skip step 2.**

The bulk-edit skill teaches the occurrence-classification check. You will reference [`occurrence_map.yaml`](../occurrence_map.yaml) at every step.

## Objective

Retire the deprecated `/spec-kitty.checklist` slash command from every generated user-facing command surface (slash-command and skills agents), from source templates, from the registry / command renderer / command installer surface, from upgrade migrations, and from regression baselines and snapshot fixtures. Preserve the canonical `kitty-specs/<mission>/checklists/requirements.md` artifact contract.

Closes #815. Supersedes #635 — close #635 with a comment linking to #815.

## Context

[`occurrence_map.yaml`](../occurrence_map.yaml) is the source of truth for this WP. It enumerates **27 REMOVE** and **6 KEEP** occurrences across 6 of 8 standard categories. The implementing agent MUST cross-check the final diff against the map before commit; anything extra or missing is a DIRECTIVE_035 violation.

**Boundary**: One reference to `/spec-kitty.checklist` lives in `src/specify_cli/cli/commands/init.py:723`. That file is owned by **WP05**, not this WP. WP05 includes a subtask (T024) to remove that line so `init.py` ownership stays single-WP.

**Why no shim**: `start-here.md` "Done Criteria" requires `/spec-kitty.checklist` to be gone from generated user-facing command surfaces. A "deprecated, use X" stub command would contradict that requirement.

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP has no dependencies; its lane is rebased directly onto `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).

## Subtasks

### T015 — Delete the source template AND its override copy

**Purpose**: Stop the renderer from generating per-agent copies of the deprecated command.

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/checklist.md` (delete)
- `.kittify/overrides/missions/software-dev/command-templates/checklist.md` (delete)

**Steps**:

1. Delete both files.
2. Run `git status` to confirm no other files were touched.

**Validation**:
- [ ] Both files no longer exist.

### T016 — Remove `/spec-kitty.checklist` entries from manifest + legacy hash catalog

**Purpose**: Stop the skill installer and upgrade migrations from recreating the deprecated surface.

**Files**:
- `.kittify/command-skills-manifest.json` (~line 36 — remove the `spec-kitty.checklist` entry)
- `src/specify_cli/upgrade/migrations/_legacy_codex_hashes.py` (~line 40 — remove the `spec-kitty.checklist.md` entry)

**Steps**:

1. Open the manifest. Remove the JSON object describing `.agents/skills/spec-kitty.checklist/SKILL.md`. Preserve JSON validity (no trailing commas).
2. Open the legacy hash catalog. Remove the entry keyed on `spec-kitty.checklist.md` (or the equivalent identifier — check the file format). Preserve any other entries unchanged.

**Validation**:
- [ ] `python -m json.tool .kittify/command-skills-manifest.json > /dev/null` exits 0 (valid JSON).
- [ ] `grep -c "spec-kitty.checklist" .kittify/command-skills-manifest.json src/specify_cli/upgrade/migrations/_legacy_codex_hashes.py` prints `0` for each file.

### T017 — Delete deprecated snapshots, regression baselines, and upgrade fixtures

**Purpose**: Strip every regression artifact that captures the deprecated surface so future test runs don't regenerate them.

**Files** (delete each):
- `tests/specify_cli/skills/__snapshots__/codex/checklist.SKILL.md`
- `tests/specify_cli/skills/__snapshots__/vibe/checklist.SKILL.md`
- `tests/specify_cli/regression/_twelve_agent_baseline/<agent>/checklist*` for each of: `claude`, `cursor`, `opencode`, `windsurf`, `kilocode`, `auggie`, `roo`, `q`, `kiro`, `antigravity`, `copilot` (note: copilot uses `checklist.prompt.md`).
- `tests/specify_cli/upgrade/fixtures/codex_legacy/mixed/.codex/prompts/spec-kitty.checklist.md`
- `tests/specify_cli/upgrade/fixtures/codex_legacy/owned_unedited_only/.codex/prompts/spec-kitty.checklist.md`

**Steps**:

1. Use `find` to enumerate before deletion:
   ```bash
   find tests/specify_cli/regression/_twelve_agent_baseline -name 'checklist*'
   find tests/specify_cli/skills/__snapshots__ -name 'checklist*'
   find tests/specify_cli/upgrade/fixtures/codex_legacy -name 'spec-kitty.checklist*'
   ```
2. Delete each file enumerated.
3. After deletion, regenerate the per-agent regression baselines so they reflect the new reduced surface. The repo's existing snapshot regen tooling (typically a `pytest --snapshot-update` flag or a script in `scripts/`) handles this — check `tests/specify_cli/regression/conftest.py` for the canonical regen invocation.

**Validation**:
- [ ] Re-run the three `find` commands above; all should print zero matches.
- [ ] `pytest tests/specify_cli/regression/ -q` exits 0 with the regenerated baselines.

### T018 — Update existing tests to drop checklist expectations

**Purpose**: Tests that currently assert the checklist skill exists must be updated so the new reduced surface passes them.

**Files**:
- `tests/specify_cli/skills/test_registry.py` (drop checklist from expected sets)
- `tests/specify_cli/skills/test_command_renderer.py` (assert checklist NOT among rendered outputs)
- `tests/specify_cli/skills/test_installer.py` (assert checklist NOT installed)
- `tests/missions/test_command_templates_canonical_path.py` (drop checklist from canonical path enumeration)

**Steps**:

1. For each file, grep for `checklist`. Remove or invert each assertion as appropriate:
   - "Expected to be present" → remove the assertion.
   - "Expected count = N" → decrement N if the checklist contributed.
   - Set membership tests → remove the checklist member.
2. Where a test exists ONLY to verify the checklist surface, delete the entire test function.
3. Run `pytest <file> -q` after each edit to confirm the changes are correct.

**Validation**:
- [ ] `pytest tests/specify_cli/skills/test_registry.py tests/specify_cli/skills/test_command_renderer.py tests/specify_cli/skills/test_installer.py tests/missions/test_command_templates_canonical_path.py -q` exits 0.

### T019 — Add aggregate `tests/specify_cli/test_no_checklist_surface.py`

**Purpose**: Future-proof the removal so any regression that recreates the surface fails at test time.

**Files**:
- `tests/specify_cli/test_no_checklist_surface.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import re
   from pathlib import Path

   import pytest


   REPO_ROOT = Path(__file__).resolve().parents[2]

   # The slash-command identifier itself — must be gone everywhere.
   CHECKLIST_CMD_RE = re.compile(r"/?spec-kitty\.checklist\b")

   # Deprecated agent-surface filenames. The allowlist below carves out
   # legitimate "checklist" concepts (mission requirements checklist,
   # release checklist, review checklist) so the scanner only flags the
   # retired command surface.
   CHECKLIST_FILENAME_RE = re.compile(r"(^|[/\\])checklist(\.SKILL|\.prompt)?\.md$")

   SCAN_ROOTS = [
       "src/specify_cli/missions",
       "tests/specify_cli/regression",
       "tests/specify_cli/skills/__snapshots__",
       "docs",
   ]

   # Per-agent rendered surfaces (rendered into the dev project itself).
   AGENT_DIRS = [
       ".claude/commands",
       ".codex/prompts",
       ".gemini/commands",
       ".cursor/commands",
       ".qwen/commands",
       ".opencode/command",
       ".windsurf/workflows",
       ".kilocode/workflows",
       ".augment/commands",
       ".roo/commands",
       ".amazonq/prompts",
       ".kiro/prompts",
       ".agent/workflows",
       ".github/prompts",
       ".agents/skills",
   ]

   # Allowlist: reserved for legitimate "checklist" concepts unrelated to
   # the retired slash command. Anything matching is skipped by the scanner.
   ALLOWLIST_PREFIXES = (
       "kitty-specs/",  # mission-level checklists/ directory is canonical
   )

   ALLOWLIST_FILENAMES = (
       "RELEASE_CHECKLIST.md",
   )

   ALLOWLIST_SUBSTRINGS = (
       "release_checklist",
       "release-checklist",
       "review_checklist",
       "review-checklist",
   )


   def _walk(root: Path):
       if not root.exists():
           return
       for p in root.rglob("*"):
           if p.is_file():
               yield p


   def _is_allowlisted(path: Path) -> bool:
       posix = path.relative_to(REPO_ROOT).as_posix()
       if any(posix.startswith(p) for p in ALLOWLIST_PREFIXES):
           return True
       if path.name in ALLOWLIST_FILENAMES:
           return True
       lowered = path.name.lower()
       return any(s in lowered for s in ALLOWLIST_SUBSTRINGS)


   def test_no_checklist_filenames_in_scan_roots():
       offenders = []
       for rel in SCAN_ROOTS + AGENT_DIRS:
           for path in _walk(REPO_ROOT / rel):
               if _is_allowlisted(path):
                   continue
               if CHECKLIST_FILENAME_RE.search(str(path)):
                   offenders.append(str(path.relative_to(REPO_ROOT)))
       assert not offenders, (
           "Found deprecated checklist filenames:\n  " + "\n  ".join(offenders)
       )


   def test_no_checklist_command_string_in_scan_roots():
       offenders = []
       for rel in SCAN_ROOTS + AGENT_DIRS:
           for path in _walk(REPO_ROOT / rel):
               if _is_allowlisted(path):
                   continue
               try:
                   text = path.read_text(encoding="utf-8", errors="ignore")
               except OSError:
                   continue
               if CHECKLIST_CMD_RE.search(text):
                   offenders.append(str(path.relative_to(REPO_ROOT)))
       assert not offenders, (
           "Found references to /spec-kitty.checklist:\n  " + "\n  ".join(offenders)
       )
   ```

2. Verify both tests pass against the current tree (after T015–T018).
3. Verify they FAIL against `main` (sabotage-test by temporarily restoring one file).

**Validation**:
- [ ] `pytest tests/specify_cli/test_no_checklist_surface.py -q` exits 0.

### T020 — Add `tests/missions/test_specify_creates_requirements_checklist.py`

**Purpose**: Lock the canonical requirements-checklist artifact contract (C-003) so future cleanup never deletes it accidentally.

**Files**:
- `tests/missions/test_specify_creates_requirements_checklist.py` (new)

**Steps**:

1. Create a test that drives `mission create` (via the existing test helper, NOT subprocess) for a tmp mission, then asserts that the path `kitty-specs/<slug>/checklists/requirements.md` exists.
2. The test does NOT need to drive the whole `/spec-kitty.specify` flow — just confirm the artifact directory and file are in place after a fresh mission scaffold. If `mission create` itself does NOT create `requirements.md` (it doesn't — `/spec-kitty.specify` does), then this test should drive whichever helper inside `tests/missions/` creates the requirements checklist.
3. Reuse existing test infrastructure under `tests/missions/`.

**Validation**:
- [ ] `pytest tests/missions/test_specify_creates_requirements_checklist.py -q` exits 0.

### T021 — Update doc references per occurrence_map

**Purpose**: README, slash-command reference, file-structure reference, and supported-agents reference should no longer mention `/spec-kitty.checklist`. References to the canonical `requirements.md` artifact MUST stay.

**Files**:
- `README.md`
- `docs/reference/slash-commands.md`
- `docs/reference/file-structure.md`
- `docs/reference/supported-agents.md`

**Steps**:

1. For each file, grep for `/spec-kitty.checklist` AND for `checklist`.
2. Distinguish:
   - **REMOVE**: Any mention of the slash-command itself (e.g. "Run `/spec-kitty.checklist` to ...").
   - **KEEP**: Any mention of the canonical artifact path (e.g. "`kitty-specs/<mission>/checklists/requirements.md`") or generic words like "release checklist", "review checklist".
3. Refer to [`occurrence_map.yaml`](../occurrence_map.yaml) `user_facing_strings` section for the per-occurrence classification.
4. Where removing the slash-command reference would leave a dangling list item or broken sentence, restructure the surrounding prose so it reads cleanly without that line.

**Validation**:
- [ ] Grep each file for `/spec-kitty\.checklist` — expect zero matches.
- [ ] Grep each file for `checklists/requirements.md` (or equivalent) — KEEP matches preserved per the occurrence map.

## Test Strategy

- **Aggregate scanner** (T019): the future-proofing regression. If anyone reintroduces the deprecated surface anywhere in the repo, this test fails.
- **Artifact preservation** (T020): the C-003 boundary. If anyone accidentally removes `kitty-specs/<mission>/checklists/requirements.md` from the spec-kitty surface, this fails.
- **Existing skills/registry tests** (T018): updated to reflect the new reduced surface, not deleted wholesale.

## Definition of Done

- [ ] T015–T021 complete.
- [ ] `pytest tests/specify_cli/test_no_checklist_surface.py tests/missions/test_specify_creates_requirements_checklist.py tests/specify_cli/skills/ tests/specify_cli/regression/ tests/missions/test_command_templates_canonical_path.py -q` exits 0.
- [ ] Diff matches [`occurrence_map.yaml`](../occurrence_map.yaml) — every REMOVE present, every KEEP preserved, no extras.
- [ ] PR description includes:
  - One-line CHANGELOG entry text for **WP02** to consolidate. Suggested: `Retire the deprecated \`/spec-kitty.checklist\` command surface from every supported agent's rendered output. The canonical requirements checklist at \`kitty-specs/<mission>/checklists/requirements.md\` is unaffected (#815, supersedes #635).`
  - Note that #635 is now closeable with a comment linking to #815.

## Risks

- **R1**: A reference to `/spec-kitty.checklist` survives in a fixture or doc not enumerated in `occurrence_map.yaml`. The aggregate scanner in T019 catches this. If it triggers during your run, ADD the new occurrence to `occurrence_map.yaml` AND remove it.
- **R2**: Snapshot regeneration in T017 inadvertently drops more than just the checklist. Diff-check the regenerated baselines against the pre-removal baselines (minus the `checklist*` files); only `checklist*` files should disappear.

## Reviewer Guidance

- Verify diff against `occurrence_map.yaml` line by line.
- Verify `docs/reference/file-structure.md` still describes the `kitty-specs/<mission>/checklists/` directory and the `requirements.md` artifact (KEEP-rationale).
- Verify the new aggregate scanner (T019) covers all 15 supported-agent directories from `CLAUDE.md`.
- Verify T020's artifact-preservation test runs on a fresh mission (not on this mission's directory).
- Confirm #635 has a comment linking to #815 for closure (this can be done at PR-merge time rather than in the diff).

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent claude
```

## Activity Log

- 2026-04-27T19:59:35Z – claude:sonnet:implementer-ivan:implementer – shell_pid=75468 – Started implementation via action command
- 2026-04-27T20:12:28Z – claude:sonnet:implementer-ivan:implementer – shell_pid=75468 – Ready for review: 27 REMOVE per occurrence_map (2 additional gemini+qwen baselines per R1, to be appended to occurrence_map by reviewer if accepted), baselines regenerated, no init.py touched, two new regression tests cover surface absence + artifact preservation
- 2026-04-27T20:13:38Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=78401 – Started review via action command
