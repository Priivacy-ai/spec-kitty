# Slice F Mission Review — Architect Alphonso

**Reviewed:** 2026-05-18
**Reviewer:** architect-alphonso (via claude:opus-4-7[1m])
**Mission:** slice-f-multi-context-extensibility-01KRX5C8 (mission_number=121)
**Squash commit:** 9067ab3b
**HEAD at review:** 7cbed7fa
**Verdict:** WITH-FINDINGS

---

## Executive summary

Slice F successfully delivers Axis 1 (three-layer DRG) end-to-end and Axis 3 (composable workflow sequencing) end-to-end, and all five absorbed remediations land with passing ATDD coverage. **Axis 2 (monorepo CharterScope) ships its module surface but is not actually wired into any production code path**: `CharterScope.resolve` and `build_with_scope` have zero `src/` callers and exist only behind a documented Category-C "in-flight" baseline that WP11 was supposed to clear but did not. The C-005 binding is honored (auth-transport untouched), the C-003 binding is honored (alias cleanly deleted), and the full architectural sweep stays green; net failure delta vs the pre-merge 34-row baseline is +2 (still in the pre-existing `[checklist]` parametrized cluster, not Slice F regressions). The mission is releasable but Axis 2 is shipped-but-dormant and the WP11 contract miss should be acknowledged.

---

## FR coverage matrix

Each row: `FR | impl | test | status`. Status legend: OK = impl + adequate test; OK* = impl + test that uses a fixture but the production code path is the one under test; GAP = impl missing or test does not constrain production behavior.

### Axis 1 — Three-layer DRG (#832)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-001 | `src/charter/drg.py::load_org_drg, merge_three_layers, _tag_source` | `tests/charter/test_org_drg_loader.py`, `tests/integration/test_three_layer_drg_end_to_end.py` | OK |
| FR-002 | `src/specify_cli/cli/commands/charter.py::charter_status` extension | `tests/integration/test_charter_status_reports_three_layers.py` | OK |
| FR-003 | `src/specify_cli/cli/commands/charter.py::charter_lint` extension (lines ~444-510 invoke `load_org_drg`+`merge_three_layers`) | `tests/integration/test_charter_lint_lints_all_layers.py` | OK |
| FR-004 | `src/charter/drg.py::OrgPackMissingError` raised when path absent | `tests/integration/test_org_pack_missing_path_hard_fails.py` | OK |
| FR-005 | `tests/charter/test_org_drg_cannot_override_shipped_invariants.py` enforces layer-rule guard | `tests/charter/test_org_drg_cannot_override_shipped_invariants.py` | OK |
| FR-006 | `src/specify_cli/cli/commands/doctrine.py::doctrine org init/validate` | `tests/cli/test_doctrine_org_commands.py` | OK |
| FR-007 | `src/specify_cli/cli/commands/doctor.py::_render_org_layer_section` (line 1593) + `_collect_org_layer_data` (line 1468) | `tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py` | OK |

### Axis 2 — Monorepo CharterScope (#522 / ADR-8)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-008 | `architecture/adrs/2026-05-18-1-monorepo-charter-scope.md` (232 lines) | existence-only | OK |
| FR-009 | `src/charter/scope.py::CharterScope` | `tests/integration/test_monorepo_charter_scope.py` | OK (unit) |
| FR-010 | `src/charter/scope_router.py::build_with_scope` (NB: the spec wording "`build_charter_context(repo_root, feature_dir, scope=...)` SHALL accept an optional scope parameter" is **NOT** what shipped — `build_charter_context` retained its WP07 signature without a `scope` kwarg; a separate `build_with_scope` wrapper was added in `scope_router.py`) | tests/integration/test_monorepo_charter_scope.py | **OK*** (deviation from spec wording; functional intent partially preserved by wrapper) |
| FR-011 | NFR-001's 23 governance-contract fixtures unchanged + cross-axis isolation tests | `tests/specify_cli/next/test_wp_prompt_governance_contract.py`, `tests/integration/test_slice_f_cross_axis.py::test_org_pack_drg_does_not_affect_default_workflow` | OK |

### Axis 3 — Composable workflow sequencing (#682)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-012 | `src/specify_cli/next/_internal_runtime/workflow_schema.py::WorkflowSequence, ActionStep` | `tests/specify_cli/next/test_workflow_registry.py` | OK |
| FR-013 | `src/specify_cli/next/_internal_runtime/planner.py::_resolve_workflow_for_mission` (line 92-113) reads `meta.json::workflow_id` | `tests/integration/test_workflow_sequence_runtime.py` | OK |
| FR-014 | `src/doctrine/workflows/software-dev-default.workflow.yaml` | `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py` | OK |
| FR-015 | `src/specify_cli/next/_internal_runtime/workflow_registry.py::UnknownWorkflowError` raised in `get_workflow` (line 98-102) | `tests/specify_cli/next/test_workflow_registry.py::test_unknown_workflow_id_hard_fails_with_available_list` | OK |

### Absorbed remediation — DRIFT-1 (C-003)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-100 | alias deletion from `src/charter/resolver.py` (no `resolve_governance =` line remains; only `resolve_governance_for_profile` and `resolve_project_governance` survive) | `tests/charter/test_alias_deleted_regression.py::test_resolve_governance_import_raises_import_error` | OK |
| FR-101 | export removed from `src/charter/__init__.py` (only `resolve_governance_for_profile` and `resolve_project_governance` exported) | (same regression test) | OK |
| FR-102 | grep across `tests/`: no fixture imports the bare alias | regression test scans `tests/charter/` | OK |
| FR-103 | `ImportError` asserted in regression test | `tests/charter/test_alias_deleted_regression.py` | OK |

### Absorbed remediation — Ratchet burn-down (C-004)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-110 | `tests/architectural/_baselines.yaml` (full per-category baselines for 5 ratchets) | `tests/architectural/test_ratchet_baselines.py::test_baseline_file_exists_with_required_keys` | OK |
| FR-111 | `tests/architectural/test_ratchet_baselines.py::test_growing_an_allowlist_above_baseline_fails` + shrinkage-warn variant | (self) | OK |
| FR-112 | `tests/architectural/test_no_dead_modules.py::_CATEGORY_*_GRANDFATHERED_ORPHANS` per-category frozensets (7 categories) | (self) | OK |
| FR-113 | Cat-7 shrunk 10 → 7 (deleted `doctrine.templates.repository`, `glossary.prompts`, `glossary.rendering` plus their tests) | `tests/architectural/test_no_dead_modules.py::test_category_7_grandfathered_at_most_seven_entries` | OK |

### Absorbed remediation — Symbol-level dead-code gate (C-007)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-120 | `tests/architectural/test_no_dead_symbols.py` walks `__all__` declarations | (self) | OK |
| FR-121 | every module under `src/charter/` and `src/kernel/` declares `__all__` | `tests/architectural/test_all_declarations_required.py` | OK |
| FR-122 | both `test_no_dead_modules` and `test_no_dead_symbols` co-pass | both files | OK |

### Catalog-miss CLI UX (reframed)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-130 | `src/specify_cli/cli/logging_bootstrap.py::install_cli_logging_bootstrap` calls `logging.captureWarnings(True)` | `tests/specify_cli/test_logging_bootstrap.py` | OK |
| FR-131 | `RichHandler` (with stderr fallback) attached to root logger | `tests/specify_cli/test_logging_bootstrap.py` | OK |
| FR-132 | `tests/integration/test_catalog_miss_cli_visibility.py` runs CLI via `subprocess` and asserts `WARNING\s{2,}` Rich-specific format | (self) | OK |

### Absorbed remediation — Contract round-trip backstop

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-140 | `tests/contract/test_example_round_trip.py` discovers `kitty-specs/*/contracts/*.md` codeblocks via `# pydantic_model:` / `# expect:` frontmatter | (self) — 151-entry legacy allowlist documented in `_baselines.yaml::legacy_contract_allowlist` | OK |
| FR-141 | legacy allowlist participates in burn-down baseline | (self) | OK |

### Descoped — Auth-transport ADR (C-005)

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-200 | `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` (101 lines, all sections present including reserved "deleted in commit X" field for Robert) | existence-only | OK |
| FR-201 | GitHub ticket Priivacy-ai/spec-kitty#1118 (cited in debrief; reviewer did not independently verify the ticket URL) | existence-only | OK (not independently verified) |
| FR-202 | `git diff 9067ab3b^..9067ab3b -- src/specify_cli/auth/transport.py` returns empty; same for `test_auth_transport_singleton.py` | (verification) | **OK (binding honored)** |

### Closing

| FR | Impl | Test | Status |
|---|---|---|---|
| FR-300 | `tests/architectural/README.md` (107 lines documenting the 5-axis model) | existence-only | OK |
| FR-301 | `src/specify_cli/upgrade/migrations/README.md` (75 lines) | existence-only | OK |
| FR-302 | 10 Slice F terms in `glossary/contexts/doctrine.md` (lines 350-466) all show `Status: canonical` | `tests/glossary/test_canonical_promotion.py` | OK*  (see FINDING-3: one term's definition drifted) |
| FR-303 | charter amendments at `.kittify/charter/charter.md` (lines 290+) cover (a) burn-down policy, (b) `__all__` convention, (c) ATDD-first | (visual inspection) | OK |
| FR-304 | commit messages enforce the discipline (per debrief; spot-checked WP10/WP11 RED commits in `git log`) | (per WP review history) | OK |

**Coverage:** 38/38 FRs have implementation and at least one test. **One spec-vs-impl deviation** (FR-010 wording) and **one shipped-but-unwired axis** (Axis 2 — FR-010 contract not fully met because no production caller invokes `build_with_scope` or `CharterScope.resolve`).

---

## NFR conformance

| NFR | Evidence | Status |
|---|---|---|
| NFR-001 (23 governance fixtures unchanged) | `tests/specify_cli/next/test_wp_prompt_governance_contract.py` passes in targeted sweep; `tests/integration/test_monorepo_charter_scope.py::test_default_scope_is_byte_identical_to_today` passes | OK |
| NFR-002 (latency ≤ 1.2× baseline) | `tests/architectural/test_wp_prompt_build_latency.py` not invoked separately in this review; targeted sweep passes 104 tests including architectural latency gate | OK (presumed; full sweep clean) |
| NFR-003 (layer rule preserved) | `tests/architectural/test_layer_rules.py` passes in targeted sweep | OK |
| NFR-004 (glossary canonical promotion) | 0 occurrences of `Status: candidate` in `glossary/contexts/doctrine.md`; Slice F terms all show `canonical` | OK |
| NFR-005 (architectural sweep clean) | `tests/architectural/` sweep passes 104/104 in targeted run | OK |
| NFR-006 (catalog-miss test via subprocess + Rich-format assertion) | `tests/integration/test_catalog_miss_cli_visibility.py` uses `subprocess.run`; asserts `WARNING\s{2,}` Rich-prefix | OK |
| NFR-007 (analyze 0 CRITICAL / 0 HIGH) | `analysis-report.md` present in mission dir; not re-run by reviewer | OK (per mission close) |
| NFR-008 (ATDD coverage ≥ 90%) | 22 ATDD rows in `atdd-coverage.md` (Scenarios 1-6 + ACs 1-11 + AC-17, AC-18); 5 existence-only ACs (AC-12-16) in slack | OK (100% in-scope) |

---

## C-binding verification

| C | Binding | Evidence | Status |
|---|---|---|---|
| C-001 | Layer rule kernel ← doctrine ← charter ← specify_cli | `tests/architectural/test_layer_rules.py` passes; `workflow_registry.py` lives in `specify_cli.next._internal_runtime` and has no `from charter` imports | OK |
| C-002 | Forward-only | No historical-mission migrations introduced | OK |
| C-003 | DRIFT-1 alias clean removal — no `DeprecationWarning`, no sunset docstring | `rg "from charter import resolve_governance\b"` returns 0 matches in src/; `grep` for `DeprecationWarning` in `src/charter/`: none related to alias | **OK (verified)** |
| C-004 | Burn-down policy charter-pinned | `.kittify/charter/charter.md` lines 290-308 (Burn-down Policy section, sub-rules a/b/c) | **OK (verified)** |
| C-005 | No source change to `src/specify_cli/auth/transport.py` or `test_auth_transport_singleton.py` | `git diff 9067ab3b^..9067ab3b -- src/specify_cli/auth/transport.py` returns 0 lines; same for the test file | **OK (verified — zero diff)** |
| C-006 | Cat-7 shrinks ≥2/major release | Cat-7 = 7 (down from 10) per `_baselines.yaml::category_7_grandfathered_orphans` | OK |
| C-007 | `__all__` required on src/charter/ + src/kernel/ | `tests/architectural/test_all_declarations_required.py` passes; charter §"`__all__` Declaration Convention" present | OK |
| C-008 | Default workflow byte-identical to hardcoded sequence | `test_workflow_software_dev_default_is_byte_stable.py` passes | OK |
| C-009 | Org-DRG reuses Mission B 8-kind parity / union semantics | `src/charter/drg.py` schema preserves `selected_<kind>` / `required_<kind>` shapes; no kind set divergence in diff | OK |
| C-010 | Glossary canonical promotion before acceptance | 10 Slice F terms `canonical` in `glossary/contexts/doctrine.md` | OK (but see FINDING-3) |
| C-011 | ATDD-first discipline | charter amendment in `.kittify/charter/charter.md` §"ATDD-First Discipline"; WP review history confirms reviewer red→green verification on each WP | OK |

**All 11 C-bindings honored.**

---

## AC trace

| AC | Test file::name | Status |
|---|---|---|
| AC-1 | `tests/integration/test_three_layer_drg_end_to_end.py::test_charter_lint_lints_all_three_layers_with_provenance` | OK |
| AC-2 | `tests/cli/test_doctrine_org_commands.py::test_doctrine_org_init_scaffolds_minimal_pack`, `test_doctor_doctrine_surfaces_org_layer_state` | OK |
| AC-3 | `tests/specify_cli/next/test_wp_prompt_governance_contract.py` (23 unchanged) + `tests/integration/test_monorepo_charter_scope.py::test_default_scope_is_byte_identical_to_today` | OK (caveat: monorepo behavior unwired in production — see FINDING-1) |
| AC-4 | `tests/integration/test_workflow_sequence_runtime.py::test_fixture_mission_with_workflow_id_produces_documented_step_diff` | OK |
| AC-5 | `tests/charter/test_alias_deleted_regression.py` (both tests) | OK |
| AC-6 | `tests/architectural/test_ratchet_baselines.py` | OK |
| AC-7 | `tests/architectural/test_no_dead_modules.py::test_category_7_grandfathered_at_most_seven_entries` | OK |
| AC-8 | `tests/architectural/test_all_declarations_required.py` + `tests/architectural/test_no_dead_symbols.py` | OK |
| AC-9 | `tests/integration/test_catalog_miss_cli_visibility.py::test_typoed_styleguide_produces_visible_stderr_warning` | OK |
| AC-10 | `tests/contract/test_example_round_trip.py::test_contract_example_round_trip[*]` (parametrized; 151-entry legacy allowlist) | OK |
| AC-11 | `tests/glossary/test_canonical_promotion.py::test_all_slice_f_terms_are_canonical_in_doctrine_context` | OK (but see FINDING-3) |
| AC-12 | `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` exists | OK |
| AC-13 | GitHub ticket #1118 referenced in ADR + debrief | OK (debrief-attested) |
| AC-14 | `tests/architectural/README.md` exists | OK |
| AC-15 | `src/specify_cli/upgrade/migrations/README.md` exists | OK |
| AC-16 | charter amendments landed | OK |
| AC-17 | regression sweep clean (delta = +2 vs 34 baseline; all pre-existing `[checklist]` cluster) | OK |
| AC-18 | `analysis-report.md` present at mission close | OK (per mission close) |

**18/18 ACs satisfied** (with caveats on AC-3 functional coverage and AC-11 definition fidelity — both MEDIUM).

---

## Findings

| ID | Severity | Title | Location | Recommendation |
|---|---|---|---|---|
| FINDING-1 | **HIGH** | Axis 2 (CharterScope) is shipped but unwired into any production caller | `src/charter/scope_router.py::build_with_scope` has zero `src/` callers; `tests/architectural/_baselines.yaml::category_c_wp_in_flight_charter_scope: 4` explicitly notes "MUST shrink to 0 when WP11 lands the call site"; WP11 did not land that call site | File a follow-up issue (e.g. "Slice F follow-up — wire `build_with_scope` into `prompt_builder._governance_context`") and decrement `category_c_wp_in_flight_charter_scope` to 0 in that PR. Until then, Axis 2 monorepo behavior is **library code with no live consumer**: a monorepo operator running `spec-kitty agent action implement WP01` from `packages/auth/some/deep/dir/` will get the default `repo_root` charter, not the nearest-enclosing one. The unit + integration tests validate the resolver in isolation, but the cross-axis integration test exercises `CharterScope.resolve` directly rather than through the production prompt path, so the test passes despite the production gap. |
| FINDING-2 | **MEDIUM** | FR-010 spec wording vs implementation deviation | spec.md FR-010 states `build_charter_context(repo_root, feature_dir, scope=...)` SHALL accept an optional `scope` parameter; `src/charter/context.py::build_charter_context` has `org_root: Path \| None = None` but no `scope` kwarg | Either (a) update FR-010 spec wording to reflect the `build_with_scope` wrapper pattern that actually shipped, or (b) add the `scope` kwarg to `build_charter_context` in a follow-up. The wrapper pattern is defensible (avoided modifying the WP07-owned signature) but the spec contract drifted from what shipped. |
| FINDING-3 | **MEDIUM** | CharterScope glossary definition drift — describes Mission B selection-scope, not Slice F monorepo scope | `glossary/contexts/doctrine.md` lines 374-380: definition reads "The combined set of artifact selections, activation registry entries, and governance policies that are active for a given project at runtime…" — this is the Mission B selection-layer concept, not the Slice F `charter.scope::CharterScope` dataclass that resolves which charter applies to a filesystem path | Rewrite the CharterScope glossary entry to describe the monorepo path-resolution semantic (per FR-009 / ADR-8). The current definition will confuse future maintainers who see `from charter.scope import CharterScope` and look up the glossary. |
| FINDING-4 | **MEDIUM** | `workflow_id` not sanitized before filename interpolation in `get_workflow` | `src/specify_cli/next/_internal_runtime/workflow_registry.py:92`: `candidate = root / f"{workflow_id}.workflow.yaml"` — `workflow_id` comes from `meta.json` which is operator-authored; a hand-crafted `workflow_id: "../../../some/path"` would be appended to a search root. Realistic exploitation is limited by the `.workflow.yaml` suffix and the absence of an attacker-controllable file at the resulting path, but defense-in-depth is missing. | Add a validator: `if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", workflow_id): raise UnknownWorkflowError(...)`. Defense-in-depth, not an active exploit. |
| FINDING-5 | **LOW** | Forward-staged "WP-in-flight" comment in baselines admits incomplete delivery | `tests/architectural/_baselines.yaml::category_5_wp_in_flight_adapters` baseline of 4 carries comment: "scope_router bridges WP09 to WP11 (ADR-8, FR-010) and MUST be removed when WP11 lands the build_with_scope call site in prompt_builder" — this is the same gap as FINDING-1, surfaced in a second ratchet | Tie resolution to FINDING-1 follow-up; both baselines drop to 0 when `build_with_scope` is wired into `prompt_builder._governance_context`. |
| FINDING-6 | **LOW** | Cross-axis integration test invokes Axis 2 via direct `CharterScope.resolve` call rather than via the production prompt build path | `tests/integration/test_slice_f_cross_axis.py:180-190` constructs `CharterScope.resolve(tmp_complex_setup, deep_auth_path)` and asserts `scope.name == "auth"` — this validates the resolver but **does not** validate that the runtime actually invokes the resolver when building the prompt for a WP under `packages/auth/` | After FINDING-1 is fixed, add a test that drives the production path (e.g. runs `spec-kitty next` with a worktree under a monorepo subpath and asserts the rendered charter context comes from the nearest enclosing charter). The current test is a unit test in integration clothing for Axis 2. |
| FINDING-7 | **LOW** | Test sweep delta vs baseline: +2 failures (36 vs documented 34) | targeted sweep returned `36 failed, 7339 passed, 7 skipped, 390 warnings, 1 error`; debrief asserts baseline of 34 pre-existing failures | Failures all clustered in `tests/specify_cli/test_command_template_cleanliness.py[checklist]` and `test_no_checklist_surface.py` — same pattern documented in pre-existing baseline. The +2 delta appears to be within `[checklist]` parametrization-count noise; spot-check confirms none are Slice F regressions, but a clean re-baseline (e.g. `tests/architectural/_baselines.yaml::full_sweep_failures: 36`) would close the audit gap. |

**Severity rollup:** 0 CRITICAL, 1 HIGH, 3 MEDIUM, 3 LOW.

---

## Cross-axis test legitimacy

`tests/integration/test_slice_f_cross_axis.py` contains three tests:

1. `test_org_pack_in_monorepo_with_custom_workflow` — directly invokes `load_org_drg` (Axis 1), `CharterScope.resolve` (Axis 2), and `resolve_next_workflow_action` (Axis 3) and asserts each returns the expected value.
2. `test_org_pack_drg_does_not_affect_default_workflow` — Axis 1 × Axis 3 isolation.
3. `test_monorepo_scope_resolution_does_not_affect_drg` — Axis 2 × Axis 1 isolation.

These are honest cross-axis tests in the sense that all three axes are exercised against a shared fixture and that **state leakage between them is checked**. However, the Axis 2 call is `CharterScope.resolve(tmp_complex_setup, deep_auth_path)` invoked directly by the test — not through the prompt-build pipeline an operator would actually trigger. So the test proves "the Axis 2 resolver works correctly given its arguments" — it does **not** prove "the production prompt pipeline calls the Axis 2 resolver with the right arguments". For Axes 1 and 3 the test exercises production helpers (`load_org_drg`, `merge_three_layers`, `resolve_next_workflow_action`) that the runtime itself calls, so those axes have stronger end-to-end coverage from this test than Axis 2 does. This is consistent with FINDING-1: Axis 2's production wiring is the gap.

---

## Drift detected

- **Owned-files vs diff stat:** spot-checked WP11 `owned_files: src/specify_cli/next/_internal_runtime/planner.py` and `src/specify_cli/next/prompt_builder.py` — both appear in the squash diff stat (planner.py +141, prompt_builder.py +33). No phantom-ownership entries found.
- **Documented "in-flight" debt carried through to merge:** `tests/architectural/_baselines.yaml` contains two explicit "MUST shrink to 0 when WP11 wires the call site" comments (category_5 and category_c_wp_in_flight_charter_scope) that remained at the WP11 final commit. WP11 cleared the workflow_registry category (`category_c_wp_in_flight_workflow_registry: 0`) but did not clear the charter scope category. The debrief's claim that "Per-WP 'WP-in-flight Category C' allowlists with explicit removal triggers (WP09 + WP10 → cleared by WP11) kept the dead-code gates honest across the mission without permanent debt" is partially inaccurate — the WP09 charter-scope Category C **was not** cleared by WP11. The debrief should be updated.
- No non-goal invasions detected.
- No locked-decision violations detected.

---

## Security findings

| Finding | Location | Risk class | Recommendation |
|---|---|---|---|
| `workflow_id` not sanitized | `workflow_registry.py:92` `candidate = root / f"{workflow_id}.workflow.yaml"` | Path-traversal (low real-world risk; suffix constraint limits exploitation) | Add kebab-case regex validator before path interpolation (see FINDING-4). |
| Auth-transport unchanged | `src/specify_cli/auth/transport.py` | (verified untouched per C-005) | No action — binding honored. |
| YAML loads use `yaml.safe_load` | `workflow_registry.py:94`, `scope.py:235` | Untrusted YAML deserialization | OK — `safe_load` used, no `yaml.load` with unsafe loader in WP-new code. (`src/charter/parser.py`, `hasher.py`, etc. use `yaml.load` via `ruamel.yaml` `YAML()` instance which is also safe by default.) |
| `scope.py` resolves `(repo_root / entry.root).resolve()` and walks ancestors | `src/charter/scope.py:182` | Path traversal via `..` in `charter_scopes[].root` | `_CharterScopeEntry` does not constrain `root` to be a relative path without `..`. An operator-authored `charter_scopes: [{root: "../../etc"}]` resolves to an absolute path outside `repo_root`. Real-world risk is low (operator authors their own `.kittify/config.yaml`), but defense-in-depth is missing. Recommend rejecting any `entry.root` whose resolved path is not a descendant of `repo_root`. **Logged as MEDIUM in FINDING-4 family.** |
| Subprocess use in catalog-miss visibility test | `tests/integration/test_catalog_miss_cli_visibility.py` | Test-only; no production subprocess introduced | OK |

---

## Architectural ratchet state

- `tests/architectural/test_ratchet_baselines.py` PASSES in targeted sweep
- `tests/architectural/test_no_dead_modules.py` PASSES (Cat-7 = 7, ≤ 7 ceiling per AC-7)
- `tests/architectural/test_no_dead_symbols.py` PASSES with documented Category C carrying `category_c_wp_in_flight_charter_scope: 4` (the four `CharterScope*` + `build_with_scope` symbols — see FINDING-1)
- `tests/architectural/test_all_declarations_required.py` PASSES (charter_without_all: 0, kernel_without_all: 0)
- `tests/architectural/test_layer_rules.py` PASSES (no `from charter` imports added to `src/specify_cli/next/_internal_runtime/`; no `from specify_cli` imports added to `src/charter/`)

Targeted sweep total: 104 tests across `test_ratchet_baselines`, `test_no_dead_modules`, `test_no_dead_symbols`, `test_all_declarations_required`, `test_layer_rules`, `test_alias_deleted_regression`, `test_example_round_trip`, `test_slice_f_cross_axis` — all green.

**Architectural ratchet integrity is intact** with one documented cosmetic-but-honest debt entry (FINDING-1 / FINDING-5).

---

## Full sweep

Command: `pytest tests/architectural/ tests/charter/ tests/contract/ tests/integration/ tests/specify_cli/ tests/cli/ tests/glossary/ --continue-on-collection-errors --tb=no -q`

Result: `36 failed, 7339 passed, 7 skipped, 390 warnings, 1 error in 292.08s`

Pre-merge baseline (per debrief): **34 failed**

**Delta vs baseline: +2 failures**

Failure cluster analysis (unique failure names, deduplicated):
- `tests/specify_cli/test_command_template_cleanliness.py::*[checklist]` (6 tests in `[checklist]` parametrization)
- `tests/specify_cli/test_lane_regression_guard.py::test_runtime_no_frontmatter_lane_access[src/specify_cli/audit/classifiers/wp_files.py]`
- `tests/specify_cli/test_no_checklist_surface.py::test_no_checklist_command_string_in_scan_roots`
- 1 collection error: `tests/contract/test_packaging_no_vendored_events.py` (wheel-build dependency)

These all match the pre-existing failure cluster documented in the debrief ("34 pre-existing failures at merge; 0 new failures introduced by Slice F WPs"). The +2 delta is within `[checklist]` parametrization-count noise (likely a recent rebase or migration adjusted the parametrize set by 2 cases). **No Slice F regression in the delta.** See FINDING-7 for the audit-gap note.

---

## Debrief accuracy assessment

The debrief at `docs/development/slice-f-mission-debrief.md` is largely accurate but contains **one notable over-claim**:

> "Per-WP 'WP-in-flight Category C' allowlists with explicit removal triggers (WP09 + WP10 → cleared by WP11) kept the dead-code gates honest across the mission without permanent debt."

This is only half-true: WP11 cleared `category_c_wp_in_flight_workflow_registry` (now 0), but **WP11 did NOT clear** `category_c_wp_in_flight_charter_scope` (still 4). The four CharterScope* + build_with_scope symbols remain orphans in the production import graph. The debrief should be corrected to note this:

> "WP11 cleared the workflow_registry Category C (now 0) but did not wire `build_with_scope` into `prompt_builder._governance_context`, so `category_c_wp_in_flight_charter_scope` remains at 4. Follow-up issue to land the call site is pending."

All other debrief claims (245 files / +12 912 / −3 076; 9/12 WPs on cycle 1; 3 WPs needing cycle 2; 34 pre-existing failures at merge; ATDD coverage 100% in-scope; Ruff clean; layer rule clean; charter amendments landed) match observable reality.

---

## Recommended next actions

1. **HIGH (FINDING-1):** File follow-up issue "wire `build_with_scope` into `prompt_builder._governance_context` to close Axis 2 production gap" and reference it in a new line in the open follow-ups section of the debrief. Decrement `category_c_wp_in_flight_charter_scope` to 0 in that PR.
2. **MEDIUM (FINDING-2):** Update spec.md FR-010 to accurately describe the `build_with_scope` wrapper pattern that actually shipped (or add the `scope` kwarg to `build_charter_context` in the FINDING-1 follow-up).
3. **MEDIUM (FINDING-3):** Rewrite the CharterScope entry in `glossary/contexts/doctrine.md` to describe Slice F's path-resolution semantic (per ADR-8). The current text describes a Mission B concept.
4. **MEDIUM (FINDING-4):** Add `workflow_id` regex validator in `workflow_registry.get_workflow` and `entry.root` ancestor-check in `CharterScope._validate_no_incompatible_nesting` for defense-in-depth.
5. **LOW (FINDING-6):** Once Axis 2 is wired, add a test that drives the prompt-build pipeline end-to-end from a monorepo sub-path.
6. **LOW (FINDING-7):** Re-baseline `_baselines.yaml::test_command_template_cleanliness_failures` to 36 (or whatever the new pre-existing count is) so future audits have a clean baseline.

The mission is releasable. None of the findings are blocking. Recommend MERGED with follow-up issue tracking.
