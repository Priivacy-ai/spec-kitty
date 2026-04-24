# Feature Specification: Resolver and Bootstrap Consolidation

**Mission ID**: `01KPZS0A9VTQP87S63MJ64DTG0`
**Mission slug**: `resolver-and-bootstrap-consolidation-01KPZS0A`
**Mission type**: `software-dev`
**Change mode**: `code` (in-place refactor, no identifier rename)
**Target branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW` (scope increase on the current mission branch — no new branch, no new worktree)
**Created**: 2026-04-24
**Status**: Draft
**Trackers**: Follow-up to `runtime-mission-execution-extraction-01KPDYGW` (#612). No external issue filed yet; the driver is SonarCloud's duplication metric on the parent mission branch (1.1% density / 1,674 duplicated lines, concentrated in three files).
**Upstream dependencies**: runtime extraction WPs on the parent mission are complete; Sonar-hygiene commits on the parent branch have landed (see `cda08d9e0` through `6da149151`). This follow-up lands on top of those.
**Downstream dependents**: none identified. Sonar hygiene and readability improvement only.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Runtime resolver no longer duplicates doctrine resolver (Priority: P1)

As a **Spec Kitty maintainer**, I want `src/runtime/discovery/resolver.py` to stop duplicating `src/doctrine/resolver.py`, so that the canonical asset-resolution logic lives in one place, future resolver changes happen once, and SonarCloud's duplication metric on the runtime-extraction branch drops below 0.3%.

**Why this priority**: Dominant contributor to the duplication metric (231 lines, 74.8% of the file). Every future resolver change has to happen twice; divergence risk is real.

**Independent Test**: Can be verified by (a) running `curl .../api/duplications/show?key=...:src/runtime/discovery/resolver.py` after landing and confirming the block count is 0, (b) running the full test suite and seeing 100% pass, (c) confirming `patch("runtime.discovery.resolver.get_kittify_home", ...)` in existing tests still produces the expected monkeypatching effect.

**Acceptance Scenarios**:

1. **Given** the runtime-extraction branch after this mission merges, **When** SonarCloud re-analyses, **Then** `src/runtime/discovery/resolver.py` has `duplicated_lines = 0` and `duplicated_blocks = 0`.
2. **Given** the same branch, **When** `pytest tests/runtime/test_resolver_unit.py tests/runtime/test_global_runtime_convergence_unit.py tests/runtime/test_home_unit.py` runs, **Then** every test passes unchanged (no test modifications to accommodate the refactor for monkeypatch tests; modifications permitted only if the original test logic was testing implementation details that the refactor removes).
3. **Given** a consumer that calls `from runtime.discovery.resolver import resolve_template`, **When** the consumer runs on the post-refactor tree, **Then** the import succeeds and the function behaves identically to the pre-refactor version on identical inputs.

---

### User Story 2 — Version-locked bootstrap logic is shared across ensure_global_agent_* entry points (Priority: P2)

As a **Spec Kitty maintainer**, I want the version-check/exclusive-lock/double-check/work/write-version sequence to exist in one place, so that `ensure_global_agent_commands` and `ensure_global_agent_skills` are thin, the pattern is obviously reusable for future bootstrap helpers, and the Sonar CPD finding on the agents subpackage is closed.

**Why this priority**: Smaller contributor (37 lines across two files), but adding new `ensure_global_agent_*` helpers in the future will multiply the duplication unless the pattern is extracted now.

**Independent Test**: Can be verified by (a) running `pytest tests/runtime/test_agent_skills.py tests/specify_cli/runtime/test_agent_commands_routing.py` and seeing green, (b) re-running SonarCloud's duplications API on the two agent files and confirming zero duplicated blocks, (c) reading both `ensure_global_agent_*` public functions and confirming they each delegate to a single shared helper.

**Acceptance Scenarios**:

1. **Given** the post-refactor tree, **When** `ensure_global_agent_commands()` is called with a fresh cache, **Then** the version file, exclusive lock acquisition, double-check, sync work, and version write happen in the same observable order as before, and both tests in `tests/runtime/test_agent_skills.py` and `tests/specify_cli/runtime/test_agent_commands_routing.py` pass unchanged.
2. **Given** two concurrent processes call `ensure_global_agent_commands()`, **When** both race on the lock, **Then** only one executes the sync work and the other observes the version file written by the first and exits via the fast path (same behaviour as today).
3. **Given** a reviewer reads `ensure_global_agent_commands` and `ensure_global_agent_skills`, **When** they compare the two, **Then** the version-lock scaffolding is not duplicated; both bodies read as thin callers of the shared helper.

---

### Edge Cases

- **Broken monkeypatch propagation after delegation** — If `runtime.discovery.resolver.get_kittify_home` is *imported from* the charter gateway rather than defined locally, `unittest.mock.patch("runtime.discovery.resolver.get_kittify_home", ...)` patches a local attribute that the resolver body no longer references. Tests appear to patch something but silently do nothing. The plan must specify how these ~15 monkeypatch call sites stay working.
- **Charter import graph cycles** — `charter` already imports from `doctrine`. `runtime` must not import from `doctrine` if the direction is `runtime → charter → doctrine`. Adding the gateway must not introduce a cycle via charter importing runtime.
- **Per-process work-function side effects in Block 2** — if `_run_version_locked_bootstrap` takes a `work` callable, that callable must be idempotent under the double-check semantics (it may be invoked once or skipped entirely; it must not be invoked twice).
- **Windows vs POSIX path differences in resolver** — the current `runtime/discovery/home.py` preserves specific Windows `%LOCALAPPDATA%` semantics. Any consolidation must keep Windows behaviour bit-identical.
- **Stale Sonar analysis** — Sonar numbers on the branch may lag recent commits; verification must be done against a fresh Sonar scan post-merge, not the snapshot that drove this mission.

### Domain Language *(include when terminology precision matters)*

- **Canonical terms**:
  - **Asset resolver** — the 4-tier resolution chain (OVERRIDE → LEGACY → GLOBAL_MISSION → GLOBAL → PACKAGE_DEFAULT) that locates template / command / mission files on disk. Produces a `ResolutionResult`.
  - **Gateway module** — a thin module that re-exports or delegates to another module's public surface, without duplicating logic. Here, a new charter-level module that exposes the doctrine resolver to runtime.
  - **Monkeypatch seam** — a module attribute (function, class, variable) that test code replaces at runtime via `unittest.mock.patch` or `monkeypatch.setattr`. Preserving a seam means the attribute must still be resolvable at the original dotted path and must be the actual binding the implementation uses.
  - **Version-locked bootstrap** — the "check-version / lock-exclusively / re-check / do work / write version" pattern used by `ensure_global_agent_commands` and `ensure_global_agent_skills` to idempotently install user-global assets.
- **Avoid / ambiguous synonyms**:
  - "Resolver" without qualifier — in this repo it can mean the asset resolver, the governance resolver (`charter/resolver.py`), the profile resolver, or the selector resolver. Always qualify.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Charter asset-resolver gateway module | As a charter maintainer, I want a charter-level module that exposes `resolve_template`, `resolve_command`, `resolve_mission`, `ResolutionTier`, `ResolutionResult` with doctrine-backed semantics, so that runtime and other consumers can depend on charter for asset resolution without touching doctrine directly. | High | Met (WP01 `fa01f65ea`) |
| FR-002 | Runtime resolver delegates to charter gateway | As a runtime maintainer, I want `src/runtime/discovery/resolver.py` to delegate its function *bodies* to the charter gateway while keeping module-level attributes intact for monkeypatch tests, so that the 231-line duplication disappears without breaking existing test seams. | High | Met (WP02 `28013c2e1`) |
| FR-003 | Runtime home delegates to kernel paths | As a runtime maintainer, I want `src/runtime/discovery/home.py` to stop duplicating `src/kernel/paths.py` while preserving `runtime.discovery.home._is_windows`, `get_kittify_home`, `get_package_asset_root` as monkeypatch-targetable module attributes, so that the remaining duplication after FR-002 drops below the Sonar threshold. | Medium | Canceled (WP03 — trigger condition not met; home.py was never in Sonar's hotlist) |
| FR-004 | Shared version-locked bootstrap helper | As a runtime maintainer, I want `_run_version_locked_bootstrap(version_filename, lock_filename, work, cli_version=...)` in `src/runtime/orchestration/bootstrap.py`, so that `ensure_global_agent_commands` and `ensure_global_agent_skills` become thin callers of a single shared helper. | Medium | Met (WP05 `9550cd294`) |
| FR-005 | Sonar duplication metric validated post-merge | As a release-gate operator, I want post-merge SonarCloud analysis on the parent mission branch to show `duplicated_lines_density < 0.3%` and `duplicated_blocks ≤ 3` project-wide, so that the duplication debt this mission pays down is measurably closed. | Low | Pending post-merge Sonar scan (WP04 captured pre-merge baseline + thresholds in `evidence/sonar-duplication-post-merge.json`) |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero behaviour drift | Every existing test in `tests/runtime/**`, `tests/specify_cli/runtime/**`, `tests/doctrine/**`, `tests/charter/**`, `tests/next/**`, `tests/init/**` passes without modification of test assertions. Test monkeypatch targets may be migrated (see FR-002), but the assertions about system behaviour must not change. | Reliability | High | Open |
| NFR-002 | No new import cycles | The post-refactor import graph satisfies `kernel ⊂ doctrine ⊂ charter ⊂ runtime ⊂ specify_cli` (reading `⊂` as "may be imported by"). `pytestarch` layer tests pass. | Architecture | High | Open |
| NFR-003 | Monkeypatch seam preservation | Of the 122 test-file references to `runtime.discovery.{resolver,home}.*` attributes, at least 90% must continue to work without edits. The remainder, if migrated, must preserve their original test intent (documented per-WP). | Maintainability | High | Open |
| NFR-004 | Windows behaviour parity | On Windows, `runtime.discovery.home.get_kittify_home()` continues to resolve to `%LOCALAPPDATA%\\spec-kitty\\` — same as before. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Land on current mission branch | All work in this mission lands on `kitty/mission-runtime-mission-execution-extraction-01KPDYGW` — no new mission branch, no new worktree, and no mission merge into main until the parent mission merges. | Process | High | Open |
| C-002 | Do not touch deprecation shims | Modules under `src/specify_cli/{next,runtime}/` are in the shim registry and scheduled for removal in 3.4.0. This mission must not edit them. | Technical | High | Open |
| C-003 | Preserve public API surface | No public symbol currently exported from `runtime.discovery.resolver`, `runtime.discovery.home`, `runtime.agents.commands`, or `runtime.agents.skills` is renamed, moved, or deleted. | Technical | High | Open |

### Key Entities

- **Charter asset-resolver gateway** — a single module under `src/charter/` that exposes the doctrine asset-resolver API to callers. Thin; no new logic.
- **Runtime resolver delegation layer** — `src/runtime/discovery/resolver.py` post-refactor: local attributes for `get_kittify_home` and `get_package_asset_root` remain, but the function *bodies* call into the charter gateway.
- **Version-locked bootstrap helper** — `_run_version_locked_bootstrap` in `src/runtime/orchestration/bootstrap.py`, callable with `(version_filename: str, lock_filename: str, work: Callable[[], None])`.

## Assumptions & Open Questions

### Assumptions

- **Assumption A1**: The ~42 lines of doctrine / runtime resolver body that differ (per `diff`) do so only through helper-call choice (`kernel.paths.get_kittify_home` vs `runtime.discovery.home.get_kittify_home`) and docstring phrasing — not in resolution semantics. Implementer must verify per-WP.
- **Assumption A2**: The lower-risk Option A (keep runtime module attributes, delegate only function bodies) is achievable without hoisting `_resolve_asset` internals that use the module-local helpers. Implementer must confirm during WP01.
- **Assumption A3**: `charter/template_resolver.py` already composes `doctrine.resolver` at the method level; the new charter gateway can either reuse it or sit alongside it. The plan phase decides which.

### Open Questions

- **Q1**: Should `charter/asset_resolver.py` be a new module, or should the gateway be added to `charter/template_resolver.py` module level? Trade-off: new module = clearer single-responsibility; existing module = fewer files. Defer to `plan.md`.
- **Q2**: Does FR-003 (home.py consolidation) materially help the Sonar metric after FR-002 is done, or is FR-002 alone sufficient? Measure after FR-002 merges before committing to FR-003.
- **Q3**: Should `_run_version_locked_bootstrap` accept `cli_version` as an argument (injectable for testing) or call `_get_cli_version()` internally? Injectable is more testable; internal is simpler. Defer to `plan.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After this mission merges, SonarCloud reports `duplicated_lines` ≤ 30 on `src/runtime/discovery/resolver.py` (down from 231).
- **SC-002**: After this mission merges, SonarCloud reports `duplicated_blocks = 0` on both `src/runtime/agents/commands.py` and `src/runtime/agents/skills.py`.
- **SC-003**: The full pytest suite reported on the parent mission branch CI passes without any test-assertion modifications. Only monkeypatch-target migrations count as acceptable test changes.
- **SC-004**: Project-wide `duplicated_lines_density` drops below 0.3% on the parent mission branch.
- **SC-005**: `pytestarch` layer-rule tests pass — no new `doctrine → charter`, `runtime → doctrine`, or similar direction-violating imports introduced.

## Non-goals

- Renaming, moving, or deleting any public symbol in `runtime.discovery.*` or `runtime.agents.*`.
- Touching deprecation shims under `src/specify_cli/{next,runtime}/`.
- Refactoring `charter/resolver.py` (the **governance** resolver; unrelated domain).
- Eliminating the monkeypatch-seam pattern itself — this mission preserves it, not reforms it.
- Addressing any SonarCloud finding not of kind `duplicated_*` metric. (S3776 cognitive complexity and S2208/S7632 etc. are handled on the parent branch directly.)

## Risks

- **R1 — Monkeypatch invisibility after delegation (High)**: `patch("runtime.discovery.resolver.get_kittify_home", ...)` will be a no-op if the resolver body accesses `charter.asset_resolver.get_kittify_home` instead of the local attribute. Mitigation: FR-002 explicitly requires Option A (keep local attributes; the resolver body *calls* a helper passing the local attribute value).
- **R2 — Import cycle via charter (Medium)**: If `charter/asset_resolver.py` imports anything from `runtime`, the layer direction breaks. Mitigation: gateway module imports from `doctrine` only; architectural test catches regressions.
- **R3 — Windows parity regression (Medium)**: `runtime.discovery.home.get_kittify_home` has Windows-specific branching that `kernel.paths.get_kittify_home` may resolve differently. Mitigation: FR-003 requires identical Windows behaviour; add explicit Windows-path unit test comparing both functions.
- **R4 — Parent mission merges before this one (Low)**: if the parent runtime-extraction mission merges while this one is mid-flight, the branch relationship needs re-evaluation. Mitigation: C-001 pins this mission's target/base to the parent branch; if parent merges, re-target to main in planning phase before implementation starts.
- **R5 — Test-suite expansion (Low)**: Sonar metric is dominated by three specific files today; adding new files with duplicated patterns during implementation (accidentally) could offset the gains. Mitigation: SC-004 is a project-wide check, not a file-local one.
