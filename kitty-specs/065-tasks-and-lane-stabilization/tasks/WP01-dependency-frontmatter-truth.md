---
work_package_id: WP01
title: Dependency and Frontmatter Truth
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T001, T002, T003, T004, T005, T006, T007, T008, T009]
history:
- at: '2026-04-06T13:45:48+00:00'
  actor: claude
  action: Created WP01 prompt during /spec-kitty.tasks
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/core/dependency_parser.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py
- tests/tasks/test_finalize_tasks_json_output_unit.py
- tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py
- tests/core/test_dependency_parser.py
---

# WP01 — Dependency and Frontmatter Truth

## Objective

Fix the `finalize-tasks` pipeline so it correctly parses dependency declarations in both inline and bullet-list formats, fails loudly when parsed and existing dependencies disagree, preserves existing dependencies when the parser finds nothing, uses the type-safe FrontmatterManager API for list fields, gates all file mutations behind `--validate-only`, and reports mutations accurately in JSON output.

This WP addresses issues #406 (dependency stripping) and #417 (validate-only mutation).

## Context

### Current State

Two independent `finalize-tasks` implementations exist:
- **Primary**: `src/specify_cli/cli/commands/agent/mission.py:1180` — used by `agent mission finalize-tasks`
- **Legacy**: `src/specify_cli/cli/commands/agent/tasks.py:1627` — used by `agent tasks finalize-tasks`

Both have the same bugs:
1. Dependency parser uses narrow regex that misses bullet-list format
2. `set_scalar()` in tasks.py receives `list` but expects `str` (type mismatch)
3. Frontmatter writes happen before `validate_only` is checked
4. Mutation reporting is inaccurate

### Target State

- Single shared dependency parser in `src/specify_cli/core/dependency_parser.py`
- Both entry points call the shared parser (C-004)
- Bullet-list and inline formats both recognized
- Non-empty disagreement between parser and existing frontmatter → diagnostic error
- Empty parse + non-empty existing → preserve existing
- `--validate-only` gates ALL file writes
- JSON output distinguishes modified/unchanged/preserved WPs

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`
- To start implementation: `spec-kitty implement WP01`

---

## Subtask T001: Extract Shared Dependency Parser

**Purpose**: Create a single canonical dependency parser that both `mission.py` and `tasks.py` call, eliminating the current duplication and inconsistency.

**Steps**:

1. Create new file `src/specify_cli/core/dependency_parser.py` with function:
   ```python
   def parse_dependencies_from_tasks_md(content: str) -> dict[str, list[str]]:
       """Parse WP dependency declarations from tasks.md content.

       Recognizes three formats:
       1. Inline: "Depends on WP01, WP02"
       2. Header-line: "**Dependencies**: WP01, WP02"
       3. Bullet-list: "### Dependencies\\n- WP01\\n- WP02"

       Returns: mapping of WP ID → list of dependency WP IDs
       """
   ```

2. Port the existing regex patterns from `mission.py:1802-1819`:
   - Pattern 1: `r"Depends?\s+on\s+(WP\d{2}(?:\s*,\s*WP\d{2})*)"` (case-insensitive)
   - Pattern 2: `r"\*?\*?Dependencies\*?\*?\s*:\s*(.+)"` (case-insensitive)

3. The function must:
   - Split content by WP section headers (lines containing `WP\d{2}` with `##` or "Work Package")
   - For each section, apply all three patterns
   - Deduplicate per WP using `dict.fromkeys()`
   - Return `dict[str, list[str]]`

**Files**: `src/specify_cli/core/dependency_parser.py` (new, ~80 lines)

**Validation**: Unit test with inline-format tasks.md input produces correct dependency map.

---

## Subtask T002: Add Bullet-List Dependency Format Recognition

**Purpose**: The parser must recognize the format the `/spec-kitty.tasks` template instructs LLMs to generate.

**Steps**:

1. Add Pattern 3 to the parser in `dependency_parser.py`:
   - Detect a line matching `^#{1,4}\s*\*?\*?Dependencies\*?\*?\s*$` (case-insensitive)
   - Collect all subsequent lines matching `^\s*[-*]\s*(WP\d{2})` until the next heading or blank line
   - Extract WP IDs from those lines

2. Implementation approach:
   ```python
   # Pattern 3: Bullet-list under Dependencies heading
   deps_heading = re.compile(
       r"^#{1,4}\s*\*?\*?Dependencies\*?\*?\s*$",
       re.IGNORECASE | re.MULTILINE,
   )
   bullet_wp = re.compile(r"^\s*[-*]\s*(WP\d{2})")

   for match in deps_heading.finditer(section_content):
       start = match.end()
       for line in section_content[start:].split("\n"):
           line = line.strip()
           if not line or line.startswith("#"):
               break
           bullet_match = bullet_wp.match(line)
           if bullet_match:
               explicit_deps.append(bullet_match.group(1))
   ```

3. Ensure all three patterns are applied and deduplicated.

**Files**: `src/specify_cli/core/dependency_parser.py`

**Validation**: Test with bullet-list format:
```markdown
### Dependencies
- WP01 (cite Divio standard)
- WP02 (new path known)
```
Parses to `["WP01", "WP02"]`.

---

## Subtask T003: Wire Both Entry Points to Shared Parser

**Purpose**: Ensure both `mission.py` and `tasks.py` call the same parser (C-004).

**Steps**:

1. In `mission.py`, replace the inline parsing at lines 1802-1819 with:
   ```python
   from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md
   wp_dependencies = parse_dependencies_from_tasks_md(tasks_content)
   ```

2. In `tasks.py`, replace the parsing at lines 1665-1692 with the same import and call.

3. Ensure both pass `tasks_md.read_text(encoding="utf-8")` as the content argument.

4. Verify that both implementations add WP IDs from `tasks_dir.glob("WP*.md")` for WPs not mentioned in tasks.md (existing behavior at tasks.py:1694-1698 and the equivalent in mission.py).

**Files**: `src/specify_cli/cli/commands/agent/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: Both entry points produce identical dependency maps for the same input.

---

## Subtask T004: Disagree-Loud on Non-Empty Dependency Conflict

**Purpose**: When tasks.md and WP frontmatter both declare non-empty dependency lists that disagree, finalize-tasks must fail with a diagnostic error instead of silently overwriting (FR-002a).

**Steps**:

1. In both `mission.py` and `tasks.py`, BEFORE writing frontmatter, add conflict detection:
   ```python
   errors: list[str] = []
   for wp_id, parsed_deps in dependencies_map.items():
       existing_deps = frontmatter_for_wp[wp_id].get("dependencies", [])
       if existing_deps and parsed_deps and set(existing_deps) != set(parsed_deps):
           errors.append(
               f"{wp_id}: frontmatter has {sorted(existing_deps)}, "
               f"tasks.md parsed {sorted(parsed_deps)}. "
               f"Resolve the disagreement in tasks.md or WP frontmatter before finalizing."
           )
   if errors:
       _output_error(json_output, "Dependency disagreement detected:\n" + "\n".join(errors))
       raise typer.Exit(1)
   ```

2. The rules (in order):
   - Both non-empty AND disagree → **fail with diagnostic** (FR-002a)
   - Parsed empty, existing non-empty → **preserve existing** (FR-002)
   - Parsed non-empty, existing empty → **write parsed**
   - Both agree → **write (idempotent)**

3. Read existing frontmatter for ALL WPs before writing ANY, so disagreements are detected before any mutations.

**Files**: `src/specify_cli/cli/commands/agent/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: Test where tasks.md says `[WP01]` but frontmatter says `[WP02]` → exit code 1 with diagnostic naming the WP.

---

## Subtask T005: Fix set_scalar Type Mismatch

**Purpose**: Replace `set_scalar()` usage for list-typed fields with the type-safe FrontmatterManager API (C-003).

**Steps**:

1. In `tasks.py`, replace the frontmatter write loop at lines 1700-1721.

   **Current (broken)**:
   ```python
   content = wp_file.read_text(encoding="utf-8-sig")
   frontmatter, body, padding = split_frontmatter(content)
   updated_front = set_scalar(frontmatter, "dependencies", deps)
   updated_doc = build_document(updated_front, body, padding)
   wp_file.write_text(updated_doc, encoding="utf-8")
   ```

   **Replacement (correct)**:
   ```python
   from specify_cli.frontmatter import read_frontmatter, write_frontmatter
   fm_dict, body = read_frontmatter(wp_file)
   fm_dict["dependencies"] = deps
   write_frontmatter(wp_file, fm_dict, body)
   ```

2. Verify that `FrontmatterManager.write()` preserves field ordering (it uses `WP_FIELD_ORDER` at `frontmatter.py:41-58`).

3. Ensure `dependencies` field is serialized as a proper YAML list, not a string representation.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: After writing, re-read frontmatter and assert `dependencies` is `list[str]`, not `str`.

---

## Subtask T006: Gate All Mutations on validate_only

**Purpose**: Ensure `--validate-only` prevents ALL file writes, not just the final commit (FR-004).

**Steps**:

1. **In `mission.py`**: The frontmatter write at line 1456 (`write_frontmatter(wp_file, frontmatter, body)`) must be wrapped:
   ```python
   if frontmatter_changed:
       if not validate_only:
           write_frontmatter(wp_file, frontmatter, body)
       updated_count += 1
   ```
   The `updated_count` still increments (for reporting what *would* change), but the file is not modified.

2. **In `tasks.py`**: The `wp_file.write_text()` at line 1720 must be wrapped:
   ```python
   if not validate_only:
       write_frontmatter(wp_file, fm_dict, body)
   updated_count += 1
   ```

3. Ensure the bootstrap call already has `dry_run=validate_only` (it does at mission.py:1511 and tasks.py:1732).

4. Ensure the lanes.json write is also gated (it is, at mission.py:1575, inside the non-validate path).

**Files**: `src/specify_cli/cli/commands/agent/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: Run finalize-tasks --validate-only, checksum WP files before and after — must be identical.

---

## Subtask T007: Implement validate-only Mutation Report

**Purpose**: When running with `--validate-only`, report what mutations WOULD occur without executing them (FR-005).

**Steps**:

1. Accumulate would-be changes during the (now-gated) write loop:
   ```python
   would_modify: list[dict] = []
   for wp_id in ...:
       if frontmatter_changed:
           would_modify.append({
               "wp_id": wp_id,
               "changes": {field: new_value for field, new_value in changes.items()},
           })
   ```

2. Include in the validate-only JSON output:
   ```json
   {
     "result": "validation_passed",
     "validate_only": true,
     "would_modify": [...],
     "would_preserve": [...],
     "unchanged": [...]
   }
   ```

**Files**: `src/specify_cli/cli/commands/agent/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: JSON output includes `would_modify` with correct WP list.

---

## Subtask T008: Implement Accurate Per-WP Mutation Reporting

**Purpose**: JSON output must distinguish modified/unchanged/preserved WPs (FR-003).

**Steps**:

1. Track three categories during the write loop:
   - `modified_wps`: Frontmatter was different and was updated
   - `unchanged_wps`: Frontmatter was already correct
   - `preserved_wps`: Parser found empty deps but existing non-empty deps were kept

2. Report in JSON:
   ```json
   {
     "result": "success",
     "modified_wps": ["WP03", "WP04"],
     "unchanged_wps": ["WP01", "WP02"],
     "preserved_wps": ["WP05"],
     "updated_wp_count": 2
   }
   ```

3. Ensure `updated_wp_count` reflects actual modifications, not just "files processed".

**Files**: `src/specify_cli/cli/commands/agent/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: Test where some WPs change and some don't → correct categorization.

---

## Subtask T009: Write Regression Tests

**Purpose**: Cover all WP01 changes with targeted tests per FR.

**Tests to add/modify**:

1. **`tests/core/test_dependency_parser.py`** (new file):
   - `test_inline_depends_on_format`: "Depends on WP01, WP02" → `["WP01", "WP02"]`
   - `test_inline_dependencies_colon_format`: "**Dependencies**: WP01" → `["WP01"]`
   - `test_bullet_list_format`: `### Dependencies\n- WP01\n- WP02` → `["WP01", "WP02"]`
   - `test_mixed_formats_in_same_file`: multiple WPs with different formats
   - `test_no_dependencies_returns_empty`: WP section without deps → `[]`
   - `test_deduplication`: same WP mentioned twice → appears once

2. **`tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py`** (modify):
   - `test_validate_only_no_file_writes`: checksum WP files before/after
   - `test_validate_only_reports_would_modify`: JSON has `would_modify` field
   - `test_non_empty_disagreement_fails`: exit code 1, diagnostic message
   - `test_empty_parse_preserves_existing_deps`: existing deps survive

3. **`tests/tasks/test_finalize_tasks_json_output_unit.py`** (modify):
   - `test_json_reports_modified_unchanged_preserved`: three categories present

**Files**: `tests/core/test_dependency_parser.py` (new), plus modifications to existing test files

---

## Definition of Done

- [ ] Both `agent mission finalize-tasks` and `agent tasks finalize-tasks` produce identical output for the same input
- [ ] Bullet-list dependency format is parsed correctly
- [ ] Non-empty dependency disagreement produces a diagnostic error (exit code 1)
- [ ] Empty parse preserves existing non-empty frontmatter dependencies
- [ ] `--validate-only` leaves all files byte-identical on disk
- [ ] `--validate-only` JSON includes `would_modify` / `unchanged` / `would_preserve`
- [ ] JSON output distinguishes modified/unchanged/preserved WPs
- [ ] `set_scalar` is no longer used for list-typed fields
- [ ] All tests pass, mypy --strict clean on changed files

## Reviewer Guidance

- Verify the shared parser handles all three formats by reading `test_dependency_parser.py`
- Verify validate_only gating by checking that `write_frontmatter` / `wp_file.write_text` only execute when `validate_only is False`
- Verify C-004 by confirming both entry points import from `dependency_parser.py`
- Run `spec-kitty agent mission finalize-tasks --validate-only --mission 065-tasks-and-lane-stabilization --json` on a real feature and verify no files change
