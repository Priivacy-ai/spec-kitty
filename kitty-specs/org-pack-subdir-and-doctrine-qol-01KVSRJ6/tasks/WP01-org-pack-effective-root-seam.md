---
work_package_id: WP01
title: OrgPackConfig effective-root seam, validation & round-trip
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-006
tracker_refs: []
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Thread A foundation
assignee: ''
agent: claude
history:
- at: '2026-06-23T09:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/org_pack_config.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/org_pack_config.py
- tests/doctrine/test_org_pack_subdir.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – OrgPackConfig effective-root seam, validation & round-trip

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Add an optional `subdir` to `OrgPackConfig` and the **single canonical effective-root seam** that every downstream consumer (WP02) will adopt. This is the foundation of the #2083 fix.

**Done when:**
- `OrgPackConfig` accepts an optional `subdir` (model still `extra="forbid"`).
- `OrgPackConfig.effective_root(repo_root)` returns the repo-root-normalized `local_path` joined with `subdir` (or just the normalized `local_path` when absent).
- Escape inputs are rejected with a structured, operator-visible error.
- `subdir` round-trips through both config shapes; absent emits no key.
- Unit tests cover all branches and pass; `ruff` + `mypy` clean; complexity ≤ 15.

## Context

- Spec: `kitty-specs/org-pack-subdir-and-doctrine-qol-01KVSRJ6/spec.md` (FR-001/002/003/005/006, NFR-001/002, C-005/C-007)
- Design: `research.md` (D-1 seam, D-2 containment), `data-model.md` (OrgPackConfig table)
- Squad evidence: `research/post-spec-squad-findings.md`
- Target file (existing): `src/doctrine/drg/org_pack_config.py` — current `resolve_org_roots` returns raw `local_path` (the split this WP retires).
- Reuse helper: `src/specify_cli/core/utils.py:ensure_within_directory(path, root)` (strict `.resolve()`, symlink-safe).

## Subtasks & Detailed Guidance

### T001 — Add `subdir` field
- Add `subdir: str | None = None` to `OrgPackConfig`. Keep `extra="forbid"` (C-005). Update `__all__`/docstring as needed.

### T002 — `subdir` string-level validator (at model validation)
- Add a pydantic `field_validator("subdir")` that, for non-None values:
  - Rejects absolute paths — POSIX (`/…`), Windows drive (`C:\…`), and UNC (`\\…`). Use `PurePosixPath`/`PureWindowsPath` checks rather than only `os.path.isabs` (which is platform-dependent).
  - Rejects any path containing a `..` component.
  - Normalizes `.` and empty string → `None`.
- On rejection raise `ValueError` with an actionable message (the *string-level* arm of NFR-002). Do NOT do filesystem/symlink work here — the clone may not exist yet (D-2).

### T003 — `effective_root(repo_root: Path) -> Path`
- Implement as a method/property on `OrgPackConfig`:
  - Normalize `local_path` relative to `repo_root` when relative (retire the raw-vs-relative split — C-007).
  - Join `subdir` when present.
  - Apply the **resolution-time** containment check: `ensure_within_directory(effective, normalized_local_path)` — this is the symlink-escape arm of NFR-002 (the clone content can plant a symlink). On failure raise the structured error (T005).

### T004 — Round-trip
- `_pack_to_yaml_dict`: emit `subdir` **only when not None** (FR-005 — no empty key).
- `_build_legacy_single_pack`: read `subdir` from the inline `doctrine.org` block (FR-006). (Currently it drops it.)

### T005 — Surface structured error (not swallowed)
- `load_pack_registry` currently catches `ValidationError`/`ValueError` and degrades to an empty `PackRegistry` with a warning (`org_pack_config.py:128-139`). A subdir-escape must NOT silently disable the org layer (contradicts Scenario A1). Distinguish containment/escape failures and re-raise (or surface) a structured, operator-visible error while leaving the existing unrelated-YAML-error degrade path intact.

### T006 — Unit tests (`tests/doctrine/test_org_pack_subdir.py`)
- `effective_root`: no-subdir → normalized `local_path` (NFR-001); with `subdir` → joined; relative `local_path` normalized vs repo_root.
- Validator: rejects `/etc`, `C:\x`, `\\unc\x`, `../escape`, `a/../../b`; normalizes `.`/`""` → None.
- Symlink-escape at resolution time rejected (create a symlink in a tmp dir pointing outside).
- Round-trip: write→read preserves `subdir`; absent emits no `subdir:` key; legacy inline shape carries it.
- Escape surfaces a structured error (not a swallowed empty registry).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}
- Execution worktree allocated per computed lane from `lanes.json`.

## Definition of Done

- [ ] T001–T006 complete; all new tests pass.
- [ ] `ruff check` + `mypy` clean on the touched file; complexity ≤ 15.
- [ ] No behavior change for configs without `subdir` (NFR-001 regression test green).
- [ ] Escape inputs raise a structured operator-visible error (NFR-002), proven by test.
- [ ] `effective_root` is the only place `subdir`/relative normalization happens (C-007).

## Risks & Reviewer Guidance

- **Risk**: putting normalization in two places reintroduces the split — verify `effective_root` is the sole seam.
- **Reviewer**: confirm the validator does NOT touch the filesystem (timing), and that the symlink check IS at resolution time. Confirm `_build_legacy_single_pack` actually reads `subdir` (easy to miss). Confirm escape does not degrade to "no org packs".
