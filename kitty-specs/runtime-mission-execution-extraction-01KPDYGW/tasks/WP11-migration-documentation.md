---
work_package_id: WP11
title: Migration Documentation + CHANGELOG
dependencies:
- WP01
requirement_refs:
- FR-014
- FR-016
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
agent: "claude:claude-sonnet-4-6:architect-alphonso:reviewer"
shell_pid: "678209"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: architect-alphonso
authoritative_surface: docs/migration/
execution_mode: planning_artifact
owned_files:
- docs/migration/runtime-extraction.md
- CHANGELOG.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load architect-alphonso
```

This is documentation work governed by DIRECTIVE_003 (Decision Documentation). Do not begin until the profile is active.

---

## Objective

Write the user-facing migration guide for external callers of `specify_cli.next.*` and `specify_cli.runtime.*`, and record the extraction in `CHANGELOG.md`. This WP is fully independent of the code moves — it can start as soon as WP01 generates the occurrence map.

---

## Context

**Read before writing**:
- `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/occurrence_map.yaml` — contains the full import-path translation table
- `docs/migration/` — check for existing migration docs to match the style (e.g., `runtime-extraction.md` if the charter migration doc is there)
- `CHANGELOG.md` — read the most recent entries to match the format
- The charter exemplar: `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` — this mission's migration and CHANGELOG format is the template (FR-016)

---

## Subtask T041 — Write `docs/migration/runtime-extraction.md`

**Purpose**: A migration guide for anyone (internal contributor or external library user) who imports from `specify_cli.next.*` or `specify_cli.runtime.*`. Must be usable without reading any other document.

**Structure**:

```markdown
# Migration Guide: Runtime Extraction (3.2.x → 3.4.0)

## Why This Migration Exists

[1-2 paragraphs: the extraction moved specify_cli.next and specify_cli.runtime 
to a canonical top-level runtime package for cleaner architecture. 
Old paths emit DeprecationWarning and are removed in 3.4.0.]

## What Changed

| Legacy import path | Canonical import path | Module |
|---|---|---|
| `specify_cli.next.decision` | `runtime.decisioning.decision` | decision.py |
| `specify_cli.next.prompt_builder` | `runtime.prompts.builder` | builder.py |
| `specify_cli.next.runtime_bridge` | `runtime.bridge.runtime_bridge` | runtime_bridge.py |
| `specify_cli.runtime.home` | `runtime.discovery.home` | home.py |
| `specify_cli.runtime.resolver` | `runtime.discovery.resolver` | resolver.py |
| `specify_cli.runtime.agent_commands` | `runtime.agents.commands` | commands.py |
| `specify_cli.runtime.agent_skills` | `runtime.agents.skills` | skills.py |
| `specify_cli.runtime.bootstrap` | `runtime.orchestration.bootstrap` | bootstrap.py |
| `specify_cli.runtime.doctor` | `runtime.orchestration.doctor` | doctor.py |
| `specify_cli.runtime.merge` | `runtime.orchestration.merge` | merge.py |
| `specify_cli.runtime.migrate` | `runtime.orchestration.migrate` | migrate.py |
| `specify_cli.runtime.show_origin` | `runtime.orchestration.show_origin` | show_origin.py |

## How to Migrate

[Code examples: before/after import blocks]

## Deprecation Timeline

- 3.2.x: Legacy paths emit DeprecationWarning; runtime.* is the canonical path
- 3.4.0: Legacy shim paths removed (shim-registry.yaml `removal_release: "3.4.0"`)

## New Seam Protocols

[Brief description of PresentationSink and StepContractExecutor; 
link to src/runtime/seams/ for the Protocol definitions]

## Questions?

[Link to the tracking issue #612 and the ownership map]
```

**Steps**:

1. Read `occurrence_map.yaml` to get the complete and accurate import-path translation table (do not guess — use the map).

2. Read any existing migration docs in `docs/migration/` to match style.

3. Write `docs/migration/runtime-extraction.md` following the structure above. Expand each section:
   - **Why**: emphasize that the API is unchanged — only the import path changes
   - **Code examples**: show 3-4 concrete before/after import blocks covering the most common patterns
   - **Seam protocols**: 2-3 sentences; external callers almost never need these but should know they exist
   - **Timeline**: clear and actionable — "if you see DeprecationWarning, update now; you have until 3.4.0"

4. Verify the doc renders as valid Markdown: no broken links, all table columns aligned.

**Files touched**: `docs/migration/runtime-extraction.md` (new file)

**Validation**: File exists; `python -m markdown docs/migration/runtime-extraction.md > /dev/null` exits 0 (or similar Markdown validation).

---

## Subtask T042 — Update `CHANGELOG.md`

**Purpose**: Record the extraction in the CHANGELOG so maintainers, packagers, and users can track the change across releases.

**Steps**:

1. Read the current `CHANGELOG.md` to locate the `## [Unreleased]` section and understand the format.

2. Add an entry under `## [Unreleased]` → `### Changed`:

   ```markdown
   ### Changed

   - Extracted Spec Kitty execution core to canonical top-level `runtime` package
     (mission `runtime-mission-execution-extraction-01KPDYGW`, tracking #612).
     `specify_cli.next.*` and `specify_cli.runtime.*` import paths now emit
     `DeprecationWarning` and will be removed in 3.4.0. Use `runtime.*` instead.
     See [docs/migration/runtime-extraction.md](docs/migration/runtime-extraction.md).
     Pattern follows the `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`
     exemplar and the #615 shim-registry contract.
   ```

3. Also add under `### Added` (if the section exists):

   ```markdown
   ### Added

   - `PresentationSink` and `StepContractExecutor` Protocols at `src/runtime/seams/`
     providing typed seams for presentation decoupling and future #461 Phase 6 implementation.
   ```

4. Verify the CHANGELOG entry is under the correct section and uses the correct format for this project.

**Files touched**: `CHANGELOG.md`

**Validation**: `CHANGELOG.md` contains "runtime-extraction" and "#612" and "3.4.0" in the Unreleased section.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP11 --agent claude`. Fully independent.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

This WP can start as soon as WP01 generates the occurrence_map.yaml (for the accurate translation table). It does NOT need to wait for WP06 or later.

---

## Definition of Done

- [ ] `docs/migration/runtime-extraction.md` exists with a complete import-path translation table covering all 12 module moves
- [ ] Migration doc includes code examples (before/after import blocks)
- [ ] Migration doc includes the deprecation timeline (3.2.x warning, 3.4.0 removal)
- [ ] `CHANGELOG.md` has an Unreleased entry citing the mission slug, tracking issue #612, and the 3.4.0 removal date
- [ ] CHANGELOG entry references the charter exemplar pattern

---

## Reviewer Guidance

- Verify the translation table is complete — every module in the extraction surface should have a row
- Confirm the CHANGELOG entry is under `## [Unreleased]` (not under a versioned section)
- Check that the migration doc explains that the API is unchanged — only the import path changes
- The doc must be usable standalone without reading spec.md, plan.md, or any other planning artifact

## Activity Log

- 2026-04-22T20:41:04Z – claude:claude-sonnet-4-6:architect-alphonso:implementer – shell_pid=675523 – Started implementation via action command
- 2026-04-22T20:43:51Z – claude:claude-sonnet-4-6:architect-alphonso:implementer – shell_pid=675523 – Ready for review: migration doc and CHANGELOG written — 12-module translation table, before/after examples, deprecation timeline, seam protocol notes
- 2026-04-22T20:45:47Z – claude:claude-sonnet-4-6:architect-alphonso:reviewer – shell_pid=678209 – Started review via action command
- 2026-04-22T20:46:37Z – claude:claude-sonnet-4-6:architect-alphonso:reviewer – shell_pid=678209 – Review passed: migration doc complete with all 12-module translation table, 4 before/after examples, deprecation timeline (3.2.x warning → 3.4.0 removal), #612 and ownership map referenced; CHANGELOG Unreleased entry includes #612, 3.4.0 removal date, charter exemplar, and PresentationSink/StepContractExecutor under Added. Only allowed files modified.
