---
work_package_id: WP06
title: Doctrine Skills Cleanup
dependencies:
- WP01
requirement_refs:
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: src/doctrine/skills/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- src/doctrine/skills/spec-kitty-runtime-next/SKILL.md
- src/doctrine/skills/spec-kitty-mission-system/SKILL.md
- src/doctrine/skills/spec-kitty-implement-review/SKILL.md
priority: P0
tags: []
---

# WP06 — Doctrine Skills Cleanup

## Objective

Update every live doctrine skill under `src/doctrine/skills/**` that teaches `--mission-run` for tracked-mission selection. Replace those instructions with `--mission`. Audit the rest of the skills directory for similar drift and fix any matches.

This is FR-009 from the spec.

## Context

The verified primary site is `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`. Spec §8.1 cites:
> `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` — instructs agents to use `--mission-run` for tracked-mission selection.

There may be additional skills with similar drift. The audit in T026 finds them.

**Critical scope rule (FR-022, C-011)**: this WP only modifies files under `src/doctrine/skills/**`. It does **not** modify:
- `kitty-specs/**` (historical mission artifacts)
- `architecture/**` (historical ADRs)
- `.kittify/**` (runtime state)
- `docs/**` (those are owned by WP07)

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP06` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T025 — Update `spec-kitty-runtime-next/SKILL.md`

**Purpose**: Replace every `--mission-run` instruction for tracked-mission selection with `--mission`.

**Steps**:
1. Open `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`.
2. Read the file in full first to understand the context — the skill teaches agents how to use `spec-kitty next`.
3. Find every reference to `--mission-run` and classify each:
   - **Tracked-mission selection** (e.g., `spec-kitty next --mission-run 077-foo`): change to `--mission`
   - **Runtime/session selection** (e.g., "to look up the running session by ID, use `--mission-run`"): leave unchanged
4. Replace every tracked-mission selection example. Common patterns:
   - `--mission-run <slug>` → `--mission <slug>`
   - `--mission-run 034-my-feature` → `--mission 034-my-feature`
   - `the --mission-run flag` (when context is tracked-mission) → `the --mission flag`
5. Update any prose explanation that says "`--mission-run` selects the active mission" to say "`--mission` selects the active mission".
6. **Do not** delete the runtime/session usage of `--mission-run` if it exists. Leave any genuine runtime examples alone.

### T026 — Audit other doctrine skills for similar drift

**Purpose**: Find other skill files in `src/doctrine/skills/**` that teach legacy selectors.

**Steps**:
1. Run a content grep:
   ```bash
   grep -rn "mission-run\|--feature" src/doctrine/skills/
   ```
2. For each match, classify:
   - Tracked-mission selection → drift, must fix in T027
   - Runtime/session selection → leave alone
   - Migration explanation (e.g., "`--feature` was the old name") → leave alone if it's accurate, fix the prose if it teaches it as current
3. Produce a list of files to fix in T027. Expected files (subject to audit):
   - `src/doctrine/skills/spec-kitty-mission-system/SKILL.md`
   - `src/doctrine/skills/spec-kitty-implement-review/SKILL.md`
   - Any others found

### T027 — Update any drifted doctrine skills found

**Purpose**: Apply the same fix from T025 to every additional file found in T026.

**Steps**:
1. For each file in the T026 list, repeat the T025 process: classify each occurrence and replace tracked-mission ones.
2. After each file is updated, re-run the grep:
   ```bash
   grep -n "mission-run\|--feature" <file>
   ```
   Expected: zero matches OR only matches in legitimate runtime/session or migration-history contexts.
3. Verify the meta-acceptance check:
   ```bash
   grep -rn "mission-run" src/doctrine/skills/ | grep -v "runtime\|session"
   ```
   Should return zero matches.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` | MODIFY | Primary verified drift site |
| `src/doctrine/skills/spec-kitty-mission-system/SKILL.md` | MODIFY (if found by audit) | Likely additional drift site |
| `src/doctrine/skills/spec-kitty-implement-review/SKILL.md` | MODIFY (if found by audit) | Likely additional drift site |

The owned_files list above includes the three most likely targets. If T026 finds additional files in `src/doctrine/skills/**`, they are within this WP's authoritative surface and may be modified — but **only files under `src/doctrine/skills/**`** (no docs, no specs, no charter).

## Definition of Done

- [ ] `spec-kitty-runtime-next/SKILL.md` no longer instructs `--mission-run` for tracked-mission selection
- [ ] T026 audit list is captured in the WP completion notes
- [ ] All files identified by T026 are updated
- [ ] `grep -rn "mission-run" src/doctrine/skills/ | grep -v "runtime\|session"` returns zero matches
- [ ] No file outside `src/doctrine/skills/**` is modified by this WP
- [ ] Internal links in updated skill files are not broken (NFR-004)

## Risks and Reviewer Guidance

**Risks**:
- A doctrine skill may legitimately mention `--mission-run` in a runtime/session context. Distinguish by reading the full sentence.
- Mass find-and-replace will incorrectly change runtime/session references. Each occurrence must be classified individually.
- If a skill file has internal links (e.g., `[--mission-run flag](#runtime-loop)`), those may break after the rename. Verify links after edits.

**Reviewer checklist**:
- [ ] T025 updates only tracked-mission references in `spec-kitty-runtime-next/SKILL.md`; runtime/session references untouched
- [ ] T026 audit list is documented
- [ ] Final grep returns zero unjustified matches
- [ ] No files outside `src/doctrine/skills/**` were touched
- [ ] No broken internal links in updated files

## Implementation Command

```bash
spec-kitty implement WP06
```

This WP depends on WP01. After WP01 is merged, WP06 can run in parallel with WP02, WP07, WP08.

## References

- Spec FR-009, FR-022
- Spec §8.1 — `spec-kitty-runtime-next/SKILL.md` cited as drift site
- WP01 audit (informs the T026 search)
