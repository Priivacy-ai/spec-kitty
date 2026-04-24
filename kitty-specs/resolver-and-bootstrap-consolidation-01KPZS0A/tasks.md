---
description: "Work package task list for the resolver-and-bootstrap-consolidation mission"
---

# Work Packages: Resolver and Bootstrap Consolidation

**Inputs**: Design documents from `kitty-specs/resolver-and-bootstrap-consolidation-01KPZS0A/`
**Prerequisites**: `plan.md` (required), `spec.md` (user stories)

**Tests**: Unit tests for WP01 (new charter gateway). All other WPs rely on existing test suite unchanged — that is a deliberate NFR (NFR-001, NFR-003).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently reviewable; WP02–WP04 have sequential dependencies, WP05 is parallel.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel with other `[P]`-tagged subtasks in the same WP.

## Path Conventions

Single project, src-layout: `src/`, `tests/`.

---

## Work Package WP01: Charter asset-resolver gateway (Priority: P1)

**Goal**: Create `src/charter/asset_resolver.py` exposing `resolve_template`, `resolve_command`, `resolve_mission`, `ResolutionTier`, `ResolutionResult`. Functions accept injected `home_provider` and `asset_root_provider` callables so runtime can route its own monkeypatch-targetable helpers through. Ship unit tests that cover the 4-tier resolution order and the provider-injection seam.
**Independent Test**: `pytest tests/charter/test_asset_resolver.py` is green; no runtime callers exist yet (no cross-file coupling introduced in this WP).
**Prompt**: `tasks/WP01-charter-asset-resolver-gateway.md`
**Requirement Refs**: FR-001, NFR-002 (import direction)
**Dependencies**: none
**Owned files**: `src/charter/asset_resolver.py`, `tests/charter/test_asset_resolver.py`

### Included Subtasks

- [x] T001 Create `src/charter/asset_resolver.py` re-exporting `ResolutionTier` and `ResolutionResult` from `doctrine.resolver`.
- [x] T002 Implement `resolve_template(name, project_dir, mission, *, home_provider, asset_root_provider)` using doctrine's 4-tier order (OVERRIDE → LEGACY → GLOBAL_MISSION → GLOBAL → PACKAGE_DEFAULT). Call `home_provider()` and `asset_root_provider()` at lookup time (not at module import) so caller-side monkeypatches win.
- [x] T003 [P] Implement `resolve_command(...)` with the same provider-injection signature.
- [x] T004 [P] Implement `resolve_mission(...)` with the same provider-injection signature.
- [x] T005 Create `tests/charter/` directory if absent; add `tests/charter/test_asset_resolver.py`.
- [x] T006 [P] Unit test — OVERRIDE tier wins when the override path exists.
- [x] T007 [P] Unit test — GLOBAL tier is consulted when override/legacy miss; uses `home_provider` callable.
- [x] T008 [P] Unit test — PACKAGE_DEFAULT fallback uses `asset_root_provider` callable.
- [x] T009 [P] Unit test — `home_provider` and `asset_root_provider` are called *per invocation*, not cached (monkeypatch-seam contract).
- [x] T010 Run `ruff check src/charter/asset_resolver.py tests/charter/test_asset_resolver.py && mypy src/charter/asset_resolver.py && pytest tests/charter/test_asset_resolver.py -x -q` — all green.

### Implementation Notes

- Reuse `ResolutionTier` and `ResolutionResult` classes from `doctrine.resolver` directly; do not redefine them. The charter gateway is *structural* delegation, not a new type system.
- Provider callables let runtime pass `runtime.discovery.home.get_kittify_home` as the `home_provider` so `patch("runtime.discovery.resolver.get_kittify_home", ...)` in the caller's test suite still takes effect when the caller re-reads the (patched) module attribute on each call. The gateway must NOT capture `home_provider()` at module init.
- Charter must not import from `runtime.*` or `specify_cli.*` — layer rule (NFR-002).

### Parallel Opportunities

- T003–T004: independent functions, can be edited concurrently by different agents if desired.
- T006–T009: independent test cases; parallel-safe.

### Dependencies

- None. Green-field module; only consumes `doctrine.resolver`.

### Risks & Mitigations

- **R (minor)**: Accidentally capturing the provider callable return value at import time (Python late-bound defaults gotcha). Mitigation: T009 explicitly asserts per-invocation calls via a spy.

---

## Work Package WP02: Route runtime resolver through charter gateway (Priority: P1)

**Goal**: Rewrite the body of `src/runtime/discovery/resolver.py` so every `resolve_*` function delegates to `charter.asset_resolver`, passing `runtime.discovery.home.get_kittify_home` and `runtime.discovery.home.get_package_asset_root` as injected providers. Keep those attributes bound at the runtime module's top level so `patch("runtime.discovery.resolver.get_kittify_home", ...)` continues to intercept every invocation. Delete the duplicated private helpers (`_resolve_asset` and friends) once their callers are redirected.
**Independent Test**: `pytest tests/runtime/test_resolver_unit.py tests/runtime/test_global_runtime_convergence_unit.py tests/runtime/test_show_origin_unit.py tests/runtime/test_config_show_origin_integration.py tests/next/test_decision_unit.py tests/next/test_runtime_bridge_unit.py -x -q` — all green with no test assertion or monkeypatch-target edits.
**Prompt**: `tasks/WP02-route-runtime-resolver-through-charter.md`
**Requirement Refs**: FR-002, NFR-001, NFR-003
**Dependencies**: WP01
**Owned files**: `src/runtime/discovery/resolver.py`

### Included Subtasks

- [x] T011 Read the current `src/runtime/discovery/resolver.py` and inventory every public symbol and every module-level attribute touched by existing monkeypatches (grep-driven).
- [x] T012 Rewrite `resolve_template`, `resolve_command`, `resolve_mission` as thin callers that pass `get_kittify_home` and `get_package_asset_root` as providers to `charter.asset_resolver`.
- [x] T013 Keep the `from runtime.discovery.home import get_kittify_home, get_package_asset_root` import at module scope so `patch("runtime.discovery.resolver.get_kittify_home", ...)` still targets the resolver module's local attribute.
- [x] T014 Remove `_is_global_runtime_configured`, `_warn_legacy_asset`, `_emit_migrate_nudge`, `_reset_migrate_nudge`, `_resolve_asset` — any that are no longer reachable after delegation. Verify via grep that nothing internal or external still imports them.
- [x] T015 Add one new regression test: `tests/runtime/test_resolver_monkeypatch_seam.py` — asserts that `patch("runtime.discovery.resolver.get_kittify_home", fake)` causes the fake to be called when `runtime.discovery.resolver.resolve_template(...)` is invoked.
- [x] T016 `ruff check src/runtime/discovery/resolver.py` — clean.
- [x] T017 Run the full focused test set listed in "Independent Test" above — all green.
- [x] T018 Measure duplicated-lines on the file by re-running the Sonar duplications API and confirming the block count is 0 (or noting in the WP prompt that CI will do the post-merge validation).

### Implementation Notes

- Option A only (per plan). Do NOT delete `get_kittify_home` / `get_package_asset_root` imports from the runtime resolver; they remain as the monkeypatch seams.
- Expected resolver module size after rewrite: ≤ 60 lines (5 resolve functions + 2 imports + re-exports). Significantly smaller than the current 308.
- `ResolutionResult` / `ResolutionTier` must be re-exported from the runtime resolver module so existing `from runtime.discovery.resolver import ResolutionResult` stays working.

### Parallel Opportunities

- None within this WP (same file).

### Dependencies

- WP01 provides the gateway.

### Risks & Mitigations

- **R1 (High, from spec §Risks)**: Monkeypatch no-op after delegation. T015 is a dedicated regression test that catches this. If T015 fails after T012–T014, the WP blocks on fixing the provider-passing approach before shipping.
- **R (Medium)**: Deleting `_resolve_asset` may remove test attachment points that aren't obvious from grep. Mitigation: T014 runs the full `tests/runtime/**` suite before committing the deletion.

---

## Work Package WP03: Consolidate runtime home ↔ kernel paths (Priority: P2, conditional)

**Goal**: If post-WP02 SonarCloud still flags `src/runtime/discovery/home.py` with ≥ 100 duplicated lines vs `src/kernel/paths.py`, rewrite `runtime/discovery/home.py` to delegate to `kernel.paths` while keeping `_is_windows`, `get_kittify_home`, `get_package_asset_root` bound as module-local attributes. If post-WP02 the metric is already below threshold, SKIP this WP and close it as a no-op.
**Independent Test**: `pytest tests/runtime/test_home_unit.py tests/runtime/test_global_runtime_convergence_unit.py -x -q` — all green. Plus a new Windows-simulation unit test pinning `_is_windows → True` (R3 mitigation).
**Prompt**: `tasks/WP03-consolidate-runtime-home.md`
**Requirement Refs**: FR-003, NFR-004 (Windows parity)
**Dependencies**: WP02
**Owned files**: `src/runtime/discovery/home.py`
**Condition to trigger**: SonarCloud's duplications API on this file reports `duplicated_lines ≥ 100` after WP02 merges. If the trigger does not fire, mark WP03 canceled with evidence in status.events.jsonl.

### Included Subtasks

- [ ] T019 Check post-WP02 SonarCloud metric for `src/runtime/discovery/home.py`. If `duplicated_lines < 100`, write a one-line evidence note in the WP prompt, cancel the WP in the lane, and stop.
- [ ] T020 (If triggered) Rewrite `runtime/discovery/home.py` body to delegate to `kernel.paths` helpers while keeping `_is_windows`, `get_kittify_home`, `get_package_asset_root` as top-level bindings on this module.
- [ ] T021 (If triggered) Add `tests/runtime/test_home_windows_simulation.py` — forces `_is_windows → True`, asserts `get_kittify_home()` resolves to `%LOCALAPPDATA%\\spec-kitty\\`.
- [ ] T022 (If triggered) Run `pytest tests/runtime/test_home_unit.py tests/runtime/test_home_windows_simulation.py tests/runtime/test_global_runtime_convergence_unit.py -x -q` — all green.
- [ ] T023 (If triggered) `ruff check src/runtime/discovery/home.py tests/runtime/test_home_windows_simulation.py` — clean.

### Implementation Notes

- This WP is conditional on empirical Sonar output; the trigger check happens after WP02 merges. Plan the trigger check to be cheap (one `curl` to the duplications API).
- If WP03 is skipped, WP04 verifies that skipping was correct (i.e., the metric is actually below threshold).

### Parallel Opportunities

- None.

### Dependencies

- WP02.

### Risks & Mitigations

- **R3 (Medium, from spec §Risks)**: Windows parity regression. T021 is the guard.
- **R (Low)**: `_is_windows` is used in conditionals — if `kernel.paths` has its own `_is_windows` the two copies could diverge. Mitigation: T020 makes `runtime.discovery.home._is_windows = kernel.paths._is_windows` (or delegates via a thin wrapper).

---

## Work Package WP04: Validate Sonar duplication metric (Priority: P3)

**Goal**: After WP02 (and WP03 if triggered) and WP05 all merge, verify on the parent mission branch that SonarCloud reports `duplicated_lines_density < 0.3%` and `duplicated_blocks ≤ 3` project-wide, and file follow-ups for any remaining duplication hotspots the spec did not cover.
**Independent Test**: Reproducible — hit the Sonar measures API, parse, assert thresholds.
**Prompt**: `tasks/WP04-validate-sonar-duplication.md`
**Requirement Refs**: FR-005, SC-001, SC-002, SC-004
**Dependencies**: WP02 (mandatory), WP05 (mandatory), WP03 (only if triggered)
**Owned files**: This WP makes no code edits. It produces evidence artifacts in the mission directory only.

### Included Subtasks

- [x] T024 Trigger a fresh SonarCloud scan on the parent mission branch (or wait for CI's scheduled scan; note timestamp of the scan consumed).
- [x] T025 Query `/api/measures/component?component=stijn-dejongh_spec-kitty&branch=kitty/mission-runtime-mission-execution-extraction-01KPDYGW&metricKeys=duplicated_lines,duplicated_lines_density,duplicated_blocks,duplicated_files`. Capture response in `kitty-specs/resolver-and-bootstrap-consolidation-01KPZS0A/evidence/sonar-duplication-post-merge.json`.
- [x] T026 Assert `duplicated_lines_density < 0.3` and `duplicated_blocks ≤ 3`. If not met, file a GitHub issue linking this mission and recording the specific files still flagged.
- [x] T027 Cross-check specifically: `src/runtime/discovery/resolver.py` has `duplicated_lines ≤ 30` (SC-001). `src/runtime/agents/commands.py` and `src/runtime/agents/skills.py` both at `duplicated_blocks = 0` (SC-002).
- [x] T028 Update the mission's `spec.md` §Success Criteria status column from `Open` to `Met` (or `Partially Met` with link to follow-up issue).

### Implementation Notes

- This WP is observational. It owns no source-code edits. Its deliverable is the evidence JSON + a commit updating `spec.md` status cells.

### Parallel Opportunities

- Can run in parallel with WP05 *after* both have merged, but must land last chronologically because it consumes the Sonar scan.

### Dependencies

- WP02, WP05 (and WP03 if triggered) all merged.

### Risks & Mitigations

- **R (Low)**: Sonar scan lag. Mitigation: T024 explicitly notes the timestamp, and if the latest scan predates the merges it re-runs or requests a manual scan.

---

## Work Package WP05: Extract version-locked bootstrap helper (Priority: P2)

**Goal**: Add `_run_version_locked_bootstrap(version_filename, lock_filename, work)` to `src/runtime/orchestration/bootstrap.py`. Refactor `runtime.agents.commands.ensure_global_agent_commands` and `runtime.agents.skills.ensure_global_agent_skills` to call it. Preserve observable sequencing (fast-path → lock → double-check → work → write-version).
**Independent Test**: `pytest tests/runtime/test_agent_skills.py tests/specify_cli/runtime/test_agent_commands_routing.py -x -q` — all green. Run the existing runtime orchestration tests that exercise `_lock_exclusive` to confirm no lock-path regression.
**Prompt**: `tasks/WP05-extract-version-locked-bootstrap.md`
**Requirement Refs**: FR-004, NFR-001
**Dependencies**: none — fully independent of the Block 1 chain.
**Owned files**: `src/runtime/orchestration/bootstrap.py`, `src/runtime/agents/commands.py`, `src/runtime/agents/skills.py`

### Included Subtasks

- [x] T029 Add `_run_version_locked_bootstrap(version_filename: str, lock_filename: str, work: Callable[[], None]) -> None` to `src/runtime/orchestration/bootstrap.py`. Reuse existing `_get_cli_version` and `_lock_exclusive`.
- [x] T030 Refactor `ensure_global_agent_skills()` in `src/runtime/agents/skills.py` — body becomes: early-return if registry is None, then call `_run_version_locked_bootstrap` passing a work closure that iterates `_unique_global_roots()` and calls `_sync_skill_root` for each.
- [x] T031 Refactor `ensure_global_agent_commands()` in `src/runtime/agents/commands.py` — body becomes: early-return if `templates_dir` is None, then call `_run_version_locked_bootstrap` passing a work closure that iterates `AGENT_COMMAND_CONFIG` and calls `_sync_agent_commands` for each.
- [x] T032 `ruff check src/runtime/orchestration/bootstrap.py src/runtime/agents/commands.py src/runtime/agents/skills.py` — clean.
- [x] T033 Run `pytest tests/runtime/test_agent_skills.py tests/specify_cli/runtime/test_agent_commands_routing.py tests/runtime/test_bootstrap_unit.py -x -q` (include `test_bootstrap_unit.py` if it exists; otherwise note its absence in the WP prompt). All pass.
- [x] T034 Sanity-check CPD on the two agent files: the duplicated block should no longer appear.

### Implementation Notes

- The `work` callable must be side-effect-only — no return value. Errors propagate up and must NOT prevent the `lock_fd.close()` in the `finally`.
- Preserve the exact exception-handling pattern: the outer try-finally around the lock, and the per-agent-key `try / except Exception: logger.warning(...)` inside the work closure.

### Parallel Opportunities

- None within the WP (shared helper, sequential edits).

### Dependencies

- None. Fully parallelisable with Lane A.

### Risks & Mitigations

- **R (Low)**: Closure-captured variables for the work callable (e.g. `templates_dir`, `script_type`) must be stable values, not mutable containers. Explicit in the refactor — both closures capture locals that do not change after closure creation.
- **R (Low)**: Accidentally dropping the fast-path check before acquiring the lock would regress the "cheap no-op on warm cache" property. T033 covers this implicitly if the existing tests exercise the fast path; T029 explicitly reproduces the two-phase version check.
