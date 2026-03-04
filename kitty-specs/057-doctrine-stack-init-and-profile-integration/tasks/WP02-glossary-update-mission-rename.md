---
work_package_id: WP02
title: Glossary Update for Mission Rename
lane: done
dependencies: [WP01]
requirement_refs:
- FR-019
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
phase: Phase A - Pre-work
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-22T11:50:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator
---

# Work Package Prompt: WP02 – Glossary Update for Mission Rename

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

This WP depends on **WP01**. If WP01 was recently changed during review, rebase before starting:

```bash
cd .worktrees/057-doctrine-stack-init-and-profile-integration-WP02
git rebase 057-doctrine-stack-init-and-profile-integration-WP01
```

---

## Objectives & Success Criteria

- `Feature` entry in `glossary/contexts/orchestration.md` documents the `--feature` → `--mission` CLI flag deprecation.
- `--feature` CLI flag appears in `glossary/historical-terms.md` as a deprecated alias entry.
- Glossary integrity check passes (no broken cross-references).
- Requirements FR-019 and SC-008 are satisfied.
- No source code changes — documentation only.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-A2
- **Spec**: FR-019, SC-008, US-7
- **Phase A gate**: This WP completes Phase A. Both WP01 and WP02 must be reviewed and merged before Phase B (WP03) begins.
- **Start command**: `spec-kitty implement WP02 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T006 – Update `Feature` entry in `glossary/contexts/orchestration.md`

- **Purpose**: The canonical glossary entry for `Feature` must document that `--feature` is deprecated as a CLI flag, with `--mission` as the replacement. This ensures any agent or user consulting the glossary understands the current state.
- **Files**: `glossary/contexts/orchestration.md`
- **Steps**:
  1. Read `glossary/contexts/orchestration.md`. Find the `Feature` term entry (or the section describing the feature concept).
  2. Add a "CLI Flag" note under the term:
     ```
     **CLI Flag (deprecated)**: The `--feature` flag is deprecated as of version 2.2.0. The canonical flag is now `--mission`. `--feature` remains a backward-compatible alias for one deprecation cycle and emits a deprecation warning when used. See `glossary/historical-terms.md` for the deprecated alias entry.
     ```
  3. If the entry already mentions `--feature`, update rather than append (no duplicates).
  4. Keep the entry format consistent with neighbouring entries in the file.

### Subtask T007 – Add `--feature` deprecated alias entry in `glossary/historical-terms.md`

- **Purpose**: Deprecated aliases live in `historical-terms.md` so that automated tooling and contributors know what is superseded and when.
- **Files**: `glossary/historical-terms.md`
- **Steps**:
  1. Read `glossary/historical-terms.md`. Study the format of existing deprecated entries.
  2. Add an entry following the existing pattern, for example:
     ```markdown
     ## `--feature` (deprecated CLI flag)

     **Superseded by**: `--mission`
     **Deprecated in**: 2.2.0
     **Removal planned**: 3.0.0 (one deprecation cycle)
     **Rationale**: The `--feature` flag used the legacy "feature" terminology. The canonical mission-oriented terminology uses `--mission` to align with the spec-kitty glossary. The flag emits a deprecation warning when used and will be removed in a future major release.
     **Cross-reference**: `glossary/contexts/orchestration.md#Feature`
     ```
  3. If no existing deprecated entries exist, create a new section `## Deprecated Aliases` and add the entry there.

### Subtask T008 – Run glossary integrity check

- **Purpose**: Validate that no cross-references are broken and no existing terms were accidentally altered.
- **Files**: No file changes — this is a verification step.
- **Steps**:
  1. Run `spec-kitty agent feature check-prerequisites --feature 057-doctrine-stack-init-and-profile-integration --json` — look for any errors or warnings about glossary files.
  2. If a `spec-kitty glossary` or `spec-kitty constitution` check command exists, run it.
  3. Run `grep -rn "historical-terms\|orchestration" glossary/` to confirm any cross-references between glossary files are consistent.
  4. Open both modified files and do a final read-through for formatting consistency.

## Test Strategy

This WP contains only documentation changes. Validation is:

```bash
# Confirm Feature entry updated
grep -A 10 "feature.*deprecated\|--feature.*deprecated" glossary/contexts/orchestration.md

# Confirm historical-terms entry present
grep -A 5 "feature.*deprecated\|--feature" glossary/historical-terms.md

# Integrity check
spec-kitty agent feature check-prerequisites --feature 057-doctrine-stack-init-and-profile-integration --json
```

## Risks & Mitigations

- File format mismatch with existing entries → read existing entries first, match format exactly.
- Missing file: if `historical-terms.md` doesn't exist, create it with a brief header and the new entry.

## Review Guidance

- Confirm both files updated with consistent terminology ("deprecated", "superseded by").
- Confirm no existing glossary content was altered beyond the targeted additions.

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
