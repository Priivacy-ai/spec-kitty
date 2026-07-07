---
work_package_id: WP01
title: Pack-path env-var indirection
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
tracker_refs: []
planning_base_branch: issue/2437-env-var-pack-paths
merge_target_branch: issue/2437-env-var-pack-paths
branch_strategy: Planning artifacts for this mission were generated on issue/2437-env-var-pack-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue/2437-env-var-pack-paths unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Core fixes
assignee: ''
agent: "cursor:composer-2.5-fast:reviewer-renata:reviewer"
shell_pid: "15524"
history:
- at: '2026-07-07T12:08:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/doctrine/drg/org_pack_config.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/org_pack_config.py
- tests/doctrine/test_org_pack_subdir.py
- tests/specify_cli/doctrine/test_config.py
- tests/integration/test_org_pack_missing_path_hard_fails.py
- docs/api/environment-variables.md
- docs/guides/create-an-org-doctrine-pack.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Pack-path env-var indirection

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (assign at dispatch time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/doctrine/drg/org_pack_config.py`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Objectives & Success Criteria

Make `doctrine.org.packs[].local_path` (and the legacy `organisation_packs[].path` shape) support `${VAR}`/`$VAR` env-var indirection, composed correctly with the existing `~` tilde-expansion, resolved at `effective_root()` time — **without** mutating the stored config value, **without** weakening the `subdir` no-`..`/no-absolute guard or the symlink-containment check, and **failing closed** (named, actionable error) when a referenced variable is unset or empty.

Done when:
- A config value like `${SPEC_KITTY_PACK_HOME}/org-pack` resolves correctly via `effective_root()` when the env var is set.
- The same config, saved and reloaded (`save_pack_registry` round-trip), still contains the literal `${SPEC_KITTY_PACK_HOME}/org-pack` string on disk — not an expanded absolute path.
- An unset `SPEC_KITTY_PACK_HOME` raises a named error identifying the variable and the pack name, rather than silently producing a literal-token path or an empty org layer.
- `~` and literal absolute paths continue to resolve exactly as before (no regression).
- `subdir` validation and the symlink-containment check are unaffected — env expansion is scoped to `local_path` only.
- The legacy `organisation_packs[].path` shape gets the same behavior through the shared `OrgPackConfig` constructor (no parallel implementation).

## Context & Constraints

This WP implements FR-001 through FR-007, NFR-001, C-003, C-004 from `kitty-specs/pack-path-env-indirection-01KWY79W/spec.md`. Read `kitty-specs/pack-path-env-indirection-01KWY79W/plan.md` (Technical Context, IC-01) and `kitty-specs/pack-path-env-indirection-01KWY79W/research.md` (WP1 section) before writing any code — they capture the exact rationale for *where* expansion must live, derived from a pre-spec investigation squad that reproduced the failure modes live in this codebase.

**The single most important constraint**: do **not** put env-var expansion inside the `local_path` field's `mode="before"` validator (`_expand_tilde`, currently at `src/doctrine/drg/org_pack_config.py:64-67`). That validator's output becomes the *stored* model value, and `_pack_to_yaml_dict` (`org_pack_config.py:342-355`, used by `save_pack_registry`) re-serializes `str(pack.local_path)` verbatim. If expansion happens there, the first save after a load will freeze the machine-local absolute path back into `.kittify/config.yaml`, destroying the entire portability goal. Expansion belongs at **resolution time**, inside `effective_root()`, applied to a local variable — never written back to `self.local_path`.

Read `effective_root()` fully (currently ~lines 117-155) before touching it. It has three steps: (1) classify `local_path` as absolute vs. relative and join against `repo_root` if relative, (2) short-circuit if `subdir is None`, (3) join `subdir` and run a symlink-escape containment check (`resolved_candidate.relative_to(resolved_pack_root)`, raising `OrgPackSubdirEscapeError` on failure). Env/tilde expansion must happen **before** step 1's `is_absolute()` check, because an unexpanded `${VAR}/...` template is not absolute and would otherwise be incorrectly joined under `repo_root`.

Read the existing `OrgPackMissingError` family in `src/specify_cli/doctrine/config.py` (`assert_pack_local_paths_exist`, ~lines 30-39) before designing the unset-var error — extend that existing fail-closed pattern rather than inventing a new one.

## Branch Strategy

- **Strategy**: single-branch mission (`topology: coord`, no per-WP lanes required for this mission's size — confirm via `lanes.json` if present at implement time).
- **Planning base branch**: `issue/2437-env-var-pack-paths`
- **Merge target branch**: `issue/2437-env-var-pack-paths`

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change them manually unless you are certain the branch topology has changed. If `spec-kitty agent action implement WP01` reports a different lane/worktree path, trust that command's output over this static text.

## Subtasks & Detailed Guidance

### Subtask T001 – Add expansion at `effective_root()` resolution time

- **Purpose**: This is the core fix. `${VAR}`/`$VAR` tokens in `local_path` must expand at read time without mutating the stored field.
- **Steps**:
  1. Add a small, pure helper function (e.g. `_expand_path_template(raw: str) -> str`) near `OrgPackConfig` that applies `os.path.expandvars(raw)` then `os.path.expanduser(...)`. Keep it pure — no filesystem access, no exceptions for the happy path.
  2. In `effective_root()`, compute the expanded string from `str(self.local_path)` via this helper, then continue the existing logic (absolute/relative classification, `repo_root` join) using the **expanded** value — but do NOT assign the expanded value back to `self.local_path`.
  3. Narrow (or retire) the eager-expansion behavior of `_expand_tilde` so it no longer changes the *stored* value's semantics — decide whether to keep it as a `Path(str(value))` type-coercion no-op, or remove it and let `local_path` stay a plain `Path` constructed from the raw string. Whichever you choose, the stored value must remain exactly what the operator wrote (including any `${...}` or `~` tokens, unexpanded).
  4. Double-check ordering: expansion must run before the `is_absolute()` branch, since `${SPEC_KITTY_PACK_HOME}/org-pack` is not absolute as written.
- **Files**: `src/doctrine/drg/org_pack_config.py`.
- **Parallel?**: No — this is the foundation the other subtasks build on.
- **Notes**: Do not touch `subdir`'s validator (`_validate_subdir`) — it must keep validating the literal, unexpanded string.

### Subtask T002 – Fail-closed error for unset/empty env var

- **Purpose**: `os.path.expandvars`'s stdlib default silently leaves `${UNSET}` as a literal token when the variable isn't set — this is exactly the "looks fixed but isn't" failure mode the pre-spec investigation flagged. Resolution must fail loudly instead.
- **Steps**:
  1. After calling `os.path.expandvars`, detect whether any `${...}` or `$IDENT` token survives unexpanded (a simple regex check, e.g. `re.search(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*", expanded)` on the *result* — if the pattern still matches after expansion, the variable was unset).
  2. Raise a new, named exception (e.g. `OrgPackEnvVarUnsetError`, following the existing `OrgPack*Error` naming convention next to `OrgPackMissingError`/`OrgPackSubdirEscapeError`) that names both the unresolved variable and the configured pack's `name`.
  3. Ensure this error surfaces through the same call sites that already handle `OrgPackMissingError` (e.g. `assert_pack_local_paths_exist` in `src/specify_cli/doctrine/config.py`) so operator-facing messaging stays consistent — check whether that function should catch-and-rewrap, or whether raising directly from `effective_root()` is sufficient given its existing callers already propagate exceptions.
  4. Confirm (via `charter/drg.py:105` `load_org_drg()` and `doctrine_service_factory.py:72`) that this failure does **not** get silently swallowed into an empty org DRG layer — it must propagate as a visible, actionable error.
- **Files**: `src/doctrine/drg/org_pack_config.py`, `src/specify_cli/doctrine/config.py` (if the error needs wrapping/re-raising there).
- **Parallel?**: No — depends on T001's expansion helper.
- **Notes**: Do not use a bare `except Exception: pass` anywhere in this path (repo-wide constraint against empty/effect-free exception handlers).

### Subtask T003 – Verify round-trip preservation

- **Purpose**: Prove the T001 design decision (expand read-side, never write-side) actually holds under a real save→load cycle.
- **Steps**:
  1. Read `_pack_to_yaml_dict` and `save_pack_registry` fully.
  2. Confirm they serialize `self.local_path` (the stored, unexpanded value) — if anything currently forces eager expansion before serialization, fix it as part of T001, not here; this subtask is verification + a regression test.
  3. Write a test that: constructs an `OrgPackConfig` with `local_path="${SPEC_KITTY_PACK_HOME}/org-pack"`, calls `save_pack_registry`, reloads via `load_pack_registry` (or the equivalent read path), and asserts the reloaded `local_path` string is still exactly `${SPEC_KITTY_PACK_HOME}/org-pack`.
- **Files**: `tests/doctrine/test_org_pack_subdir.py` (extend the existing `TestRoundTrip` class, ~lines 354-393).
- **Parallel?**: [P] — can be written alongside T004/T006 once T001 lands.
- **Notes**: This is the regression test that directly proves the squad's highest-severity finding is closed.

### Subtask T004 – Confirm legacy shape coverage

- **Purpose**: `organisation_packs[].path` must inherit the same fix with zero duplicated logic.
- **Steps**:
  1. Read `_registry_from_legacy_organisation_packs` and `_build_legacy_single_pack` (~lines 302-339) and confirm both construct `OrgPackConfig` (not a bespoke parallel path).
  2. Add a test using the legacy config shape with an env-var-templated path, asserting it resolves identically to the canonical shape.
- **Files**: `tests/specify_cli/doctrine/test_config.py`.
- **Parallel?**: [P] — independent of T003, both depend only on T001.
- **Notes**: If you find the legacy path does NOT funnel through the same constructor, treat that as a bug to fix here (single canonical seam), not a reason to duplicate the expansion logic.

### Subtask T005 – Full regression + new test suite for WP01

- **Purpose**: Close every scenario named in `spec.md`'s User Scenarios & Testing section for WP1.
- **Steps**: Ensure the following are all covered (some may already exist as T003/T004 above — this subtask is the completeness pass):
  1. Env-var expansion success case (`${SPEC_KITTY_PACK_HOME}/org-pack` with the var set) — via `effective_root()` directly, not just via `load_pack_registry`, to prove the fix works for directly-constructed `OrgPackConfig` instances too.
  2. Tilde expansion regression (`~/pack` still works).
  3. Literal absolute path regression (unchanged behavior).
  4. Unset-var fail-closed case (T002's new error, asserting the error message names the variable and the pack).
  5. Round-trip preservation (T003).
  6. Legacy shape coverage (T004).
  7. `subdir` remains validated as a literal (no `..`/absolute bypass) — add or confirm a test proving env-var syntax in `subdir` is rejected or ignored (does NOT get expanded), preserving `_validate_subdir`'s existing guarantees.
  8. Symlink-escape containment check (`TestSymlinkEscape`, existing ~lines 250-290) still passes unmodified — run it, don't just assume.
- **Files**: `tests/doctrine/test_org_pack_subdir.py`, `tests/specify_cli/doctrine/test_config.py`, `tests/integration/test_org_pack_missing_path_hard_fails.py`.
- **Parallel?**: No — this is the completeness/verification pass after T001-T004.
- **Notes**: Run `pytest tests/doctrine/test_org_pack_subdir.py tests/specify_cli/doctrine/test_config.py tests/integration/test_org_pack_missing_path_hard_fails.py -v` and confirm all pass, including the pre-existing tests (no regressions).

### Subtask T006 – Documentation

- **Purpose**: Operators need to discover the new env-var name and syntax.
- **Steps**:
  1. Add `SPEC_KITTY_PACK_HOME` to `docs/api/environment-variables.md`, following the existing entry format for `SPEC_KITTY_HOME`/`SPEC_KITTY_TEMPLATE_ROOT`.
  2. Update `docs/guides/create-an-org-doctrine-pack.md`'s `local_path` documentation to mention `${VAR}`/`$VAR` indirection support, with a short example.
- **Files**: `docs/api/environment-variables.md`, `docs/guides/create-an-org-doctrine-pack.md`.
- **Parallel?**: [P] — independent of the code subtasks, can be done any time after T001 lands.
- **Notes**: Keep the example consistent with the quickstart in `kitty-specs/pack-path-env-indirection-01KWY79W/quickstart.md`.

### Subtask T007 – Quality gate

- **Purpose**: Confirm the WP is mergeable.
- **Steps**:
  1. Run `pytest tests/doctrine/ tests/specify_cli/doctrine/ tests/integration/test_org_pack_missing_path_hard_fails.py tests/integration/test_org_pack_subdir_e2e.py tests/doctrine/drg/test_org_pack_auto_emit.py -v` — all green, no regressions.
  2. Run `ruff check src/doctrine/drg/org_pack_config.py src/specify_cli/doctrine/config.py` and `mypy` on the same files — zero issues (per repo-wide standing rule: no `# noqa`/`# type: ignore` additions to silence real findings).
- **Files**: N/A (verification only).
- **Parallel?**: No — final gate.
- **Notes**: If mypy flags the new error class or helper, fix the types — don't suppress.

## Test Strategy

- Unit tests: `tests/doctrine/test_org_pack_subdir.py`, `tests/specify_cli/doctrine/test_config.py`.
- Integration tests: `tests/integration/test_org_pack_missing_path_hard_fails.py`, `tests/integration/test_org_pack_subdir_e2e.py`.
- No org pack is configured in this repository — all new tests use fixture-based `tmp_path` repos, consistent with the existing test files in this area.
- Run: `pytest tests/doctrine/test_org_pack_subdir.py tests/specify_cli/doctrine/test_config.py tests/integration/test_org_pack_missing_path_hard_fails.py tests/integration/test_org_pack_subdir_e2e.py tests/doctrine/drg/test_org_pack_auto_emit.py -v`

## Risks & Mitigations

- **Risk**: Expanding inside the field validator by mistake, silently reintroducing the round-trip corruption bug. **Mitigation**: T003's round-trip test is the non-negotiable proof; do not consider T001 done until it passes.
- **Risk**: Expanding `subdir` by mistake (bypassing `_validate_subdir`'s no-`..`/no-absolute guard). **Mitigation**: T005 item 7 explicitly tests that `subdir` is not expanded.
- **Risk**: Unset-var detection regex being too loose/strict. **Mitigation**: Test both `${VAR}` and bare `$VAR` forms explicitly (spec requires both syntaxes).

## Review Guidance

- Confirm the round-trip test (T003) actually fails on the pre-fix code (temporarily revert T001's resolution-time change and re-run, or review the git history) to prove it's a real regression guard, not a tautology.
- Confirm no expansion logic was added to `_validate_subdir` or the `subdir` field path.
- Confirm the new error class follows the existing `OrgPack*Error` naming and message conventions.
- Confirm `docs/api/environment-variables.md` and the org-pack guide were updated (T006) — this is an easy subtask to skip.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-07T12:08:11Z – system – Prompt created.
- 2026-07-07T12:37:19Z – cursor:composer-2.5-fast:implementer-ivan:implementer – shell_pid=5112 – Assigned agent via action command
- 2026-07-07T12:46:16Z – cursor:composer-2.5-fast:implementer-ivan:implementer – shell_pid=5112 – Ready for review: env-var indirection implemented, tested, docs updated
- 2026-07-07T12:46:25Z – cursor:composer-2.5-fast:reviewer-renata:reviewer – shell_pid=15524 – Started review via action command
