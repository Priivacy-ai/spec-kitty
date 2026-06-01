---
work_package_id: WP03
title: '#1301 Part B: Contract Fixtures & Sync Lifecycle'
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: tests/contract/
execution_mode: code_change
owned_files:
- tests/contract/fixtures/**
- tests/contract/test_handoff_fixtures.py
- tests/contract/test_example_round_trip.py
- tests/sync/test_lifecycle_readiness.py
- tests/sync/tracker/test_origin_integration.py
- docs/how-to/check_docs_freshness.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This configures your Python implementer persona. Proceed only after the profile is loaded.

---

## Objective

Fix the contract-fixture and sync-lifecycle causes of the #1301 cluster that remain after WP02:
1. Update `WPCreated` fixture payloads to include `actor` and `wp_title` (spec_kitty_events 5.2.0 schema).
2. Add the required `# pydantic_model:` frontmatter to the YAML codeblock in `check_docs_freshness.md`.
3. Fix `test_init_emits_project_init_event_offline` (offline sync lifecycle).
4. Fix `test_event_queued_when_no_websocket` (offline queue tracker origin).

Finish with a full #1301 targeted run confirming zero failures.

---

## Context

After WP02 resolves the packaging and daemon items, these contract/lifecycle tests remain from the #1301 cluster:

- `tests/contract/test_handoff_fixtures.py::test_fixture_payload_passes_emitter_rules[WPCreated:01JMBYA1B2C3]` — payload missing `actor` / `wp_title`.
- `tests/contract/test_example_round_trip.py::test_contract_example_round_trip[...check_docs_freshness.md::block-MISSING_FRONTMATTER]` — YAML codeblock missing `# pydantic_model:` frontmatter.
- `tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline` — offline mode lifecycle.
- `tests/sync/tracker/test_origin_integration.py::test_event_queued_when_no_websocket` — offline-queue path.

**Prerequisite**: WP02 must be complete with its commit merged/present in this worktree.

---

## Subtask T009 — Update WPCreated Contract Fixture Payload

**Purpose**: The `spec_kitty_events 5.2.0` schema for `WPCreated` events requires `actor` and `wp_title` fields. Existing fixture files were written for an older schema.

**Steps**:
1. Run the failing fixture test with long traceback:
   ```bash
   pytest "tests/contract/test_handoff_fixtures.py::test_fixture_payload_passes_emitter_rules[WPCreated:01JMBYA1B2C3]" -v --tb=long
   ```
   The error should show which fields are missing and their expected types.

2. Locate the fixture file. It's likely under `tests/contract/fixtures/` or inline in the test. Search:
   ```bash
   grep -r "WPCreated" tests/contract/ --include="*.py" --include="*.json" -l
   grep -r "01JMBYA1B2C3" tests/contract/ -l
   ```

3. Add the missing fields to the fixture:
   - `actor`: A string identifying who created the WP (e.g., `"claude"` or `"system"`)
   - `wp_title`: A string title for the work package

   Check the `spec_kitty_events` model definition to get the exact field types:
   ```bash
   .venv/bin/python -c "from spec_kitty_events import WPCreated; help(WPCreated)"
   ```

4. Run the test again to confirm it passes.

**Files modified**:
- Fixture file under `tests/contract/fixtures/` (JSON or Python dict)
- Possibly `tests/contract/test_handoff_fixtures.py` if fixtures are inline

**Validation**:
- [ ] `test_fixture_payload_passes_emitter_rules[WPCreated:01JMBYA1B2C3]` passes
- [ ] No other fixture tests regress

---

## Subtask T010 — Add pydantic_model Frontmatter to YAML Codeblock

**Purpose**: The round-trip test parses YAML codeblocks in documentation files and expects a `# pydantic_model: <ClassName>` comment to identify the model for validation. One codeblock is missing this comment.

**Steps**:
1. Run the failing test with long output:
   ```bash
   pytest "tests/contract/test_example_round_trip.py" -v --tb=long -k "check_docs_freshness"
   ```
   The test output should show the file path and codeblock location.

2. Find `check_docs_freshness.md`:
   ```bash
   find . -name "check_docs_freshness.md" 2>/dev/null
   ```

3. Open the file and locate the YAML codeblock that the test exercises. It will be a triple-backtick yaml block without a `# pydantic_model:` comment at the top.

4. Add the comment as the first line inside the YAML block:
   ```yaml
   # pydantic_model: <ClassName>
   field_a: value
   field_b: value
   ```
   The correct `<ClassName>` is shown in the test error or can be inferred from the codeblock content.

5. Run the test to confirm it passes.

**Files modified**: The `check_docs_freshness.md` doc file (under `docs/` or similar).

**Validation**:
- [ ] `test_contract_example_round_trip[...check_docs_freshness.md::block-MISSING_FRONTMATTER]` passes

---

## Subtask T011 — Fix test_init_emits_project_init_event_offline

**Purpose**: The sync lifecycle test for `project_init` event emission in offline mode is failing.

**Steps**:
1. Run the failing test with full traceback:
   ```bash
   pytest "tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline" -v --tb=long -s
   ```

2. Read the test to understand what it expects:
   - What event should be emitted?
   - How does it simulate offline mode (mocking, env var, etc.)?
   - What assertion fails?

3. Investigate whether the failure is:
   a. **A test mock is stale** (the source was refactored and the mock target path changed) — fix the mock.
   b. **Source behavior changed** (the source no longer emits the event in offline mode) — fix the source.
   c. **A new module import issue** from the spec_kitty_events version upgrade — add/update the import.

4. Apply the minimal fix. Stay within `src/specify_cli/sync/` only — do not touch `src/specify_cli/next/` (WP04's domain).

5. Run the test again to confirm it passes.

**Validation**:
- [ ] `test_init_emits_project_init_event_offline` passes
- [ ] No other lifecycle tests regress

---

## Subtask T012 — Fix test_event_queued_when_no_websocket

**Purpose**: The offline-queue integration test for tracker origin event queueing fails when no WebSocket connection is available.

**Steps**:
1. Run the failing test:
   ```bash
   pytest "tests/sync/tracker/test_origin_integration.py::test_event_queued_when_no_websocket" -v --tb=long -s
   ```

2. Read the test to understand the setup: how it patches the WebSocket absence, what event it expects to be queued, and what assertion fails.

3. Investigate the failure cause (same pattern as T011 — stale mock, behavior drift, or import change).

4. Apply the minimal fix within `tests/sync/tracker/test_origin_integration.py` or the source path it exercises (stay within `src/specify_cli/sync/` only — `src/specify_cli/next/` is WP04's scope; if the fix requires changes there, carry the task forward to WP04).

5. Confirm the test passes.

**Validation**:
- [ ] `test_event_queued_when_no_websocket` passes

---

## Subtask T013 — Full #1301 Verification

**Purpose**: Confirm all #1301 cluster tests pass and no regressions were introduced.

**Steps**:
1. Run the full #1301 cluster:
   ```bash
   pytest tests/sync/ tests/contract/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/wp03-after.txt
   ```

2. Confirm zero failures in `tests/sync/` and `tests/contract/`.

3. Run a broader slice to check for regressions:
   ```bash
   pytest tests/ -q --tb=no -p no:cacheprovider --ignore=tests/next/ --ignore=tests/doctrine/ --ignore=tests/charter/ -x 2>&1 | tail -5
   ```

4. **FR-007 — Add/confirm regression test**: Verify that the test changes made in T009–T012 constitute a regression guard. If any fix was purely mechanical (e.g., adding a field to a fixture), add a comment or assertion that would catch the same drift next time. Document which test serves as the regression guard in the commit message.

5. **FR-008 — Record post-fix results**: Save the verification output:
   ```bash
   cat /tmp/wp03-after.txt >> docs/p0-baseline-refresh.md
   # Append a "## WP03 Post-Fix Results" section with the summary line
   ```

6. Commit all WP03 changes:
   ```bash
   git add -p
   git commit -m "fix(#1301): update contract fixtures, YAML frontmatter, and offline sync lifecycle"
   ```

**Note on `owned_files`**: This WP declares `docs/how-to/check_docs_freshness.md` as an owned file, but the actual path is discovered at runtime via `find`. Update the WP frontmatter `owned_files` list to the real path before committing (use `git diff --name-only HEAD` to confirm the actual file changed).

**Validation**:
- [ ] Zero failures in `tests/sync/` and `tests/contract/`
- [ ] No regressions in the broader slice
- [ ] Regression guard identified/added per FR-007
- [ ] Post-fix results appended to `docs/p0-baseline-refresh.md` per FR-008
- [ ] Changes committed

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: Allocated by `lanes.json`.

Implementation command:
```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Definition of Done

- [ ] `test_fixture_payload_passes_emitter_rules[WPCreated:01JMBYA1B2C3]` passes
- [ ] `test_contract_example_round_trip[...check_docs_freshness.md::block-MISSING_FRONTMATTER]` passes
- [ ] `test_init_emits_project_init_event_offline` passes
- [ ] `test_event_queued_when_no_websocket` passes
- [ ] Full `tests/sync/` + `tests/contract/` run shows zero failures
- [ ] No regressions in broader test slice
- [ ] **FR-007**: Regression guard identified/added (documented in commit message)
- [ ] **FR-008**: Post-fix results appended to `docs/p0-baseline-refresh.md`
- [ ] No changes made to `src/specify_cli/next/` (WP04's domain)
- [ ] Changes committed with issue-scoped message

---

## Risks

- **T011/T012 require source changes**: If the source behavior genuinely changed, the fix may be non-trivial. In that case, prefer fixing the source to match the test's documented intent, not the other way around.
- **Scope creep**: Stay within `tests/contract/`, `tests/sync/`, and `src/specify_cli/sync/`. Do not touch `tests/next/`, `tests/doctrine/`, or `tests/charter/`.

## Activity Log

- 2026-06-01T17:23:16Z – claude – Starting WP03 implementation: contract fixtures and sync lifecycle
- 2026-06-01T17:31:31Z – claude – Ready for review (cycle 1/3). All target tests pass after WP02 fix. FR-007 guard documented. FR-008 results appended to docs/p0-baseline-refresh.md. 1951 passed, 0 failed.
