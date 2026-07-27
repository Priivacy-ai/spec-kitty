---
work_package_id: WP02
title: Prose / help / docstring disambiguation sweep
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-011
tracker_refs: []
planning_base_branch: feat/terminology-primary-merge-disambiguation
merge_target_branch: feat/terminology-primary-merge-disambiguation
branch_strategy: Planning artifacts for this mission were generated on feat/terminology-primary-merge-disambiguation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/terminology-primary-merge-disambiguation unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Vocabulary
assignee: ''
agent: "claude"
shell_pid: "1187852"
shell_pid_created_at: "1784230860.93"
history:
- at: '2026-07-16T18:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/agent/mission_accept_merge.py
- docs/adr/3.x/2026-06-24-2-write-branch-resolution-primary-anchor.md
- CLAUDE.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Prose / help / docstring disambiguation sweep

## ⚡ Do This First: Load Agent Profile
Load `implementer-ivan` via `/ad-hoc-profile-load`.

## Objectives & Success Criteria
- Reword conflating **prose** to name the specific sense — NO identifier/flag/enum rename (occurrence_map `user_facing_strings: rename_if_user_visible`, `cli_commands: do_not_change`).
- Condense `CLAUDE.md`'s 3 defensive "primary/merge" warnings into ONE glossary pointer that STILL names the partition-vs-branch footgun (FR-011 — do not silently drop the tripwire).

## Context & Constraints
- Depends on WP01 (glossary entries to cross-reference).
- EXEMPT: `MergeStrategy` literals `merge/squash/rebase`, the `merge` command name, all flag names — clarify only their help *text*.
- Edge case: if a `--help` string is asserted byte-exact in a test, update the assertion in lockstep OR treat the string as a stable contract.
- **C-006**: merge-step doctrine prompts live under `src/doctrine/missions/mission-steps/` which `mission-step-authority` is restructuring — coordinate/defer T009 if it collides.

## Subtasks & Detailed Guidance
### T005 – `cli/commands/merge.py` help/docstrings — name Sense 1 (consolidate) vs Sense 2 (integrate); strategy literals unchanged.
### T006 – `mission_accept_merge.py` accept→merge help (`--target`/`--push`/`--keep-branch`) — `--push` = Sense 3 (publish to origin).
### T007 – ADR `2026-06-24-2` conflating paragraph — sentence-level rewrite (mixed-sense: qualify each "primary" to partition/branch/checkout/target).
### T008 – `CLAUDE.md` — 3 warnings → 1 glossary cross-reference naming the footgun (FR-011).
### T009 – merge-step doctrine prompts — **DEFERRED (do NOT implement as part of this WP).** These live under `src/doctrine/missions/mission-steps/` which in-flight `mission-step-authority-01KXNZMT` is actively restructuring (C-006), and those files are NOT in this WP's `owned_files`. Land this WP without T009; file a follow-up to clarify the merge-step prompts AFTER `mission-step-authority` merges (then the paths are stable and ownable). If the operator wants T009 in-scope now, add the specific `mission-steps/*/prompt.md` paths to owned_files and confirm land-order first.

## Test Strategy
- Terminology guard proven to execute (#2701); no exempt string-literal test red. Run touched-module tests + `ruff`.

## Risks & Mitigations
- Silent test red on a pinned help string → grep tests for the string before editing.

## Review Guidance
- Confirm zero flag/enum/command renames; footgun still named in CLAUDE.md.

## Activity Log
- 2026-07-16T18:15:00Z – system – Prompt created.
- 2026-07-16T19:23:29Z – claude – shell_pid=1126696 – Assigned agent via action command
- 2026-07-16T19:37:06Z – claude – shell_pid=1126696 – Prose/help/docstring sweep done (T005-T008). T009 DEFERRED per C-006: merge-step doctrine prompts under src/doctrine/missions/mission-steps/ are being restructured by in-flight mission-step-authority-01KXNZMT and are not in WP02 owned_files. Forced past subtask-completeness gate — T009 honestly unchecked, tracked as a mission-close follow-up. Also flagged: merge one-liner docstring 'Merge a lane-based feature into its target branch.' carries legacy 'feature' but is a golden pin owned by mission #2057 (test_merge_cli_golden) — left byte-exact, follow-up.
- 2026-07-16T19:41:07Z – claude – shell_pid=1187852 – Started review via action command
- 2026-07-16T19:41:59Z – user – shell_pid=1187852 – APPROVED (T009 honestly unchecked — deferred per C-006, NOT marked done). FR-003: all 4 owned surfaces name the specific sense; zero flag/enum/command renames (added flag tokens == removed byte-exact; MergeStrategy + golden one-liner 'Merge a lane-based feature into its target branch.' untouched). FR-011: footgun still named (partition-vs-branch + consolidate-vs-publish) in AGENTS.md Terminology Canon; no-direct-push + coord/primary routing intact. Exempt identifiers byte-exact. Gates green: ruff clean, test_merge_cli_golden + test_no_legacy_terminology (12) + test_mission_accept_merge (9) pass. T009 deferral ACCEPTED: mission-steps prompts unowned + contended by in-flight mission-step-authority-01KXNZMT; forced past subtask gate to preserve honest unchecked state (not falsely marked done). Mission-close follow-up required.
