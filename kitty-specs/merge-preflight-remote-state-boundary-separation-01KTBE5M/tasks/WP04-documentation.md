---
work_package_id: WP04
title: Documentation
dependencies:
- WP02
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
agent: claude
history:
- date: '2026-06-05'
  author: spec-kitty.tasks
  note: Initial WP generation
agent_profile: curator-carla
authoritative_surface: AGENTS.md
execution_mode: code_change
owned_files:
- AGENTS.md
- CHANGELOG.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Remove the `AGENTS.md` guidance that advised users to use a PR-based workaround when local `main` is ahead of origin during merge. Add a `CHANGELOG.md` entry documenting the behaviour change introduced in this mission.

---

## Context

**WP02 must be merged before this WP starts** — confirms the behaviour change is in the codebase.

**The outdated guidance** lives in `AGENTS.md` in the "Branch Protection and CI" section (around line 412-418 per the research analysis). It currently says something like: "If `spec-kitty merge` blocks because local `main` is ahead of/diverged from `origin/main`, inspect before acting" and advises the "focused PR path" as a workaround. After WP02, local-ahead no longer blocks — the workaround note is obsolete.

---

## Subtask T012 — Remove Focused-PR-Path Workaround from `AGENTS.md`

**Purpose**: Eliminate misleading guidance that directed users to a workaround for a bug that no longer exists.

**File**: `AGENTS.md`

**Steps**:

1. Read the full "Branch Protection and CI" section (and any section in `AGENTS.md` that discusses what to do when `spec-kitty merge` blocks due to origin sync state).

2. Find the specific guidance about:
   - "local `main` is ahead of/diverged from `origin/main`"
   - "focused PR path" workaround for blocked merges
   - "inspect before acting" advice related to the origin sync preflight block

3. **Remove** the workaround-specific guidance. Preserve any adjacent content that is still accurate (e.g., the general instruction to "inspect before pushing directly to main" is still valid for `diverged` state when `--push` is used).

4. **Replace with accurate guidance** (brief, authoritative):
   ```
   `spec-kitty merge` (without `--push`) performs a purely local operation.
   It does not check or require origin sync. Run it freely regardless of
   whether local `main` is ahead of, behind, or diverged from `origin/main`.

   When using `spec-kitty merge --push`, if local `main` is diverged from
   origin, the push step will be blocked with remediation guidance. Rebase
   or use the focused-PR-branch escape hatch in that case.
   ```

5. Search for any other references in `AGENTS.md` to "TARGET_BRANCH_NOT_SYNCHRONIZED", "ahead", "focused PR path", or "origin sync" in the context of merge guidance. Update or remove as appropriate.

**Validation**: After edit, no paragraph in `AGENTS.md` instructs users to use a workaround for a non-push `spec-kitty merge` blocked by origin sync state.

---

## Subtask T013 — Add `CHANGELOG.md` Entry

**Purpose**: Document the user-visible behaviour change for operators and contributors.

**File**: `CHANGELOG.md`

**Steps**:

1. Read `CHANGELOG.md` to understand the format (version headers, categories, entry style).

2. Find or create the appropriate version entry (the current development version or an `[Unreleased]` section).

3. Add an entry under a `Fixed` or `Changed` category:

   ```markdown
   ### Fixed

   - `spec-kitty merge` (without `--push`) no longer checks or requires origin
     sync before performing local lane integration. A local target branch that
     is ahead of, behind, or diverged from its remote tracking branch does not
     block a local-only merge. This resolves issue #1706 where users with
     accumulated orchestration commits on local `main` could not run
     `spec-kitty merge` until they pushed to origin first.

   - Push-safety checks now fire only when `--push` is requested, and only
     immediately before the push step. The `"diverged"` state continues to
     block a push with remediation guidance. `"ahead"` and `"behind"` states
     do not block a push (git handles those cases directly).

   - `MergeState` now persists `push_requested` for correct resume semantics:
     a resumed merge respects the original invocation's push intent without
     requiring re-specification of `--push`.
   ```

4. Format the entry to match surrounding CHANGELOG style (some projects use bullet points, some use paragraph form — match the existing format).

**Validation**: Entry is present in CHANGELOG.md, references #1706, and accurately describes the three changes (local merge no longer blocked; push check only on push; MergeState.push_requested).

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`

To start: `spec-kitty agent action implement WP04 --agent claude --mission merge-preflight-remote-state-boundary-separation-01KTBE5M`

---

## Definition of Done

- [ ] `AGENTS.md` no longer advises the focused-PR-path workaround for non-push merges blocked by origin sync state
- [ ] `AGENTS.md` accurately describes: local merge is network-free; push-safety check fires only on `--push`
- [ ] `CHANGELOG.md` has an entry referencing issue #1706 covering all three behaviour changes
- [ ] `CHANGELOG.md` entry is in the correct version section and matches the file's formatting conventions

## Risks

- **Over-removal**: Do not remove the diverged-state guidance for `--push` invocations. That guidance is still accurate and useful.
- **CHANGELOG version placement**: If there is no `[Unreleased]` section and the current version is not obvious from the file header, add the entry under the most recent version section with a note that it is new in the next release.
