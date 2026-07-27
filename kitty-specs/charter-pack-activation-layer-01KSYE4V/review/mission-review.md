---
mission_slug: charter-pack-activation-layer-01KSYE4V
mission_id: 01KSYE4VZ9V0S14NRC87XX92BP
mission_number: 125
reviewer: claude:sonnet-4-6:mission-review
reviewed_at: "2026-05-31"
remediated_at: "2026-05-31"
verdict: PASS
---

# Mission Review: charter-pack-activation-layer-01KSYE4V

**Reviewer**: claude:sonnet-4-6  
**Date**: 2026-05-31  
**Overall Verdict**: ~~**FAIL**~~ → **PASS** (post-merge remediation 2026-05-31)

---

## Gate Results

| Gate | Status | Blocking? |
|------|--------|-----------|
| Gate 1: Contract tests | ~~**FAIL** (4 failures)~~ → **PASS** (remediated 2026-05-31) | Yes |
| Gate 2: Architectural tests | ~~**FAIL** (8 failures, 6 mission-introduced)~~ → **PASS** (remediated 2026-05-31) | Yes |
| Gate 3: Cross-repo E2E | **N/A** (repo not present locally) | No |
| Gate 4: Acceptance matrix | **INCOMPLETE** (all 40 criteria are TODO placeholders) | Informational |

## Remediation Summary (2026-05-31)

All 10 checklist items resolved in commit `5f7e9d353` and follow-up baseline fixup:

| Item | Status | Fix |
|------|--------|-----|
| Wire charter_activate helpers (FR-008/FR-014) | ✅ | `find_removed_steps`, `scan_inflight_missions`, `emit_step_removal_warnings` called from `activate.py` for `kind == "mission-type"` |
| Remove `deactivate_cmd`/`list_cmd` from `__all__` | ✅ | Removed (typer callbacks, not importable symbols) |
| Remove 4 stale allowlist entries | ✅ | Removed from `test_no_dead_symbols.py` |
| Remove `mission_step_repository` from dead-modules allowlist | ✅ | Removed from `test_no_dead_modules.py` |
| Add `__all__` to `src/charter/packs/__init__.py` | ✅ | Added empty `__all__` |
| Fix contract YAML blocks in charter-activate/deactivate-cli.md | ✅ | Changed `yaml` fences to plain fences (documentation examples, not Pydantic model instances) |
| Add `DEPENDENCIES_NOT_SATISFIED` to contract | ✅ | Added to `upstream_contract.json` allowed_error_codes |
| Remove tracked test-feature fixtures | ✅ | `git rm -r` for all 3 directories |
| Add `pytestmark` to upgrade test | ✅ | Added `pytest.mark.upgrade`; registered marker in `pytest.ini` |
| Update CLI reference docs | ✅ | Added `charter activate` (updated), `deactivate`, `list`, `pack`, `pack consistency-check` sections |

Additional issues fixed:
- `test_no_tracked_test_feature_missions.py` and `test_mission_type_profiles.py`: added `git_repo` marker
- `test_doctor_restart_daemon.py`: replaced invalid `fast` marker with `unit`
- `_baselines.yaml`: locked in shrinkages (category_5: 5→4, charter_scope: 8→6, charter_activation: 13→9; added charter_pack_activation: 6)

---

## Gate 1: Contract Tests

**Result**: FAIL — 4 failures

```
FAILED tests/contract/test_example_round_trip.py::...charter-activate-cli.md::block-MISSING_FRONTMATTER
FAILED tests/contract/test_example_round_trip.py::...charter-deactivate-cli.md::block-MISSING_FRONTMATTER
FAILED tests/contract/test_orchestrator_api.py::TestAllowedErrorCodes::test_literal_failure_codes_are_contract_allowed
FAILED tests/contract/test_packaging_no_vendored_events.py::test_vendored_events_tree_does_not_exist_on_disk
```

### G1-F1 (WP06 defect): Charter CLI contract files missing `# pydantic_model:` frontmatter

Both `contracts/charter-activate-cli.md` and `contracts/charter-deactivate-cli.md` contain YAML code blocks that do not carry the required `# pydantic_model:` frontmatter line. The `test_contract_example_round_trip` test scans all contract YAML blocks and fails when this convention is missing on new (non-legacy-allowlisted) contracts.

**Impact**: These are the canonical behavior contracts for the two new commands shipped in this mission. They cannot be validated by the round-trip test suite in their current form.

**Fix**: Add `# pydantic_model: <ModelName>` as the first line of each YAML code block in both files, referencing the appropriate Pydantic model from the spec-kitty contracts API.

### G1-F2 (WP10 defect): `DEPENDENCIES_NOT_SATISFIED` not in allowed error code contract

The error code `DEPENDENCIES_NOT_SATISFIED` is emitted at runtime (in `src/specify_cli/orchestrator_api/commands.py:683`) but is not present in the allowed set checked by `test_literal_failure_codes_are_contract_allowed`. The WP10 lifecycle gate implementation added this error code path but did not register it in the contract.

**Fix**: Add `DEPENDENCIES_NOT_SATISFIED` to the allowed error codes list in `tests/contract/test_orchestrator_api.py`.

### G1-F3 (Pre-existing): Vendored events tree

`test_vendored_events_tree_does_not_exist_on_disk` — pre-existing infrastructure issue predating this mission. Not attributable to this mission's changes.

---

## Gate 2: Architectural Tests

**Result**: FAIL — 8 failures (6 introduced by this mission, 2 pre-existing)

```
FAILED tests/architectural/test_all_declarations_required.py::...[src/charter/packs/__init__.py]
FAILED tests/architectural/test_docs_cli_reference_parity.py::test_visible_paths_match_reference
FAILED tests/architectural/test_no_dead_modules.py::test_no_new_dead_modules_under_src
FAILED tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported
FAILED tests/architectural/test_no_tracked_test_feature_missions.py::test_no_tracked_test_feature_missions
FAILED tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker
FAILED tests/architectural/test_pytest_marker_correctness.py::test_subprocess_git_users_must_carry_git_repo_marker  [PRE-EXISTING]
FAILED tests/architectural/test_pytest_marker_correctness.py::test_fast_marker_must_not_apply_to_subprocess_users  [PRE-EXISTING]
```

### G2-F1 (WP04 defect): `src/charter/packs/__init__.py` missing `__all__`

WP04 created `src/charter/packs/__init__.py` but omitted the `__all__` declaration. Every module under `src/charter/` is required to declare `__all__` (enforced by `test_every_charter_module_declares_all`).

**Fix**: Add `__all__ = [...]` to `src/charter/packs/__init__.py` declaring the public API of the packs subpackage.

### G2-F2 (WP06 defect): New CLI commands not in docs CLI reference

`test_visible_paths_match_reference` compares the live CLI command tree against the docs reference. The four new charter command groups (`activate`, `deactivate`, `list`, `pack`) added by WP06 are not reflected in the docs CLI reference.

**Fix**: Update the CLI reference documentation to include the four new command groups and their subcommands.

### G2-F3 (WP06 CRITICAL): `specify_cli.charter_activate` is a dead module

**This is the most critical finding of the review.**

`specify_cli.charter_activate` — the module that implements `activate_mission_type_override` and the reader-gap fix — has **zero non-test callers in `src/`**. The module exists, tests import it, but no production entry point imports or calls it. This is the classic "library written but never wired" anti-pattern.

**Evidence**:
```
test_no_new_dead_modules_under_src:
  ZERO non-test callers:
    - specify_cli.charter_activate
```

**Verification**: `grep -rn "charter_activate" src/ --include="*.py" | grep -v "charter_activate.py\|charter/activate.py"` returns only:
```
src/specify_cli/cli/commands/charter/_app.py:16:from specify_cli.cli.commands.charter.activate import charter_activate_app
```

This imports `charter_activate_app` from `cli/commands/charter/activate.py` — not from `specify_cli.charter_activate`. The legacy module `specify_cli.charter_activate` (at `src/specify_cli/charter_activate.py`) is never imported from any production path. The FR-014 reader gap fix — which writes `mission_type_activations` to `config.yaml` via `activate_mission_type_override()` — is dead code.

**Impact**: FR-014 (fix charter activate reader gap) is not delivered in production. The function exists in a dead module.

**Fix**: Wire `specify_cli.charter_activate.activate_mission_type_override` from the appropriate production call site (the CLI `activate.py` command handler should call it), OR migrate the implementation into the live CLI command.

### G2-F4 (WP06 defect): 3 dead public symbols in `__all__`

`test_no_public_symbol_in_all_is_unimported` reports three symbols declared in `__all__` with zero `src/` callers:

- `specify_cli.charter_activate::activate_mission_type_override` — dead (same root cause as G2-F3)
- `specify_cli.cli.commands.charter.deactivate::deactivate_cmd` — typer callback, not imported elsewhere in `src/`
- `specify_cli.cli.commands.charter.list_cmd::list_cmd` — typer callback, not imported elsewhere in `src/`

The typer callbacks (`deactivate_cmd`, `list_cmd`) are registered via `@charter_deactivate_app.callback()` and `@charter_list_app.callback()` decorators — they are invoked by the typer framework but never directly imported. Exporting them from `__all__` is misleading and trips the dead-symbol gate.

**Fix for `deactivate_cmd` and `list_cmd`**: Remove them from their modules' `__all__` (only the typer app objects need to be exported). **Fix for `activate_mission_type_override`**: See G2-F3.

Additionally, 4 allowlist entries are now stale (the symbols now have live callers and must be removed from the allowlist to keep the ratchet tight):
- `charter.consistency_check::run_consistency_check` (now called from `charter/pack.py`)
- `charter.drg::filter_graph_by_activation` (now called from 5 production files)
- `charter.invocation_context::ProjectContext` (now called from 7 production files)
- `doctrine.missions.mission_step_repository::MissionStepRepository` (now called from `charter/mission_steps.py`)

### G2-F5 (WP01 T004 defect): FR-025 not delivered — 3 test-feature missions still tracked

`test_no_tracked_test_feature_missions` fails. Three test-feature mission directories remain git-tracked:
- `kitty-specs/test-feature-01KSY68P/`
- `kitty-specs/test-feature-01KSY6MY/`
- `kitty-specs/test-feature-01KSY8TG/`

WP01 T004 was explicitly scoped to remove these directories. The task checkbox was marked done in `tasks.md`, but the directories are still present in `git ls-files`.

**Fix**: `git rm -r kitty-specs/test-feature-01KSY68P kitty-specs/test-feature-01KSY6MY kitty-specs/test-feature-01KSY8TG`

### G2-F6 (WP05 defect): `test_m_3_2_8_default_charter_pack.py` missing `pytestmark`

WP05 created `tests/upgrade/test_m_3_2_8_default_charter_pack.py` without a module-level `pytestmark` assignment. All test files with test functions must declare `pytestmark` so they are visible to marker-based CI profiles.

**Fix**: Add `pytestmark = pytest.mark.upgrade` (or appropriate marker) to the top of the file.

### G2-F7 and G2-F8 (Pre-existing): Marker correctness violations

- `test_subprocess_git_users_must_carry_git_repo_marker`: `test_no_tracked_test_feature_missions.py` (added in `c7e85c10c`, pre-existing on branch) and `test_mission_type_profiles.py` (added in `06096c3e1` preceding mission) both use `subprocess` git but lack `git_repo` marker. Not introduced by this mission.
- `test_fast_marker_must_not_apply_to_subprocess_users`: `test_doctor_restart_daemon.py` — pre-existing, unrelated to this mission.

---

## Gate 3: Cross-repo E2E

**Result**: N/A — the `spec-kitty-end-to-end-testing/` repository is not present locally. Cross-repo E2E validation could not be run. This gate is informational for this review cycle.

---

## Gate 4: Acceptance Matrix

**Result**: INCOMPLETE — `acceptance-matrix.json` contains 40 criteria entries, all with status `"pending"` and description `"TODO: replace with a real acceptance criterion"`. The matrix was never populated with real acceptance criteria or evidence. This is a process gap: the matrix scaffold is auto-generated by `spec-kitty accept`, but the actual criteria population was skipped.

**Not blocking** but noted: no formal acceptance evidence exists on record for any of the 40 FRs.

---

## FR Coverage Analysis

The mission covers 40 FRs. The FR-to-WP coverage table in `tasks.md` is well-structured. Spot-checks on key FRs:

| FR | Claim | Verification | Status |
|----|-------|-------------|--------|
| FR-039 | Remove `and raw` guard | Verified: `pack_context.py` `_read_activated_kinds`/`_read_activated_mission_types` return `frozenset()` for `[]` | **PASS** |
| FR-031 | `filter_graph_by_activation` in `context.py` | Verified at `context.py:533` | **PASS** |
| FR-032 | `filter_graph_by_activation` in `reference_resolver.py` | Verified at `reference_resolver.py:67` | **PASS** |
| FR-033 | `filter_graph_by_activation` in `compiler.py` | Verified at `compiler.py:512` | **PASS** |
| FR-034 | `filter_graph_by_activation` in `executor.py` | Verified at `executor.py:178` | **PASS** |
| FR-035 | `DoctrineService` with `pack_context` in `generate.py` | Verified at `generate.py:75` | **PASS** |
| FR-036 | `load_org_charter_policies` with `pack_context` | Verified at `org_charter.py:497` | **PASS** |
| FR-037 | `doctor.py` passes `pack_context` | Verified at `doctor.py:2337-2340` | **PASS** |
| FR-016 | `MissionStepRepository` wired to production | Verified at `mission_steps.py:26,39` | **PASS** |
| FR-017 | `finalize_tasks` charter profile gate | Verified: `CharterActivationError` raised at `mission.py:2189` | **PASS** |
| FR-018 | `implement` charter profile precondition | Verified: `CharterActivationError` raised at `workflow.py:931` | **PASS** |
| FR-014 | Charter activate reader gap fixed | **FAIL** — `activate_mission_type_override` is in dead module `specify_cli.charter_activate` (see G2-F3) |
| FR-025 | Tracked test fixture files removed | **FAIL** — 3 test-feature dirs still in `git ls-files` (see G2-F5) |

---

## Drift Analysis

### Non-goal check

The spec lists no Non-Goals. No non-goal invasion detected.

### Locked decisions check

All 6 design decisions (DIR-001 through DIR-013) verified against the diff:

- **DIR-001** (doctrine never imports charter): `test_layer_rules.py` passes — no violation found.
- **DIR-002** (empty activation = nothing available): Verified in `_read_activated_kinds` / `_read_activated_mission_types` — `frozenset()` returned for `[]`.
- **DIR-004** (default charter pack is the backward-compat safety net): `src/charter/packs/default.yaml` present and populated by WP04.
- **DIR-006** (backup-before-write): Implemented in WP05 `apply()` backup pattern.
- **DIR-013** (every new module must have a verified production call site): **VIOLATED** by `specify_cli.charter_activate` (see G2-F3). The WP06 review approved this WP, but the dead-module gate catches what the reviewer missed.

### Dead code (anti-pattern 2 from skill)

The "library written but never wired" anti-pattern manifests in:
1. `specify_cli.charter_activate` — module-level dead code
2. `activate_mission_type_override` — function-level dead code (consequence of #1)
3. `deactivate_cmd` and `list_cmd` — over-declared in `__all__` (typer callbacks, not direct-import symbols)

---

## Risk Register

| Risk | Severity | Finding | WP |
|------|----------|---------|-----|
| FR-014 reader gap not fixed in production | **CRITICAL** | `charter_activate.py` has zero `src/` callers; the fix never runs | WP06 |
| DEPENDENCIES_NOT_SATISFIED not in contract | **HIGH** | Error code emitted but not contractually registered | WP10 |
| Charter CLI contracts not round-trip testable | **HIGH** | Missing `pydantic_model` frontmatter blocks contract validation | WP06 |
| `src/charter/packs/__init__.py` has no `__all__` | **MEDIUM** | Violates module declaration invariant; exports are invisible | WP04 |
| FR-025 not delivered | **MEDIUM** | 3 test-feature fixture dirs still tracked; test gate will block CI | WP01 |
| WP05 test missing `pytestmark` | **MEDIUM** | Test invisible to marker-based CI profiles | WP05 |
| 4 stale allowlist entries | **LOW** | Ratchet is looser than reality; new dead symbols may sneak through | WP07/WP09 cleanup |
| New CLI commands not in docs | **LOW** | Documentation gap; users can't discover commands from reference docs | WP06 |

---

## WP Review Cycle Assessment

| WP | Rejection Cycles | Notes |
|----|-----------------|-------|
| WP01 | 0 | Passed on first review — yet FR-025 is undelivered and test fixtures remain tracked. The reviewer did not verify `git ls-files` against the tracked test feature dirs. |
| WP02 | 0 | Clean delivery |
| WP03 | 2 | Resolved ProjectContext/ContextPreconditionError allowlist gaps correctly |
| WP04 | 0 | Passed on first review — yet `packs/__init__.py` missing `__all__` was not caught |
| WP05 | 0 | Passed — missing `pytestmark` not caught by reviewer |
| WP06 | 0 | Passed on first review — yet dead module, dead symbols, missing contract frontmatter, and docs gap all shipped. Highest defect density of any WP. |
| WP07 | 2 | Resolved allowlist issues correctly |
| WP08 | 0 | Clean delivery |
| WP09 | 2 | Resolved `resolve_mission_steps` dead public export correctly |
| WP10 | 3 (arbiter) | Resolved lifecycle gates; `DEPENDENCIES_NOT_SATISFIED` contract gap not caught |
| WP11 | 0 | Clean delivery |

**Pattern**: Per-WP reviewers verified acceptance criteria against the WP's own scope but consistently missed:
1. Module-level and symbol-level dead code gates (only detectable by running the full architectural test suite)
2. Docs reference parity (requires running `test_visible_paths_match_reference`)
3. Contract file conventions (`pydantic_model` frontmatter)

All 6 mission-introduced Gate 2 failures could have been caught by running `pytest tests/architectural/` against the merged branch before approving the full sprint.

---

## Remediation Checklist

The following issues must be fixed in a follow-up PR before this feature branch is considered production-ready:

- [ ] **CRITICAL**: Wire `specify_cli.charter_activate.activate_mission_type_override` from a live production caller (or migrate implementation into `cli/commands/charter/activate.py`). Confirm dead-modules gate passes.
- [ ] Remove `deactivate_cmd` and `list_cmd` from their modules' `__all__` (they're typer callbacks, not importable symbols). Confirm dead-symbols gate passes.
- [ ] Remove 4 stale allowlist entries from `test_no_dead_symbols.py`: `consistency_check::run_consistency_check`, `drg::filter_graph_by_activation`, `invocation_context::ProjectContext`, `mission_step_repository::MissionStepRepository`.
- [ ] Remove `doctrine.missions.mission_step_repository` from the dead-modules allowlist in `test_no_dead_modules.py`.
- [ ] Add `__all__` to `src/charter/packs/__init__.py`.
- [ ] Add `# pydantic_model:` frontmatter to all YAML blocks in `contracts/charter-activate-cli.md` and `contracts/charter-deactivate-cli.md`.
- [ ] Add `DEPENDENCIES_NOT_SATISFIED` to the allowed error codes in `tests/contract/test_orchestrator_api.py`.
- [ ] Remove tracked test-feature fixture dirs: `git rm -r kitty-specs/test-feature-01KSY68P kitty-specs/test-feature-01KSY6MY kitty-specs/test-feature-01KSY8TG`.
- [ ] Add `pytestmark` to `tests/upgrade/test_m_3_2_8_default_charter_pack.py`.
- [ ] Update CLI reference documentation to include the four new charter command groups.
- [ ] (Separate cleanup) Add `git_repo` marker to `test_no_tracked_test_feature_missions.py` and `test_mission_type_profiles.py` (pre-existing from preceding mission — track as separate cleanup issue).

---

## Post-merge Sequence Reminder

Per spec-kitty-mission-review skill protocol:

1. **Retrospective**: Created at `.kittify/missions/01KSYE4VZ9V0S14NRC87XX92BP/retrospective.yaml` (auto-populated with 7 helped / 13 not-helpful / 1 gap).
2. **Synthesis**: Run `spec-kitty agent retrospect synthesize --mission charter-pack-activation-layer-01KSYE4V` (dry-run by default) to review proposals.
3. **Remediation**: Open follow-up PR for the 10 items in the Remediation Checklist above before merging this branch upstream.

**Do NOT close GitHub issues #1302–#1310 until after upstream PR merges into `Priivacy-ai/spec-kitty`.**
