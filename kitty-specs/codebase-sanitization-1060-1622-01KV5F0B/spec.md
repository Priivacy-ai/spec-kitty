# Mission Specification: Internal `--feature` & `status_service` sanitization

**Mission ID**: `01KV5F0BPCVR42KCJX10ZQNB9D`
**Slug**: `codebase-sanitization-1060-1622-01KV5F0B`
**Type**: software-dev
**Epic**: #1797 (3.2.0 codebase sanitization — dead-code & LOC reduction)
**Addresses**: #1060 (partial — internal-cluster slice), #1622 (full)

## Purpose

Remove two pockets of dead/legacy surface so later missions inherit a cleaner CLI
and status boundary, while keeping the change set small enough to rebase cleanly
through a period of heavy parallel bug-fix landings.

1. **#1060-A** — the terminology canon is `--mission`, yet the *internal/agent*
   command cluster still declares a hidden deprecated `--feature` alias. Retiring
   it on the low-external-risk cluster removes parsing paths and old vocabulary
   without touching the user-facing top-level commands (deferred behind #1059).
2. **#1622** — **already resolved in code** by mission 01KTPKST WP09 (commit
   `be932d19a`): the 2 truly-dead functions (`append_event_log_batch`,
   `read_wp_lane_actor`) were deleted, and the 3 remaining symbols
   (`StatusReadSource`, `EventLogWriteTarget`, `StatusContractError`) were
   correctly de-exported (they are load-bearing live internals of the contract
   facade). The "5 dead symbols" premise was stale (pre-#1614-rebase). This
   mission carries #1622 as a **verify-only task**: confirm the resolved state on
   the import graph and close the ticket. **No code change** for #1622.

## Scope

### In scope

- Remove the hidden `--feature` Typer option from the **internal/agent command
  cluster**: `agent status`, `agent tasks`, `agent workflow`, `agent context`,
  `agent mission`, `charter lint`, `materialize`, `validate_encoding`,
  `validate_tasks`, `verify`.
- Update first-party templates/skills (`src/doctrine/`, generated agent command
  surfaces) that pass `--feature` to any in-scope command, to use `--mission`.
- Tighten the contract gate so a `--feature` Typer option on an in-scope command
  fails CI whether hidden or visible (the cluster moves from "hidden allowed" to
  "absent").
- Boyscout (same surface): remove the dead `hidden_feature_option()` +
  `LEGACY_FEATURE_HELP` from `_legacy_aliases.py` (0 `src/` callers), retiring
  their tests + dead-symbol allowlist entries.
- For #1622: a **verify-only** task — confirm on the import graph that
  `append_event_log_batch`/`read_wp_lane_actor` are gone and that
  `StatusReadSource`/`EventLogWriteTarget`/`StatusContractError` remain as live
  de-exported internals; record the re-classification; close #1622. No code edit.

### Out of scope

- The user-facing top-level commands `implement`, `merge`, `next`, `research`,
  `context`, `accept`, `lifecycle`, `mission_type` (scripted-user compatibility
  risk; deferred behind the #1059 sunset policy).
- Deleting `selector_resolution.resolve_selector` — it remains in service for
  the deferred commands above. (Note: the *dead* `hidden_feature_option` helper
  inside `_legacy_aliases.py` IS removed under FR-009 — it has no callers; this
  is distinct from the resolver, which stays.)
- Any change to the runtime/status *hot paths* (`status/`, `task_utils/`,
  `legacy_detector.py`) beyond the `status_service` symbol removals.
- Renaming internal `feature_slug` variables (tracked separately under #1060).

## User Scenarios & Testing

**Primary actor**: a Spec Kitty maintainer / CI gate (the "user" of the CLI
surface and the terminology guard).

- **Scenario — alias is gone (happy path)**: A maintainer runs an in-scope
  internal command (e.g. `spec-kitty agent tasks status --feature 012-x`).
  Trigger: a `--feature` argument is supplied. Outcome: the command rejects the
  unknown option (Typer "no such option") rather than silently accepting it; the
  equivalent `--mission` invocation succeeds unchanged.
- **Scenario — gate enforces absence**: A contributor adds a `--feature` Typer
  option (hidden or visible) to an in-scope command. Trigger: CI runs the
  terminology guard. Outcome: `test_no_visible_feature_alias_in_cli_commands`
  (or its successor) fails, naming the file and line.
- **Scenario — first-party callers updated**: A template or skill that used to
  pass `--feature` to an in-scope command now passes `--mission`. Trigger: the
  generated command surface is exercised. Outcome: no `--feature` is emitted for
  in-scope commands anywhere in `src/doctrine/` or generated agent dirs.
- **Scenario — status_service prune**: After the symbol removals, the import
  graph has no references to the removed names. Trigger: the dead-symbol gate and
  full test suite run. Outcome: both pass; baseline counts are not regressed.
- **Edge case — deferred commands still accept `--feature`**: An out-of-scope
  command (e.g. `spec-kitty merge --feature 012-x`) continues to accept the
  hidden alias. Trigger: the alias is supplied. Outcome: it resolves via
  `resolve_selector` exactly as before (no behavior change).

### Rules / invariants that must always hold

- The conflict surface is confined to CLI option *declarations* in the in-scope
  command modules + the `coordination/status_service.py` module + the terminology
  guard test + first-party caller templates. No edits to runtime/status hot paths.
- A test is never deleted merely to reduce code: retiring a tested symbol
  requires removing the symbol *and* its now-meaningless tests together, with a
  written rationale (DIRECTIVE_003).
- The dead-symbol gate baseline is never loosened to hide a regression.

## Domain Language

- **Mission / `--mission`** — canonical selector (Terminology Canon).
- **`--feature`** — deprecated, hidden legacy alias for `--mission`; prohibited
  for active systems.
- **Internal/agent command cluster** — commands invoked primarily by Spec
  Kitty's own templates/skills and automation, not by external scripted users.
- **Wire-or-retire** — for a dead symbol, the choice between connecting it to a
  live call site (wire) or deleting it together with its tests (retire).

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The hidden `--feature` Typer option MUST be removed from every in-scope internal/agent command (`agent status`, `agent tasks`, `agent workflow`, `agent context`, `agent mission`, `charter lint`, `materialize`, `validate_encoding`, `validate_tasks`, `verify`). | Draft |
| FR-002 | Each de-aliased in-scope command MUST continue to accept `--mission` with identical resolution semantics to before this mission. | Draft |
| FR-003 | First-party templates and skills under `src/doctrine/` and the generated agent command surfaces MUST NOT pass `--feature` to any in-scope command; they MUST use `--mission`. | Draft |
| FR-004 | The terminology contract gate MUST fail when an in-scope command declares a `--feature` Typer option, whether `hidden=True` or visible. | Draft |
| FR-005 | Out-of-scope user-facing commands MUST retain the hidden `--feature` alias and its `resolve_selector` semantics unchanged (no behavior regression). | Draft |
| FR-006 | #1622 MUST be verified as already-resolved: a grep over `src/` + `tests/` MUST confirm `append_event_log_batch` and `read_wp_lane_actor` are absent, and that `StatusReadSource`/`EventLogWriteTarget`/`StatusContractError` exist only as de-exported live internals (not in `status_service.__all__`, but with live internal callers). | Draft |
| FR-007 | #1622 MUST be closed on the tracker with the re-classification recorded (the upstream 01KTPKST dead-symbol directive delivered 2/5 deletions; the other 3 are retained-because-live and de-exported). No code change is made to `status_service.py` under this mission. | Draft |
| FR-008 | `selector_resolution.resolve_selector` (the load-bearing shared resolver) MUST remain present and functional after this mission, so the deferred out-of-scope commands keep their `--feature` alias. | Draft |
| FR-009 | The dead `hidden_feature_option()` helper and `LEGACY_FEATURE_HELP` constant in `missions/_legacy_aliases.py` (zero `src/` callers — every command declares `--feature` inline) MUST be removed, their tests retired with a documented rationale (C-001), and the corresponding `test_no_dead_symbols`/`test_no_dead_modules` allowlist entries deleted. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | The change set MUST stay within the bounded conflict surface so it rebases onto `upstream/main` without conflicts in runtime/status hot paths. | Zero diff hunks under `src/specify_cli/status/`, `src/specify_cli/task_utils/`, or `legacy_detector.py`; rebase onto a fresh `upstream/main` produces no conflicts in those paths. | Draft |
| NFR-002 | The mission MUST be net LOC-negative. | `git diff --shortstat` against the merge base shows more deletions than insertions in `src/`. | Draft |
| NFR-003 | No quality-gate regression. | `ruff`, `mypy`, and the full `tests/` suite pass with zero new issues; dead-symbol baseline counts unchanged or reduced. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | No test may be deleted solely to reduce code; a tested symbol is retired only together with its tests under a written rationale (DIRECTIVE_003). | Active |
| C-002 | This is a bulk edit (`change_mode: bulk_edit`): an `occurrence_map.yaml` classifying every `--feature` occurrence MUST be produced at plan and honored at review. | Active |
| C-003 | PR-bound: lands via PR to `upstream/main`; never a direct push to `origin/main`. | Active |
| C-004 | Every addressed issue (#1060, #1622) gets an issue-matrix row, a tracker comment naming this mission, and operator-assigned claim. | Active |

## Success Criteria

- SC-001: Running any in-scope internal command with `--feature` errors as an
  unknown option; the `--mission` form behaves identically to pre-mission.
- SC-002: The terminology gate fails the build if a `--feature` option is
  reintroduced on an in-scope command (verified by a deliberate red test before
  green).
- SC-003: No reference to the five `status_service` symbols remains on the import
  graph after the mission; dead-symbol gate and full suite stay green.
- SC-004: The mission's diff is net LOC-negative in `src/` and touches none of
  the runtime/status hot paths.
- SC-005: Out-of-scope commands' `--feature` behavior is provably unchanged.

## Key Entities

- **In-scope command module** — a CLI command file whose `--feature` option is
  being removed.
- **`coordination.status_service` symbol** — one of the five dead names targeted
  for prune-or-wire.
- **Terminology guard test** — the contract test that enforces alias absence.
- **occurrence_map.yaml** — the bulk-edit classification artifact (built at plan).

## Assumptions

- The internal/agent command cluster is invoked by first-party templates/skills
  that this mission can update in the same PR, so external scripted-user risk for
  these commands is negligible.
- #1622's code work is already done on `upstream/main` `b995cd99c` (mission
  01KTPKST WP09): nothing to implement; the mission only verifies + closes it.

## Dependencies

- Epic #1797; related sunset policy #1059 (gates the deferred user-facing slice).
- Builds on the de-export/baseline-removal already landed by the
  execution-context-unification mission (01KTPKST).
