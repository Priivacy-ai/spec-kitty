---
work_package_id: WP01
title: State Contract Module
lane: "planned"
dependencies: []
base_branch: 2.x
base_commit: 72ed47b6df33996bab220f03079dfe414774d713
created_at: '2026-03-18T18:59:29.551952+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
assignee: ''
agent: codex
shell_pid: '11803'
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
review_feedback: "feedback://050-state-model-cleanup-foundations/WP01/20260318T191021Z-4d79aed0.md"
history:
- timestamp: '2026-03-18T18:52:42Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- NFR-001
- NFR-003
---

# Work Package Prompt: WP01 – State Contract Module

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

> **Reference-only section** – Canonical review feedback is stored via frontmatter `review_feedback` (`feedback://...`).

---

## Objectives & Success Criteria

- Create `src/specify_cli/state_contract.py` containing a complete typed registry of all durable CLI state surfaces.
- Every surface from the 007 state architecture audit (sections A–G) has a corresponding registry entry.
- Enums cover all classification dimensions: root, authority, git policy, format.
- Helper functions enable querying the registry by root, git class, authority, and extracting gitignore patterns.
- Unit tests validate completeness, uniqueness, serialization, and helper correctness.
- Module is data-first: no side effects, no business logic beyond lookups.

## Context & Constraints

- **Spec**: `kitty-specs/050-state-model-cleanup-foundations/spec.md` (FR-001 through FR-005, FR-011)
- **Plan**: `kitty-specs/050-state-model-cleanup-foundations/plan.md` (Module Interfaces section)
- **Data Model**: `kitty-specs/050-state-model-cleanup-foundations/data-model.md` (entity definitions)
- **Audit source**: The 007 state architecture audit inventory (`02-state-inventory.md`) at `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/research/007-spec-kitty-2x-state-architecture-audit/02-state-inventory.md`
- **Constraint C-001**: Constitution surfaces are classified but Git boundary decision is deferred. Use `git_class=INSIDE_REPO_NOT_IGNORED` with notes for `answers.yaml`, `references.yaml`, `library/**`.
- **Constraint C-002**: Legacy surfaces (e.g., `active-mission`) are classified as `deprecated=True` in the registry.
- **Constraint NFR-001**: Zero new runtime dependencies beyond stdlib and existing spec-kitty imports.
- **Constraint NFR-003**: Data-first — no side effects in module-level code.

## Implementation Command

```bash
spec-kitty implement WP01
```

No `--base` flag needed (no dependencies).

## Subtasks & Detailed Guidance

### Subtask T001 – Create State Enums

- **Purpose**: Define the classification vocabulary for state surfaces as `str` enums.
- **File**: `src/specify_cli/state_contract.py` (new file)
- **Steps**:
  1. Create the module with a module docstring: "Machine-readable state contract for spec-kitty CLI state surfaces."
  2. Define `StateRoot(str, Enum)`:
     - `PROJECT = "project"` — `.kittify/`
     - `FEATURE = "feature"` — `kitty-specs/<feature>/`
     - `GLOBAL_RUNTIME = "global_runtime"` — `~/.kittify/`
     - `GLOBAL_SYNC = "global_sync"` — `~/.spec-kitty/`
     - `GIT_INTERNAL = "git_internal"` — `.git/spec-kitty/`
  3. Define `AuthorityClass(str, Enum)`:
     - `AUTHORITATIVE = "authoritative"`
     - `DERIVED = "derived"`
     - `COMPATIBILITY = "compatibility"`
     - `LOCAL_RUNTIME = "local_runtime"`
     - `SECRET = "secret"`
     - `GIT_INTERNAL = "git_internal"`
     - `DEPRECATED = "deprecated"`
  4. Define `GitClass(str, Enum)`:
     - `TRACKED = "tracked"`
     - `IGNORED = "ignored"`
     - `INSIDE_REPO_NOT_IGNORED = "inside_repo_not_ignored"`
     - `GIT_INTERNAL = "git_internal"`
     - `OUTSIDE_REPO = "outside_repo"`
  5. Define `StateFormat(str, Enum)`:
     - `JSON`, `YAML`, `TOML`, `JSONL`, `SQLITE`, `MARKDOWN`, `TEXT`, `LOCKFILE`, `DIRECTORY`, `SYMLINK`
- **Notes**: Use `str, Enum` base so enum values are JSON-serializable by default.

### Subtask T002 – Create StateSurface Frozen Dataclass

- **Purpose**: Define the data structure for a single state surface entry.
- **File**: `src/specify_cli/state_contract.py` (append after enums)
- **Steps**:
  1. Import `dataclass` from `dataclasses`.
  2. Define `StateSurface` with `@dataclass(frozen=True)`:
     ```python
     @dataclass(frozen=True)
     class StateSurface:
         name: str
         path_pattern: str
         root: StateRoot
         format: StateFormat
         authority: AuthorityClass
         git_class: GitClass
         owner_module: str
         creation_trigger: str
         deprecated: bool = False
         notes: str = ""

         def to_dict(self) -> dict:
             return {
                 "name": self.name,
                 "path_pattern": self.path_pattern,
                 "root": self.root.value,
                 "format": self.format.value,
                 "authority": self.authority.value,
                 "git_class": self.git_class.value,
                 "owner_module": self.owner_module,
                 "creation_trigger": self.creation_trigger,
                 "deprecated": self.deprecated,
                 "notes": self.notes,
             }
     ```
- **Notes**: Frozen ensures immutability. `to_dict()` uses `.value` on enums for clean JSON output.

### Subtask T003 – Populate STATE_SURFACES Registry

- **Purpose**: Create the complete inventory of all state surfaces from the 007 audit.
- **File**: `src/specify_cli/state_contract.py` (append after dataclass)
- **Steps**:
  1. Read the audit inventory at `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/research/007-spec-kitty-2x-state-architecture-audit/02-state-inventory.md`
  2. Create `STATE_SURFACES: tuple[StateSurface, ...] = (...)` with one entry per audit surface.
  3. Cover all sections:

  **Section A — Project-Level State (`.kittify/`)**:
  - `project_config`: `.kittify/config.yaml` — AUTHORITATIVE, TRACKED, owner: `init/config writers`
  - `project_metadata`: `.kittify/metadata.yaml` — AUTHORITATIVE, TRACKED, owner: `init/upgrade`
  - `dashboard_control`: `.kittify/.dashboard` — LOCAL_RUNTIME, IGNORED, owner: `dashboard lifecycle`
  - `workspace_context`: `.kittify/workspaces/<feature>-<WP>.json` — LOCAL_RUNTIME, IGNORED, owner: `workspace_context`
  - `merge_resume_state`: `.kittify/merge-state.json` — LOCAL_RUNTIME, IGNORED (will be after this sprint), owner: `merge/state`
  - `runtime_feature_index`: `.kittify/runtime/feature-runs.json` — LOCAL_RUNTIME, IGNORED (will be), owner: `next/runtime_bridge`
  - `runtime_run_snapshot`: `.kittify/runtime/runs/<run_id>/state.json` — LOCAL_RUNTIME, IGNORED (will be), owner: `spec-kitty-runtime`
  - `runtime_run_event_log`: `.kittify/runtime/runs/<run_id>/run.events.jsonl` — LOCAL_RUNTIME, IGNORED (will be), owner: `spec-kitty-runtime`
  - `runtime_frozen_template`: `.kittify/runtime/runs/<run_id>/mission_template_frozen.yaml` — LOCAL_RUNTIME, IGNORED (will be), owner: `spec-kitty-runtime`
  - `glossary_fallback_events`: `.kittify/events/glossary/<mission_id>.events.jsonl` — LOCAL_RUNTIME, IGNORED (will be), owner: `glossary event adapter`
  - `dossier_snapshot`: `.kittify/dossiers/<feature>/snapshot-latest.json` — DERIVED, IGNORED (will be), owner: `dossier snapshot save`
  - `dossier_parity_baseline`: `.kittify/dossiers/<feature>/parity-baseline.json` — LOCAL_RUNTIME, IGNORED (will be), owner: `dossier drift detector`

  **Section B — Constitution State (`.kittify/constitution/`)**:
  - `constitution_source`: `.kittify/constitution/constitution.md` — AUTHORITATIVE, TRACKED, owner: `constitution compiler`
  - `constitution_interview_answers`: `.kittify/constitution/interview/answers.yaml` — AUTHORITATIVE, INSIDE_REPO_NOT_IGNORED, owner: `constitution interview`, notes: "Git boundary decision deferred to constitution cleanup sprint"
  - `constitution_references`: `.kittify/constitution/references.yaml` — DERIVED, INSIDE_REPO_NOT_IGNORED, owner: `constitution compiler`, notes: "Git boundary decision deferred"
  - `constitution_library`: `.kittify/constitution/library/*.md` — DERIVED, INSIDE_REPO_NOT_IGNORED, owner: `constitution compiler`, notes: "Git boundary decision deferred"
  - `constitution_governance`: `.kittify/constitution/governance.yaml` — DERIVED, IGNORED, owner: `constitution sync`
  - `constitution_directives`: `.kittify/constitution/directives.yaml` — DERIVED, IGNORED, owner: `constitution sync`
  - `constitution_sync_metadata`: `.kittify/constitution/metadata.yaml` — DERIVED, IGNORED, owner: `constitution sync`
  - `constitution_context_state`: `.kittify/constitution/context-state.json` — LOCAL_RUNTIME, IGNORED, owner: `constitution context`

  **Section C — Feature State (`kitty-specs/<feature>/`)**:
  - `feature_metadata`: `kitty-specs/<feature>/meta.json` — AUTHORITATIVE, TRACKED, owner: `feature creation/acceptance`
  - `canonical_status_log`: `kitty-specs/<feature>/status.events.jsonl` — AUTHORITATIVE, TRACKED, owner: `status emit`
  - `canonical_status_snapshot`: `kitty-specs/<feature>/status.json` — DERIVED, TRACKED, owner: `status reducer`
  - `wp_prompt_frontmatter`: `kitty-specs/<feature>/tasks/WP*.md` — COMPATIBILITY, TRACKED, owner: `task creation/move-task/legacy bridge`
  - `wp_activity_log`: `kitty-specs/<feature>/tasks/WP*.md body` — COMPATIBILITY, TRACKED, owner: `move-task/manual edits`
  - `tasks_status_block`: `kitty-specs/<feature>/tasks.md` — DERIVED, TRACKED, owner: `legacy bridge`

  **Section D — Git-Internal**:
  - `review_feedback_artifact`: `.git/spec-kitty/feedback/<feature>/<WP>/<timestamp>-<id>.md` — GIT_INTERNAL, GIT_INTERNAL, owner: `agent tasks move-task`

  **Section E — User-Home Sync (`~/.spec-kitty/`)**:
  - `sync_config`: `~/.spec-kitty/config.toml` — AUTHORITATIVE, OUTSIDE_REPO, owner: `sync/config`
  - `sync_credentials`: `~/.spec-kitty/credentials` — SECRET, OUTSIDE_REPO, owner: `sync/auth + tracker/credentials`
  - `credential_lock`: `~/.spec-kitty/credentials.lock` — LOCAL_RUNTIME, OUTSIDE_REPO, owner: `sync/auth`
  - `lamport_clock`: `~/.spec-kitty/clock.json` — AUTHORITATIVE, OUTSIDE_REPO, owner: `sync/clock`
  - `active_queue_scope`: `~/.spec-kitty/active_queue_scope` — LOCAL_RUNTIME, OUTSIDE_REPO, owner: `sync/queue`
  - `legacy_queue`: `~/.spec-kitty/queue.db` — AUTHORITATIVE, OUTSIDE_REPO, owner: `sync/queue`
  - `scoped_queue`: `~/.spec-kitty/queues/queue-<hash>.db` — AUTHORITATIVE, OUTSIDE_REPO, owner: `sync/queue`
  - `tracker_cache`: `~/.spec-kitty/trackers/<scope>.db` — AUTHORITATIVE, OUTSIDE_REPO, owner: `tracker/store`

  **Section F — Global Runtime (`~/.kittify/`)**:
  - `runtime_version_stamp`: `~/.kittify/cache/version.lock` — LOCAL_RUNTIME, OUTSIDE_REPO, owner: `runtime/bootstrap`
  - `runtime_update_lock`: `~/.kittify/cache/.update.lock` — LOCAL_RUNTIME, OUTSIDE_REPO, owner: `runtime/bootstrap`

  **Section G — Legacy**:
  - `active_mission_marker`: `.kittify/active-mission` — DEPRECATED, INSIDE_REPO_NOT_IGNORED, deprecated: True, owner: `legacy fallback`, notes: "deprecated but still read as fallback"

  4. Use `git_class=IGNORED` for surfaces that WILL BE ignored after this sprint's migration (merge-state, runtime/, events/, dossiers/). The contract reflects the target state, not the pre-sprint state.

- **Notes**: This is the largest subtask. Use the audit as the authoritative source. Aim for ~35-40 surface entries total.

### Subtask T004 – Implement Helper Functions

- **Purpose**: Provide query functions for consumers (doctor, GitignoreManager, tests).
- **File**: `src/specify_cli/state_contract.py` (append after registry)
- **Steps**:
  1. `get_surfaces_by_root(root: StateRoot) -> list[StateSurface]`: Filter `STATE_SURFACES` by root.
  2. `get_surfaces_by_git_class(git_class: GitClass) -> list[StateSurface]`: Filter by git_class.
  3. `get_surfaces_by_authority(authority: AuthorityClass) -> list[StateSurface]`: Filter by authority.
  4. `get_runtime_gitignore_entries() -> list[str]`: Return path patterns for project-root surfaces that should be in `.gitignore`. Logic:
     ```python
     def get_runtime_gitignore_entries() -> list[str]:
         patterns = []
         for s in STATE_SURFACES:
             if s.root == StateRoot.PROJECT and s.git_class == GitClass.IGNORED:
                 patterns.append(s.path_pattern)
         return sorted(patterns)
     ```
     This naturally includes `.kittify/.dashboard`, `.kittify/workspaces/`, `.kittify/missions/`, `.kittify/runtime/`, `.kittify/merge-state.json`, `.kittify/events/`, `.kittify/dossiers/`, and the constitution ignored surfaces.
- **Notes**: Keep helpers pure — no I/O, no side effects. Return new lists (not views).

### Subtask T005 – Write Unit Tests

- **Purpose**: Validate contract completeness, consistency, serialization, and helper correctness.
- **File**: `tests/specify_cli/test_state_contract.py` (new file)
- **Steps**:
  1. **Test: all surface names are unique**:
     ```python
     def test_surface_names_unique():
         names = [s.name for s in STATE_SURFACES]
         assert len(names) == len(set(names))
     ```
  2. **Test: minimum surface count** (at least 30 surfaces from audit):
     ```python
     def test_minimum_surface_count():
         assert len(STATE_SURFACES) >= 30
     ```
  3. **Test: all enum values used** — at least one surface per `StateRoot` value.
  4. **Test: `to_dict()` produces valid JSON-serializable dict**:
     ```python
     def test_to_dict_serializable():
         import json
         for s in STATE_SURFACES:
             d = s.to_dict()
             json.dumps(d)  # must not raise
             assert d["name"] == s.name
             assert d["root"] == s.root.value
     ```
  5. **Test: `get_surfaces_by_root()` returns correct subsets**:
     ```python
     def test_get_surfaces_by_root():
         project = get_surfaces_by_root(StateRoot.PROJECT)
         assert all(s.root == StateRoot.PROJECT for s in project)
         assert len(project) > 0
     ```
  6. **Test: `get_runtime_gitignore_entries()` includes known patterns**:
     ```python
     def test_runtime_gitignore_entries():
         entries = get_runtime_gitignore_entries()
         assert ".kittify/.dashboard" in entries
         assert ".kittify/runtime/" in entries or any("runtime" in e for e in entries)
         assert ".kittify/merge-state.json" in entries
     ```
  7. **Test: deprecated surfaces have `deprecated=True`**:
     ```python
     def test_deprecated_surfaces():
         deprecated = [s for s in STATE_SURFACES if s.deprecated]
         assert any(s.name == "active_mission_marker" for s in deprecated)
     ```
  8. **Test: frozen dataclass is immutable**:
     ```python
     def test_frozen():
         s = STATE_SURFACES[0]
         with pytest.raises(FrozenInstanceError):
             s.name = "modified"
     ```
  9. **Test: constitution deferred surfaces have notes**:
     ```python
     def test_constitution_deferred_notes():
         deferred = [s for s in STATE_SURFACES if "deferred" in s.notes.lower()]
         assert len(deferred) >= 3  # answers, references, library
     ```

## Test Strategy

Run tests with:
```bash
pytest tests/specify_cli/test_state_contract.py -v
```

All tests are unit tests — no filesystem I/O, no subprocess calls, no external dependencies.

## Risks & Mitigations

- **Risk**: Missing a surface from the audit. **Mitigation**: Cross-check against audit section headings; test asserts minimum count.
- **Risk**: Enum values diverge from audit terminology. **Mitigation**: Use exact audit vocabulary.

## Review Guidance

- Verify every surface in audit section 02 has a corresponding `StateSurface` entry.
- Verify constitution surfaces use `INSIDE_REPO_NOT_IGNORED` with deferred notes (C-001).
- Verify `active-mission` is `deprecated=True` (C-002).
- Verify `get_runtime_gitignore_entries()` returns patterns for surfaces that should be ignored (including the four new ones: runtime/, merge-state.json, events/, dossiers/).
- Verify no imports beyond stdlib.

## Activity Log

- 2026-03-18T18:52:42Z – system – lane=planned – Prompt created.
- 2026-03-18T18:59:29Z – coordinator – shell_pid=9963 – lane=doing – Assigned agent via workflow command
- 2026-03-18T19:03:58Z – coordinator – shell_pid=9963 – lane=for_review – State contract module complete: 4 StrEnum classes, frozen StateSurface dataclass, 39-surface registry covering audit sections A-G, 4 helper functions, 36 passing unit tests, ruff clean
- 2026-03-18T19:04:21Z – codex – shell_pid=11803 – lane=doing – Started review via workflow command
- 2026-03-18T19:10:21Z – codex – shell_pid=11803 – lane=planned – Codex review: 2 high findings - incomplete registry and unusable gitignore patterns
