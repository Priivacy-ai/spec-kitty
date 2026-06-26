# Mission Specification: Remove hidden --feature alias from user-facing CLI commands

**Mission Branch**: `feat/feature-alias-removal`
**Mission ID**: `01KW0N879YNT6HYB6DX1JE6STX`
**Created**: 2026-06-26
**Status**: Draft
**Input**: GitHub issue #1060 — Legacy cleanup: remove hidden --feature aliases from the CLI surface

---

## Background

The `--mission` flag is the canonical mission selector across the Spec Kitty CLI. Eight
user-facing top-level commands still carry a hidden `--feature` Typer option as a
deprecated compatibility alias. A prior clean-up (PR #1985) fully removed the alias from
ten internal/agent-facing commands; this mission removes it from the remaining eight
user-facing commands and hardens the terminology guard to prohibit any future
reintroduction.

The scope is bounded. Issue #1059 (compatibility inventory and sunset policy) is a
separate workstream and is explicitly out of scope.

---

## User Scenarios & Testing

### User Story 1 — CLI users can no longer accidentally use `--feature` (P1)

A developer or automated agent running any of the eight in-scope commands passes
`--feature some-slug` by mistake (e.g. from a stale script or shell alias).
After this mission, the CLI rejects the invocation with an unknown-option error
rather than silently accepting it.

**Why this priority**: Allowing `--feature` to keep working — even silently — keeps
the legacy vocabulary alive in scripts and muscle memory. Hard removal is the stated
intent and is the only mechanism that triggers a clean break.

**Independent Test**: Run `spec-kitty implement WP01 --feature some-slug` against an
initialized project; confirm exit code 2 and "No such option: --feature" in stderr.
Repeat for all eight commands.

**Acceptance Scenarios**:

1. **Given** a valid project repo, **When** a user runs any in-scope command with
   `--feature <handle>`, **Then** the CLI exits with a non-zero code and prints
   "No such option: --feature" (or equivalent unknown-option message). No crash,
   no `TypeError`, no traceback.

2. **Given** a valid project repo, **When** a user runs any in-scope command with
   `--mission <handle>`, **Then** the command proceeds normally, unaffected by this
   change.

---

### User Story 2 — Operators get a clean error when `--mission` is omitted (P1)

A developer runs an in-scope command without supplying any selector (neither
`--mission` nor the now-deleted `--feature`).

**Why this priority**: PR #1985's adversarial audit found that simply dropping the
alias branch without preserving the no-selector guard causes an uncaught `TypeError`.
This story locks the guard requirement at spec level.

**Independent Test**: Run each in-scope command with no `--mission` argument against an
initialized project; confirm a user-facing error message (not a Python traceback) and
exit code 2.

**Acceptance Scenarios**:

1. **Given** an initialized project, **When** `spec-kitty implement WP01` is run with
   no `--mission` flag, **Then** the command prints a clear selector-required error
   and exits with a non-zero code.

2. **Given** the same setup, **When** `spec-kitty implement WP01 --mission "  "` is
   run (whitespace-only value), **Then** the command rejects the empty-after-trim
   value and exits with a non-zero code (whitespace normalization guard preserved).

3. **Acceptance scenarios 1 and 2 apply identically to all eight in-scope commands.**

---

### User Story 3 — The terminology guard blocks future reintroductions (P2)

A contributor who adds `--feature` back to any in-scope command file (whether as a
hidden alias, a `resolve_selector` alias_flag argument, or a bare string literal) sees
a CI gate failure on `tests/contract/test_terminology_guards.py` before the PR is
merged.

**Why this priority**: The guard is what makes the removal durable. Without it, the
pattern drifts back silently.

**Independent Test**: Manually add `"--feature"` to one in-scope file, run
`pytest tests/contract/test_terminology_guards.py` — confirm the test fails. Revert
and confirm it passes.

**Acceptance Scenarios**:

1. **Given** the updated test guard, **When** any in-scope file contains the literal
   `"--feature"` in any context, **Then**
   `test_no_feature_alias_in_internal_command_cluster` (or its equivalent for the
   eight in-scope files) fails.

2. **Given** a clean codebase (all eight files alias-free), **When** the full guard
   suite is run, **Then** all guard tests pass.

---

### User Story 4 — Internal variable names reflect the canonical term (P2)

A contributor reading or modifying an in-scope command file sees `mission` and
`mission_slug` in parameter names, not `feature` or `feature_slug`.

**Why this priority**: Lingering `feature` parameter names in signatures are
terminology drift and make it harder to onboard contributors. This satisfies the
issue's full AC requirement for the internal rename.

**Independent Test**: Inspect the signatures and local bodies of the eight in-scope
command files; confirm no `feature: str | None` function parameters or `_feature_number`
local variables remain in the direct command entrypoints.

**Acceptance Scenarios**:

1. **Given** an in-scope command function, **When** it previously declared `feature:
   str | None` as a Typer parameter or `_feature_number` as a local variable,
   **Then** those names are renamed to `mission: str | None` and `_mission_number`
   respectively.

2. **Given** historical-data-parsing fields (e.g., `feature_slug` dict keys read from
   `meta.json` or event JSONL), **When** those fields are read from stored artifacts,
   **Then** the field-key strings are NOT renamed (they reflect the stored data
   schema, not the CLI surface).

---

### Edge Cases

- `spec-kitty lifecycle plan` and `spec-kitty lifecycle tasks` each have their own
  `--feature` hidden option in `lifecycle.py`. Both must be removed; the `specify`
  sub-command of lifecycle uses `feature` only as a positional argument (a different
  construct) and is not in scope for flag removal.
- `spec-kitty merge` internally constructs `mission or feature` to derive the handle.
  After removal, the `feature` local variable is eliminated and the fallback collapses
  to just `mission`.
- `spec-kitty accept` uses `raw_handle = mission or feature`. After removal, this
  collapses to `raw_handle = mission`; the existing no-handle check (`if raw_handle is
  None`) must remain.
- `src/specify_cli/missions/_legacy_aliases.py`: the issue text references this file.
  An audit of the current codebase confirms the file does not exist. FR-005 records
  the verification step; if it reappears it must be audited before deletion.
- `resolve_selector` in `selector_resolution.py` is called by commands outside the
  eight in-scope files (e.g., `charter/interview.py`, `charter/generate.py`,
  `agent/mission_create.py`). Those callers are out of scope and must not be touched.

---

## Requirements

### Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Hard-remove `--feature` Typer option from 8 commands | Delete the `--feature` Typer option declaration from the entrypoint functions of `implement`, `merge`, `next`, `research`, `context`, `accept`, `lifecycle plan`, `lifecycle tasks`, and `mission_type current`. Passing `--feature` on any of these commands yields an unknown-option error. | High | Open |
| FR-002 | Rename internal `feature`/`feature_slug` parameters and variables | In the eight in-scope command files and their direct intra-file call-site functions, rename `feature: str \| None` Typer/function parameters to `mission: str \| None`, `_feature_number` locals to `_mission_number`, and analogous `feature`-prefixed identifiers where the rename is unambiguous and stays inside the same file. Do not rename historical-data-parsing field keys (e.g., `feature_slug` in stored JSON). | High | Open |
| FR-003 | Preserve required-selector guard on every de-aliased command | Each in-scope command that previously relied on `resolve_selector` (or the `mission or feature` fallback) to raise an error on no-selector must retain equivalent validation after the alias is removed. An empty or whitespace-only `--mission` value must produce a clean user-facing error (not a `TypeError` or unhandled exception). | High | Open |
| FR-004 | Preserve whitespace-normalization in selector validation | Each in-scope command's selector validation must strip leading/trailing whitespace from the `--mission` value before checking emptiness, matching the prior `resolve_selector` normalization behavior (`_normalize_selector`). | High | Open |
| FR-005 | Confirm absence of `src/specify_cli/missions/_legacy_aliases.py` | Verify at implementation time that the file does not exist. If it is present, perform a zero-caller audit (`grep -rn "_legacy_aliases"` across `src/`) before deletion. Do not delete if any live importer remains; de-export first. | Medium | Open |
| FR-006 | Update `resolve_selector` call sites in in-scope commands | Remove the `alias_value=feature` and `alias_flag="--feature"` arguments from every `resolve_selector` call in the eight in-scope files. After the alias branch is removed, the alias-related parameters in these calls become `alias_value=None`. Prefer inlining the simplified guard (direct `require_explicit_feature` call or equivalent) rather than passing `alias_value=None` as dead arguments. | High | Open |
| FR-007 | Flip terminology guard to forbid `--feature` in in-scope files | Extend `INSCOPE_FEATURE_FREE_FILES` in `tests/contract/test_terminology_guards.py` (or add an equivalent set) with all eight in-scope command file paths. The updated guard must fail on ANY occurrence of the literal `"--feature"` in those files — not just inside Typer Option blocks — whether visible or hidden. This satisfies the issue's "fails on ANY `--feature` Typer option" acceptance criterion. | High | Open |
| FR-008 | Add no-selector regression test for each in-scope command | Add at least one focused unit or integration test per in-scope command (eight tests total) that invokes the command with no `--mission` argument and asserts: (a) a user-facing error string appears, (b) exit code is non-zero, (c) no `TypeError` or Python traceback is present. | High | Open |
| FR-009 | Update `tests/specify_cli/cli/test_no_visible_feature_alias.py` | The existing test `test_every_feature_flag_is_hidden` currently passes because remaining aliases are `hidden=True`. After removal, that test must still pass (no `--feature` flags remain to be visible). Update or replace it with a test that asserts zero `--feature` Typer options exist across the entire CLI tree (not just that they are hidden). | Medium | Open |
| FR-010 | Update live docs and CHANGELOG | All active CLI-usage examples in `docs/` and the `CHANGELOG.md` unreleased section must use `--mission`, not `--feature`. The migration note at `docs/migration/feature-flag-deprecation.md` may retain `--feature` as a named-deprecated flag (it is excluded from doc scanning per the existing guard). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No test deletions to make the build green | All tests that existed before this mission must still pass after it. No test may be deleted to resolve a test failure caused by this change; tests must be fixed or updated to match the new behavior. Measured by: zero test count reduction in the in-scope command test suites. | Correctness | High | Open |
| NFR-002 | No regression in `--mission` resolution behavior | The behavior of `--mission` (handle resolution, disambiguation errors, mission-not-found errors, JSON error payloads) is functionally identical before and after this change. Measured by: existing `resolve_mission_handle` and mission-resolver test suites pass without modification. | Correctness | High | Open |
| NFR-003 | No new Sonar/ruff complexity violations | No function modified by this mission may exceed cyclomatic complexity 15 after the change. Any guard logic inlined from `resolve_selector` must be expressed as a one-to-three-line conditional, not a nested block. | Maintainability | Medium | Open |
| NFR-004 | Out-of-scope callers of `resolve_selector` are untouched | `resolve_selector` call sites outside the eight in-scope files (e.g., `charter/interview.py`, `charter/generate.py`, `agent/mission_create.py`) are not modified. The `resolve_selector` function itself is not deleted by this mission. | Stability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Scope limited to 8 user-facing command files | Only the following files may have `--feature`-related changes applied: `src/specify_cli/cli/commands/implement.py`, `merge.py`, `next_cmd.py`, `research.py`, `context.py`, `accept.py`, `lifecycle.py`, `mission_type.py`. The ten already-cleaned internal files (`agent/status.py`, `agent/tasks.py`, `agent/workflow.py`, `agent/context.py`, `agent/mission.py`, `charter/lint.py`, `materialize.py`, `validate_encoding.py`, `validate_tasks.py`, `verify.py`) are not modified. | Technical | High | Open |
| C-002 | Does not implement issue #1059 | This mission does not build a compatibility inventory, a sunset-policy document, or any mechanism for tracking deprecated alias usage. Those are the subject of issue #1059, which remains a separate workstream. | Scope | High | Open |
| C-003 | Historical data-parsing field names are immutable | Field key names in stored artifacts (`meta.json`, `status.events.jsonl`, `feature-runs.json`, and any other persisted JSON that uses `feature_slug` as a data field) are not renamed. Only CLI surface and in-memory variable names change. | Data Integrity | High | Open |
| C-004 | No deprecation grace period | The `--feature` alias is deleted outright — no `DeprecationWarning`, no warning-then-fail transition period, no hidden passthrough. The issue specifies hard removal. | Scope | High | Open |
| C-005 | `resolve_selector` function is not deleted | The `resolve_selector` function in `src/specify_cli/cli/selector_resolution.py` is retained for out-of-scope callers. Only the alias-bearing call sites in the eight in-scope files are updated. | Technical | Medium | Open |

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All eight in-scope command files contain zero occurrences of the literal `"--feature"` at merge time, as verified by the updated `INSCOPE_FEATURE_FREE_FILES` gate.
- **SC-002**: `pytest tests/contract/test_terminology_guards.py` passes on a clean branch after the change. Adding `"--feature"` back to any in-scope file causes the guard to fail (verified by a manual toggle test).
- **SC-003**: All eight in-scope commands return exit code 2 and a user-readable error string (no `TypeError` traceback) when invoked without `--mission`, as verified by the new no-selector regression tests (FR-008).
- **SC-004**: The full test suite passes with zero new failures and zero deleted tests.
- **SC-005**: No live CLI `--help` output for any in-scope command mentions `--feature`, as verified by `test_help_output_never_mentions_feature_alias`.

---

## Assumptions

1. PR #1985 has already removed the `hidden_feature_option` helper from
   `_legacy_aliases.py` and deleted that file. The absence of the file in the current
   codebase is treated as confirmed; FR-005 encodes the verification step in case
   it reappears on the branch.
2. The `resolve_selector` function will remain in `selector_resolution.py` for the
   foreseeable future; no deprecation of that function is in scope.
3. `lifecycle.specify` uses `feature` as a **positional argument** for the mission
   name (e.g., `spec-kitty lifecycle specify my-mission-name`). This positional
   argument is NOT the `--feature` flag and is out of scope for this mission.
4. The `test_every_feature_flag_is_hidden` test in
   `tests/specify_cli/cli/test_no_visible_feature_alias.py` currently passes by
   confirming all `--feature` flags are hidden. After removal, no `--feature` flags
   exist at all, so the test either passes trivially or must be updated to assert
   zero `--feature` flags (FR-009).
5. Renaming `feature_slug` as a local variable is in scope where it is a call-site
   parameter name in the eight in-scope files; renaming it as a dict-key string
   constant or JSON field name is out of scope (C-003).

---

## Domain Language

| Canonical Term | Deprecated / Forbidden Form | Notes |
|----------------|-----------------------------|-------|
| `--mission` | `--feature` | CLI flag for mission handle selection |
| `mission_slug` | `feature_slug` | Internal variable name (CLI layer only; JSON field name unchanged) |
| `_mission_number` | `_feature_number` | Local variable in `detect_feature_context` call sites |
| mission | feature | Domain object name in user-facing surfaces |
