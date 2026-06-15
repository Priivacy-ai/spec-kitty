# Task Workflow Bug Fixes: Spec Path and Error Hint

## Overview

Two bugs disrupt the standard `map-requirements → finalize-tasks` task workflow. The P1 bug silently breaks `map-requirements` whenever a coordination worktree exists. The P2 bug leaves agents without an actionable recovery path when `finalize-tasks --validate-only` rejects a planned-new-file entry in `owned_files`.

**GitHub issues:** #1981 (P1), #1982 (P2)

---

## Problem Statement

After a mission's coordination worktree is created by `setup-plan`, `map-requirements` stops being able to read `spec.md`. The command resolves the mission directory through the topology-aware resolver, which returns the coordination worktree path — but `spec.md` is never staged there. This makes `map-requirements` entirely unusable in the `setup-plan → map-requirements → finalize-tasks` sequence that the documented workflow prescribes.

Independently, when an agent authors a WP whose `owned_files` includes a path that will be created during implementation (a planned-new-file), `finalize-tasks --validate-only` emits an error that does not include a concrete YAML example of how to add that path to `create_intent`. Agents cannot self-recover without reading source code or documentation.

---

## Actors

- **Agents** running `map-requirements` and `finalize-tasks --validate-only` in automated mission loops
- **Human developers** authoring WP frontmatter and triaging finalize-tasks errors

---

## User Scenarios & Testing

### Scenario 1: map-requirements after setup-plan (P1)

1. Agent creates a mission and commits `spec.md` in the primary checkout.
2. Agent runs `setup-plan` — coordination worktree is created at `.worktrees/<slug>-<mid8>-coord/`.
3. Agent runs `map-requirements --wp WP01 --refs FR-001 --mission <slug> --json`.
4. **Expected**: command reads `spec.md` from the primary checkout and succeeds.
5. **Previously actual**: error `"spec.md not found: <coord-worktree-path>/kitty-specs/.../spec.md"`.

### Scenario 2: map-requirements before setup-plan (regression guard)

1. Agent creates a mission and commits `spec.md`.
2. Agent runs `map-requirements` before `setup-plan` — no coordination worktree exists.
3. **Expected**: command works correctly (this was never broken; must stay green).

### Scenario 3: finalize-tasks --validate-only with planned-new-file (P2)

1. Agent authors a WP with `owned_files: [src/new_module.py]` where `src/new_module.py` does not yet exist on disk.
2. Agent runs `finalize-tasks --validate-only --json`.
3. **Expected**: JSON output includes an error message containing a concrete YAML snippet such as `create_intent:\n  - src/new_module.py` so the agent can self-recover without consulting documentation.

### Scenario 4: finalize-tasks --validate-only, planned-new-file with create_intent set (regression guard)

1. Agent authors WP with `owned_files: [src/new_module.py]` and `create_intent: [src/new_module.py]`.
2. **Expected**: validation passes; no error emitted for that path.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `map-requirements` reads `spec.md` from the primary checkout regardless of whether a coordination worktree exists for the mission. | Proposed |
| FR-002 | `map-requirements` continues to resolve WP task files from the topology-aware (coordination-worktree-preferred) path, preserving existing write-side behavior. | Proposed |
| FR-003 | When `finalize-tasks --validate-only` (or any `finalize-tasks` invocation) rejects a literal `owned_files` path that matches zero files, the error output includes a ready-to-paste YAML example showing how to declare that path under `create_intent` in the WP frontmatter. | Proposed |
| FR-004 | A regression test asserts that running `finalize-tasks --validate-only` with a planned-new-file in `owned_files` (without `create_intent`) produces an error whose text contains both the path and the `create_intent` YAML key, verifiable by string match. | Proposed |
| FR-005 | A regression test asserts that `map-requirements` succeeds when a coordination worktree exists and `spec.md` is present only in the primary checkout. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | No existing `map-requirements` or `finalize-tasks` tests regress after the fix. | 0 new test failures | Proposed |
| NFR-002 | The `spec.md` path fix introduces no additional subprocess calls or git operations. | Resolution remains pure-path (filesystem stat only) | Proposed |
| NFR-003 | The enhanced error message for `create_intent` fits within a single JSON string value visible in the `--json` output without truncation. | ≤ 300 characters per per-path error entry | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | `map-requirements` must use the canonical `primary_feature_dir_for_mission` helper already present in `feature_dir_resolver.py` for `spec.md` resolution — no inline path construction bypassing the sanctioned resolver module (enforced by `tests/architectural/test_no_raw_mission_spec_paths.py`). | Proposed |
| C-002 | The `create_intent` YAML example in the error message must use the field name exactly as it appears in `WPMetadata` (i.e., `create_intent`, not an alias). | Proposed |
| C-003 | Both fixes land in the same PR; they affect different call sites and have no shared code, so they must not be entangled in a way that prevents independent revert. | Proposed |

---

## Assumptions

- `primary_feature_dir_for_mission` in `feature_dir_resolver.py` is the authoritative topology-blind resolver and is already tested; the fix uses it without modification.
- The `create_intent` YAML hint enhancement applies to the `validate_glob_matches` error message in `ownership/validation.py`, which is the single source for all per-path zero-match errors.
- The existing `_nearest_match_suggestion` helper output (when a close file name is found) must remain in the error alongside the new `create_intent` example; the two hints are not mutually exclusive.

---

## Out of Scope

- Issue #1983 (Host-CLI ⇄ source provenance contract) — unrelated; requires a separate design.
- Changing how the coordination worktree is populated (e.g., copying `spec.md` into it) — the correct fix is a targeted resolver swap, not topology restructuring.
- Altering the `create_intent` suppression behavior itself — the mechanism is correct; only the error hint is improved.

---

## Success Criteria

1. `map-requirements` completes successfully after `setup-plan` has run, with no change to observed command output for the happy path.
2. `finalize-tasks --validate-only` on a WP with a planned-new-file produces an error JSON whose `ownership_literal_path_errors` entries each contain the string `create_intent` and a ready-to-use YAML fragment.
3. All pre-existing tests in `tests/specify_cli/` pass without modification.
4. Two new regression tests added — one per bug — are collected and green in the standard parallel test run.
