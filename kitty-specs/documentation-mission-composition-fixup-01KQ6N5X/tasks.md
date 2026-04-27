# Tasks — Documentation Mission Composition Fix-up

**Mission**: `documentation-mission-composition-fixup-01KQ6N5X` (mission_id `01KQ6N5X9EHGJPPMZN00X6EVX1`)
**Total subtasks**: 13 across 3 work packages
**Branch**: `main`

## Subtask Index

| ID | Description | WP |
|---|---|---|
| T01 | Author `templates/discover.md` (governance prose for discover phase) | WP01 |
| T02 | Author `templates/audit.md` | WP01 |
| T03 | Author `templates/design.md` | WP01 |
| T04 | Author `templates/generate.md` | WP01 |
| T05 | Author `templates/validate.md` | WP01 |
| T06 | Author `templates/publish.md` | WP01 |
| T07 | Author `templates/accept.md` | WP01 |
| T08 | Author `tests/specify_cli/test_documentation_prompt_resolution.py` parametrized over 7 step ids | WP01 |
| T09 | Extend integration walk: full-advancement test through 6 actions via `decide_next_via_runtime` | WP02 |
| T10 | Extend integration walk: per-action paired-trail-record assertions | WP02 |
| T11 | Replace direct `_check_composed_action_guard` call with `decide_next_via_runtime` blocked-decision assertion | WP02 |
| T12 | Fix `quickstart.md` JSON field references (use `step_id` / `preview_step`, never `issued_step_id`) | WP03 |
| T13 | Run dogfood smoke that issues a composed action; capture paired trail records; commit `evidence/smoke-v2.md` | WP03 |

---

## WP01 — Ship documentation prompt templates

**Goal**: every documentation step returns a non-null `prompt_file`.
**Closes**: F-1, FR-001, FR-002, SC-001.
**Independent test**: `tests/specify_cli/test_documentation_prompt_resolution.py` parametrized over 7 step ids.
**Dependencies**: none.

- [ ] T01 Author `src/specify_cli/missions/documentation/templates/discover.md` (≥30 lines governance prose)
- [ ] T02 Author `src/specify_cli/missions/documentation/templates/audit.md`
- [ ] T03 Author `src/specify_cli/missions/documentation/templates/design.md`
- [ ] T04 Author `src/specify_cli/missions/documentation/templates/generate.md`
- [ ] T05 Author `src/specify_cli/missions/documentation/templates/validate.md`
- [ ] T06 Author `src/specify_cli/missions/documentation/templates/publish.md`
- [ ] T07 Author `src/specify_cli/missions/documentation/templates/accept.md`
- [ ] T08 Author `tests/specify_cli/test_documentation_prompt_resolution.py` (parametrize 7 steps; assert `Decision.prompt_file` resolves to an existing non-empty file)

## WP02 — Deepen integration walk

**Goal**: integration walk advances all 6 actions via dispatch and asserts dispatch-level guard failures.
**Closes**: F-3, F-4, FR-003, FR-004, FR-005, SC-003, SC-004.
**Independent test**: the new tests in `tests/integration/test_documentation_runtime_walk.py`.
**Dependencies**: WP01 (so the walk gets non-null prompt_files when it advances actions).

- [ ] T09 Add `test_full_advancement_through_six_actions` — drive 6 sequential advances via `decide_next_via_runtime`, write happy-path artifacts before each, assert each succeeds.
- [ ] T10 Add `test_paired_trail_records_per_action` — after the full walk, inspect `<repo>/.kittify/events/profile-invocations/` and assert one paired `started`/`done` record per advancing action.
- [ ] T11 Refactor `test_missing_artifact_blocks_with_structured_failure` to call `decide_next_via_runtime` (not `_check_composed_action_guard()` directly); assert `Decision.kind == "blocked"`, failures naming `spec.md`, and snapshot before/after equal.

## WP03 — Quickstart fix + real dogfood smoke

**Goal**: quickstart runs without KeyError; new smoke evidence shows action issuance + paired trail records.
**Closes**: F-2, F-5, FR-007, FR-008, FR-009, SC-002, SC-005, SC-006, NFR-005 hard gate.
**Independent test**: `evidence/smoke-v2.md` shows `kind: success` (or `step_id`) and a paired-trail-record section.
**Dependencies**: WP01 (smoke needs templates to actually dispatch with a usable prompt) and WP02 (so the integration tests prove the same path the smoke walks).

- [ ] T12 Edit `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md`: replace `d['issued_step_id']` with `d.get('step_id') or d.get('preview_step')`; update the "Expected outcomes" prose to match the actual `Decision` schema.
- [ ] T13 Run a real smoke that issues an action: temp repo outside spec-kitty tree, `uv --project`, `spec-kitty next` followed by an action issuance (read predecessor smoke transcript and research walk to find the correct flag/sequence to issue an action). Capture stdout to `evidence/smoke-v2.md` including: command sequence, `next.json`, action-issuance JSON, contents of `<temp_repo>/.kittify/events/profile-invocations/` (paired records), grep showing zero substantive `--directory` uses. Cleanup the temp repo.

## Branch Strategy

Single lane (`lane-a`). WP01 → WP02 → WP03 sequential by dependency.

## Owned files

- WP01: `src/specify_cli/missions/documentation/templates/{discover,audit,design,generate,validate,publish,accept}.md` + `tests/specify_cli/test_documentation_prompt_resolution.py`
- WP02: `tests/integration/test_documentation_runtime_walk.py` (edit only)
- WP03: `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md` (edit) + `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke-v2.md` (new)
