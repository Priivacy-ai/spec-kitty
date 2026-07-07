# Tasks: Pack-Path Portability & Language-Scope Authority

**Input**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md` from `kitty-specs/pack-path-env-indirection-01KWY79W/`
**Prerequisites**: plan.md (required), spec.md (required) — both present and committed.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `${VAR}`/`$VAR` + `~` expansion at `effective_root()` resolution time; keep stored `local_path` literal | WP01 | |
| T002 | Add fail-closed error for unset/empty env var (extend `OrgPackMissingError` family) | WP01 | |
| T003 | Verify/fix `save_pack_registry` round-trip preserves the literal template | WP01 | |
| T004 | Confirm legacy `organisation_packs[].path` shape shares the same expansion seam | WP01 | [P] |
| T005 | Add regression + new test coverage for WP01 (env-var, tilde, absolute, unset, round-trip, subdir-escape-guard) | WP01 | |
| T006 | Document `SPEC_KITTY_PACK_HOME` in `docs/api/environment-variables.md` and `docs/guides/create-an-org-doctrine-pack.md` | WP01 | [P] |
| T007 | Run doctrine test subset + ruff/mypy for WP01 surfaces | WP01 | |
| T008 | Persist structured `languages` field on the compiled charter at compile time (`src/charter/compiler.py`) | WP02 | |
| T009 | Update `infer_repo_languages` resolution to read the structured field first, interview-transcript as pre-compile fallback only | WP02 | |
| T010 | Verify `context.py`/`compact.py` consumers work correctly against the corrected resolution (read-path only) | WP02 | [P] |
| T011 | Invert `test_infer_repo_languages_prefers_interview_answers` (red-first), add disagreement + structured-field test cases | WP02 | |
| T012 | Add backward-compatibility test: pre-existing compiled charter without the structured field | WP02 | [P] |
| T013 | Update charter/language-scope documentation to describe the compiled-charter authority model | WP02 | [P] |
| T014 | Run charter test subset + ruff/mypy + terminology guard for WP02 surfaces | WP02 | |

## Work Packages

### WP01 — Pack-path env-var indirection (#2437)

**Goal**: `doctrine.org.packs[].local_path` (and the legacy `organisation_packs[].path` shape) supports `${VAR}`/`$VAR` env-var indirection composed with existing `~` tilde-expansion, resolved at `effective_root()` time without mutating the stored config value, failing closed on unset variables, and never weakening the `subdir` containment guard.

**Priority**: P1 (upstream-tagged usability enhancement; independent of WP02).
**Independent test**: `quickstart.md` WP1 steps 1-4.
**Estimated size**: 7 subtasks, ~350-400 lines.

Included subtasks:
- [ ] T001 Add `${VAR}`/`$VAR` + `~` expansion at `effective_root()` resolution time; keep stored `local_path` literal (WP01)
- [ ] T002 Add fail-closed error for unset/empty env var (WP01)
- [ ] T003 Verify/fix `save_pack_registry` round-trip preserves the literal template (WP01)
- [ ] T004 Confirm legacy `organisation_packs[].path` shape shares the same expansion seam (WP01)
- [ ] T005 Add regression + new test coverage (WP01)
- [ ] T006 Document `SPEC_KITTY_PACK_HOME` (WP01)
- [ ] T007 Run doctrine test subset + ruff/mypy (WP01)

**Implementation sketch**: Read `org_pack_config.py` fully first. Add a pure helper (e.g. `_expand_path_template`) that applies `os.path.expandvars` then `os.path.expanduser` to a raw string, raising a new `OrgPackEnvVarUnsetError` (or extending `OrgPackMissingError`) when `expandvars` leaves an unresolved `${...}`/`$...` token. Call this helper inside `effective_root()` immediately before the `is_absolute()` branch — not inside the `local_path` field validator. Narrow or retire `_expand_tilde`'s eager-expansion behavior so the stored field stays literal. Confirm `_pack_to_yaml_dict`/`save_pack_registry` still round-trips the literal string. Confirm `_registry_from_legacy_organisation_packs` inherits the fix for free via the shared `OrgPackConfig` constructor.

**Dependencies**: None.
**Risks**: The round-trip re-freeze hazard (see `research.md`) — do not expand inside the field validator. Do not extend expansion to `subdir`.

### WP02 — Charter-authoritative language-scope resolution (#2395)

**Goal**: Doctrine language-scope filtering resolves `active_languages` from a structured field persisted on the compiled charter at compile time, eliminating the runtime re-derivation from the raw interview transcript (DIRECTIVE_044 unification), with a documented fallback for charters compiled before this change.

**Priority**: P2 (upstream-tagged correctness bug; independent of WP01).
**Independent test**: `quickstart.md` WP2 steps 1-5.
**Estimated size**: 7 subtasks, ~350-400 lines.

Included subtasks:
- [ ] T008 Persist structured `languages` field at compile time (WP02)
- [ ] T009 Update `infer_repo_languages` resolution precedence (WP02)
- [ ] T010 Verify consumers (`context.py`, `compact.py`) (WP02)
- [ ] T011 Invert pinning test + add disagreement/structured-field cases (WP02)
- [ ] T012 Add backward-compatibility test (WP02)
- [ ] T013 Update documentation (WP02)
- [ ] T014 Run charter test subset + ruff/mypy + terminology guard (WP02)

**Implementation sketch**: Read `compiler.py`, `language_scope.py`, `context.py` (lines ~1320,1326,2188-2207), and `compact.py:195` fully first. Extend the compiler's output schema with a structured language set computed from interview answers at compile time (reusing the existing `extract_declared_languages` extractor, invoked once, canonically, at compile time). Update `infer_repo_languages` (or introduce its replacement, keeping the public call signature stable for existing callers) to read that structured value first; only fall back to today's interview-transcript-then-charter-prose extraction when no structured value exists yet. Run `tests/charter/test_language_scope.py::test_infer_repo_languages_prefers_interview_answers` unmodified first to confirm it is currently green (i.e., encodes the bug), then invert its assertion and add the missing disagreement case.

**Dependencies**: None.
**Risks**: Do not delete the pinning test — invert it. Preserve backward compatibility for un-recompiled charters (FR-010).
