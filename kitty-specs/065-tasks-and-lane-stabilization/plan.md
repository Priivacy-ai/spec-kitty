# Implementation Plan: Tasks And Lane Stabilization

**Branch**: `main` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/065-tasks-and-lane-stabilization/spec.md`

## Summary

Fix six confirmed bugs in the planning/tasks control plane so that `finalize-tasks` preserves dependency intent, `--validate-only` is genuinely non-mutating, lane computation is complete and explains collapse, `mark-status` handles both task formats, and generated command guidance includes required flags. All changes target existing Python runtime code, templates, and tests.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (YAML), pathlib (filesystem)
**Storage**: Filesystem only (YAML frontmatter, JSONL event logs, JSON manifests)
**Testing**: pytest with 90%+ coverage on modified code, mypy --strict
**Target Platform**: CLI tool (macOS, Linux)
**Project Type**: Single project (existing spec-kitty codebase)
**Performance Goals**: `finalize-tasks` completes in under 5 seconds for features with up to 20 WPs
**Constraints**: Both `agent mission finalize-tasks` and `agent tasks finalize-tasks` must exhibit identical behavior (C-004). No regressions for mid-implementation features (C-005).

## Charter Check

**Testing**: pytest with 90%+ coverage for new code. Integration tests for CLI commands.
**Type checking**: mypy --strict, zero errors on changed files.
**Directives**:
- DIRECTIVE_003 (Decision Documentation): All fix decisions documented in research.md with rationale and alternatives.
- DIRECTIVE_010 (Specification Fidelity): Implementation must match spec FR-001 through FR-015 and FR-010a/b.

No violations. Charter gates pass.

## Project Structure

### Documentation (this feature)

```
kitty-specs/065-tasks-and-lane-stabilization/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Root cause analysis and decisions
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/agent/
│   ├── mission.py        # WP01: finalize_tasks (primary entry point)
│   ├── tasks.py          # WP01: finalize_tasks (legacy entry point), WP04: mark_status
│   └── context.py        # WP05: context resolve
├── lanes/
│   ├── compute.py        # WP02+WP03: compute_lanes, _UnionFind, surface heuristics
│   └── models.py         # WP02+WP03: ExecutionLane, LanesManifest, CollapseReport (new)
├── ownership/
│   ├── inference.py       # WP02: infer_owned_files, src/** fallback
│   └── validation.py      # WP02: _globs_overlap, validate_no_overlap
├── core/
│   └── paths.py           # WP05: require_explicit_feature
├── context/
│   ├── middleware.py       # WP05: --feature → --mission error fix
│   └── store.py            # WP05: --feature → --mission error fix
├── shims/
│   └── generator.py        # WP05: shim template --mission hint
├── frontmatter.py          # WP01: FrontmatterManager (correct API)
├── tasks_support.py        # WP01: set_scalar (broken for lists)
└── missions/software-dev/command-templates/
    └── tasks.md            # WP05: context resolve example, task format instructions

tests/
├── specify_cli/cli/commands/agent/
│   ├── test_feature_finalize_bootstrap.py    # WP01: finalize + validate-only tests
│   └── test_tasks_canonical_cleanup.py       # WP01: tasks.py finalize tests
├── tasks/
│   └── test_finalize_tasks_json_output_unit.py  # WP01: JSON output schema tests
├── core/
│   ├── test_dependency_parser.py             # WP01: shared parser tests
│   └── test_paths.py                         # WP05: require_explicit_feature tests
├── lanes/
│   ├── test_compute.py                       # WP03: lane computation tests
│   ├── test_models.py                        # WP03: model serialization tests
│   └── test_collapse_report.py               # WP03: collapse report tests
├── ownership/
│   ├── test_inference.py                     # WP02: ownership inference tests
│   └── test_validation.py                    # WP02: glob validation tests
├── context/
│   ├── test_middleware.py                    # WP05: middleware error message tests
│   └── test_store.py                         # WP05: store error message tests
├── shims/
│   └── test_generator.py                     # WP05: shim template tests
└── git_ops/
    ├── test_atomic_status_commits_unit.py    # WP04: mark-status tests
    └── test_mark_status_pipe_table.py        # WP04: pipe-table mutation tests
```

---

## WP01 — Dependency and Frontmatter Truth

**Issues**: #406, #417
**Files**:
- `src/specify_cli/cli/commands/agent/mission.py` (primary)
- `src/specify_cli/cli/commands/agent/tasks.py` (legacy)
- `src/specify_cli/frontmatter.py` (correct API)
- `src/specify_cli/tasks_support.py` (broken `set_scalar`)

### Change 1: Expand dependency parser to support bullet-list format

**In `mission.py` around lines 1802-1819**, add a third pattern after the existing two:

```
Pattern 3: Bullet-list dependencies under a "Dependencies" heading
  Match "### Dependencies" (or "**Dependencies**") followed by
  lines starting with "- WP##" (with optional trailing text).
```

The parser currently has:
- Pattern 1 (line 1802): `Depends on WP01, WP02` — keep
- Pattern 2 (line 1811): `**Dependencies**: WP01, WP02` — keep
- Pattern 3 (new): Bullet-list under a Dependencies heading

Implementation approach: After extracting `section_content` for each WP, scan for a line matching `^#{1,4}\s*\*?\*?Dependencies\*?\*?\s*$` (case-insensitive). If found, collect all subsequent lines matching `^\s*[-*]\s*(WP\d{2})` until the next heading or blank line.

### Change 2: Consolidate tasks.py to use the same parser

**In `tasks.py` lines 1665-1692**, replace the independent regex with a call to a shared extraction function. Extract the parser from `mission.py` into a reusable module function (e.g., `specify_cli.core.dependency_graph.parse_dependencies_from_tasks_md(content: str) -> dict[str, list[str]]`).

Both `mission.py` and `tasks.py` call this single function. This satisfies C-004 (identical behavior).

### Change 3: Disagree-loud on non-empty conflict (FR-002a)

After parsing dependencies from `tasks.md`, before writing frontmatter:

```python
existing_deps = frontmatter.get("dependencies", [])
parsed_deps = dependencies_map.get(wp_id, [])

if existing_deps and parsed_deps and set(existing_deps) != set(parsed_deps):
    # Non-empty disagreement: fail with diagnostic
    errors.append(f"{wp_id}: frontmatter has {existing_deps}, "
                  f"tasks.md parsed {parsed_deps}")
```

If errors are non-empty, finalize-tasks fails before writing any files.

If parsed is empty and existing is non-empty: preserve existing (FR-002).
If parsed is non-empty and existing is empty: write parsed.
If both agree: write (idempotent).

### Change 4: Fix set_scalar type mismatch in tasks.py

**At `tasks.py:1716`**, replace:
```python
updated_front = set_scalar(frontmatter, "dependencies", deps)
```
with the `FrontmatterManager` API or direct dict assignment + `write_frontmatter()`:
```python
fm_dict, body = read_frontmatter(wp_file)
fm_dict["dependencies"] = deps
write_frontmatter(wp_file, fm_dict, body)
```

### Change 5: Gate all mutations on validate_only (FR-004)

**In `mission.py`**: Move the `validate_only` check BEFORE the frontmatter write loop (before line 1419). When `validate_only=True`, accumulate would-be changes in a report dict but do not call `write_frontmatter()`.

**In `tasks.py`**: Wrap `wp_file.write_text()` at line 1720 in `if not validate_only:`. Still compute the dependency map and report, but don't write.

### Change 6: Accurate mutation reporting (FR-003)

In both implementations, track:
- `modified_wps`: WPs whose frontmatter actually changed
- `unchanged_wps`: WPs whose frontmatter was already correct
- `preserved_wps`: WPs where existing non-empty deps were kept (parsed was empty)

Report all three in JSON output.

### Tests

- `test_bullet_list_dependency_parsing`: tasks.md with bullet-list deps parsed correctly
- `test_inline_dependency_parsing_preserved`: existing inline format still works
- `test_non_empty_disagreement_fails`: frontmatter says [WP01], parser says [WP02] → error
- `test_empty_parse_preserves_existing`: parser finds nothing, existing [WP01] kept
- `test_validate_only_no_file_writes`: assert files byte-identical before/after
- `test_validate_only_reports_would_be_changes`: JSON output includes mutation report
- `test_set_scalar_not_used_for_lists`: verify FrontmatterManager API used
- `test_both_entry_points_identical`: same input → same output from both commands

---

## WP02 — Lane Materialization Correctness

**Issues**: #422 (completeness half)
**Files**:
- `src/specify_cli/lanes/compute.py`
- `src/specify_cli/ownership/inference.py`
- `src/specify_cli/ownership/validation.py`

### Change 1: Assert all executable WPs are lane-assigned (FR-006)

**In `compute.py` after line 219** (after `raw_groups = uf.groups()`), add:

```python
# Verify every executable WP appears in a group
assigned_wps = set()
for group in raw_groups.values():
    assigned_wps.update(group)

missing = set(code_wp_ids) - assigned_wps
if missing:
    raise LaneComputationError(
        f"Executable WPs not assigned to any lane: {sorted(missing)}. "
        f"Check dependency_graph keys and ownership_manifests."
    )
```

### Change 2: Diagnostic for planning-artifact exclusions (FR-006)

Add a `planning_artifact_wps` field to `LanesManifest` or return it alongside:

```python
planning_wps = [wp_id for wp_id in all_wp_ids
                if ownership_manifests.get(wp_id, None)
                and ownership_manifests[wp_id].execution_mode == ExecutionMode.PLANNING_ARTIFACT]
```

Include in JSON output so operators can verify exclusions.

### Change 3: Fail on unassignable executable WPs (FR-007)

**In `compute.py` lines 177-181**, when a WP has no ownership manifest AND is not a planning artifact, fail:

```python
manifest = ownership_manifests.get(wp_id)
if manifest and manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
    continue
if not manifest:
    raise LaneComputationError(
        f"Executable WP {wp_id} has no ownership manifest. "
        f"Ensure owned_files and execution_mode are set in frontmatter."
    )
code_wp_ids.append(wp_id)
```

### Change 4: Warn on zero-match owned_files globs (FR-014)

**In `ownership/validation.py`**, add a new function:

```python
def validate_glob_matches(manifests: dict[str, OwnershipManifest],
                          repo_root: Path) -> list[str]:
    """Warn when owned_files globs match zero files."""
    warnings = []
    for wp_id, manifest in manifests.items():
        for glob_pattern in manifest.owned_files:
            matches = list(repo_root.glob(glob_pattern))
            if not matches:
                warnings.append(
                    f"{wp_id}: owned_files glob '{glob_pattern}' "
                    f"matches zero files in repository"
                )
    return warnings
```

Call this during finalize-tasks and include warnings in JSON output.

### Change 5: Warn on src/** fallback (FR-015)

**In `ownership/inference.py` line 135-136**, add a warning return:

```python
if not globs:
    globs = ["src/**"]
    # Return alongside a warning flag that callers can surface
```

Modify `infer_owned_files` to return `(globs, warnings)` tuple, or add the warning to a module-level warning collector. The finalize-tasks caller surfaces this in its output.

### Tests

- `test_all_executable_wps_in_lanes`: N WPs in, N WPs appear in lanes.json
- `test_planning_artifact_excluded_with_diagnostic`: planning WP excluded, listed in summary
- `test_missing_manifest_fails_diagnostically`: WP without manifest → error with WP name
- `test_zero_match_glob_warning`: owned_files pointing to nonexistent path → warning
- `test_src_fallback_warning`: WP with no paths → warning about synthetic scope

---

## WP03 — Realistic Parallelism Preservation

**Issues**: #423
**Files**:
- `src/specify_cli/lanes/compute.py`
- `src/specify_cli/lanes/models.py`

### Change 1: Add CollapseReport data model

**In `models.py`**, add:

```python
@dataclass(frozen=True)
class CollapseEvent:
    wp_a: str
    wp_b: str
    rule: str          # "dependency", "write_scope_overlap", "surface_heuristic"
    evidence: str      # e.g., "src/core/** overlaps src/core/utils/**"

@dataclass
class CollapseReport:
    events: list[CollapseEvent]
    independent_wps_collapsed: int  # count of WPs independent in dep graph but same lane
```

### Change 2: Record collapse events during union-find

**In `compute.py`**, modify the three union rules to record events:

```python
collapse_events: list[CollapseEvent] = []

# Rule 1: Dependencies
for wp_id in code_wp_ids:
    for dep in dependency_graph.get(wp_id, []):
        if dep in uf._parent:
            if uf.find(wp_id) != uf.find(dep):
                collapse_events.append(CollapseEvent(
                    wp_a=wp_id, wp_b=dep,
                    rule="dependency",
                    evidence=f"{wp_id} depends on {dep}"
                ))
            uf.union(wp_id, dep)

# Rule 2: Write-scope overlap
for wp_a, wp_b in find_overlap_pairs(code_manifests):
    if uf.find(wp_a) != uf.find(wp_b):
        # Find the specific overlapping globs for evidence
        overlap_detail = _find_overlap_detail(code_manifests[wp_a], code_manifests[wp_b])
        collapse_events.append(CollapseEvent(
            wp_a=wp_a, wp_b=wp_b,
            rule="write_scope_overlap",
            evidence=overlap_detail
        ))
    uf.union(wp_a, wp_b)

# Rule 3: Surface heuristic (refined — see Change 3)
```

### Change 3: Refine Rule 3 — gate on non-disjoint ownership (FR-009)

**Current Rule 3** (`compute.py:204-216`) unions any two WPs that share a surface keyword, regardless of ownership. Change to:

```python
# Rule 3: Shared surfaces → same lane ONLY if ownership is not provably disjoint
for wp_a, wp_b in combinations(code_wp_ids, 2):
    surfaces_a = set(wp_surfaces.get(wp_a, []))
    surfaces_b = set(wp_surfaces.get(wp_b, []))
    if surfaces_a & surfaces_b:
        # Only merge if their owned_files actually overlap
        if (wp_a in code_manifests and wp_b in code_manifests
                and not _globs_are_disjoint(code_manifests[wp_a], code_manifests[wp_b])):
            if uf.find(wp_a) != uf.find(wp_b):
                shared = surfaces_a & surfaces_b
                collapse_events.append(CollapseEvent(
                    wp_a=wp_a, wp_b=wp_b,
                    rule="surface_heuristic",
                    evidence=f"shared surfaces {shared} with non-disjoint ownership"
                ))
            uf.union(wp_a, wp_b)
```

Add helper `_globs_are_disjoint(manifest_a, manifest_b) -> bool` that returns True when no glob pair from A overlaps with any glob from B (inverse of `find_overlap_pairs` for a single pair).

### Change 4: Return CollapseReport from compute_lanes

Add `collapse_report` field to `LanesManifest`, or return a tuple `(LanesManifest, CollapseReport)`. Include in JSON output from finalize-tasks.

### Change 5: Count independent-WP collapses

After computing collapse events, cross-reference with `dependency_graph` to identify events where the two WPs have no direct or transitive dependency. Report this count in `CollapseReport.independent_wps_collapsed`.

### Tests

- `test_disjoint_ownership_preserves_parallelism`: WP A owns `src/a/**`, WP B owns `src/b/**`, same surface keyword → two lanes (not one)
- `test_overlapping_ownership_with_surface_collapses`: WP A owns `src/core/**`, WP B owns `src/core/utils/**`, same surface → one lane
- `test_collapse_report_includes_rule_and_evidence`: collapse events contain rule name and specific overlap/surface
- `test_collapse_report_counts_independent_collapses`: independent WPs forced into same lane counted
- `test_dependency_collapse_not_reported_as_independent`: dependent WPs in same lane → not flagged as independent collapse
- `test_existing_lane_assignments_unchanged`: features with valid lanes.json still compute identically (regression)

---

## WP04 — Mutable Task-State Compatibility

**Issues**: #438
**Files**:
- `src/specify_cli/cli/commands/agent/tasks.py` (mark_status function)
- `src/specify_cli/missions/software-dev/command-templates/tasks.md` (generation instructions)

### Change 1: Add pipe-table row parser to mark-status

**In `tasks.py` around line 1340-1352**, extend the search loop:

```python
for task_id in task_ids:
    task_found = False
    for i, line in enumerate(lines):
        # Strategy 1: Checkbox format (existing)
        if re.search(rf'-\s*\[[ x]\]\s*{re.escape(task_id)}\b', line):
            lines[i] = re.sub(r'-\s*\[[ x]\]', f'- {new_checkbox}', line)
            updated_tasks.append(task_id)
            task_found = True
            break

        # Strategy 2: Pipe-table format (new)
        if _is_pipe_table_task_row(line, task_id):
            lines[i] = _update_pipe_table_status(line, status)
            updated_tasks.append(task_id)
            task_found = True
            break
```

Helper functions:

```python
def _is_pipe_table_task_row(line: str, task_id: str) -> bool:
    """Match a pipe-delimited row containing the task ID."""
    return bool(re.search(
        rf'\|\s*{re.escape(task_id)}\s*\|', line
    ))

def _update_pipe_table_status(line: str, status: str) -> str:
    """Replace status marker in a pipe-table row.

    Recognizes [P] (planned/pending), [D] (done), [x] (done),
    [ ] (pending) in any pipe-delimited cell.
    """
    if status == "done":
        return re.sub(r'\[\s*[P ]\s*\]', '[D]', line)
    else:
        return re.sub(r'\[\s*[Dx]\s*\]', '[P]', line)
```

### Change 2: Standardize future generation to checkbox format (FR-010a)

**In `missions/software-dev/command-templates/tasks.md`**, ensure the task-format instructions explicitly tell LLMs to generate checkbox format:

```markdown
### Task Tracking Format

Use checkbox format for all task rows in tasks.md:

```markdown
- [ ] T001 Description of task (WP01)
- [ ] T002 Another task (WP01)
```

Do NOT use pipe-table format for task tracking rows.
```

If any template currently shows pipe-table examples as the primary format, replace with checkbox examples.

### Tests

- `test_mark_status_checkbox_done`: `- [ ] T001` → `- [x] T001`
- `test_mark_status_checkbox_pending`: `- [x] T001` → `- [ ] T001`
- `test_mark_status_pipe_table_done`: `| T001 | desc | WP01 | [P] |` → `| T001 | desc | WP01 | [D] |`
- `test_mark_status_pipe_table_pending`: `| T001 | desc | WP01 | [D] |` → `| T001 | desc | WP01 | [P] |`
- `test_mark_status_mixed_format`: file has both checkbox and pipe-table rows, both updated correctly
- `test_legacy_pipe_table_file_editable`: existing pipe-table tasks.md from mission 063 can be updated
- `test_template_generates_checkbox_format`: verify template instructions specify checkbox

---

## WP05 — Command Ergonomics for External Agents

**Issues**: #434
**Files**:
- `src/specify_cli/context/middleware.py`
- `src/specify_cli/context/store.py`
- `src/specify_cli/shims/generator.py`
- `src/specify_cli/missions/software-dev/command-templates/tasks.md`
- `src/specify_cli/core/paths.py`

### Change 1: Fix --feature → --mission in error messages (FR-012)

**In `middleware.py` line 100**, change:
```python
"Run `spec-kitty agent context resolve --wp <WP> --feature <feature>` first, "
```
to:
```python
"Run `spec-kitty agent context resolve --wp <WP> --mission <slug>` first, "
```

**In `store.py` line 65**, same change:
```python
"Run `spec-kitty agent context resolve --wp <WP> --mission <slug>` "
```

### Change 2: Add --mission hint to shim template (FR-011)

**In `shims/generator.py` lines 53-76**, add guidance line:

```python
return (
    f"<!-- spec-kitty-command-version: {version} -->\n"
    "Run this exact command and treat its output as authoritative.\n"
    "Do not rediscover context from branches, files, or prompt contents.\n"
    "Pass --mission <slug> when operating on a specific mission.\n"
    "\n"
    f'`spec-kitty agent shim {command} --agent {agent_name} --raw-args "{arg_placeholder}"`\n'
)
```

### Change 3: Fix tasks.md template context resolve example (FR-011)

**In `missions/software-dev/command-templates/tasks.md` around lines 52-58**, ensure the example includes `--mission`:

```bash
spec-kitty agent context resolve --action tasks --mission <mission-slug> --json
```

Audit all other command examples in the template (check-prerequisites, finalize-tasks, mark-status) for missing `--mission`.

### Change 4: Improve require_explicit_feature error message (FR-013)

**In `core/paths.py` lines 333-339**, make the example a complete copy-pasteable command:

```python
msg = (
    f"Mission slug is required. Provide it explicitly: {flag}\n"
    "No auto-detection is performed (branch scanning / env vars removed).\n"
    f"{available}"
    f"Example:\n  spec-kitty agent context resolve --action tasks {flag.split()[0]} {example_slug} --json"
)
```

### Tests

- `test_middleware_error_uses_mission_flag`: error message contains `--mission`, not `--feature`
- `test_store_error_uses_mission_flag`: error message contains `--mission`, not `--feature`
- `test_shim_template_mentions_mission`: generated shim content includes `--mission` guidance
- `test_tasks_template_context_resolve_has_mission`: template example includes `--mission <slug>`
- `test_require_explicit_feature_example_is_complete`: error message includes full copy-pasteable command
- `test_all_tasks_template_commands_have_mission`: grep all `spec-kitty agent` invocations in template, assert all include `--mission`

---

## Dependency Map

```
WP01 (dependency/frontmatter truth)
  ↑ no deps — can start immediately
  owns: tasks.py (finalize_tasks function), mission.py, dependency_parser.py

WP02 (lane materialization correctness)
  ↑ no deps — can start immediately
  owns: lanes/compute.py, ownership/inference.py, ownership/validation.py

WP03 (parallelism preservation)
  ↑ depends on WP02 (builds on lane computation changes, shares compute.py)
  owns: lanes/models.py, lanes/compute.py (shared with WP02, sequenced by dep)

WP04 (task-state compatibility)
  ↑ depends on WP01 (shared tasks.py) and WP05 (shared tasks template)
  owns: test files only; modifies tasks.py mark_status + tasks template under WP01/WP05 ownership

WP05 (command ergonomics)
  ↑ no deps — can start immediately
  owns: context/middleware.py, context/store.py, shims/generator.py, core/paths.py, tasks template
```

**Parallelism**: WP01, WP02, WP05 can run in parallel (Phase 1). WP03 and WP04 can run in parallel with each other in Phase 2 (WP03 after WP02; WP04 after WP01+WP05).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Dependency parser change breaks existing inline-format features | Medium | High | Regression tests with both formats; test against real kitty-specs/ artifacts |
| validate_only mutation guard misses an edge case | Low | High | Assert file checksums before/after in tests; test against both entry points |
| Rule 3 refinement changes existing valid lane assignments | Medium | Medium | Run compute_lanes on all existing features and compare output (C-005) |
| Pipe-table status marker regex too broad/narrow | Low | Medium | Test against real 063 tasks.md; cover edge cases in cell formatting |
| Shim regeneration needed after template change | Low | Low | Migration handles shim updates on next `spec-kitty upgrade` |

## Charter Re-Check (Post-Design)

- **Testing**: Plan includes 30+ specific test cases across 5 WPs. 90%+ coverage target.
- **Type checking**: All new code must pass mypy --strict. `set_scalar` type mismatch is being fixed (Change 4, WP01).
- **DIRECTIVE_003**: All decisions documented in research.md with rationale and alternatives.
- **DIRECTIVE_010**: Plan maps every FR to specific file changes.

No new charter violations.
