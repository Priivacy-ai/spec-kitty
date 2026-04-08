---
work_package_id: WP07
title: Agent-Facing Docs and Top-Level Project Docs Cleanup
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-022
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: docs/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- docs/**
- README.md
- CONTRIBUTING.md
- CHANGELOG.md
priority: P0
tags: []
---

# WP07 — Agent-Facing Docs and Top-Level Project Docs Cleanup

## Objective

Update every live `docs/**` file (excluding `docs/migration/**` which is owned by WP08) and the top-level project files (`README.md`, `CONTRIBUTING.md`, and the **Unreleased section** of `CHANGELOG.md`) that teach legacy selectors. The verified drift sites are:

- `docs/explanation/runtime-loop.md` (cited in spec §8.1)
- `README.md:883` (legacy `--feature` example block)
- `README.md:910` (`--feature <slug>` documented as a live option for `spec-kitty accept`)

This is FR-010 + FR-022 from the spec.

## Context

**Critical scope rule (FR-022, C-011)**:
- ✅ **In scope**: `docs/**` (excluding `docs/migration/**`), top-level `README.md`, top-level `CONTRIBUTING.md`, and the **Unreleased section only** of top-level `CHANGELOG.md`.
- ❌ **Out of scope**: `kitty-specs/**`, `architecture/**`, `docs/migration/**` (owned by WP08), `.kittify/**`.

The Unreleased section of `CHANGELOG.md` is the portion above the first `## [<version>]` heading. Historical version entries are explicitly excluded by FR-022's "CHANGELOG-style historical entries" carve-out and by C-011 (no rewriting historical artifacts).

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP07` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T028 — Update `docs/explanation/runtime-loop.md` [P]

**Purpose**: Replace legacy selector teaching in the canonical runtime-loop explanation doc.

**Steps**:
1. Open `docs/explanation/runtime-loop.md`.
2. Read the file in full to understand context — this doc explains the runtime loop and uses CLI examples.
3. Find every reference to `--mission-run` or `--feature` and classify each:
   - Tracked-mission selection → change to `--mission`
   - Runtime/session selection → leave alone
4. Update prose explanations and command-line examples to use `--mission`.
5. **Critical**: do not delete any genuine runtime/session usage of `--mission-run` (the doc is about the runtime loop, so legitimate runtime references may exist).

### T029 — Audit and fix other live `docs/**` drift

**Purpose**: Find any other live `docs/**` file that teaches legacy selectors.

**Steps**:
1. Run a targeted grep:
   ```bash
   grep -rn "mission-run\|--feature" docs/ 2>/dev/null
   ```
2. **Do not** include `docs/migration/**` in this scan (those are the deprecation docs themselves, owned by WP08).
3. For each match in a live `docs/**` file, classify and fix as in T028.
4. `docs/reference/event-envelope.md` and `docs/reference/orchestrator-api.md` may also be touched by WP13, but WP07 is still responsible for removing live legacy selector teaching anywhere under `docs/**`. Coordinate rather than deferring the drift.
5. Re-run the grep until it returns zero unjustified matches in live `docs/**`.

### T030 — Clean up `README.md:883` (legacy `--feature` example block) [P]

**Purpose**: Remove the verified drift at `README.md` line 883.

**Steps**:
1. Open `README.md` and locate line ~883:
   ```markdown
   # Accept mission (legacy `--feature` flag name)
   spec-kitty agent mission accept --json
   ```
2. **Action**: remove the "(legacy `--feature` flag name)" parenthetical from the comment. The example itself uses no flags so the canonical command is unchanged. The cleaned-up version:
   ```markdown
   # Accept mission
   spec-kitty agent mission accept --json
   ```
3. If there are other example blocks nearby that teach `--feature` for tracked-mission selection, replace `--feature` with `--mission` in those examples.

### T031 — Clean up `README.md:910` (`--feature` row in Options table) [P]

**Purpose**: Remove the verified drift at `README.md` line 910.

**Steps**:
1. Open `README.md` and locate the `### \`spec-kitty accept\` Options` section (around line 906+).
2. The current Options table has a row at line 910:
   ```markdown
   | `--feature <slug>` | Mission slug to accept. Legacy flag name retained as a software-dev compatibility alias. |
   ```
3. **Action**: replace this row with:
   ```markdown
   | `--mission <slug>` | Mission slug to accept |
   ```
4. **Critical**: this row is the **most visible terminology drift** in the entire repo. Removing it satisfies the spec's "no canonical doc teaches `--feature` as a usable option" requirement.
5. If there are other rows in this Options table or in other Options tables in the README that document `--feature` for tracked-mission selection, replace them too.

### T032 — Audit `CONTRIBUTING.md` and `CHANGELOG.md` Unreleased section [P]

**Purpose**: Confirm there is no live drift in the other two top-level files.

**Steps**:
1. **CONTRIBUTING.md** — full-file scan:
   ```bash
   grep -n "mission-run\|--feature" CONTRIBUTING.md
   ```
   For each match, classify and fix.

2. **CHANGELOG.md** — Unreleased section ONLY (above the first `## [<version>]` heading):
   ```bash
   awk '/^## \[[0-9]+\.[0-9]+\.[0-9]+/{exit} {print}' CHANGELOG.md > /tmp/changelog-unreleased.md
   grep -n "mission-run\|--feature" /tmp/changelog-unreleased.md
   ```
   For each match in the Unreleased section, classify and fix.

   **Critical**: the historical version entries (e.g., `CHANGELOG.md:172` cited in the reviewer feedback as `--mission-run as canonical CLI flag — added as alias for --feature`) are **explicitly out of scope**. Do not modify them. They are append-only history.

3. If `CONTRIBUTING.md` and `CHANGELOG.md` Unreleased are clean (no matches), document that finding in the WP completion notes — the audit was performed and the files are confirmed clean.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `docs/explanation/runtime-loop.md` | MODIFY | Verified drift site |
| Other files under `docs/**` | MODIFY (as needed) | Per T029 audit; exclude `docs/migration/**` |
| `README.md` | MODIFY | Lines 883 and 910 (verified) + any others found |
| `CONTRIBUTING.md` | MODIFY (if drift found) | Full-file scan |
| `CHANGELOG.md` | MODIFY (if drift in Unreleased section only) | Historical entries excluded |

**Out of bounds (do not modify)**:
- `kitty-specs/**` (other than `077-mission-terminology-cleanup/`)
- `architecture/**`
- `docs/migration/**` (owned by WP08)
- `.kittify/**`
- Any historical version section of `CHANGELOG.md` (below the first `## [<version>]` heading)

## Definition of Done

- [ ] `docs/explanation/runtime-loop.md` no longer teaches `--mission-run` for tracked-mission selection
- [ ] T029 audit returns zero unjustified matches across live `docs/**` (excluding `docs/migration/**`)
- [ ] `README.md:883` legacy comment is cleaned up
- [ ] `README.md:910` Options table row uses `--mission`, not `--feature`
- [ ] Any other drift in `README.md` is fixed
- [ ] `CONTRIBUTING.md` is audited and clean (or fixed)
- [ ] `CHANGELOG.md` Unreleased section is audited and clean (or fixed)
- [ ] No file under `kitty-specs/**`, `architecture/**`, `docs/migration/**`, or `.kittify/**` is modified
- [ ] `CHANGELOG.md` historical version entries (below the first `## [<version>]` heading) are unchanged
- [ ] No broken internal links in updated docs (NFR-004)

## Risks and Reviewer Guidance

**Risks**:
- README.md is large (~900+ lines). Use targeted edits for the verified drift sites; do not rewrite unrelated sections.
- A `docs/**` file may legitimately mention `--mission-run` for runtime/session context. Distinguish by reading the surrounding sentence.
- Accidentally editing `kitty-specs/**` historical artifacts is the most likely scope violation. C-011 forbids this absolutely. Check git diff before committing.
- The CHANGELOG.md Unreleased section may not exist (the file may go straight to historical entries). If so, T032 is a no-op for CHANGELOG.

**Reviewer checklist**:
- [ ] All edits are in `docs/**` (excluding `docs/migration/**`), `README.md`, `CONTRIBUTING.md`, or the Unreleased section of `CHANGELOG.md`
- [ ] No edits in `kitty-specs/**`, `architecture/**`, `docs/migration/**`, or historical CHANGELOG sections
- [ ] README.md verified drift sites at lines 883 and 910 are both fixed
- [ ] Internal links in modified files are not broken
- [ ] git diff shows the expected files only

## Implementation Command

```bash
spec-kitty implement WP07
```

This WP depends on WP01. After WP01 is merged, WP07 can run in parallel with WP02, WP06, WP08.

## References

- Spec FR-010, FR-022, C-011
- Spec §8.1 — `docs/explanation/runtime-loop.md` cited as drift site
- Reviewer feedback (Finding 2 in this session): verified drift at `README.md:883`, `README.md:910`, and `CHANGELOG.md:172` (historical, out of scope)
- `quickstart.md` Step 7a/7b — line-by-line walkthrough

## Activity Log

- 2026-04-08T15:01:33Z – unknown – Done override: Mission completed in main checkout
