# Work Packages: Planning Pipeline Integrity and Runtime Reliability

**Mission**: 069-planning-pipeline-integrity
**Inputs**: `kitty-specs/069-planning-pipeline-integrity/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Change `reduce()` to derive `materialized_at` from last event timestamp | WP01 | | [D] | [D] |
| T002 | Add skip-write guard to `materialize()` — compare bytes, skip if identical | WP01 | | [D] |
| T003 | Fix `materialize_if_stale()` return to call `reduce()` not `materialize()` | WP01 | | [D] |
| T004 | Unit tests: `reduce()` determinism — same events → same `materialized_at` | WP01 | P | [D] |
| T005 | Unit tests: `materialize()` idempotency — two calls, one write | WP01 | P | [D] |
| T006 | Integration test: clean git tree after read-only status commands | WP01 | P | [D] |
| T007 | Define `WorkPackageEntry` and `WpsManifest` Pydantic models | WP02 | | [D] |
| T008 | Implement `load_wps_manifest()` — ruamel.yaml loader with presence tracking | WP02 | | [D] |
| T009 | Implement `dependencies_are_explicit()` helper — detect present-empty `[]` vs absent key | WP02 | | [D] |
| T010 | Implement `generate_tasks_md_from_manifest()` — human-readable tasks.md generator | WP02 | | [D] |
| T011 | Write `src/specify_cli/schemas/wps.schema.json` (JSON Schema Draft 2020-12) | WP02 | P | [D] |
| T012 | Unit tests: load, absent returns None, malformed raises ValidationError with field name | WP02 | P | [D] |
| T013 | Unit tests: `dependencies_are_explicit` for present-empty vs absent key | WP02 | P | [D] |
| T014 | Unit tests: `generate_tasks_md_from_manifest` preserves WP titles, deps, subtask counts | WP02 | P | [D] |
| T015 | Add wps.yaml detection at top of `finalize_tasks()` — load manifest, build `wp_dependencies` | WP03 | |
| T016 | Bypass prose parser when wps.yaml present (tier 0 takes precedence over tasks.md scanning) | WP03 | |
| T017 | Add tasks.md regeneration step when wps.yaml present | WP03 | |
| T018 | Integration test: wps.yaml present → manifest deps used, prose parser skipped | WP03 | P |
| T019 | Integration test: `dependencies: []` in wps.yaml → WP has no deps after finalize | WP03 | P |
| T020 | Integration test: tasks.md overwritten with manifest-generated content | WP03 | P |
| T021 | Integration test: no wps.yaml → prose parser path unchanged (backward compat) | WP03 | P |
| T022 | Rewrite `tasks-outline.md` template — produce wps.yaml, not tasks.md | WP04 | |
| T023 | Rewrite `tasks-packages.md` template — read/update wps.yaml, generate WP files | WP04 | |
| T024 | Write `m_3_2_0_update_planning_templates.py` migration with detect + apply | WP04 | |
| T025 | Migration unit tests: detect returns True/False correctly | WP04 | P |
| T026 | Migration unit tests: apply overwrites stale files, respects agent config, is idempotent | WP04 | P |
| T027 | Add `DecisionKind.query` constant and `is_query: bool = False` to `Decision` dataclass | WP05 | |
| T028 | Implement `query_current_state()` in `runtime_bridge.py` — read state without advancing | WP05 | |
| T029 | Change `result` default to `None` in `next_cmd.py`; add query mode branch | WP05 | |
| T030 | Add explicit `is_query` branch to `_print_human()` — SC-003 verbatim label as first line | WP05 | |
| T031 | Unit test: bare `spec-kitty next` does not advance state machine | WP05 | P |
| T032 | Unit test: query output begins with `[QUERY — no result provided, state not advanced]` verbatim | WP05 | P |
| T033 | Unit test: `--result success` still advances (no regression) | WP05 | P |
| T034 | Unit test: JSON output includes `"is_query": true` | WP05 | P |
| T035 | Update `KEBAB_CASE_PATTERN` regex to accept digit-prefixed slugs | WP06 | | [D] |
| T036 | Update error message — add valid digit-prefix example, remove invalid example, add comment | WP06 | | [D] |
| T037 | Unit tests: digit-prefix slugs accepted; existing rejections unchanged | WP06 | P | [D] |
| T038 | Integration test: `create "070-new-feature"` passes slug validation | WP06 | P | [D] |

---

## Work Package WP01: Fix status.json dirty-git (#524)

**Goal**: Make all status read paths idempotent — no write to disk unless the event log actually changed.
**Priority**: P0 (blocks CI pipelines and agent workflows)
**Independent Test**: After running `spec-kitty agent tasks status` against a clean git repo, `git status --porcelain` is empty.
**Prompt**: `tasks/WP01-fix-status-json-dirty-git.md`
**Requirement Refs**: FR-001, FR-002, FR-003, NFR-001

### Included Subtasks

- [ ] T001 Change `reduce()` to derive `materialized_at` from last event timestamp (WP01)
- [ ] T002 Add skip-write guard to `materialize()` — compare bytes, skip if identical (WP01)
- [ ] T003 Fix `materialize_if_stale()` return to call `reduce()` not `materialize()` (WP01)
- [ ] T004 [P] Unit tests: `reduce()` determinism — same events → same `materialized_at` (WP01)
- [ ] T005 [P] Unit tests: `materialize()` idempotency — two calls, one write (WP01)
- [ ] T006 [P] Integration test: clean git tree after read-only status commands (WP01)

### Implementation Notes

- `reducer.py:reduce()` — both the empty case (line ~127) and the normal case (line ~157) call `_now_utc()`. Fix: normal case uses `sorted_events[-1].at`; empty case uses `""`.
- `reducer.py:materialize()` — after computing `json_str`, read `out_path` if it exists and compare with `out_path.read_text()`. Skip `os.replace` if identical.
- `views.py:materialize_if_stale()` — final `return materialize(feature_dir)` (line ~154) must become `return reduce(read_events(feature_dir))`. NOTE: the `write_derived_views()` call earlier in this function also calls `materialize()` internally; this is handled by T002's skip-write guard. Both T002 and T003 are needed together for a fully clean fix.
- Existing `test_reducer.py` uses `pytest.mark.fast` — add new test cases to the same file following existing `_make_event()` helper.

### Dependencies

None (independent).

### Risks

- Consumers that assumed `materialized_at` was a "freshness" wall-clock timestamp may behave differently. The field's semantics shift to "timestamp of last event." Any consumer that compared `materialized_at` to `datetime.now()` to detect stale cache should be updated or will incorrectly infer the cache is perpetually stale.

---

## Work Package WP02: Add wps_manifest Module (#525 core)

**Goal**: New `wps_manifest.py` module providing the Pydantic data model, YAML loader, and tasks.md generator that WP03 and WP04 depend on.
**Priority**: P0 (WP03 and WP04 depend on this)
**Independent Test**: `from specify_cli.core.wps_manifest import load_wps_manifest` works; loading a valid wps.yaml returns a `WpsManifest`; loading an absent path returns None; loading malformed YAML raises ValidationError with the failing field name.
**Prompt**: `tasks/WP02-add-wps-manifest-module.md`
**Requirement Refs**: FR-004, FR-005, FR-007, NFR-002, NFR-003

### Included Subtasks

- [ ] T007 Define `WorkPackageEntry` and `WpsManifest` Pydantic models (WP02)
- [ ] T008 Implement `load_wps_manifest()` — ruamel.yaml loader with presence tracking (WP02)
- [ ] T009 Implement `dependencies_are_explicit()` helper — detect present-empty `[]` vs absent key (WP02)
- [ ] T010 Implement `generate_tasks_md_from_manifest()` — human-readable tasks.md generator (WP02)
- [ ] T011 [P] Write `src/specify_cli/schemas/wps.schema.json` (JSON Schema Draft 2020-12) (WP02)
- [ ] T012 [P] Unit tests: load, absent returns None, malformed raises ValidationError with field name (WP02)
- [ ] T013 [P] Unit tests: `dependencies_are_explicit` for present-empty vs absent key (WP02)
- [ ] T014 [P] Unit tests: `generate_tasks_md_from_manifest` preserves WP titles, deps, subtask counts (WP02)

### Implementation Notes

- Use `ruamel.yaml` (charter standard) with `YAML(typ="safe")` for loading.
- Track whether `dependencies` key was present: after `yaml.load()` returns a raw dict, check `"dependencies" in raw_wp_dict` before constructing the Pydantic model. Store this as `_dependencies_explicit: bool` on the model (private field, not part of schema) or pass as a separate set.
- `generate_tasks_md_from_manifest()` output must include WP titles, dependency lines, and subtask counts — see `data-model.md` for required fields.
- JSON Schema file at `src/specify_cli/schemas/` (create directory if absent). Use `$schema: https://json-schema.org/draft/2020-12/schema`.
- T011 and T012-T014 are parallel-safe — the schema file and the tests can be written simultaneously with the implementation.

### Dependencies

None (independent).

### Risks

- `ruamel.yaml` `YAML(typ="safe")` mode doesn't expose the raw dict the same way as `dict`. Use `yaml.load()` which returns a Python dict for safe-mode, and inspect `"dependencies" in result["work_packages"][i]` before Pydantic validation.

---

## Work Package WP03: Integrate wps.yaml into finalize-tasks (#525 integration)

**Goal**: Update `finalize_tasks()` to use wps.yaml as the authoritative dependency source when present; regenerate tasks.md from the manifest after processing.
**Priority**: P0
**Independent Test**: A wps.yaml with an explicit empty dep list for a work package, combined with misleading prose in tasks.md, leaves that work package with no deps after finalize-tasks runs.
**Prompt**: `tasks/WP03-integrate-wps-yaml-into-finalize-tasks.md`
**Requirement Refs**: FR-006, FR-007, FR-008, FR-011, FR-012, C-006

### Included Subtasks

- [ ] T015 Add wps.yaml detection at top of `finalize_tasks()` — load manifest, build `wp_dependencies` (WP03)
- [ ] T016 Bypass prose parser when wps.yaml present (tier 0 takes precedence) (WP03)
- [ ] T017 Add tasks.md regeneration step when wps.yaml present (WP03)
- [ ] T018 [P] Integration test: wps.yaml present → manifest deps used, prose parser skipped (WP03)
- [ ] T019 [P] Integration test: explicit empty dep list in wps.yaml protects WP from prose-inferred deps (WP03)
- [ ] T020 [P] Integration test: tasks.md overwritten with manifest-generated content (WP03)
- [ ] T021 [P] Integration test: no wps.yaml → prose parser path unchanged (WP03)

### Implementation Notes

- In `mission.py:finalize_tasks()`, before the existing `if tasks_md.exists():` block (around line 1278), add a wps.yaml check:
  ```python
  wps_manifest = load_wps_manifest(feature_dir)  # returns None if absent
  if wps_manifest is not None:
      wp_dependencies = {e.id: e.dependencies for e in wps_manifest.work_packages
                         if dependencies_are_explicit(e)}
      # Also include WPs with no explicit deps as empty:
      for e in wps_manifest.work_packages:
          if e.id not in wp_dependencies:
              wp_dependencies[e.id] = []
  ```
- After the existing WP frontmatter writing step, if `wps_manifest is not None`, regenerate tasks.md:
  ```python
  tasks_md.write_text(generate_tasks_md_from_manifest(wps_manifest, mission_slug), encoding="utf-8")
  ```
- The existing prose parser block (`if tasks_md.exists(): ... _shared_parse_deps(tasks_content)`) is skipped entirely when wps.yaml is present.
- Tests go in `tests/tasks/test_finalize_tasks_wps_yaml_unit.py` (new file), following the mock-patch pattern in `test_finalize_tasks_json_output_unit.py`.

### Dependencies

- WP02 (requires load_wps_manifest, dependencies_are_explicit, generate_tasks_md_from_manifest)

### Risks

- `finalize_tasks()` is a 700+ line function. Keep the wps.yaml addition minimal and well-isolated — a single block at the start of the dependency resolution section, with a clearly named variable (`wps_manifest`).

---

## Work Package WP04: Update Planning Templates and Migration (#525 prompts)

**Goal**: Rewrite `tasks-outline.md` and `tasks-packages.md` source templates to produce/consume `wps.yaml`; write a new migration that propagates these changes to existing installations.
**Priority**: P1 (planning UX improvement; not a runtime bug)
**Independent Test**: After `spec-kitty upgrade` on a project with the old tasks-outline prompt, the deployed tasks-outline file instructs the LLM to write `wps.yaml` (not `tasks.md`). The `detect()` method of the new migration returns True for stale files and False after apply.
**Prompt**: `tasks/WP04-update-planning-templates-and-migration.md`
**Requirement Refs**: FR-009, FR-010

### Included Subtasks

- [ ] T022 Rewrite `tasks-outline.md` template — produce wps.yaml, not tasks.md (WP04)
- [ ] T023 Rewrite `tasks-packages.md` template — read/update wps.yaml, generate WP files (WP04)
- [ ] T024 Write `m_3_2_0_update_planning_templates.py` migration with detect + apply (WP04)
- [ ] T025 [P] Migration unit tests: detect returns True/False correctly (WP04)
- [ ] T026 [P] Migration unit tests: apply overwrites stale files, respects agent config, idempotent (WP04)

### Implementation Notes

- **tasks-outline.md** new Purpose: "Create `wps.yaml` — the structured WP manifest." Remove all instructions to write `tasks.md` prose. Add the wps.yaml YAML schema example (from data-model.md). State explicitly: "Do NOT write tasks.md — it is generated by finalize-tasks from wps.yaml."
- **tasks-packages.md**: Change Step 2 from "Read `feature_dir/tasks.md`" to "Read `feature_dir/wps.yaml` — the manifest written in the previous step." Update Step 4 (Dependencies) to "Update the `dependencies` and `owned_files` fields in `wps.yaml` for each WP as you process it." Keep all WP prompt file generation instructions unchanged.
- **Migration** `m_3_2_0_update_planning_templates.py`:
  - Pattern exactly: `m_2_1_3_restore_prompt_commands.py` (see lines 221–310)
  - `_STALE_MARKER = "Create \`tasks.md\`"` (note: backtick-escaped in Python string)
  - `detect()` — iterate configured agent dirs, check for stale marker in any `spec-kitty.tasks-outline.*` file
  - `apply()` — use `_get_runtime_command_templates_dir()` + `_render_full_prompt()` (import from m_2_1_3's helpers) to overwrite stale files
  - Register with `@MigrationRegistry.register`, `target_version = "3.2.0"`
- Tests go in `tests/upgrade/migrations/test_m_3_2_0_update_planning_templates.py`

### Dependencies

- WP02 (migration references schema from wps_manifest module in its description/docs only; not a runtime import dependency)

### Risks

- `_get_runtime_command_templates_dir()` and `_render_full_prompt()` are internal helpers in `m_2_1_3`. Import them or extract them to a shared `migration_helpers.py`. Do not duplicate the logic.

---

## Work Package WP05: Implement Query Mode for spec-kitty next (#526)

**Goal**: Bare `spec-kitty next` calls (no `--result`) return current state without advancing the DAG; output begins with the SC-003 verbatim label.
**Priority**: P0 (ghost completions corrupt mission history)
**Independent Test**: Before running `spec-kitty next`, record the current step ID from the run snapshot. After running `spec-kitty next` without `--result`, the step ID is unchanged. The first line of stdout is `[QUERY — no result provided, state not advanced]`.
**Prompt**: `tasks/WP05-implement-query-mode-for-next.md`
**Requirement Refs**: FR-012, FR-013, FR-014, FR-015, FR-016, NFR-004, C-005

### Included Subtasks

- [ ] T027 Add `DecisionKind.query` constant and `is_query: bool = False` to `Decision` dataclass (WP05)
- [ ] T028 Implement `query_current_state()` in `runtime_bridge.py` — read state without advancing (WP05)
- [ ] T029 Change `result` default to `None` in `next_cmd.py`; add query mode branch (WP05)
- [ ] T030 Add explicit `is_query` branch to `_print_human()` — SC-003 verbatim label as first line (WP05)
- [ ] T031 [P] Unit test: bare call does not advance state machine (WP05)
- [ ] T032 [P] Unit test: query output begins with `[QUERY — no result provided, state not advanced]` verbatim (WP05)
- [ ] T033 [P] Unit test: `--result success` still advances (no regression) (WP05)
- [ ] T034 [P] Unit test: JSON output includes `"is_query": true` (WP05)

### Implementation Notes

- `decision.py`: Add `query = "query"` to `DecisionKind`. Add `is_query: bool = False` field to `Decision` dataclass. Update `to_dict()` to include `is_query`.
- `runtime_bridge.py:query_current_state()`: 
  1. Call `get_or_start_run()` (idempotent — only starts a run if none exists)
  2. Call `_read_snapshot(Path(run_ref.run_dir))` from `spec_kitty_runtime.engine`
  3. Return `Decision(kind=DecisionKind.query, is_query=True, reason=None, mission_state=current_step_id, ...)`
  4. Do NOT call `next_step()` — this is the key invariant
- `next_cmd.py`: Change `result: str = "success"` to `result: str | None = None`. Add block immediately after `mission_slug` resolution: `if result is None: decision = query_current_state(...); print/return`.
- `_print_human()`: Add `if getattr(decision, "is_query", False):` block at the very top. Print `"[QUERY — no result provided, state not advanced]"` verbatim as line 1, then `"  Mission: {mission} @ {step}"`, then progress. Return early. Do NOT enter the normal `[{kind.upper()}]` path.
- Add new test file `tests/next/test_query_mode_unit.py`. Existing `test_next_command_integration.py` can be extended for regression tests (T033).

### Dependencies

None (independent).

### Risks

- `_read_snapshot` is a private function in `spec_kitty_runtime.engine`. If it's renamed or moved, query mode breaks silently. Add a `# type: ignore` comment noting the private-API dependency, or wrap in a try/except that returns a `DecisionKind.blocked` result on ImportError.

---

## Work Package WP06: Fix Slug Validator (#527)

**Goal**: Update `KEBAB_CASE_PATTERN` to accept digit-prefixed slugs; update error message and add tests.
**Priority**: P1
**Independent Test**: `spec-kitty agent mission create "070-test-slug" --json` (or the equivalent Python API call) does not raise `MissionCreationError` for the slug. `User-Auth` still raises an error.
**Prompt**: `tasks/WP06-fix-slug-validator.md`
**Requirement Refs**: FR-017, FR-018, FR-019

### Included Subtasks

- [ ] T035 Update `KEBAB_CASE_PATTERN` regex to accept digit-prefixed slugs (WP06)
- [ ] T036 Update error message — add valid digit-prefix example, remove invalid example, add comment (WP06)
- [ ] T037 [P] Unit tests: digit-prefix slugs accepted; existing rejections unchanged (WP06)
- [ ] T038 [P] Integration test: `create "070-new-feature"` passes slug validation (WP06)

### Implementation Notes

- `mission_creation.py` line 47: change `r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"` to `r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$"`.
- Update error message (lines 202–211): add `"  - 068-feature-name"` to valid examples; remove `"  - 123-fix (starts with number)"` from invalid examples. Add inline comment `# Intentionally permissive: bare-digit slugs like "069" are accepted; create() prefixes the mission number anyway.`
- Update docstring at line ~179 to include a digit-prefixed example slug.
- New test file `tests/core/test_slug_validator_unit.py` (alongside `test_dependency_parser.py`). Test cases: `"068-feature"` accepted, `"001-foo"` accepted, `"User-Auth"` rejected, `"user_auth"` rejected, `""` rejected, `"069"` accepted (bare digit — intentionally permissive).

### Dependencies

None (independent).
