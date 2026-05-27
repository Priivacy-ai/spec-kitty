---
work_package_id: WP02
title: README Governance + chokepoint guards
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:19:05.009307+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008

shell_pid: '36710'
history:
- date: '2026-05-27'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/audit/classifiers/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- README.md
- src/specify_cli/audit/classifiers/wp_files.py
- tests/specify_cli/audit/test_wp_files_classifier.py
- tests/specify_cli/docs/test_readme_governance.py
- src/specify_cli/cli/commands/__init__.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Fix three independent confirmed bugs:
1. **FR-002**: `README.md` is missing a `## Governance layer` section — 6 tests fail
2. **FR-003**: `wp_files.py:92` reads `frontmatter.get("lane")` — a Phase-2 (3.x) regression
3. **FR-004**: `doctrine` CLI group is still registered in `commands/__init__.py` — a regression from mission 01KP54J6

**Closes**: GitHub issues #1308 (FR-002), #1309 (FR-003), #1310 partial (FR-004)

---

## Context

All three bugs are immediately verifiable in current main. The fixes are independent and can be developed in any order within this WP. The most complex is FR-003 because the fix must preserve the "never raises" contract of `classify_wp_files()`.

**Phase-2 invariant (C-003)**: Frontmatter `lane` reads are illegal in 3.x runtime code. The canonical lane read is `specify_cli.status.lane_reader.get_wp_lane(feature_dir, wp_id)`. However, `get_wp_lane()` raises `CanonicalStatusNotFoundError` for missions without a `status.events.jsonl` file (pre-3.0 missions, or missions that haven't run `finalize-tasks`). The guard is mandatory.

---

## Subtask T004 — Pre-check skill file links (FR-002 pre-condition)

**Purpose**: Tests 5 and 6 of `test_readme_governance.py` are link-integrity checks on existing skill files, independent of README content. Run them first to see if they already pass. If they fail, there is pre-existing link-rot that requires a separate fix (file a DIR-013 issue).

**Steps**:

1. Run tests 5 and 6 in isolation:
   ```bash
   pytest tests/specify_cli/docs/test_readme_governance.py -v --tb=short -k "advise_skill or runtime_next"
   ```

2. Read the two skill files to understand their link structure:
   - `.agents/skills/spec-kitty.advise/SKILL.md`
   - `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`

3. If tests 5 or 6 already fail (before you touch README.md): this is a pre-existing broken link. Fix the broken link in the skill file, and file a GitHub issue documenting the pre-existing failure per DIR-013 protocol.

4. If both pass: proceed to T005 knowing tests 5 and 6 are already covered.

**Validation**:
- [ ] Tests 5 and 6 status is known (pass or fail) before editing README.md
- [ ] Pre-existing failures, if any, are filed as GitHub issues

---

## Subtask T005 — Add `## Governance layer` section to README.md (FR-002)

**Purpose**: Add the section so all six assertions in `test_readme_governance.py` pass.

**Read the test file first**:
```bash
cat tests/specify_cli/docs/test_readme_governance.py
```

The six assertions that must all pass:
1. **Heading present**: `## Governance layer` exists in README.md
2. **Trail model linked**: `docs/trail-model.md` is linked somewhere in the section
3. **Host surface linked**: `docs/host-surface-parity.md` is linked somewhere in the section
4. **Command mentions**: The substrings `spec-kitty advise`, `spec-kitty ask`, and `spec-kitty do` all appear within the section
5. **Advise skill links resolve**: All relative `.md` links in `.agents/skills/spec-kitty.advise/SKILL.md` resolve to existing files (checked by the test, not by README content)
6. **Runtime-next skill links resolve**: All relative `.md` links in `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` resolve to existing files (checked by the test, not by README content)

**Steps**:

1. Find the right place to insert in README.md (likely after the CLI overview section, before Contributing or similar)

2. Add a section similar to this (adjust prose to match the README's tone):
   ```markdown
   ## Governance layer

   Spec Kitty includes a governance layer that advises, queries, and acts on your project's
   architectural conventions. Three primary commands drive this layer:

   - `spec-kitty advise` — surfaces relevant doctrine, guidelines, and warnings for the current context
   - `spec-kitty ask` — queries the knowledge base for specific guidance
   - `spec-kitty do` — executes governed actions, ensuring compliance with the trail model

   The governance layer is anchored by two key reference documents:

   - [Trail model](docs/trail-model.md) — defines how spec-kitty traces mission provenance and
     decision history through the project lifecycle
   - [Host surface parity](docs/host-surface-parity.md) — describes the contract between
     spec-kitty and the host project's agent integration surfaces
   ```

3. Run all six governance tests:
   ```bash
   pytest tests/specify_cli/docs/test_readme_governance.py -v
   ```

4. Iterate on the section content until all six pass.

**Files**: `README.md`

**Validation**:
- [ ] All six tests in `test_readme_governance.py` pass
- [ ] Section heading is exactly `## Governance layer` (no trailing space, correct case)
- [ ] Both doc links are present and use relative paths

---

## Subtask T006 — Replace frontmatter lane read in wp_files.py (FR-003)

**Purpose**: `wp_files.py:92` reads `frontmatter.get("lane")` which is illegal in Phase-2 (3.x) code. Replace with a guarded call to `get_wp_lane()` that preserves the "never raises" contract.

**Steps**:

1. Read the current classifier:
   ```bash
   cat -n src/specify_cli/audit/classifiers/wp_files.py
   ```

2. Locate line 92 (approximately):
   ```python
   lane = frontmatter.get("lane") or frontmatter.get("status")
   ```

3. Understand the context: `classify_wp_files()` iterates over WP file paths and needs the lane for each WP. The `feature_dir` (mission directory) and `wp_id` (WP stem, e.g. "WP01") must be derivable from the file path.

4. Replace the lane read with the guarded pattern:
   ```python
   from specify_cli.status.lane_reader import get_wp_lane
   from specify_cli.status.store import has_event_log
   from specify_cli.status.models import CanonicalStatusNotFoundError

   # ... inside the loop over WP files:
   if has_event_log(feature_dir):
       try:
           lane = get_wp_lane(feature_dir, wp_path.stem)
       except CanonicalStatusNotFoundError:
           lane = None
   else:
       lane = None  # pre-3.0 / unfinalized mission — skip terminal-lane evidence
   ```

5. Update the imports at the top of `wp_files.py`; remove the old lane-read imports if they become unused.

6. Run the lane regression guard:
   ```bash
   pytest tests/specify_cli/test_lane_regression_guard.py -v --tb=short
   ```

**Files**: `src/specify_cli/audit/classifiers/wp_files.py`

**Validation**:
- [ ] `test_lane_regression_guard[src/specify_cli/audit/classifiers/wp_files.py]` passes
- [ ] No `frontmatter.get("lane")` or `frontmatter.get("status")` remains in wp_files.py
- [ ] The function still works correctly for missions WITH an event log

---

## Subtask T007 — Add test: classify_wp_files() does not raise on mission without event log (FR-003)

**Purpose**: The "never raises" contract of `classify_wp_files()` must be verified by a new test that exercises the guard path (mission with WP files but no `status.events.jsonl`).

**Steps**:

1. Find the existing test file for wp_files classifier:
   ```bash
   find tests/ -name "*wp_files*" -o -name "*classifier*" | head -10
   ```

2. Add a new test (or add to the existing test file) that:
   - Creates a temporary directory with at least one WP markdown file (e.g., `WP01-something.md` with frontmatter)
   - Ensures there is NO `status.events.jsonl` in that directory
   - Calls `classify_wp_files(tmpdir)` (or however the function is invoked)
   - Asserts it does NOT raise (call succeeds)

3. Example test structure:
   ```python
   def test_classify_wp_files_does_not_raise_without_event_log(tmp_path):
       """classify_wp_files() must not raise for pre-3.0 / unfinalized missions."""
       # Create a WP file without a status.events.jsonl
       wp_file = tmp_path / "WP01-test-task.md"
       wp_file.write_text("---\ntitle: Test\nlane: in_progress\n---\n")
       # No status.events.jsonl created

       # Must not raise CanonicalStatusNotFoundError or any other exception
       from specify_cli.audit.classifiers.wp_files import classify_wp_files
       result = classify_wp_files(tmp_path)  # adjust call signature as needed
       assert result is not None  # basic sanity; exact type depends on implementation
   ```

4. Add `pytestmark = [pytest.mark.unit, pytest.mark.fast]` at the module level of the test file.

5. Run the new test:
   ```bash
   pytest tests/specify_cli/audit/ -v --tb=short -k "event_log"
   ```

**Files**: `tests/specify_cli/audit/test_wp_files_classifier.py` (create if doesn't exist, or add to existing)

**Validation**:
- [ ] New test passes
- [ ] New test uses `tmp_path` (no real mission directory dependency)
- [ ] Test file has `pytestmark = [pytest.mark.unit, pytest.mark.fast]`

---

## Subtask T008 — Remove doctrine CLI group from commands/__init__.py (FR-004)

**Purpose**: The `doctrine` Typer app was supposed to be removed by mission `excise-doctrine-curation-and-inline-references-01KP54J6`. It was re-registered — a regression. Remove it now.

**Steps**:

1. Confirm the current state:
   ```bash
   grep -n "doctrine" src/specify_cli/cli/commands/__init__.py
   ```

   Expect to find:
   - Line 40 (approx): `from . import doctrine as doctrine_module`
   - Line 78 (approx): `app.add_typer(doctrine_module.app, name="doctrine", ...)`

2. Verify the `charter` group registration is NOT on either of these lines (it must remain):
   ```bash
   grep -n "charter" src/specify_cli/cli/commands/__init__.py
   ```

3. Remove ONLY the two doctrine lines (import and add_typer). Leave all other registrations untouched.

4. Run the doctrine-removed tests:
   ```bash
   pytest tests/specify_cli/cli/test_doctrine_cli_removed.py -v
   ```

5. Confirm charter CLI group still works:
   ```bash
   spec-kitty charter --help 2>&1 | head -5
   ```

**Files**: `src/specify_cli/cli/commands/__init__.py`

**Validation**:
- [ ] All three assertions in `test_doctrine_cli_removed.py` pass
- [ ] `spec-kitty charter --help` still works (charter group intact)
- [ ] No `doctrine` import or `add_typer` call remains in `__init__.py`
- [ ] `doctrine.py` module file is NOT deleted (leaving it on disk is fine; it is imported nowhere after deregistration)

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`
- **Execution**: Worktree allocated per computed lane from `lanes.json`

To start implementation:
```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Definition of Done

- [ ] All six `test_readme_governance` assertions pass
- [ ] `test_lane_regression_guard[src/specify_cli/audit/classifiers/wp_files.py]` passes
- [ ] New no-raise test for `classify_wp_files()` on event-log-less mission passes
- [ ] All three `test_doctrine_cli_removed` assertions pass
- [ ] `spec-kitty charter --help` still works
- [ ] New test file has `pytestmark = [pytest.mark.unit, pytest.mark.fast]`

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Test 5 or 6 of readme_governance fails due to pre-existing link rot | Medium | Pre-check in T004; file DIR-013 issue if found |
| has_event_log() import path differs from expected | Low | Read lane_reader.py imports first |
| classify_wp_files() call signature differs from expectation | Low | Read the function signature before writing the test |
| doctrine.py has additional imports used elsewhere | Very low | Verify with grep before deleting lines |

---

## Reviewer Guidance

1. README section must contain all three command names verbatim: `spec-kitty advise`, `spec-kitty ask`, `spec-kitty do`
2. wp_files.py must have zero `frontmatter.get("lane")` or `frontmatter.get("status")` calls
3. New test must exercise the NO-event-log path specifically (not just any classifier test)
4. `commands/__init__.py` must have zero doctrine references; charter must remain
</content>