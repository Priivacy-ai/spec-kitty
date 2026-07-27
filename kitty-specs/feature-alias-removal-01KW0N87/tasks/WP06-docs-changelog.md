---
work_package_id: WP06
title: Docs and CHANGELOG updates (FR-010)
dependencies:
- WP05
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/feature-alias-removal
merge_target_branch: feat/feature-alias-removal
branch_strategy: Planning artifacts for this mission were generated on feat/feature-alias-removal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/feature-alias-removal unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
agent: claude
shell_pid: '2123913'
history:
- timestamp: '2026-06-26T00:56:06Z'
  agent: system
  action: Prompt generated via spec-kitty tasks
agent_profile: curator-carla
authoritative_surface: docs/
create_intent: []
execution_mode: code_change
owned_files:
- docs/status-model.md
- docs/reference/environment-variables.md
- docs/reference/orchestrator-api.md
- docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md
- CHANGELOG.md
role: curator
tags: []
---

# Work Package Prompt: WP06 – Docs and CHANGELOG updates (FR-010)

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Remove all stale `--feature` references from live CLI-usage documentation. Mark the
`SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` environment variable as now inert. Add a CHANGELOG
unreleased entry for the `--feature` alias removal.

**Files in scope:**
- `docs/status-model.md`
- `docs/reference/environment-variables.md`
- `docs/reference/orchestrator-api.md`
- `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md`
- `CHANGELOG.md`

**Explicitly excluded (do NOT update):**
- `docs/migration/feature-flag-deprecation.md` — this file is excluded from the terminology
  scan by existing guard configuration. Its job is to document the deprecated `--feature` form.
  Do NOT claim in this file that `--feature` is "fully gone" — the migration note's role is to
  name the deprecated form for users migrating from it.

---

## Context

**Terminology guard** (from plan.md D-04 / research.md Table 4):
- `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` env var previously suppressed `--feature`
  deprecation warnings. After WP01-WP03, those warnings are never emitted on any in-scope
  command. The env var check in `selector_resolution.py` is NOT removed (that file is
  out of scope), but the variable is effectively inert for the 8 in-scope commands.
- Update the env var reference doc to note it is now inert rather than delete it.

**Scan approach**: Before editing, search for `--feature` in each target file:
```bash
grep -n "\-\-feature" \
  docs/status-model.md \
  docs/reference/environment-variables.md \
  docs/reference/orchestrator-api.md \
  "docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md" \
  CHANGELOG.md
```
Only update the occurrences found. Do not blanket-replace if there are none.

---

## Subtask T025 — Update `docs/status-model.md`

**Purpose**: Remove or rewrite any live-usage example in `status-model.md` that shows
`--feature` as an accepted flag on a user-facing command.

**Steps:**
1. Open `docs/status-model.md`.
2. Search for `--feature` occurrences.
3. For each occurrence:
   - If in a CLI example showing `spec-kitty <command> --feature <slug>`: change to
     `spec-kitty <command> --mission <slug>`.
   - If in a historical note explaining migration: leave it as-is (migration docs are exempt).
   - If in a code block showing the flag was removed (e.g., a diff): leave as-is.
4. Save the file.

**Validation:**
- `grep "\-\-feature" docs/status-model.md` → 0 live-usage example matches (comments/migration
  notes may remain if clearly labeled historical).

---

## Subtask T026 — Update `docs/reference/environment-variables.md`

**Purpose**: Mark `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` as now inert after this release.
The env var check in `selector_resolution.py` is retained (out of scope), but it is never
triggered by any of the 8 in-scope commands post-cleanup.

**Steps:**
1. Open `docs/reference/environment-variables.md`.
2. Find the entry for `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION`.
3. Update the description to note: "This variable is now inert. The `--feature` alias has been
   hard-removed from all user-facing commands as of this release. No deprecation warnings are
   emitted; this variable has no effect."
4. Do NOT delete the entry — operators may have this set in their environment and need to know
   it is no longer needed.
5. If `--feature` appears as a live-usage example anywhere else in this file, update to
   `--mission`.

**Validation:**
- The `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` entry clearly states it is inert.
- `grep "\-\-feature" docs/reference/environment-variables.md` → 0 live-usage examples
  (the env var name itself is fine to retain).

---

## Subtask T027 — Update `docs/reference/orchestrator-api.md`

**Purpose**: Remove `--feature` from any option lists, parameter tables, or usage examples
in the orchestrator API reference docs.

**Steps:**
1. Open `docs/reference/orchestrator-api.md`.
2. Search for `--feature` occurrences.
3. For each occurrence in an option list or parameter table: remove the row or update it
   to note the flag has been removed.
4. For each occurrence in a code example showing `--feature`: update to `--mission`.
5. For any prose explaining that `--feature` is still available: update to note it has been
   removed.

**Validation:**
- `grep "\-\-feature" docs/reference/orchestrator-api.md` → 0 matches (or only clearly-labeled
  historical references).

---

## Subtask T028 — Update `pedro-command-drift.md` engineering note

**Purpose**: The engineering note at
`docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md` documents known
command-drift issues for the `implement` command. Update the `implement` opts section to
remove `--feature` from the documented option list.

**Steps:**
1. Open `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md`.
2. Search for `--feature` occurrences.
3. In the `implement` opts section (or equivalent), remove `--feature` from the listed options.
4. If there is a "known aliases" or "deprecated options" section, update it to reflect
   `--feature` is now fully removed (not just hidden).
5. Leave the historical context about WHY the drift occurred — just remove the flag from
   current option listings.

**Validation:**
- `grep "\-\-feature" "docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md"` → 0
  live-usage matches.

---

## Subtask T029 — Add CHANGELOG.md unreleased entry

**Purpose**: Record the `--feature` alias hard-removal in the CHANGELOG so users, operators,
and other contributors know this breaking change happened.

**Steps:**
1. Open `CHANGELOG.md`.
2. Find or create the `## [Unreleased]` section.
3. Under `### Breaking Changes` (or `### Removed`), add an entry:
   ```markdown
   - **Removed**: Hidden `--feature` alias hard-removed from 8 user-facing CLI commands
     (`implement`, `merge`, `next`, `research`, `context`, `accept`,
     `lifecycle plan`, `lifecycle tasks`, `mission-type current`).
     Passing `--feature` on any of these commands now yields exit code 2 with
     "No such option: --feature". Use `--mission` instead. (#1060)
   ```
4. Under `### Fixed` (or `### Changed`), optionally add:
   ```markdown
   - **Fixed**: No-selector guard on all 8 commands now exits with code 2 and a readable
     error message instead of a potential `TypeError` traceback.
   ```

**Validation:**
- `CHANGELOG.md` unreleased section contains the `--feature` removal entry.
- Entry references issue #1060.

---

## Branch Strategy

```
planning branch: feat/feature-alias-removal
merge target:    feat/feature-alias-removal
depends on:      WP05 (all code changes and tests must be in place first)
```

---

## Definition of Done

- [ ] `grep "\-\-feature" docs/status-model.md docs/reference/environment-variables.md docs/reference/orchestrator-api.md "docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md"` → 0 live-usage matches.
- [ ] `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` doc entry notes it is now inert.
- [ ] `CHANGELOG.md` unreleased section has the removal entry with issue #1060 reference.
- [ ] `docs/migration/feature-flag-deprecation.md` is NOT modified.
- [ ] `pytest tests/contract/test_terminology_guards.py -v -k "live_first_party_docs"` passes.

## Risks

- Do not accidentally update `docs/migration/feature-flag-deprecation.md` — the guard excludes
  it from scanning, but it must still correctly document the deprecated form for migration users.
- CHANGELOG format must match the existing sections (headers, date format, issue reference style).
  Look at recent CHANGELOG entries for the correct format before writing.

## Reviewer Guidance

1. Confirm no live-usage example in the 4 target docs still shows `--feature`.
2. Confirm `docs/migration/feature-flag-deprecation.md` is untouched.
3. Confirm the CHANGELOG entry is in the `[Unreleased]` section, not a versioned section.
4. Confirm the env var doc entry explicitly says "inert" rather than silently removing the variable.
