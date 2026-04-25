---
work_package_id: WP03
title: Deprecation Header, Tasks Action Parity, Polish
dependencies:
- WP01
- WP02
requirement_refs:
- C-007
- C-008
- FR-010
- FR-011
- NFR-001
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-25T11:39:00+00:00'
subtasks:
- T010
- T011
- T012
- T013
history:
- at: '2026-04-25T11:39:00Z'
  actor: claude
  action: created
authoritative_surface: src/doctrine/missions/software-dev/
execution_mode: code_change
mission_slug: software-dev-composition-rewrite-01KQ26CY
owned_files:
- src/doctrine/missions/software-dev/mission-runtime.yaml
- src/doctrine/missions/software-dev/actions/tasks/guidelines.md
priority: P2
tags: []
---

# WP03 — Deprecation Header, Tasks Action Parity, Polish

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- WP03 depends on WP01 + WP02. By the time this WP runs, the live path for `software-dev` is already composition-driven, which is the precondition for the deprecation header to be truthful.

## Objective

Three things, none of which change executable behavior on its own:

1. Mark the legacy `mission-runtime.yaml` deprecated with a header comment so future readers know the live path moved to composition (per locked decision D-3).
2. Bring `actions/tasks/` to parity with the four sibling action directories by adding a `guidelines.md` mirroring the others.
3. Verify the slice landed cleanly: focused test sweep green, no out-of-scope file touches (C-007 boundary check).

## Context

Read first:
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/spec.md` — full spec, especially FR-010, FR-011, C-007, C-008
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/plan.md` — locked decision D-3
- `src/doctrine/missions/software-dev/mission-runtime.yaml` — file getting the header
- `src/doctrine/missions/software-dev/actions/specify/guidelines.md`, `…/plan/guidelines.md`, `…/implement/guidelines.md`, `…/review/guidelines.md` — siblings to mirror
- `src/doctrine/missions/software-dev/actions/tasks/index.yaml` — tasks-action governance scope (already correct)

Constraints active for this WP:
- **C-007**: DO NOT touch any file under `src/spec_kitty_events/` or `.kittify/charter/`. T013 verifies this hard.
- **C-008**: Do NOT touch any other mission's directory.
- **D-3 (plan)**: `mission.yaml` left fully untouched. Only `mission-runtime.yaml` gets the header.

## Subtasks

### T010 — Prepend deprecation header to `mission-runtime.yaml`

**Purpose**: Make it unambiguous to future readers that this template is no longer the authoritative source for action dispatch on `software-dev`.

**File**: `src/doctrine/missions/software-dev/mission-runtime.yaml` (modify — prepend comment block; do NOT change YAML body)

**Header content** (verbatim, prepended above the existing `# =====` banner):

```yaml
# DEPRECATED (since #503 / phase 6 wp6.2): this template is no longer the
# authoritative source for action dispatch on the built-in software-dev
# mission. The live runtime path is now driven by mission step contracts
# under src/doctrine/mission_step_contracts/shipped/ via
# StepContractExecutor + ProfileInvocationExecutor composition. This file
# is retained as a transitional reference and may be removed in a future
# slice. Do not extend it.
#
```

**Validation**:
- File still parses as valid YAML (header lines are pure comments).
- `head -10 src/doctrine/missions/software-dev/mission-runtime.yaml` shows the deprecation banner.
- No change to the YAML body.

### T011 — Create `actions/tasks/guidelines.md`

**Purpose**: Bring `actions/tasks/` to parity with `actions/specify/`, `actions/plan/`, `actions/implement/`, `actions/review/`, each of which has a `guidelines.md` describing the action's quality and authoring standards. The new file is loaded by the charter context bootstrap on `--action tasks` calls.

**File**: `src/doctrine/missions/software-dev/actions/tasks/guidelines.md` (new)

**Approach**:
1. Read `src/doctrine/missions/software-dev/actions/plan/guidelines.md` for tone, length, and structural template.
2. Author a parallel `tasks` guidelines file. Suggested sections (mirroring siblings):
   - **Core Authorship Rules** (1–3 bullets): use absolute paths, ERROR on dependency cycles or unresolved refs, mark `[NEEDS CLARIFICATION]` only on explicit deferral.
   - **Charter Compliance** (charter referenced; tasks must respect locality-of-change DIRECTIVE_024 and specification-fidelity DIRECTIVE_010).
   - **Subtask Granularity** (3–7 subtasks per WP, 200–500 line prompts; reference the mission's task-sizing rules).
   - **Dependency Hygiene** (every WP frontmatter has explicit `dependencies:`; no cycles; finalize-tasks validates).
   - **Phase Discipline** (this command produces tasks.md + tasks/WP##.md; it does NOT begin implementation).

**Length**: ≤80 lines, mirroring siblings. Do not pad.

**Validation**:
- File exists, ≤80 lines, parallels sibling structure.
- File is referenced via the charter context bootstrap when `spec-kitty charter context --action tasks --json` runs (no code change needed; the bootstrap looks up `actions/<action>/guidelines.md` automatically).

### T012 — Run focused tests + broader sweep

**Purpose**: Final regression check.

**Commands**:

```bash
cd src && pytest \
    tests/specify_cli/mission_step_contracts/ \
    tests/specify_cli/next/ \
    tests/specify_cli/runtime/ \
    -v
```

Then a broader sweep to catch any incidental breakage:

```bash
cd src && pytest tests/ -x --ignore=tests/regressions
```

**Validation**:
- Focused suite: 100% green.
- Broader sweep: no failures attributable to this slice. (Pre-existing flakies/skips noted but not blocking.)
- NFR-001 (≤±15% wall-clock): time the focused suite before and after; report in the WP review.

### T013 — C-007 boundary check

**Purpose**: Verify the slice did not touch any out-of-scope file.

**Command**:

```bash
git diff --name-only main..HEAD | grep -E '^(src/spec_kitty_events/|\.kittify/charter/)' && echo "BOUNDARY VIOLATION" || echo "C-007 boundary clean"
```

**Validation**:
- Output: `C-007 boundary clean`. Any file matched is a violation; root-cause and revert before declaring T013 done.
- Also report `git diff --stat main..HEAD` so the reviewer can scan the full slice surface.

## Definition of Done

- [ ] `src/doctrine/missions/software-dev/mission-runtime.yaml` first lines show the deprecation header.
- [ ] `src/doctrine/missions/software-dev/actions/tasks/guidelines.md` exists, ≤80 lines, mirrors sibling structure.
- [ ] Focused test suite (`mission_step_contracts/`, `next/`, `runtime/`) 100% green.
- [ ] Broader test sweep shows no slice-attributable failures.
- [ ] C-007 boundary check passes (no `spec_kitty_events/` or `.kittify/charter/` files touched).
- [ ] `git diff --stat main..HEAD` shows only files in the WP01/WP02/WP03 owned set.

## Reviewer Guidance

- Confirm the deprecation header is comments only — no YAML body change.
- Confirm `actions/tasks/guidelines.md` is structurally parallel to siblings (length within 50–80 lines; section headers match).
- Confirm `mission.yaml` is NOT modified (D-3).
- Confirm the C-007 boundary check command in T013 returned clean.

## Risks

| Risk | Mitigation |
|------|------------|
| Header inadvertently breaks YAML parsing | Reviewer to spot-check by parsing the file with `yaml.safe_load`; existing tests that parse the template will catch as well. |
| `actions/tasks/guidelines.md` over- or under-shoots sibling style | Follow the closest sibling (`plan/guidelines.md`) line-by-line in structure. Keep it short. |
| Broader test sweep surfaces a pre-existing flaky test | Note explicitly in the WP review whether the failure is slice-attributable; if not, do not block on it. |
| Touching `mission.yaml` by mistake | Strictly enforce that only `mission-runtime.yaml` is modified for the deprecation header. |

## Implementation command

`spec-kitty agent action implement WP03 --agent <your-agent-name>`
