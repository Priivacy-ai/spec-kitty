---
work_package_id: WP02
title: Track 4 — Dependency Parser Hotfix
dependencies: []
requirement_refs:
- FR-301
- FR-302
- FR-303
- FR-304
- FR-305
planning_base_branch: main
merge_target_branch: main
branch_strategy: WP02 runs in an execution lane allocated by finalize-tasks. Implementation happens in the lane worktree. Merge target is main.
subtasks:
- T007
- T008
- T009
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: src/specify_cli/core/dependency_parser.py
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- src/specify_cli/core/dependency_parser.py
- tests/core/test_dependency_parser.py
tags: []
---

# WP02 — Track 4: Dependency Parser Hotfix

**Spec FRs**: FR-301, FR-302, FR-303, FR-304, FR-305
**Priority**: P1 — land early; downstream `finalize-tasks` calls depend on correct section bounding.
**Estimated size**: ~200 lines

## Objective

Fix `dependency_parser.py` so the final WP section is bounded at a top-level non-WP `##` heading rather than slurping to EOF. This prevents trailing prose (e.g., a `## Notes` or `## Appendix` section at the end of `tasks.md`) from being parsed for dependencies of the last WP.

This is a narrow hotfix only. Do NOT introduce a manifest redesign, a new file format, or a mandatory sentinel marker. The fix must be backward-compatible with all existing `tasks.md` files.

## Context

**Current bug** (from Phase 0 research, `dependency_parser.py:56`):
```python
end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tasks_content)
```
The final WP section ends at `len(tasks_content)` (EOF), which includes any trailing prose.

**Important clarification**: The parser does NOT do "prose inference" in the traditional sense. It only matches three explicit declaration formats: `"Depends on WP##"` (inline), `"**Dependencies**: WP##"` (header-colon), and a `### Dependencies` bullet list. The false-positive in the bug report happens when trailing prose after the final WP happens to contain one of these literal patterns (e.g., `"This component depends on WP01 being finalized."`).

**The fix**: Add a second stop condition to the section splitter — stop at any top-level `## ` markdown heading whose text is **not** a WP id. Sub-headings (`### `) inside a WP section must NOT trigger the stop.

**Existing tests**: 21 tests in `tests/core/test_dependency_parser.py` — all 21 must still pass after the fix.

## Branch Strategy

Plan in `main`, implement in the lane worktree allocated by `finalize-tasks`. Merge back to `main` on completion.

## Subtask Guidance

### T007 — Bound `_split_wp_sections()` at non-WP `##` headings

**File**: `src/specify_cli/core/dependency_parser.py`

**Current code** (lines 39-59):
```python
_WP_SECTION_HEADER = re.compile(
    r"^## (?:Work Package )?(WP\d{2})\b", re.MULTILINE
)

def _split_wp_sections(tasks_content: str) -> dict[str, str]:
    matches = list(_WP_SECTION_HEADER.finditer(tasks_content))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        wp_id = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tasks_content)
        sections[wp_id] = tasks_content[start:end]
    return sections
```

**Fix**: Introduce a "non-WP section stop" pattern. For the final WP (where the current fallback is EOF), scan forward for the first `## ` heading that is NOT a WP heading and stop there.

**Implementation approach**:
```python
# Add a new regex for any top-level ## heading (non-WP or WP):
_ANY_H2_HEADER = re.compile(r"^## ", re.MULTILINE)

def _split_wp_sections(tasks_content: str) -> dict[str, str]:
    matches = list(_WP_SECTION_HEADER.finditer(tasks_content))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        wp_id = match.group(1)
        start = match.end()
        if idx + 1 < len(matches):
            # There's a next WP header — use it as the end (existing behavior)
            end = matches[idx + 1].start()
        else:
            # Final WP: stop at the first non-WP ## heading after this WP header,
            # or at EOF if no such heading exists.
            end = len(tasks_content)  # default: EOF
            for h2_match in _ANY_H2_HEADER.finditer(tasks_content, match.end()):
                # If this ## heading is NOT a WP header, it's a stop boundary.
                if not _WP_SECTION_HEADER.match(tasks_content, h2_match.start()):
                    end = h2_match.start()
                    break
        sections[wp_id] = tasks_content[start:end]
    return sections
```

**Critical invariant**: `_ANY_H2_HEADER` must scan from `match.end()` (after the final WP header line), not from 0. Otherwise it would stop at earlier WP headers.

**Invariant for sub-headings**: `### ` headings inside a WP section are NOT matched by `^## ` (they have three `#`s, not two). They are fully preserved. Add a regression test to confirm this (see T009 test T4.3).

**Validation**:
- Run the full existing test suite: `pytest tests/core/test_dependency_parser.py -q` → all 21 pass.
- Manual mental check: a `tasks.md` with `## WP01\n...text...\n## Notes\n...trailing...` → section for WP01 does NOT include anything from `## Notes` onward.

---

### T008 — Document explicit-dependencies-only invariant

**File**: `src/specify_cli/core/dependency_parser.py`

**Steps**:

1. Find the module or class docstring for `dependency_parser.py` (likely at the top of the file). Add a note clarifying:
   > **Parser contract**: This parser matches only three explicit dependency declaration formats. It does NOT perform prose inference. The common false-positive (prose containing "Depends on WP##" being parsed as a dependency) is addressed by section bounding, not by disabling the patterns.

2. Add inline comments above the three pattern-matching blocks (`Pattern 1`, `Pattern 2`, `Pattern 3` at lines ~106, ~111, ~120) noting that these are explicit-declaration formats, not prose inference.

3. In the `finalize-tasks` path (`src/specify_cli/cli/commands/agent/tasks.py` around lines 1923-1937), the existing "disagree-loud" (T004) logic correctly prevents frontmatter `dependencies` from being silently overwritten by parsed values. Verify this logic is unaffected by the section-bound change. Add a comment noting this is the precedence guarantee for FR-302/FR-303.

**Validation**:
- `mypy --strict src/specify_cli/core/dependency_parser.py` is clean.
- No behavioral changes from adding comments.

---

### T009 — Regression tests for Track 4

**File**: `tests/core/test_dependency_parser.py` (extend)

**Tests to add**:

**Test T4.1 — Trailing prose after `## Notes` does NOT bleed into final WP** (FR-304, the main regression):
```python
def test_trailing_non_wp_heading_stops_final_wp_section():
    content = """
## Plan

Some intro.

## WP01

**Dependencies**: WP00

Body of WP01.

## WP02

**Dependencies**: []

Body of WP02.

## Notes

This component depends on WP01 being signed off. Depends on WP01.
"""
    result = parse_dependencies_from_tasks_md(content)
    assert result == {"WP01": ["WP00"], "WP02": []}
    # Specifically: WP02 must NOT have WP01 from the ## Notes section
    assert "WP01" not in result.get("WP02", [])
```

**Test T4.3 — Sub-headings inside a WP section do NOT trigger the stop** (FR-301 edge case):
```python
def test_subheadings_inside_wp_section_preserved():
    content = """
## WP01

**Dependencies**: WP00

### Implementation notes

Some notes here.

### Test plan

- This plan depends on WP02 being reviewed first.
  (Note: "Depends on WP02" below is intentional and should be parsed.)

Depends on WP02

## WP02

Body.
"""
    result = parse_dependencies_from_tasks_md(content)
    # WP01's ### sub-headings are part of WP01's section (not a stop boundary)
    # The "Depends on WP02" inside WP01 should be parsed
    assert "WP02" in result.get("WP01", [])
```

**Test T4.4 — Explicit `dependencies: []` in frontmatter is preserved** (FR-302):
This tests the disagree-loud / preserve-existing logic in `agent/tasks.py`, not the parser itself. Write an integration test that verifies: when a WP's frontmatter has `dependencies: []` and the parser finds nothing (because the section has no explicit-format text), the finalized WP keeps `dependencies: []`.

```python
def test_explicit_empty_dependencies_not_overwritten():
    # This tests the finalize-tasks preserve-existing logic
    # WP01 frontmatter: dependencies: []
    # WP01 section: no "Depends on" text
    # Expected: WP01 finalized with dependencies: [] (not inferred as anything)
    ...
```

**Verify all 21 existing tests still pass**:
```bash
pytest tests/core/test_dependency_parser.py -v
```
All 21 tests from `TestInlineDependsOnFormat`, `TestInlineDependenciesColonFormat`, `TestBulletListFormat`, `TestMixedFormatsInSameFile`, and edge-case classes must still pass.

## Definition of Done

- [ ] `_split_wp_sections()` stops at non-WP `##` headings for the final WP.
- [ ] Sub-headings (`###`) inside a WP section are NOT treated as stop boundaries.
- [ ] All 21 existing parser tests pass.
- [ ] Test T4.1 (trailing-prose regression) passes.
- [ ] Test T4.3 (sub-headings preserved) passes.
- [ ] Test T4.4 (explicit empty dependencies preserved) passes.
- [ ] `mypy --strict src/specify_cli/core/dependency_parser.py` clean.

## Risks

| Risk | Mitigation |
|------|-----------|
| False-positive bound: stop too early if a WP section contains a non-standard `## ` heading | The `^## ` stop only applies to the FINAL WP (when there is no next WP header). Interior WPs are bounded by the next WP header. Risk is minimal. |
| The `_ANY_H2_HEADER` scan starts from wrong position | Confirm `finditer(tasks_content, match.end())` starts from after the WP header line, not from the beginning of the file. |

## Reviewer Guidance

1. Confirm `_split_wp_sections()` modification is minimal: the only change is the `else` branch for the final WP's `end`.
2. Run `pytest tests/core/test_dependency_parser.py -v` and verify all 21 existing tests + 3 new tests pass.
3. Confirm sub-headings (`###`) inside a WP section are unaffected.
4. Confirm the fix does NOT touch `agent/tasks.py` (except for the comment in T008).
