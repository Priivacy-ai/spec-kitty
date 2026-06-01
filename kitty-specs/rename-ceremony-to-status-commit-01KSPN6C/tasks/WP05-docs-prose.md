---
work_package_id: WP05
title: Docs Prose + F-09 Config Flag Rewrite
dependencies: []
requirement_refs:
- FR-001
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rename-ceremony-to-status-commit-01KSPN6C
base_commit: 6a553f0a7841a3e2c17652192160cd11af4bfcfa
created_at: '2026-06-01T07:34:31.067102+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 1 - Foundation
agent: claude
shell_pid: '61077'
history:
- at: '2026-05-28T07:11:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/
execution_mode: code_change
owned_files:
- docs/development/org-doctrine-layer-architecture-review.md
- docs/development/3-2-publication-checklist.md
- docs/engineering_notes/reflections/README.md
- docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 — Docs Prose + F-09 Config Flag Rewrite

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

Scope governance context to terminology curation before reading anything else. This WP rewrites docs prose including a config-flag name rewrite in an engineering-notes finding — load the curator profile so canonical-term enforcement applies.

---

## Objective

Rewrite 7 occurrences in 4 `docs/` files. Mix of commit-class and workflow-sense per occurrence_map. The F-09 engineering finding (`2026-05-24-mission-01KSAF14-orchestration-findings.md`) contains 5 occurrences including the proposed config-flag name `vcs.allow_ceremony_commits_on_target_branch` — rewrite to `vcs.allow_status_commits_on_target_branch` per spec FR-010. **Plan-time verification confirmed the flag does not exist in live code**, so this WP is the only place that name appears in the repo.

## Context

- **Spec anchors**: [FR-001](../spec.md#functional-requirements), [FR-009](../spec.md#functional-requirements), [FR-010](../spec.md#functional-requirements).
- **Occurrence-map entries**: `dd-007` through `dd-014`.
- **Coordination note with WP02**: The F-09 finding doc at line 264 quotes the live error string. The quote currently reads `"Run ceremony write operations..."`; the post-rename quote in this WP should match the post-WP02 canonical `"Run status commit operations..."`. If WP05 lands before WP02 merges, the quote briefly references a string that doesn't exist yet — acceptable, they land in the same PR.

## Subtask Detail

### T019 — `docs/development/org-doctrine-layer-architecture-review.md` line 481

**Current**:

```
2. **Policy-vs-mechanism asymmetry.** The charter contains policy ("terminology canon", "regression vigilance rules", "code reviewers MUST grep for X"). The framework lacks mechanism — there is no `spec-kitty agent action review` step that calls a terminology linter, no `/spec-kitty.analyze` pass that diffs against the charter's `Terminology Canon` section. The reviewer profile loads directive 032 *because directive 032 exists in the doctrine catalog*, but the review prompt template does not render it as a checklist item. Policy without mechanism degrades to ceremony.
```

**Replacement** (occurrence_map `dd-007` — workflow-sense English idiom):

```
2. **Policy-vs-mechanism asymmetry.** The charter contains policy ("terminology canon", "regression vigilance rules", "code reviewers MUST grep for X"). The framework lacks mechanism — there is no `spec-kitty agent action review` step that calls a terminology linter, no `/spec-kitty.analyze` pass that diffs against the charter's `Terminology Canon` section. The reviewer profile loads directive 032 *because directive 032 exists in the doctrine catalog*, but the review prompt template does not render it as a checklist item. Policy without mechanism degrades to performative gesture.
```

Note: the English idiom "degrades to ceremony" means "becomes empty ritual". Mechanical substitution to "status commit" would change the meaning entirely. Approved rewrite by decision `01KSPP3SSZ5GKHTTB1C9EJQ13V`.

### T020 — `docs/development/3-2-publication-checklist.md` line 210

**Current**:

```
| **S8** Plan-only gate respected | All planning WPs (specify/plan/tasks ceremony) — satisfied at planning, locked by C-001/C-002. | Audited via git-log path filter. |
```

**Replacement** (occurrence_map `dd-008` — workflow-sense):

```
| **S8** Plan-only gate respected | All planning WPs (specify/plan/tasks workflow) — satisfied at planning, locked by C-001/C-002. | Audited via git-log path filter. |
```

### T021 — `docs/engineering_notes/reflections/README.md` line 12

**Current**:

```
- Observations about how Spec Kitty's own ceremony surfaces interact with the project's protected-branch / pre-commit / CI configuration.
```

**Replacement** (occurrence_map `dd-009` — commit-class):

```
- Observations about how Spec Kitty's own status commit surfaces interact with the project's protected-branch / pre-commit / CI configuration.
```

### T022 — `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md` — 5 occurrences

This is the F-09 finding doc. All 5 edits are in the same section.

**Line 257** (occurrence_map `dd-010` — commit-class heading):

Current:

```
## F-09 — Protected-branch guard blocks ceremony writes even from authorised operators on solo forks
```

Replacement:

```
## F-09 — Protected-branch guard blocks status commits even from authorised operators on solo forks
```

**Line 264** (occurrence_map `dd-011` — commit-class; this is a quote of the live error string):

Current:

```
Run ceremony write operations from the mission lane branch/worktree.
```

Replacement:

```
Run status commit operations from the mission lane branch/worktree.
```

(Matches the post-WP02 canonical string in `commit_helpers.py:159`.)

**Line 272** (occurrence_map `dd-012` — workflow-sense):

Current:

```
**Why it matters.** The guard forces extra ceremony (manual `git commit`,
```

Replacement:

```
**Why it matters.** The guard forces extra workflow overhead (manual `git commit`,
```

**Line 277** (occurrence_map `dd-013` — commit-class):

Current:

```
**Workaround.** Every ceremony commit was authored manually via
```

Replacement:

```
**Workaround.** Every status commit was authored manually via
```

**Line 280** (occurrence_map `dd-014` — Rule R6, config-flag rename per FR-010):

Current:

```
**Follow-up candidate.** A config flag (`vcs.allow_ceremony_commits_on_target_branch: true`) opt-in for solo forks. Default off (current
```

Replacement:

```
**Follow-up candidate.** A config flag (`vcs.allow_status_commits_on_target_branch: true`) opt-in for solo forks. Default off (current
```

Confirmed at plan time: this flag does not exist in live code. Line 280 is the only place its name appears in the repository.

### T023 — Verify zero stragglers in `docs/`

```bash
grep -rn 'ceremony' docs/
```

Expected: **zero hits**. If any hit appears, classify per occurrence_map and apply the matching replacement.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution workspace: allocated per lane in `lanes.json` after `finalize-tasks`.
- Resolve via `spec-kitty agent context resolve --action implement --wp WP05 --mission rename-ceremony-to-status-commit-01KSPN6C --json`.

## Test Strategy

- No new tests. Docs are not executed.
- WP06 regression guard will assert no `ceremony` substring remains in `docs/` (and no `allow_ceremony_commits_on_target_branch` substring anywhere).
- Optionally inspect via `markdownlint` if installed.

## Definition of Done

- [ ] All 7 prose lines updated exactly per the replacement text above.
- [ ] Line 280 of the F-09 finding doc uses `vcs.allow_status_commits_on_target_branch` (matches FR-010).
- [ ] `grep -rn 'ceremony' docs/` returns zero hits.
- [ ] `grep -rn 'allow_ceremony_commits_on_target_branch' .` (whole repo) returns zero hits.
- [ ] No code, no other files modified — only the 4 docs markdown files in owned_files.

## Risks & Reviewer Guidance

- **Risk 1**: Implementer mechanically substitutes the English idiom at line 481 and loses the meaning. Mitigation: the line says "degrades to performative gesture" — verify the meaning of "becomes empty ritual" survived.
- **Risk 2**: Implementer leaves the old quote at line 264 because they think it's "just quoting history". Mitigation: spec FR-003 + WP02 establish the post-rename error string; the doc must match the new live string.
- **Risk 3**: Implementer overlooks the config-flag rewrite at line 280. Mitigation: the verification command `grep -rn 'allow_ceremony_commits_on_target_branch' .` is the gate.
- **Reviewer check 1**: Diff touches only the 4 files in owned_files.
- **Reviewer check 2**: Each edited line matches occurrence_map exactly.
- **Reviewer check 3**: Both verification greps return zero hits.

## References

- Spec: [../spec.md](../spec.md) — FR-001, FR-009, FR-010
- Plan: [../plan.md](../plan.md) — research item R2 (config-flag live state) + R4 (doctrine/docs rewording strategy)
- Decision: [../decisions/DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md](../decisions/DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md)
- Occurrence map: [../occurrence_map.yaml](../occurrence_map.yaml) — `dd-007` through `dd-014`
- Term-rename contract: [../contracts/term-rename-contract.md](../contracts/term-rename-contract.md) — Rules R1, R2, R6
