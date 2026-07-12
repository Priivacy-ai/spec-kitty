---
work_package_id: WP04
title: Manifest output_path repo-relative (cross-machine deterministic)
dependencies: []
requirement_refs:
- FR-006
- NFR-004
tracker_refs:
- '2589'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: 551ac0f0dfd8992d37a1ee320c126411d2189488
created_at: '2026-07-12T21:34:45.480289+00:00'
subtasks:
- T013
- T014
- T015
- T016
phase: Portability
agent: "claude"
shell_pid: '1484725'
shell_pid_created_at: '1783892074.19'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-04; re-sized M from papercut per squad)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/profiles/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/profiles/manifest.py
- tests/specify_cli/tool_surface/profiles/test_manifest.py
- .kittify/agent_profiles_manifest.json
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 — Manifest output_path repo-relative

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

Store `output_path` repo-root-relative in the committed `agent_profiles_manifest.json` (in-memory
representation and internal key stay ABSOLUTE), tolerating legacy absolute values with zero migration, so
`spec-kitty upgrade` is cross-machine deterministic.

- **SC (#2589)**: `upgrade` on a second machine/path produces 0 manifest diff (was 152 ins / 34 del).
- **SC (NFR-004)**: a legacy absolute manifest loaded under a different `project_root` still `.exists()`-resolves; no migration.
- **SC**: an out-of-tree entry serializes absolute (fallback), like `source_path`.

## Context & Constraints

Bug (#2589): `manifest.py:106` serializes `"output_path": str(entry.output_path)` (absolute), while
`source_path` is already relativized by `projection.py::_manifest_source_path` (:52-59). The committed
manifest currently carries a foreign machine's absolute path, so every `upgrade` on another machine rewrites
every entry.

**KEEP invariants:**
- The in-memory `output_path` (a `Path`) and the internal manifest **key** (`str(output_path)`, used at
  `manifest.py:69/73/77/86` by `get_hash`/prune/`.exists()`) MUST stay ABSOLUTE. Relativize ONLY at the
  JSON serialization boundary; reconstruct absolute at read.
- `_manifest_source_path` is the pattern, but only HALF: `source_path` is never reconstructed, whereas
  `output_path` is the key and MUST resolve — so you must reconstruct on read. Thread `project_root`
  (derive as `manifest_path.parent.parent`) through `_entry_to_json`/`_entry_from_json`/`_read`/`save`.

Plan: IC-04. Research: R-06. Contract: C-C1.

## Branch Strategy

- **Planning base branch / Merge target**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T013 — Thread `project_root` through reader/writer

- **Steps**: Give `_read`/`save` access to `project_root` (from `manifest_path.parent.parent`) and pass it
  into `_entry_to_json`/`_entry_from_json`. Keep signatures minimal.
- **Files**: `src/specify_cli/tool_surface/profiles/manifest.py`.

### Subtask T014 — Relative serialize + absolute reconstruct (SSOT: share the relativize helper)

- **Steps**: **Do NOT inline a second copy of the `relative_to(...).as_posix()` + `ValueError` fallback**
  (alphonso D1 — that idiom already lives in `projection.py::_manifest_source_path`). Extract/reuse ONE shared
  serialize helper `relativize_under_root(path, project_root) -> str` that BOTH `_manifest_source_path` and
  the new `output_path` serializer call. `_entry_to_json` calls it for `output_path`. The reconstruct half is
  legitimately new (because `output_path` is the manifest KEY): add `absolutize_from_root(value, project_root)`
  used by `_entry_from_json` (relative → `project_root / value`; absolute legacy → pass through). In-memory
  `output_path` + key remain absolute.
- **Files**: `manifest.py` (+ the shared helper's home so `projection.py` can import it without a cycle).

### Subtask T015 — Red-first tests

- **Steps**: In `tests/specify_cli/tool_surface/profiles/test_manifest.py`: (a) an in-tree entry serializes
  to a repo-relative string (no leading `/`, no home dir); (b) a legacy absolute manifest loaded under a
  DIFFERENT `project_root` reconstructs an `output_path` that `.exists()`-resolves; (c) keying invariant —
  after a relative-store round-trip, `get_hash(absolute_path)` still finds the entry; **(d) an OUT-OF-TREE
  entry (output_path outside `project_root`) serializes ABSOLUTE (fallback) and round-trips** (G1 — the
  `ValueError`→absolute branch, otherwise untested → NFR-007 hole).
- **Files**: the test file.

### Subtask T016 — Regenerate the committed manifest

- **Steps**: Regenerate `.kittify/agent_profiles_manifest.json` once via the new relative logic so it lands
  clean (8-field, relative). Verify `git diff` on a second checkout would be empty (describe the check in the PR).
- **Files**: `.kittify/agent_profiles_manifest.json`.

## Definition of Done

- `output_path` serialized relative (fallback absolute out-of-tree); reader tolerant of both; in-memory/key absolute.
- Three regression cases pass; committed manifest regenerated clean.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/tool_surface/profiles/test_manifest.py -q` green; `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Risk**: relativizing the in-memory key breaks `get_hash`/prune (the #2589 bug itself) — reviewer verifies T015(c).
- **Risk**: a genuinely out-of-tree profile path must not crash — reviewer confirms the absolute fallback.

## Activity Log

- 2026-07-12T21:58:26Z – claude – shell_pid=1484725 – reviewer-renata APPROVE: keying invariant preserved+tested; SSOT one helper no cycle; deterministic relative manifest
- 2026-07-12T21:58:40Z – claude – shell_pid=1484725 – reviewer-renata APPROVE
