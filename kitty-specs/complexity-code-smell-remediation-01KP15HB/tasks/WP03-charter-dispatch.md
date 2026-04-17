---
work_package_id: WP03
title: 'Charter: Dispatch Table and Decomposition'
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-019
planning_base_branch: feat/complexity-debt-remediation
merge_target_branch: feat/complexity-debt-remediation
branch_strategy: Planning artifacts for this feature were generated on feat/complexity-debt-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/complexity-debt-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-complexity-code-smell-remediation-01KP15HB
base_commit: cf17d751d273f8896e901ced4811b034d9b4d7e9
created_at: '2026-04-13T15:08:41.587771+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
- T019
- T032
shell_pid: "128893"
agent: "claude"
history:
- date: '2026-04-12'
  action: created
  author: spec-kitty.tasks
authoritative_surface: src/charter/
execution_mode: code_change
owned_files:
- src/charter/extractor.py
- src/charter/resolver.py
- src/charter/compiler.py
- src/charter/context.py
- src/charter/parser.py
- src/charter/catalog.py
- tests/agent/test_workflow_charter_context.py
- tests/agent/cli/commands/test_charter_cli.py
- tests/merge/test_profile_charter_e2e.py
- tests/init/test_charter_runtime_integration.py
tags: []
---

# WP03 — Charter: Dispatch Table and Decomposition

## Objective

Eliminate `# noqa: C901` suppressions in `src/charter/extractor.py` by replacing a 26-branch
`if/elif` with a dispatch table. Decompose `resolve_governance` (conditional). Reduce
`_build_references_from_service` parameter count. Fix two trivial smell items.

**FRs**: FR-006, FR-007 (conditional on C-001), FR-008, FR-009, FR-010
**Governing tactics**: `refactoring-conditional-to-strategy`, `refactoring-extract-first-order-concept`, `refactoring-change-function-declaration`, `refactoring-guard-clauses-before-polymorphism`, `change-apply-smallest-viable-diff`
**Procedure**: `src/doctrine/procedures/shipped/refactoring.procedure.yaml`
**Directives**: DIRECTIVE_034, DIRECTIVE_024, DIRECTIVE_030

**IMPORTANT — C-002**: This WP only touches `src/charter/`. Never touch `src/specify_cli/charter/` — that module is deprecated and will be removed in a separate PR.

## Branch Strategy

- **Lane**: B (independent)
- **Planning base / merge target**: `feat/complexity-debt-remediation`
- **Worktree**: Allocated by `finalize-tasks` — check `lanes.json` for the exact path.
- **Implementation command**: `spec-kitty agent action implement WP03 --agent <name>`

## Context

`src/charter/extractor.py::_extract_governance` is the worst function in the charter slice:
CC=28, two `# noqa: C901` suppressions. It dispatches on `field_name` via a 26-branch
`if/elif` chain. Each branch does one thing: extract a specific field from a `Section` object
and set it on a `GovernanceConfig`. The fix is to replace the chain with a
`dict[str, Callable]` dispatch table — one handler per field name.

`src/charter/resolver.py::resolve_governance` (CC=20) has three independent resource-resolution
blocks (paradigms, tools, directives) inlined into a single function. Each block is an
independent concept that deserves its own helper. FR-007 is conditional on C-001 (DRG gate).

`src/charter/compiler.py::_build_references_from_service` (7 args, 17 branches) is a long
parameter list smell. Reducing to ≤ 5 parameters is sufficient per FR-008.

`src/charter/context.py` and `src/charter/parser.py` have trivial one-line fixes (FR-009, FR-010).

## Pre-work: C-001 gate check

Before implementing T015, run:
```bash
grep -rl "drg\|dependency-resolution\|charter-rebuild" kitty-specs/ --include="*.json" | xargs grep -l '"in_progress"\|"claimed"' 2>/dev/null
```

If any DRG rebuild mission is active, **skip T015 entirely** and note the deferral in your
WP review comment. FRs 006, 008, 009, 010 are independent and must still be completed.

---

## Subtask T013 — Characterization tests for `_extract_governance`

**Purpose**: Lock observable behaviour before replacing the 26-branch dispatch (DIRECTIVE_034).

**File**: `tests/agent/test_workflow_charter_context.py` (extend) or a new file in the charter test area.

**Strategy**: `_extract_governance` is called with a `Section` object and a `GovernanceConfig`.
The 26 branches correspond to 26 field names on `GovernanceConfig`. Write a parametrized test
that exercises each field name:

```python
@pytest.mark.parametrize("field_name,section_content,expected_attr", [
    ("paradigms", {"paradigms": ["pragmatic"]}, "paradigms"),
    ("directives", {"directives": ["DIRECTIVE_001"]}, "directives"),
    ("tools", {"tools": ["git", "python"]}, "tools"),
    # ... at least 10 representative branches covering different field types
])
def test_extract_governance_field_dispatch(field_name, section_content, expected_attr):
    section = Section(name=field_name, content=section_content)
    config = GovernanceConfig()
    _extract_governance(section, config)
    assert getattr(config, expected_attr) is not None
```

You don't need to parametrize all 26 branches — cover enough to be confident the dispatch
table produces the same results. Focus on fields with distinct extraction logic (list fields,
string fields, optional fields with defaults).

Run: `pytest tests/ -k "extract_governance" -x` — all tests must pass on unmodified code.

---

## Subtask T014 — Replace `_extract_governance` if/elif with dispatch table

**Purpose**: Reduce CC from 28 to ≤ 10; remove both `# noqa: C901` suppressions (FR-006).

**File**: `src/charter/extractor.py`

**Pattern** (`refactoring-conditional-to-strategy`):

```python
# Define a type alias for the handler signature
FieldHandler = Callable[[Section, GovernanceConfig], None]

# Build the dispatch table at module scope (or as a class variable)
_FIELD_HANDLERS: dict[str, FieldHandler] = {
    "paradigms": _handle_paradigms,
    "directives": _handle_directives,
    "tools": _handle_tools,
    "available_tools": _handle_available_tools,
    # ... one entry per branch
}

def _handle_paradigms(section: Section, config: GovernanceConfig) -> None:
    config.paradigms = section.content.get("paradigms", [])

def _handle_directives(section: Section, config: GovernanceConfig) -> None:
    config.directives = section.content.get("directives", [])

# ... one handler per field ...

def _extract_governance(section: Section, config: GovernanceConfig) -> None:
    handler = _FIELD_HANDLERS.get(section.name)
    if handler:
        handler(section, config)
    # unknown field → ignored (preserves existing behaviour)
```

**Migration steps**:
1. Create `_FIELD_HANDLERS` as an empty dict above `_extract_governance`.
2. For each `if/elif` branch:
   a. Extract the branch body into a named `_handle_<fieldname>` function.
   b. Add `"<fieldname>": _handle_<fieldname>` to `_FIELD_HANDLERS`.
   c. Remove the branch from `_extract_governance`.
   d. Run `pytest tests/ -k "extract_governance" -x` — must stay green.
3. Remove both `# noqa: C901` comments once all branches are migrated.
4. Verify: `ruff check src/charter/extractor.py --select C901` → CC ≤ 10.

---

## Subtask T015 — Decompose `resolve_governance` helpers (FR-007, conditional on C-001)

**Purpose**: Extract three independent resource blocks into named helpers (FR-007).

**File**: `src/charter/resolver.py`

**SKIP IF**: DRG rebuild mission is active (see pre-work check above). Document the skip in the
WP review comment so it can be tracked.

**Pattern** (`refactoring-extract-first-order-concept`):

`resolve_governance` inlines three independent resource-resolution blocks:
- Paradigms resolution
- Tools resolution
- Directives resolution

Extract each into a named function:

```python
def _resolve_paradigms(charter: CharterConfig, service: DoctrineService) -> list[str]:
    """Resolve paradigm references from the charter."""
    ...

def _resolve_tools(charter: CharterConfig) -> list[str]:
    """Resolve tool availability from the charter."""
    ...

def _resolve_directives(charter: CharterConfig, service: DoctrineService) -> list[Directive]:
    """Resolve directive references from the charter."""
    ...

def resolve_governance(charter: CharterConfig, service: DoctrineService) -> GovernanceResult:
    paradigms = _resolve_paradigms(charter, service)
    tools = _resolve_tools(charter)
    directives = _resolve_directives(charter, service)
    return GovernanceResult(paradigms=paradigms, tools=tools, directives=directives)
```

After extraction, CC of `resolve_governance` must be ≤ 8.

**Validation**: `pytest tests/ -k "charter" -x` — passes.

---

## Subtask T016 — Reduce `_build_references_from_service` parameters

**Purpose**: Reduce from 7 arguments to ≤ 5 (FR-008).

**File**: `src/charter/compiler.py`

**Current signature** (inspect the actual file before implementing):
Read the function, identify which parameters are logically grouped. The most natural grouping
is to bundle the service-related parameters into an existing context object or pass the service
directly (callers likely already have a service reference).

**Approach** (verify against actual code before applying):
1. If multiple parameters come from the same caller context (e.g., `repo_root`, `config_path`
   that both come from a `ProjectConfig`), pass the `ProjectConfig` directly.
2. If the function has separate "source A" and "source B" parameters, introduce a small
   `ReferenceSources` dataclass grouping them.
3. Aim for ≤ 5 parameters. ≤ 12 branches is the hard CC limit.

**Before refactoring**:
- Read the function fully with `Read` tool
- Write one or two characterization tests that call the function
- Apply the reduction tactic
- Run `pytest tests/ -k "compiler or charter" -x`

---

## Subtask T017 — Named depth constants in `context.py`

**Purpose**: Replace magic numbers 2 and 3 with named constants (FR-009).

**File**: `src/charter/context.py`

**Change** (one-liner per constant):
```python
# Add at module scope, before any use
_MIN_EFFECTIVE_DEPTH = 2
_EXTENDED_CONTEXT_DEPTH = 3
```

Replace each occurrence of the literal `2` and `3` used as depth thresholds with the named
constant. Do not replace occurrences of `2` or `3` that are used for other purposes (e.g.,
list indices, string formatting).

**Validation**: `ruff check src/charter/context.py --select PLR2004` — zero magic number violations.

---

## Subtask T018 — Fix `else: if` anti-pattern in `parser.py:170`

**Purpose**: Replace `else:` block containing only an `if` with `elif` (FR-010).

**File**: `src/charter/parser.py`, line 170 (verify exact line before editing)

**Change**:
```python
# Before
else:
    if condition:
        do_something()

# After
elif condition:
    do_something()
```

This is a `change-apply-smallest-viable-diff` — one mechanical replacement, no logic change.

**Validation**: `ruff check src/charter/parser.py` — zero violations.

---

## Subtask T032 — Decompose S3776-violating functions in `catalog.py`

**Purpose**: Reduce Sonar cognitive complexity for the functions in `src/charter/catalog.py`
that are flagged by SonarCloud (`python:S3776`) in PR #592 backlog (#594, FR-019).

**File**: `src/charter/catalog.py` (263 lines, 7 functions)

**Pre-work — identify the offenders**:

```bash
ruff check src/charter/catalog.py --select C901   # ruff proxy for CC
```

Read the file and identify which functions have the highest branch depth. Likely candidates:
`load_doctrine_catalog` (builds the full catalog in one pass) and `_load_yaml_id_catalog`
(YAML walking with error handling).

**Strategy** (`refactoring-extract-first-order-concept`):

The Sonar S3776 metric penalises deeply nested control flow more than CC does. Look for:
- Nested `try/except` inside loops
- Multiple independent loading blocks inlined in one function
- Conditional presence checks mixed with loading logic

Extract each independent loading concern (paradigms, tactics, directives, etc.) into a named
`_load_<asset>` helper. The top-level function becomes a composition of helpers with no nested
branches of its own.

**Approach** (apply DIRECTIVE_034 — characterize first):

1. Write at least two tests exercising `load_doctrine_catalog` with a minimal fixture directory.
   Verify they pass on unmodified code.
2. Extract helpers one at a time; run tests after each extraction.
3. Remove branches from the parent function; verify CC drops after each extraction.

**Validation**:

```bash
ruff check src/charter/catalog.py --select C901     # CC ≤ 10 per function
pytest tests/ -k "catalog or charter" -x -q
mypy src/charter/catalog.py
```

**Note**: If `load_doctrine_catalog` is already ≤ 10 CC according to ruff (Sonar uses a
different metric), document the actual ruff CC for the record and confirm whether manual
helpers are still needed to satisfy the Sonar S3776 threshold.

---

## Subtask T019 — Quality gate

```bash
ruff check src/charter/
mypy src/charter/
pytest tests/ -x --timeout=120
```

**Expected outcomes**:
- ruff: zero violations on all charter files; both `# noqa: C901` comments gone from `extractor.py`
- mypy: zero errors
- pytest: no new failures
- CC of `_extract_governance`: ≤ 10 (verified with `ruff check src/charter/extractor.py --select C901`)
- CC of `resolve_governance`: ≤ 8 (if T015 was not deferred)
- `_build_references_from_service` parameter count: ≤ 5
- CC of all functions in `catalog.py`: ≤ 10 (T032)

---

## Definition of Done

- [ ] `_extract_governance` CC ≤ 10, no `# noqa: C901` (FR-006)
- [ ] `resolve_governance` CC ≤ 8 with named helpers (FR-007) — OR T015 explicitly deferred with documented C-001 reason
- [ ] `_build_references_from_service` has ≤ 5 parameters and ≤ 12 branches (FR-008)
- [ ] Named depth constants replace magic numbers in `context.py` (FR-009)
- [ ] `elif` replaces `else: if` in `parser.py:170` (FR-010)
- [ ] `ruff check src/charter/` — zero violations
- [ ] `mypy src/charter/` — zero errors
- [ ] `pytest tests/` — no new failures
- [ ] All functions in `catalog.py` have CC ≤ 10 (FR-019); Sonar S3776 no longer reported for this file
- [ ] No new `# noqa` suppressions added anywhere in `src/charter/`

## Reviewer Guidance

1. Run `ruff check src/charter/extractor.py --select C901` — confirm CC ≤ 10 for `_extract_governance`.
2. Confirm both `# noqa: C901` comments are removed from `extractor.py`.
3. Check that `_FIELD_HANDLERS` contains an entry for every field name that was previously an `if/elif` branch. Count the branches in the old code and compare.
4. For T015: if deferred, the review comment must explicitly state "T015 deferred — DRG mission <slug> is active".
5. Confirm no changes were made to `src/specify_cli/charter/` (C-002 constraint).
6. Run `ruff check src/charter/catalog.py --select C901` — confirm CC ≤ 10 for all functions (T032).

## Activity Log

- 2026-04-13T15:08:41Z – claude – shell_pid=73286 – Assigned agent via action command
- 2026-04-14T06:26:37Z – claude – shell_pid=73286 – Ready for review: T013-T016 dispatch table characterization + resolver decomposition; T017-T018 trivial fixes; T032 catalog cognitive-complexity reduction. All 239 charter tests pass, ruff+mypy clean.
- 2026-04-14T06:32:45Z – claude – shell_pid=125925 – Started review via action command
- 2026-04-14T06:50:24Z – claude – shell_pid=125925 – Moved to for_review
- 2026-04-14T06:50:47Z – claude – shell_pid=128893 – Started review via action command
- 2026-04-14T08:23:40Z – claude – shell_pid=128893 – Review passed: dispatch table in place, both C901 noqa removed, ruff+mypy clean, C-002 respected, pre-existing flaky contract test not introduced by WP03
