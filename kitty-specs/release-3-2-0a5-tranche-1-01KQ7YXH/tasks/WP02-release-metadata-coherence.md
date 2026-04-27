---
work_package_id: WP02
title: NFR-002 release metadata coherence (final consolidator)
dependencies:
- WP01
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
requirement_refs:
- NFR-002
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: claude
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: CHANGELOG.md
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- pyproject.toml
- CHANGELOG.md
role: implementer
tags:
- release-prep
- consolidator
---

# WP02 — NFR-002 release metadata coherence (final consolidator)

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, and bug-fixing-checklist tactic. Even though this WP is mostly metadata bumping, the release-prep tests verify executable invariants and a wrong version string can break downstream installs.

## Objective

Bring `pyproject.toml`, `CHANGELOG.md`, and the release-prep test fixtures into mutual agreement on the next prerelease state (`3.2.0a5`). Consolidate per-FR CHANGELOG entries that the other six WPs (WP01, WP03–WP07) noted in their PR descriptions but did NOT land themselves (CHANGELOG.md ownership belongs solely to this WP to avoid merge conflicts across parallel WPs).

## Context

`pyproject.toml::[project].version` is currently `3.2.0a4`. The parent stabilization epic ([#822](https://github.com/Priivacy-ai/spec-kitty/issues/822)) names this tranche as `3.2.0a5`. `CHANGELOG.md` heading is currently `## [Unreleased - 3.2.0]` (no alpha marker). The release-prep tests (`tests/release/test_dogfood_command_set.py`, `tests/release/test_release_prep.py`) treat metadata coherence as an executable invariant.

CHANGELOG ownership is centralized in this WP because the tranche is composed of seven parallel WPs that would otherwise produce CHANGELOG merge conflicts. Each implementer was asked to put a one-line "CHANGELOG entry candidate" in their PR description; this WP collects them.

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP **lands last**. Its execution worktree should be created AFTER WP01/WP03/WP04/WP05/WP06/WP07 have all merged into `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json`; the dependency declaration (`dependencies: [WP01, WP03, WP04, WP05, WP06, WP07]`) tells `lane_planner` to schedule this WP into a serial lane after the others.

## Subtasks

### T005 — Bump `pyproject.toml::[project].version` to `3.2.0a5`

**Purpose**: Shift the canonical version source so all downstream consumers (CLI banner, packaging, release tag) see the new prerelease.

**Files**:
- `pyproject.toml`

**Steps**:

1. Open `pyproject.toml`. Locate `[project]` table; find `version = "3.2.0a4"`.
2. Change to `version = "3.2.0a5"`.
3. Do NOT touch `requires-python` (`>=3.11` stays — coordinated with WP03's `.python-version` change).
4. Do NOT touch any other `[project]` field.

**Validation**:
- [ ] `grep '^version' pyproject.toml` prints exactly `version = "3.2.0a5"`.
- [ ] `uv run spec-kitty --version` prints `spec-kitty-cli version 3.2.0a5` after `uv sync --reinstall` (or your editable install equivalent).

### T006 — Split `CHANGELOG.md` heading into `[3.2.0a5]` + new `[Unreleased]`

**Purpose**: Carve a versioned section for the tranche and seed a fresh `[Unreleased]` section for the next tranche.

**Files**:
- `CHANGELOG.md`

**Steps**:

1. Open `CHANGELOG.md`. Find the heading `## [Unreleased - 3.2.0]` near the top.
2. Replace it with **two** headings, top to bottom:

   ```markdown
   ## [Unreleased]

   ### Added

   ### Changed

   ### Fixed

   ### Removed

   ## [3.2.0a5] — 2026-04-XX
   ```

   (Replace `XX` with the actual ship date when the PR for this WP is opened.)
3. Move the existing Added/Changed/Fixed/Removed bullet content from the old `[Unreleased - 3.2.0]` block into the new `[3.2.0a5]` block — those are real changes already in this tranche's parent commits.
4. Leave the new top-level `[Unreleased]` block empty (with the four sub-headings present but no bullets).

**Validation**:
- [ ] `head -30 CHANGELOG.md` shows `## [Unreleased]` first, then `## [3.2.0a5] — 2026-04-XX` second, then the Added/Changed/Fixed/Removed sub-blocks under `[3.2.0a5]` populated with the existing content.
- [ ] No content from before the tranche is deleted; only the heading is split.

### T007 — Consolidate per-FR CHANGELOG entries under `[3.2.0a5]`

**Purpose**: Roll up one-line candidates from each landed WP's PR description into the appropriate Added/Changed/Fixed/Removed section.

**Files**:
- `CHANGELOG.md`

**Steps**:

1. For each merged WP (WP01, WP03, WP04, WP05, WP06, WP07), open its PR description and copy the proposed CHANGELOG entry line.
2. File each line under the correct sub-heading inside `[3.2.0a5]`. Suggested mapping (verify against actual PR text):

   - **Fixed**:
     - `Fix \`spec-kitty upgrade\` silently leaving projects in PROJECT_MIGRATION_NEEDED state by stamping schema_version after metadata save (#705, WP01).`
     - `Suppress misleading "shutdown / final-sync" red error lines after a successful \`spec-kitty agent mission create --json\` payload (#735, WP06).`
     - `Deduplicate "Not authenticated, skipping sync" / "token refresh failed" diagnostics to at most once per CLI invocation (#717, WP06).`
     - `\`spec-kitty init\` in a non-git directory now prints an actionable "run \`git init\`" message (#636, WP05).`
   - **Changed**:
     - `Loosen \`.python-version\` from a hard \`3.13\` pin to \`3.11\` (the floor declared by \`pyproject.toml\`) and restore \`mypy --strict\` cleanliness on \`mission_step_contracts/executor.py\` (#805, WP03).`
   - **Removed**:
     - `Retire the deprecated \`/spec-kitty.checklist\` command surface from every supported agent's rendered output. The canonical requirements checklist at \`kitty-specs/<mission>/checklists/requirements.md\` is unaffected (#815, supersedes #635, WP04).`
   - **Internal** (or under Fixed if no Internal section is used):
     - `Add regression tests confirming \`--feature\` aliases stay hidden from \`--help\` while remaining accepted (#790, WP07).`
     - `Add regression test confirming \`spec-kitty agent decision\` command shape stays consistent across docs / help / skill snapshots (#774, WP07).`

3. Where a sub-heading would have no entries, leave it empty rather than removing it (consistency with prior versions).

**Validation**:
- [ ] Every issue from `start-here.md` (#805, #705, #815, #635, #636, #790, #774, #735, #717) appears at least once in the `[3.2.0a5]` block.
- [ ] No entry references a WP that did not actually land.

### T008 — Run release-prep tests; update fixtures if drifted

**Purpose**: The release-prep tests are the executable form of NFR-002.

**Files**:
- `tests/release/test_dogfood_command_set.py` (read; update fixtures only if the test points to a fixture file that hardcodes the version)
- `tests/release/test_release_prep.py` (same)

**Steps**:

1. Run: `PWHEADLESS=1 uv run --extra test python -m pytest tests/release/ -q`.
2. If a test fails because it greps for `3.2.0a4` in a fixture, update the fixture to the new version. Do NOT change test logic.
3. Re-run until green.

**Validation**:
- [ ] `pytest tests/release/ -q` exits 0.

### T009 — Verify `spec-kitty --version` reports `3.2.0a5`

**Purpose**: Final sanity check that the version bump propagated into the installed CLI.

**Steps**:

1. Run `uv sync --reinstall` (or `pip install -e .` if your dev environment uses that).
2. Run `spec-kitty --version`. Expect a banner ending with `spec-kitty-cli version 3.2.0a5`.
3. Run `uv run spec-kitty --version`. Expect the same.

**Validation**:
- [ ] Both invocations print `3.2.0a5`.
- [ ] Capture stdout in the PR description.

## Test Strategy

- `tests/release/` is the entire executable contract for this WP. Pass = done.

## Definition of Done

- [ ] T005–T009 complete.
- [ ] `pyproject.toml::[project].version == "3.2.0a5"`.
- [ ] `CHANGELOG.md` has `[Unreleased]` (empty) above `[3.2.0a5] — <date>` (populated).
- [ ] All nine tranche issues are referenced under `[3.2.0a5]`.
- [ ] `pytest tests/release/ -q` exits 0.
- [ ] `spec-kitty --version` reports `3.2.0a5`.

## Risks

- **R1**: A WP merged before this one slipped a CHANGELOG edit in by accident, creating a merge conflict. Mitigation: T006 reconciles by hand; assert no other WP has an entry under `[Unreleased]`.
- **R2**: Release-prep test fixtures may have multiple hardcoded version strings (one in pyproject snapshot, one in dogfood fixture, etc.). Address each; do not change the assertion logic.

## Reviewer Guidance

- Verify `[Unreleased]` is empty (with empty sub-headings) and `[3.2.0a5]` carries the actual content.
- Verify every tranche issue number appears at least once in `[3.2.0a5]`.
- Verify no per-WP CHANGELOG entries are duplicated across sub-headings.
- Verify the `requires-python` field in `pyproject.toml` was NOT touched (that's WP03's domain via `.python-version`).

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent claude
```
