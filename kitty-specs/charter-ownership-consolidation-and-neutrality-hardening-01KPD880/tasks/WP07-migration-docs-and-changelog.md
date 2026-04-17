---
work_package_id: WP07
title: Migration Docs and CHANGELOG
dependencies:
- WP04
requirement_refs:
- C-004
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main.
subtasks:
- T024
- T025
- T026
phase: Phase 3 — Hygiene
assignee: ''
agent: ''
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: docs/migration/charter-ownership-consolidation.md
execution_mode: code_change
owned_files:
- docs/migration/charter-ownership-consolidation.md
- CHANGELOG.md
tags: []
---

# Work Package Prompt: WP07 – Migration Docs and CHANGELOG

## Objective

Produce the contributor-facing migration guide and CHANGELOG entry that together satisfy FR-015 and SC-006. Both artifacts must name `charter` as the canonical import path and `3.3.0` as the shim-removal target. Cross-validate that the `__removal_release__` constant installed by WP04 agrees with the CHANGELOG text.

## Context

The deprecation warning from WP04 instructs users to read CHANGELOG.md and `docs/migration/charter-ownership-consolidation.md`. Those two documents must exist and must carry consistent information. This WP is the last step of the mission: it closes the user-facing loop.

C-004 constrains messaging: the migration guide speaks to **downstream Python integrators** who may have `from specify_cli.charter import ...` in their own code. Keep the audience narrow and the path explicit. Do not mix in marketing language or Phase 3 synthesizer roadmap references.

Removal release `3.3.0` is the coordinated value. WP04 installs `__removal_release__ = "3.3.0"`. The contracts (C-1, C-2) set this value. Any drift here breaks the test in WP04.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. Execution worktree path is resolved by the runtime from `lanes.json`.

## Implementation Sketch

### Subtask T024 — Author `docs/migration/charter-ownership-consolidation.md`

**File**: `docs/migration/charter-ownership-consolidation.md` (new, ~90 lines).

Structure (no emojis, terse, action-focused):

```markdown
# Migration — Charter ownership consolidation

**Status**: Deprecation active (landed in release 3.2.0). **Removal target**: 3.3.0.

## What changed

The authoritative implementation of charter services lives under the top-level
`charter` package. The legacy `specify_cli.charter` package and its
submodules (`compiler`, `interview`, `resolver`) remain as thin re-export shims
for backward compatibility, with a `DeprecationWarning` on first import.

## Who is affected

Any downstream Python code that imports directly from `specify_cli.charter`:

- `from specify_cli.charter import build_charter_context, ensure_charter_bundle_fresh`
- `from specify_cli.charter.compiler import <X>`
- `from specify_cli.charter.interview import <X>`
- `from specify_cli.charter.resolver import <X>`

First-party code inside spec-kitty no longer uses these paths (three test files
are retained as deliberate compatibility exceptions per mission-internal
occurrence-map rules).

## What to do

Replace the import path:

| Old | New |
|-----|-----|
| `from specify_cli.charter import X` | `from charter import X` |
| `from specify_cli.charter.compiler import X` | `from charter.compiler import X` |
| `from specify_cli.charter.interview import X` | `from charter.interview import X` |
| `from specify_cli.charter.resolver import X` | `from charter.resolver import X` |

No call-site or signature changes are required — the re-exports are identity
re-exports, and the submodule shims alias `sys.modules` to the canonical module,
so the imported symbol is the same object.

## Timeline

- **3.2.0** (this release): shims remain functional; importing them emits a
  single `DeprecationWarning` per process pointing at the caller.
- **3.3.0**: shim package removed. Imports from `specify_cli.charter` will
  raise `ModuleNotFoundError`.

## How to silence the warning temporarily

If you need to quiet the warning while you migrate, the standard `warnings`
module controls apply:

```python
import warnings
warnings.filterwarnings(
    "ignore",
    message=r"specify_cli\.charter is deprecated.*",
    category=DeprecationWarning,
)
```

Prefer migrating over filtering — the filter will stop working in 3.3.0 because
the target module will be gone.

## Questions

File an issue against the `spec-kitty` repository with the `charter-migration`
label.
```

Notes for the author:

- Use exactly the two module-level constant names the shim carries: `__deprecated__` does not need to appear in this document, but `__removal_release__` should be described as `3.3.0`.
- Do not list `src/charter/` paths — downstream users don't `cd` into spec-kitty's source tree; they see the package surface only.
- Do not include emoji.

### Subtask T025 — Add CHANGELOG entry

**File**: `CHANGELOG.md` (edit the Unreleased or next-version section).

Add under "Deprecated" (create the subsection if absent):

```markdown
### Deprecated

- `specify_cli.charter` and its submodules (`compiler`, `interview`, `resolver`).
  Import from the top-level `charter` package instead. These shims will be
  removed in release **3.3.0**. See
  [docs/migration/charter-ownership-consolidation.md](docs/migration/charter-ownership-consolidation.md)
  for the full migration guide.
```

Match the existing CHANGELOG style — if the file uses Keep-a-Changelog layout, the `### Deprecated` header is canonical. If the file uses prose sections, match the prose style. Do not reformat the rest of the file.

### Subtask T026 — Cross-validate the removal release constant

Open `src/specify_cli/charter/__init__.py` (WP04 has already edited this file — do NOT edit it again). Confirm:

```python
__removal_release__ = "3.3.0"
```

And confirm the CHANGELOG entry and the migration guide both say `3.3.0` in the removal-target position. One grep:

```bash
grep -n '3\.3\.0' \
  src/specify_cli/charter/__init__.py \
  docs/migration/charter-ownership-consolidation.md \
  CHANGELOG.md
```

Expected: the string `3.3.0` appears in at least one location in each file, in the correct context (removal target). If any of the three is missing or names a different version, fix **this WP's** file (the migration guide or CHANGELOG), not the `__init__.py`. WP04 is authoritative for the constant value.

Record the grep output in the PR body as evidence the cross-validation passed.

## Files

- **New**: `docs/migration/charter-ownership-consolidation.md`
- **Edited**: `CHANGELOG.md`

## Definition of Done

- [ ] `docs/migration/charter-ownership-consolidation.md` exists and contains all the sections listed in T024.
- [ ] `CHANGELOG.md` has a Deprecated entry naming `specify_cli.charter`, the `charter` canonical path, and `3.3.0` as removal target.
- [ ] Both documents name removal release `3.3.0` consistently with `src/specify_cli/charter/__init__.py`.
- [ ] The migration guide does not reference `src/charter/` internal paths and does not include emoji.
- [ ] Markdown renders cleanly (no broken links, no unclosed code fences).
- [ ] Grep from T026 shows `3.3.0` present in all three files.

## Risks

- **Version drift**: if the project moves the deprecation window later (e.g., to 3.4.0), three artifacts need coordinated updates: the constant in `__init__.py` (WP04's file), the CHANGELOG entry, and the migration guide. Drift is caught by WP04's test (`assert "3.3.0" in msg`), which will fail if the constant diverges from the message. This WP inherits the risk; if the release target changes mid-flight, coordinate via a follow-up issue.
- **Out-of-scope edits**: this WP touches only docs and CHANGELOG. Do NOT edit `__init__.py` here — WP04 owns that file, and the ownership overlap would violate the occurrence-map lockdown. If the constant needs a value change, raise it as a WP04 correction, not a WP07 edit.
- **Style mismatch with existing CHANGELOG**: the repo's CHANGELOG may use specific conventions (version prefixes, date formats). Match them exactly — do not introduce a new format in this entry.
- **Audience misalignment**: the migration guide is for downstream Python integrators, not for spec-kitty contributors. Keep it concise and action-oriented. Avoid referencing internal mission numbers, research IDs, or WP IDs.

## Reviewer Checklist

- [ ] The migration guide names `charter` as canonical and `3.3.0` as removal target, both in the headline and in the body.
- [ ] The CHANGELOG entry links to the migration guide at the expected relative path.
- [ ] `grep -n '3\.3\.0' src/specify_cli/charter/__init__.py docs/migration/charter-ownership-consolidation.md CHANGELOG.md` shows matches in all three files.
- [ ] No edits to `src/specify_cli/charter/__init__.py` in this WP (WP04 owns that surface).
- [ ] No emoji in the migration guide.
- [ ] Markdown is well-formed (render it locally or in a PR preview to confirm).
