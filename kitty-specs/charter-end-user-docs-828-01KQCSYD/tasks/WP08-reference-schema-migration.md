---
work_package_id: WP08
title: Reference — Schema, Migration, Documentation Mission
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
- FR-013
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/
execution_mode: planning_artifact
owned_files:
- docs/reference/retrospective-schema.md
- docs/migration/from-charter-2x.md
- docs/explanation/documentation-mission.md
tags: []
---

# WP08 — Reference: Schema, Migration, Documentation Mission

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Write `retrospective-schema.md` and `from-charter-2x.md`; review and update `documentation-mission.md` for phase accuracy. These cover the retrospective YAML schema, migration from 2.x, and documentation mission phase alignment.

This WP can run in parallel with WP02–WP07 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP08 --agent <name>`; do not guess the worktree path

## Context

### Source of Truth

Before writing, gather current state:

```bash
# Check documentation mission phases
grep -r 'documentation' src/specify_cli/missions/documentation/ 2>/dev/null | head -30
# Or check mission-runtime.yaml directly
find src/ -name 'mission-runtime.yaml' 2>/dev/null
cat src/specify_cli/missions/documentation/mission-runtime.yaml 2>/dev/null || echo "NOT FOUND"

# Check retrospective schema
find src/ -name '*.yaml' | xargs grep -l 'retrospective' 2>/dev/null | head -10
uv run spec-kitty agent retrospect synthesize --help
uv run spec-kitty retrospect summary --help
```

**Critical rule**: Documentation mission phases in `documentation-mission.md` must match exactly what `mission-runtime.yaml` declares. Do not invent or elide phases.

### Migration Scope

The migration guide covers changes between 2.x and Charter-era 3.x that affect operators. Read `docs/2x/` content for what 2.x offered; compare to current CLI surface for what changed.

## Subtask Guidance

### T031 — Write docs/reference/retrospective-schema.md

**File**: `docs/reference/retrospective-schema.md`  
**Title**: "Retrospective Schema and Events Reference"

**Scope** (from data-model.md): `retrospective.yaml` field schema; proposal kinds and required fields; status event fields for retrospective; exit codes for synthesizer.

**Structure**:
1. Brief intro: "This reference documents the `retrospective.yaml` schema, proposal types, and synthesizer exit codes. For how to use the retrospective loop, see [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md)."

2. **retrospective.yaml schema** — table of all fields:

| Field | Type | Required | Description |
|---|---|---|---|
| (derive from source — do not invent) | | | |

To find the schema: look for `retrospective.yaml` in `src/specify_cli/` or check `uv run spec-kitty retrospect summary --json` output if available. If the schema is not directly inspectable, derive from what `retrospect summary` outputs and document that.

3. **Proposal kinds** — one section per proposal type:
   - Name
   - Required fields
   - When the synthesizer accepts vs rejects it
   
   If proposal kinds are not directly documented, use the default dry-run output from `agent retrospect synthesize --mission <mission>`.

4. **Retrospective status event fields** — what events appear in the status trail for a retrospective lifecycle. Reference the 9-lane status model (status.events.jsonl).

5. **Synthesizer exit codes**:

| Exit code | Meaning | Action required |
|---|---|---|
| 0 | Success — proposals applied | None |
| (non-zero codes from --help or source) | | |

If exit codes are not documented in `--help`, write: "Consult `uv run spec-kitty agent retrospect synthesize --help` for current exit codes."

**Cross-links**:
- `docs/how-to/use-retrospective-learning.md`
- `docs/explanation/retrospective-learning-loop.md`

### T032 — Write docs/migration/from-charter-2x.md

**File**: `docs/migration/from-charter-2x.md`  
**Title**: "Migrating from 2.x / Early 3.x Charter Projects"

**Scope** (from data-model.md): changes between 2.x and Charter-era 3.x that affect operators; new paths and commands; what to re-run after upgrade; known migration failures and fixes.

**Structure**:
1. Intro: "This guide covers what changed when upgrading a project from Spec Kitty 2.x (or early 3.x before the Charter era) to the current Charter-era 3.x."

2. **What changed** — comparison table:

| Area | 2.x behavior | 3.x Charter behavior |
|---|---|---|
| Governance file location | (derive from docs/2x/) | `.kittify/charter/charter.md` |
| Synthesis command | (if existed in 2.x) | `charter synthesize` + `charter bundle validate` |
| CLI structure | (from docs/2x/ reference) | `spec-kitty charter <subcommand>` |
| Mission execution | (2.x pattern) | `spec-kitty next --agent <agent>` with Charter context |

Derive 2.x behavior by reading `docs/2x/` content (particularly `docs/2x/doctrine-and-charter.md` if present).

3. **Migration steps** — what to re-run after upgrade:
   - Re-run `charter interview` if `charter.md` format changed
   - Re-run `charter generate` to regenerate governance files
   - Re-run `charter bundle validate` to verify the new bundle
   - Verify `charter status` reports no drift

4. **Known migration failures and fixes**:
   - If the 2.x governance file was at a different path, describe how to move it.
   - If synthesis commands changed signature, show old vs new.

5. **Getting help** — "If you encounter issues not covered here, see [Troubleshooting Charter Failures](../how-to/troubleshoot-charter.md)."

**Cross-links**:
- `docs/how-to/setup-governance.md`
- `docs/how-to/synthesize-doctrine.md`
- `docs/how-to/troubleshoot-charter.md`
- `docs/3x/index.md`
- `docs/2x/index.md` (archived docs)

### T033 — Review docs/explanation/documentation-mission.md for phase accuracy

**Action**: Read the file. Compare the phases described in it to `mission-runtime.yaml`. Also check for any references to `charter context`, `retro summary`, or `retro synthesizer` — these are stale command names if present:

```bash
cat docs/explanation/documentation-mission.md
cat src/specify_cli/missions/documentation/mission-runtime.yaml 2>/dev/null
# If different path:
find src/ -name 'mission-runtime.yaml' 2>/dev/null
```

Check each phase name in the doc against what `mission-runtime.yaml` declares. Record:
- Phases in the doc that match mission-runtime.yaml: accurate ✅
- Phases in the doc that don't appear in mission-runtime.yaml: stale ❌
- Phases in mission-runtime.yaml that don't appear in the doc: missing ❌

### T034 — Update docs/explanation/documentation-mission.md if stale

**Condition**: Only update if T033 found stale or missing phases.

**Action**: Update the phases in the doc to match mission-runtime.yaml exactly. Do not change any other content. Do not invent phases.

If the file uses old phase names (e.g., from the pre-3.0 documentation mission), replace them with the names from `mission-runtime.yaml`. Use the exact string from the YAML file, not a paraphrase.

If no changes are needed (all phases match), skip this subtask and note "documentation-mission.md phases confirmed current" in the commit message.

### T035 — Verify docs/migration/toc.yml and reference/toc.yml have correct entries

The migration page and retrospective-schema.md should already appear in their toc.yml files (added by WP01). Verify:

```bash
grep 'from-charter-2x' docs/migration/toc.yml
grep 'retrospective-schema' docs/reference/toc.yml
```

Both must appear. Do not modify toc.yml files in this WP if the entries are already there.

Also verify:
```bash
grep -r 'TODO' docs/reference/retrospective-schema.md \
  docs/migration/from-charter-2x.md
```
Zero results required.

## Definition of Done

- [ ] `retrospective-schema.md` written: retrospective.yaml schema, proposal kinds, status event fields, exit codes
- [ ] `from-charter-2x.md` written: what changed, migration steps, known failures and fixes
- [ ] `documentation-mission.md` reviewed against `mission-runtime.yaml`
- [ ] `documentation-mission.md` updated if phases were stale (or confirmed current)
- [ ] All pages use DocFX frontmatter
- [ ] `retrospective-schema.md` appears in `docs/reference/toc.yml`
- [ ] `from-charter-2x.md` appears in `docs/migration/toc.yml`
- [ ] `grep -r 'TODO' docs/reference/retrospective-schema.md docs/migration/from-charter-2x.md` → zero results
- [ ] `uv run pytest tests/docs/ -q` passes
