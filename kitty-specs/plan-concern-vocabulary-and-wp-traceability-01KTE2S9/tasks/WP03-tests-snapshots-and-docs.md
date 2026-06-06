---
work_package_id: WP03
title: Tests, Snapshots, and Docs
dependencies:
- WP01
- WP02
requirement_refs:
- FR-010
- FR-012
- FR-013
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-plan-concern-vocabulary-and-wp-traceability-01KTE2S9
base_commit: 4cd236fee28614cf42acc981601ddda14d9887c9
created_at: '2026-06-06T11:57:30.669171+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "98012"
history:
- date: '2026-06-06'
  event: created
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/
execution_mode: code_change
owned_files:
- tests/specify_cli/core/test_wps_manifest.py
- tests/specify_cli/skills/__snapshots__/**
- tests/specify_cli/regression/_twelve_agent_baseline/**
- docs/how-to/create-plan.md
- docs/how-to/generate-tasks.md
- docs/reference/missions.md
- docs/reference/file-structure.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Write unit tests for the new `plan_concern_refs` and `cross_cutting` fields. Run the stale-phrase ripple check to confirm no banned language remains. Regenerate command-renderer snapshots. Update user-facing docs to explain the new concern vocabulary.

---

## Context

WP01 and WP02 must be merged before this WP begins. The test suite, snapshot suite, and docs must all reflect the final state of the template and schema changes.

**Project test standards**:
- `pytest tests/` is the canonical test command
- `PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/skills/test_command_renderer.py` regenerates snapshots
- `mypy --strict` must pass on all modified files
- ≥90% branch coverage on new `wps_manifest.py` paths

Read `tests/specify_cli/core/test_wps_manifest.py` before writing tests to understand existing test patterns and fixtures.

---

## Subtask T010 — Unit tests for plan_concern_refs

**File**: `tests/specify_cli/core/test_wps_manifest.py`

**Purpose**: Test all behaviour of the `plan_concern_refs` field — valid values, invalid values, empty default, and backwards-compatibility.

**Read the existing test file** to understand how fixtures are structured (likely uses `WpsManifest.model_validate(...)` or `load_wps_manifest(...)`).

**Tests to write**:

```python
class TestPlanConcernRefs:
    def test_valid_single_ref(self):
        entry = WorkPackageEntry(id="WP01", title="t", plan_concern_refs=["IC-01"])
        assert entry.plan_concern_refs == ["IC-01"]

    def test_valid_multiple_refs(self):
        entry = WorkPackageEntry(id="WP01", title="t", plan_concern_refs=["IC-01", "IC-23"])
        assert entry.plan_concern_refs == ["IC-01", "IC-23"]

    def test_empty_default(self):
        entry = WorkPackageEntry(id="WP01", title="t")
        assert entry.plan_concern_refs == []

    def test_invalid_no_leading_zero(self):
        with pytest.raises(ValidationError):
            WorkPackageEntry(id="WP01", title="t", plan_concern_refs=["IC-1"])

    def test_invalid_wrong_prefix(self):
        with pytest.raises(ValidationError):
            WorkPackageEntry(id="WP01", title="t", plan_concern_refs=["WP01"])

    def test_invalid_wp_prefix(self):
        with pytest.raises(ValidationError):
            WorkPackageEntry(id="WP01", title="t", plan_concern_refs=["ic-01"])

    def test_backwards_compat_missing_key(self):
        # A wps.yaml dict without plan_concern_refs must parse without error
        raw = {"work_packages": [{"id": "WP01", "title": "t"}]}
        manifest = WpsManifest.model_validate(raw)
        assert manifest.work_packages[0].plan_concern_refs == []

    def test_load_wps_manifest_with_concern_refs(self, tmp_path):
        # Write a wps.yaml with plan_concern_refs and load it
        wps_yaml = tmp_path / "wps.yaml"
        wps_yaml.write_text(
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: Test WP\n"
            "    plan_concern_refs:\n"
            "      - IC-01\n"
            "      - IC-02\n"
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert manifest.work_packages[0].plan_concern_refs == ["IC-01", "IC-02"]
```

**Validation**:
- [ ] All tests pass: `pytest tests/specify_cli/core/test_wps_manifest.py -v -k "PlanConcernRefs"`
- [ ] Coverage includes the validator branch for invalid values

---

## Subtask T011 — Unit tests for cross_cutting and rendering

**File**: `tests/specify_cli/core/test_wps_manifest.py`

**Purpose**: Test `cross_cutting` field defaults, `generate_tasks_md_from_manifest()` rendering of concern refs, and the absence of rendering when refs are empty.

**Tests to write**:

```python
class TestCrossCuttingField:
    def test_default_false(self):
        entry = WorkPackageEntry(id="WP01", title="t")
        assert entry.cross_cutting is False

    def test_explicit_true(self):
        entry = WorkPackageEntry(id="WP01", title="t", cross_cutting=True)
        assert entry.cross_cutting is True

    def test_backwards_compat_missing_key(self):
        raw = {"work_packages": [{"id": "WP01", "title": "t"}]}
        manifest = WpsManifest.model_validate(raw)
        assert manifest.work_packages[0].cross_cutting is False


class TestGenerateTasksMdConcernRefs:
    def test_renders_concern_refs_when_present(self):
        manifest = WpsManifest(work_packages=[
            WorkPackageEntry(
                id="WP01", title="Test", plan_concern_refs=["IC-01", "IC-03"]
            )
        ])
        output = generate_tasks_md_from_manifest(manifest, "test-feature")
        assert "IC-01" in output
        assert "IC-03" in output
        assert "Plan concerns" in output  # or whatever label the renderer uses

    def test_does_not_render_when_empty(self):
        manifest = WpsManifest(work_packages=[
            WorkPackageEntry(id="WP01", title="Test")
        ])
        output = generate_tasks_md_from_manifest(manifest, "test-feature")
        assert "Plan concerns" not in output
        assert "IC-" not in output

    def test_renders_for_some_not_all_wps(self):
        manifest = WpsManifest(work_packages=[
            WorkPackageEntry(id="WP01", title="Has refs", plan_concern_refs=["IC-01"]),
            WorkPackageEntry(id="WP02", title="No refs"),
        ])
        output = generate_tasks_md_from_manifest(manifest, "test-feature")
        # IC-01 appears once (WP01), not twice
        assert output.count("IC-01") == 1
```

**Validation**:
- [ ] All tests pass: `pytest tests/specify_cli/core/test_wps_manifest.py -v -k "CrossCutting or GenerateTasksMdConcernRefs"`
- [ ] `pytest --cov=specify_cli.core.wps_manifest tests/specify_cli/core/test_wps_manifest.py` shows ≥90% branch coverage

---

## Subtask T012 — Stale-phrase ripple check

**Purpose**: Confirm that no banned plan-phase pseudo-WP language remains in any live source template file.

**Run**:
```bash
rg "Parallel Work Analysis|Work Distribution|work-package outline derived from the plan|Break a plan into work packages" \
  src/doctrine/missions/ \
  src/specify_cli/missions/
```

**Expected result**: Zero hits. If hits remain, fix them before proceeding.

**Also check** for "Agent assignments" in planning-context files (plan templates, not WP prompt templates where "agent" in a different sense is valid):
```bash
rg "Agent assignments" src/doctrine/missions/software-dev/templates/
```

Expected: Zero hits.

**Document** the final clean run output in a commit message or comment. The CI ripple check acceptance criterion in the spec (NFR-003) requires this to be verifiable.

**Validation**:
- [ ] All four banned phrases return 0 hits in `src/doctrine/missions/` and `src/specify_cli/missions/`
- [ ] "Agent assignments" returns 0 hits in `src/doctrine/missions/software-dev/templates/`

---

## Subtask T013 — Regenerate command-renderer snapshots

**Purpose**: The command-renderer snapshot tests compare rendered slash-command output against golden files. The WP01 template changes will alter the rendered plan-template content in generated commands — regenerate to update the golden files.

**Run**:
```bash
PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/skills/test_command_renderer.py -v
```

**Then verify** the updated snapshots look correct:
```bash
pytest tests/specify_cli/skills/test_command_renderer.py -v
```

All tests should pass.

**Also check** the twelve-agent regression baseline:
```bash
pytest tests/specify_cli/regression/ -v 2>&1 | head -50
```

If any baseline tests fail due to "Parallel Work Analysis" appearing in expected fixtures, update those fixtures — they are test fixtures for the renderer, not historical artifacts.

**What to look for in updated snapshots**: The regenerated snapshots should contain "Implementation Concern Map" instead of "Parallel Work Analysis". Confirm this visually by inspecting the diff of changed snapshot files:
```bash
git diff tests/specify_cli/skills/__snapshots__/
```

**Validation**:
- [ ] `pytest tests/specify_cli/skills/test_command_renderer.py` passes with exit code 0
- [ ] Updated snapshots contain "Implementation Concern Map" not "Parallel Work Analysis"
- [ ] No unexpected test failures in `tests/specify_cli/regression/`

---

## Subtask T014 — Update user docs

**Purpose**: Update user-facing documentation to explain the new concern vocabulary so planners understand what IC-## means and how plan.md relates to tasks.md.

**Files to check and update** (read each before editing):

1. `docs/how-to/create-plan.md`
   - Add a section or paragraph explaining "Implementation Concern Map" and IC-## IDs
   - Remove any instructions that say "identify work package slices" or similar at the plan phase
   - Explain that `/spec-kitty.tasks` translates concerns into WPs

2. `docs/how-to/generate-tasks.md`
   - Update the introduction to explain tasks receives IC-## concerns from plan.md
   - Add a note that each generated WP should cite `plan_concern_refs`

3. `docs/reference/missions.md`
   - If it describes plan-phase output, update to mention Implementation Concern Map
   - Add IC-## to the glossary or terminology section if one exists

4. `docs/reference/file-structure.md`
   - If it describes `plan.md` structure, update to mention the concern map section

**Key phrases to add** (adapt to the doc's existing tone):
- "Implementation concerns (IC-01, IC-02…) are plan-level architectural units. They are not executable work packages."
- "The Implementation Concern Map in plan.md captures purpose, affected surfaces, and sequencing. `/spec-kitty.tasks` translates these into executable WPs."

**What NOT to change**: Do not rewrite entire docs. Locate the relevant sections and make targeted additions/replacements.

**Validation**:
- [ ] `docs/how-to/create-plan.md` mentions "implementation concern" and "IC-##"
- [ ] `docs/how-to/generate-tasks.md` mentions that tasks translates concerns from plan.md
- [ ] None of the updated docs say "work package" in the context of plan.md output
- [ ] No doc changes introduce implementation details (tech stack, file paths, code)

---

## Branch Strategy

Planning branch: `main`
Merge target: `main`
Execution worktree: allocated by `lanes.json` after `finalize-tasks`
Depends on: WP01 and WP02 merged first

Implement using: `spec-kitty agent action implement WP03 --agent claude`

---

## Definition of Done

- [ ] All new unit tests pass: `pytest tests/specify_cli/core/test_wps_manifest.py`
- [ ] Coverage ≥90% on new `wps_manifest.py` paths
- [ ] Stale-phrase ripple check returns 0 hits
- [ ] Snapshot tests pass after regeneration
- [ ] Updated snapshots contain "Implementation Concern Map" not "Parallel Work Analysis"
- [ ] At least `create-plan.md` and `generate-tasks.md` explain the new terminology
- [ ] `mypy --strict` passes on test files (if applicable per project config)

---

## Reviewer Guidance

1. **Tests**: Verify backwards-compatibility tests exist — a `wps.yaml` without `plan_concern_refs` must parse without error.
2. **Validator coverage**: The validator should be tested for both the valid path (returns the list) and the invalid path (raises `ValidationError`).
3. **Snapshots**: The diff of updated snapshot files should contain "Implementation Concern Map" additions and "Parallel Work Analysis" removals. If snapshots changed but those strings are not present, something else changed unexpectedly.
4. **Docs**: Check that the tone matches the existing doc style. Do not over-engineer — targeted additions are preferred over rewrites.

## Activity Log

- 2026-06-06T11:57:39Z – claude:sonnet-4-6:implementer:implementer – shell_pid=21949 – Assigned agent via action command
- 2026-06-06T12:26:25Z – claude:sonnet-4-6:implementer:implementer – shell_pid=21949 – Ready for review: 28 tests for plan_concern_refs/cross_cutting/check_concern_refs_coverage; stale-phrase fix in plan-template.md; codex/vibe snapshots + twelve-agent baselines regenerated; docs updated with IC-## vocabulary
- 2026-06-06T12:26:56Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=91867 – Started review via action command
- 2026-06-06T12:36:07Z – user – shell_pid=91867 – Moved to planned
- 2026-06-06T12:38:13Z – claude:sonnet-4-6:implementer:implementer – shell_pid=96942 – Started implementation via action command
- 2026-06-06T12:39:50Z – claude:sonnet-4-6:implementer:implementer – shell_pid=96942 – Cycle 2: wired check_concern_refs_coverage into finalize-tasks; verified non-zero callers
- 2026-06-06T12:40:15Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=98012 – Started review via action command
- 2026-06-06T12:41:27Z – user – shell_pid=98012 – Review passed cycle 2: check_concern_refs_coverage wired into finalize-tasks at line 2172; non-fatal yellow warnings only (no sys.exit/typer.Exit follows); all 28 tests pass
