---
work_package_id: WP04
title: Audit-Mode WP Scope Relaxation
dependencies: []
requirement_refs:
- C-004
- FR-009
- FR-010
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-067-runtime-recovery-and-audit-safety
base_commit: 3d2111f0a8ae6f38cc87624d0da7a2f93d012fad
created_at: '2026-04-06T18:54:42.111429+00:00'
subtasks: [T018, T019, T020, T021, T022]
shell_pid: '90780'
history:
- timestamp: '2026-04-06T18:43:32+00:00'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/ownership/
execution_mode: code_change
owned_files:
- src/specify_cli/frontmatter.py
- src/specify_cli/ownership/models.py
- src/specify_cli/ownership/validation.py
- tests/specify_cli/ownership/**
- tests/specify_cli/test_frontmatter*
---

# WP04: Audit-Mode WP Scope Relaxation

## Objective

Enable audit work packages to operate across the entire codebase without being forced into fake narrow file ownership. Audit/cutover WPs should be definable with codebase-wide scope, and validation should explicitly include command template and documentation directories as audit targets.

**Issue**: [#442](https://github.com/Priivacy-ai/spec-kitty/issues/442)

## Context

Currently all WPs are identical in scope model — there is zero WP-type distinction. The ownership model at `src/specify_cli/ownership/` enforces:
- `validate_no_overlap()` at `validation.py:81-105` — no two WPs may own the same files
- `validate_authoritative_surface()` at `validation.py:108-132` — authoritative_surface must be prefix of owned_files
- `validate_execution_mode_consistency()` at `validation.py:135-173` — execution_mode matches file paths

These rules are correct for narrow implementation WPs but make it impossible to define an audit WP that needs to scan the entire repository. Currently, audit WPs must fabricate narrow ownership to pass validation, which defeats their purpose.

WP frontmatter fields are defined in `frontmatter.py:41-58` (`WP_FIELD_ORDER`). There is no `scope` field.

### Key files

| File | Line(s) | What |
|------|---------|------|
| `src/specify_cli/frontmatter.py` | 41-58 | WP_FIELD_ORDER — field list for frontmatter |
| `src/specify_cli/frontmatter.py` | 283-296 | Required field validation |
| `src/specify_cli/ownership/models.py` | 14-23 | ExecutionMode enum (CODE_CHANGE, PLANNING_ARTIFACT) |
| `src/specify_cli/ownership/validation.py` | 81-105 | `validate_no_overlap()` |
| `src/specify_cli/ownership/validation.py` | 108-132 | `validate_authoritative_surface()` |
| `src/specify_cli/ownership/validation.py` | 135-173 | `validate_execution_mode_consistency()` |
| `src/specify_cli/ownership/validation.py` | 176-199 | `validate_all()` — runs all validations |

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Subtasks

### T018: Add `scope` Field to Frontmatter

**Purpose**: Add an optional `scope` field to WP frontmatter that allows declaring codebase-wide ownership.

**Steps**:

1. In `src/specify_cli/frontmatter.py`, add `"scope"` to `WP_FIELD_ORDER` (line 41-58):
   - Position: after `execution_mode` or `owned_files` (logical grouping)
   - Values: `"codebase-wide"` or omitted (implicit narrow/per-WP default)

2. **CRITICAL**: This field MUST be optional. Do NOT add it to required-field validation at lines 283-296. When `scope` is absent from a WP's frontmatter, all behavior remains exactly as it is today.

3. The field is parsed by the existing `read()` function (lines 68-115) which returns all YAML keys. No special parsing needed — just include in the field order for canonical sorting.

**Validation**:
- [ ] `scope: codebase-wide` is parsed correctly from frontmatter
- [ ] Omitting `scope` produces no error (backward compatible)
- [ ] Field appears in correct position when frontmatter is written back

### T019: Relax Ownership Validation for Codebase-Wide Scope

**Purpose**: When a WP declares `scope: codebase-wide`, skip the ownership validations that enforce narrow scope.

**Steps**:

1. In `validate_no_overlap()` at `validation.py:81-105`:
   - Before computing overlap, filter out WPs with `scope == "codebase-wide"`
   - Codebase-wide WPs are expected to overlap with everything — that's the point
   - Log a note: "Skipping overlap check for WP## (codebase-wide scope)"

2. In `validate_authoritative_surface()` at `validation.py:108-132`:
   - Skip WPs with `scope == "codebase-wide"`
   - Codebase-wide WPs may have `authoritative_surface: "/"` or similar broad value

3. In `validate_execution_mode_consistency()` at `validation.py:135-173`:
   - Relax for codebase-wide WPs: any execution_mode + any paths is valid
   - An audit WP might be `code_change` but touch `kitty-specs/`, or `planning_artifact` but scan `src/`

4. In `validate_all()` at `validation.py:176-199`:
   - Ensure the scope-aware behavior propagates through the aggregate validator

**Validation**:
- [ ] `scope: codebase-wide` WP with `owned_files: ["**/*"]` passes all validations
- [ ] Narrow-scope WPs are still validated as before
- [ ] Mix of codebase-wide and narrow WPs in one mission works correctly

### T020: Define Audit Template Target Paths

**Purpose**: Provide a canonical list of directories that audit WPs should cover, especially command template and documentation directories.

**Steps**:

1. Create an `AUDIT_TEMPLATE_TARGETS` constant (in `ownership/models.py` or a new `audit_targets.py`):
   ```python
   AUDIT_TEMPLATE_TARGETS: tuple[str, ...] = (
       "src/specify_cli/missions/*/command-templates/",
       "docs/",
       ".claude/commands/",
       ".github/prompts/",
       ".gemini/commands/",
       ".cursor/commands/",
       ".qwen/commands/",
       ".opencode/command/",
       ".windsurf/workflows/",
       ".codex/prompts/",
       ".kilocode/workflows/",
       ".augment/commands/",
       ".roo/commands/",
       ".amazonq/prompts/",
   )
   ```

2. This list should be aligned with the 12 agent directories from `AGENT_DIRS` in `m_0_9_1_complete_lane_migration.py`. Consider importing from there or sharing a common source.

3. Provide a utility function `get_audit_targets(repo_root: Path) -> list[Path]` that resolves these patterns to actual directories that exist.

**Validation**:
- [ ] Audit targets include all 12 agent directories
- [ ] Audit targets include `docs/` and `src/**/command-templates/`
- [ ] `get_audit_targets()` filters to directories that actually exist

### T021: Add Finalize-Time Validation for Template/Doc Coverage

**Purpose**: When a mission has audit WPs, validate that they explicitly cover template and documentation directories.

**Steps**:

1. In the finalize-tasks logic (or as a validation hook):
   - After all WP frontmatter is parsed, check if any WP has `scope: codebase-wide`
   - If yes: verify that the combined `owned_files` of codebase-wide WPs covers the audit template targets
   - If audit targets are not covered: emit a warning (not error) listing uncovered directories

2. The check:
   ```python
   for target in get_audit_targets(repo_root):
       covered = any(
           fnmatch(str(target), pattern)
           for wp in codebase_wide_wps
           for pattern in wp.owned_files
       )
       if not covered:
           warnings.append(f"Audit target {target} not covered by any codebase-wide WP")
   ```

3. This is a warning, not a hard error — some missions may intentionally scope audit to specific directories.

**Validation**:
- [ ] Finalize detects uncovered audit targets and warns
- [ ] `scope: codebase-wide` with `owned_files: ["**/*"]` covers all targets (no warnings)
- [ ] Warning is non-blocking (finalize still succeeds)

### T022: Write Tests for Audit Scope

**Test scenarios**:

1. **test_codebase_wide_passes_overlap_validation**: Two WPs with overlapping files where one is codebase-wide — no error
2. **test_narrow_wps_still_fail_overlap**: Two narrow WPs with overlap — error as before
3. **test_codebase_wide_skips_authoritative_surface**: WP with `scope: codebase-wide` and broad authoritative_surface passes
4. **test_scope_field_optional**: WP without `scope` field passes validation normally
5. **test_audit_targets_include_agent_dirs**: Verify `AUDIT_TEMPLATE_TARGETS` covers all 12 agents
6. **test_finalize_warns_uncovered_targets**: Mission with audit WP that doesn't cover docs/ — warning emitted
7. **test_mixed_scope_mission**: Mission with both narrow and codebase-wide WPs validates correctly

**Files**: `tests/specify_cli/ownership/test_audit_scope.py` (new file)

## Definition of Done

- `scope: codebase-wide` field is parseable in WP frontmatter (optional, backward compatible)
- Codebase-wide WPs pass ownership validation without fake narrow scope
- Audit template targets are defined covering all 12 agent dirs + docs/
- Finalize-time validation warns about uncovered template/doc targets
- Existing narrow-scope WPs behave identically
- 90%+ test coverage on new code

## Risks

- Broad audit WPs could accidentally own files that conflict with narrow WPs (mitigate: audit WPs are excluded from overlap checks, but narrow WPs still checked against each other)

## Reviewer Guidance

- Verify `scope` field is truly optional — search for required-field validation lists
- Check that narrow WPs are NOT affected by the scope relaxation
- Verify audit targets list matches AGENT_DIRS from the migration module
