# Mission Specification: Execution-State Canonical Domain Surface

**Mission Branch**: `feat/execution-state-strangler`
**Created**: 2026-06-07
**Status**: Draft
**Input**: User description: "Execution-state domain unification — Strangler slice 2: stand up a canonical execution-state domain umbrella with a lean API over the context objects, then strangle the status-facade bypasses, duplicated path-builders, and residue command surfaces into it; extend the parity ratchet to the full command sequence across all execution modes; fold in the mission-identity field-drop fix. Next implementation slice of epic #1666 (blocks #1619)."

<!--
  Purpose (stakeholder TL;DR): Mission commands today re-derive execution context,
  paths, and work-package status independently, so the same command behaves
  differently depending on the working directory it runs from. This mission stands
  up one owned execution-state domain module with a clean public API, then
  incrementally routes the scattered call sites and status-facade bypasses through
  it while deleting the duplicated code paths — unblocking reliable,
  location-independent mission execution. Issue traceability lives in issue-matrix.md.
-->

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canonical execution-state domain surface (Priority: P1)

A developer or agent resolving mission execution context (mission directory, workspace, branch) goes through a single owned domain module with a clean API over the context objects, instead of one of many ad-hoc resolvers.

**Why this priority**: Every subsequent strangling step needs a single destination to route into. Without the canonical surface, "fixing" a bypass just moves the duplication. This is the Screaming-Architecture home the redesign (doc 06 §4) mandates.

**Independent Test**: Stand up the new module, register it in the layer meta-guard, relocate `resolve_action_context` into it, and prove via architectural tests that it is the only sanctioned execution-context resolver — without yet migrating all consumers.

**Acceptance Scenarios**:

1. **Given** the new canonical module exists and is layer-registered, **When** `test_no_unregistered_src_packages` and the new architectural tests run, **Then** they pass and confirm the module is the sole sanctioned execution-context resolver.
2. **Given** a residue surface needs a mission directory, **When** it calls the canonical API, **Then** it receives a resolved context object (not raw path fragments).

---

### User Story 2 - Full-sequence parity ratchet across execution modes (Priority: P1)

An agent runs the full `next → implement → move-task → review → status` sequence from the repository root checkout, from a lane worktree, and as a direct-to-target run, and gets identical results.

**Why this priority**: The ratchet is the regression gate for the entire slice. Per #1672 it must exist and be green before any strangling change can be trusted. It is the only automated proof that a surface was unified rather than re-masked.

**Independent Test**: Extend `test_execution_context_parity.py` to drive the full sequence across all three modes and assert parity, with a negative control that fails when re-derivation is injected.

**Acceptance Scenarios**:

1. **Given** a mission with ≥2 work packages, **When** the full sequence runs from the repository-root-checkout CWD and from the lane-worktree CWD, **Then** resolved WP identity, lane transitions, and status output are identical.
2. **Given** a direct-to-target mission run with no worktree, **When** the sequence runs, **Then** results match the other modes and the mode-correct target branch is used.
3. **Given** a surface is deliberately reverted to re-derive context independently, **When** the ratchet runs, **Then** it fails (non-vacuous).

---

### User Story 3 - Strangle the path-builder residue (Priority: P2)

The residue command surfaces and duplicated path-builders are routed through the canonical surface and deleted, so no surface re-derives feature-dir paths independently.

**Why this priority**: This is the bulk behavioral remediation that removes the divergence class. It depends on US1 (a destination) and US2 (a gate), so it is P2.

**Independent Test**: Route `runtime_bridge.py` query-mode and `workflow.py` fix-mode through the canonical surface, collapse the 8 duplicate feature-dir resolvers to one, delete the dead path-builders, and confirm the ratchet stays green.

**Acceptance Scenarios**:

1. **Given** the residue surfaces are routed, **When** grep scans `src/` outside the canonical module and `status/`, **Then** zero `main_repo_root / "kitty-specs" / mission_slug`-class constructions remain.
2. **Given** a direct-to-target run, **When** the gate resolves the write branch, **Then** it observes the declared target branch and refuses an unauthorized mainline write.

---

### User Story 4 - Repo-wide status facade enforcement (Priority: P2)

No code outside `status/` reaches into status submodules; consumers use the published facade or the `MissionStatus` aggregate, and the boundary is enforced across all of `src/specify_cli`.

**Why this priority**: Makes `status/` an actually-bounded Mission-Management module. High value but mechanically large; depends on the facade promotions being designed, so P2.

**Independent Test**: Promote/demote symbols, fix the ~225 bypass imports, widen the boundary test to all of `src/specify_cli`, and confirm it bites on an injected violation.

**Acceptance Scenarios**:

1. **Given** the boundary test is widened, **When** a developer adds `from specify_cli.status.emit import build_status_event` in `cli/commands/`, **Then** CI fails identifying the violation and pointing to the facade.
2. **Given** all bypasses are fixed, **When** grep scans `src/` outside `status/` (excluding documented plumbing), **Then** zero deep `status.*` imports remain.

---

### User Story 5 - Consistent MissionStatus usage (Priority: P3)

Mission-level status read and write access goes through the `MissionStatus` aggregate, not through direct `emit`/`lane_reader`/`BookkeepingTransaction` calls.

**Why this priority**: Consolidates the status entry point onto the already-landed aggregate. Important for ownership but lower blast radius than US3/US4, so P3.

**Independent Test**: Rework the direct status callers onto `MissionStatus.load()/.claim()/.transition()` and confirm no consumer outside the plumbing exemption calls `BookkeepingTransaction` directly.

**Acceptance Scenarios**:

1. **Given** the consumption rework lands, **When** grep scans for `BookkeepingTransaction(` outside `status/` and documented plumbing, **Then** zero hits remain.

---

### User Story 6 - Mission identity survives snapshot reconstruction (Priority: P3)

A `MissionRunSnapshot` keeps its `mission_id`/`mission_slug` across all reconstruction paths, so a run can always name its mission.

**Why this priority**: A real but narrow field-drop bug (#1663) at the runtime_bridge hotspot we are already editing for US3. Folding it in is efficient; standalone value is modest, so P3.

**Independent Test**: Carry the fields through `runtime_bridge.py:1723/:1860` and add a regression test on the auto-complete reconstruction path.

**Acceptance Scenarios**:

1. **Given** a snapshot with mission identity, **When** it passes through the auto-complete reconstruction, **Then** `mission_id` and `mission_slug` are preserved (not reset to `None`).

---

### User Story 7 - Ownership `scope` is backfill-aware and single-ported (Priority: P3)

An operator who declares `scope: codebase-wide` on a work package — whether authoring it fresh or adding it to an *already-backfilled* WP — gets the overlap exemption honored, because the field flows through one canonical owner on every path (read, backfill, validation) and the finalize resolve→validate path is exercisable without stubbing the frontmatter reader.

**Why this priority**: Follow-up gaps from the #1756 (#1753) adversarial review that *unblocked this mission's own finalize step*. The `scope` field now has three representations (`WPMetadata`, `OwnershipManifest`, raw dict) but the backfill/inference paths never learned about it, so an exemption can silently fail (latent). Folding it in here is the same single-owning-port theme as US4/US5 (epic #1666), but lower blast radius — hence P3.

**Independent Test**: Add `scope` to the backfill "already present" guard + write step; normalize the `from_frontmatter` dict path; drive the finalize ownership resolve→validate path through a frontmatter-source port and prove it is testable without stubbing `read_wp_frontmatter`.

**Acceptance Scenarios**:

1. **Given** a WP already backfilled (`execution_mode`/`owned_files`/`authoritative_surface` present), **When** an operator adds `scope: codebase-wide` and re-runs `backfill_ownership`, **Then** the "already present" guard accounts for `scope` and the field is persisted (not silently dropped).
2. **Given** `infer_ownership` runs with no human-authored `scope`, **Then** it produces a narrow manifest and the "no inference path for `scope`" contract is documented (the field is human-authored only).
3. **Given** a raw frontmatter dict with `authoritative_surface: None`, **When** `from_frontmatter` parses it, **Then** `authoritative_surface` normalizes to `""` — provably equivalent to the `WPMetadata` input path.
4. **Given** the finalize ownership resolve→validate path, **When** it is exercised in tests, **Then** it runs through a single frontmatter-source port (no stubbing of `read_wp_frontmatter`).

---

### User Story 8 - Legacy migration event-rebuild routes through one canonical `mission_state` port (Priority: P3)

A maintainer migrating a legacy project gets per-mission event-log rebuild through a single canonical `mission_state` entry point — not the deprecated `rebuild_event_log` — with event counts preserved for the runner's reporting.

**Why this priority**: Follow-up from #1756: `migration/runner.py` (Step 4) and `migration/normalize_mission_lifecycle.py` still depend on the deprecated `specify_cli.migration.rebuild_state.rebuild_event_log` because `repair_repo` is repo-level (not a per-feature drop-in). This is the same filesystem-as-shared-state / one-owning-port concern as the rest of this mission (epic #1666), scoped to the migration surface. It needs migration fixtures and is a behavioral change to legacy-project migration — hence P3, not a deprecation-cleanup.

**Independent Test**: Expose a per-mission canonical event-rebuild entry on `mission_state` returning event counts (or retire the legacy runner flow onto `repair_repo` end-to-end), migrate the two callers, and prove behavior preservation with migration fixtures.

**Acceptance Scenarios**:

1. **Given** the legacy migration runner (Step 4) and `normalize_mission_lifecycle`, **When** they rebuild a mission's event log, **Then** they call a canonical `mission_state` entry (not `specify_cli.migration.rebuild_state.rebuild_event_log`).
2. **Given** a per-mission rebuild, **When** it runs, **Then** the canonical entry returns event counts (`events_generated`/`events_corrected`/`errors`/`warnings`) sufficient for the runner's reporting.
3. **Given** legacy missions and migration fixtures, **When** migration runs end-to-end, **Then** behavior is preserved (events generated/corrected equivalent; legacy missions migrate unchanged) and the deprecated `rebuild_event_log` is removed or reduced to a thin shim with no live callers.

### Edge Cases

- What happens when a coord-topology mission's coord authority path is unavailable? → The status read fails closed (no silent stale primary-checkout fallback).
- How does the gate handle a write that resolves to mainline (main/master) without explicit operator authorization? → It is refused.
- What happens to legacy (pre-coord-topology) missions and existing on-disk `state.json` files after remediation? → They load and operate unchanged.
- What happens if a reviewer spots a reintroduced parallel resolver? → It is a blocking finding under the leanness IC (NFR-002).
- What happens when an operator adds `scope: codebase-wide` to an *already-backfilled* WP without re-finalizing? → After FR-028 a `backfill_ownership` re-run accounts for and persists `scope`; the field is no longer silently dropped (the #1757.1 latent failure).
- What does static analysis see for the deprecated `rebuild_event_log` entry in `migration/__init__.__all__`? → After FR-033 the symbol is removed or eagerly bound, so linters that inspect `__all__` by namespace no longer flag a declared-but-undefined name (the #1757.4 nuisance).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Canonical module exists | US1 · A new canonical execution-state module (expected `src/mission_runtime/`; final name per the design ADR) exposes a curated public API (`__all__`) over execution-context resolution. | High | Open |
| FR-002 | Layer-guard registration | US1 · The module is registered in `_DEFINED_LAYERS` (`tests/architectural/test_layer_rules.py`) and the `conftest.py` landscape fixture, with `test_no_unregistered_src_packages` passing. | High | Open |
| FR-003 | Relocate canonical entry point | US1 · `resolve_action_context` and the `ExecutionContext`/`ActionContext` type are relocated into (or re-exported as) the module's single entry point; `core/execution_context.py` retains at most a thin shim or is removed. | High | Open |
| FR-004 | Context-object abstraction | US1 · The API is expressed in terms of the per-domain context objects; callers receive a resolved context object, not raw path fragments. | High | Open |
| FR-005 | Sole-resolver architectural test | US1 · Architectural tests assert no import-level access to relocated internals from outside the module. | High | Open |
| FR-006 | Design ADR | US1 · An ADR under `architecture/3.x/adr/` records the module name, public API shape, context-object abstraction, and Strangler migration order. | High | Open |
| FR-007 | Route runtime_bridge query-mode | US3 · `runtime_bridge.py` query-mode derives feature dir/workspace/branch through the canonical surface, not from the mission slug. | High | Open |
| FR-008 | Route workflow fix-mode | US3 · `cli/commands/agent/workflow.py` fix-mode routes its `repo_root`/`target_branch` resolution through the canonical surface. | High | Open |
| FR-009 | Eliminate path-builder residue | US3 · No surface outside the canonical module and `status/` constructs `main_repo_root / "kitty-specs" / mission_slug` (or equivalent) directly; the ~125 current occurrences across ~160 files are routed or deleted. | High | Open |
| FR-010 | Collapse duplicate resolvers | US3 · The 8 duplicated feature-dir resolver implementations are collapsed to one canonical resolver; redundant copies are deleted. | High | Open |
| FR-011 | Delete dead path-builders | US3 · Path-builder functions made unreachable by this work are deleted (not left as dead code). | Medium | Open |
| FR-012 | Mode-correct branch gate | US3 · The execution-context gate observes the mode-correct authorized target branch (coordination/planning, declared target/direct-to-target, lane/worktree), not a fixed always-main or always-worktree surface. | High | Open |
| FR-013 | Facade promotion/demotion | US4 · Symbols with genuine external consumers are promoted to `status/__init__.py`; symbols with no external consumers are renamed private with a `_` prefix. | High | Open |
| FR-014 | Fix all status bypass imports | US4 · All ~225 deep `status.*` submodule imports from outside `status/` are fixed to use the facade or the `MissionStatus` aggregate. | High | Open |
| FR-015 | Widen boundary test repo-wide | US4 · `test_status_module_boundary.py` is widened from the 6 WP03 packages to all of `src/specify_cli`, preserving the documented plumbing exemptions. | High | Open |
| FR-016 | Prevent new bypasses | US4 · No new direct `status.*` submodule imports outside `status/` are introduced after this mission lands. | Medium | Open |
| FR-017 | MissionStatus read consolidation | US5 · Status read paths calling `lane_reader`/`store`/`reducer` directly for mission-level access are reworked onto `MissionStatus.load()`/`.claim()`. | Medium | Open |
| FR-018 | MissionStatus write consolidation | US5 · Status write/transition paths calling `emit`/`BookkeepingTransaction` directly (outside plumbing) are reworked onto `MissionStatus.transition()`. | Medium | Open |
| FR-019 | No direct BookkeepingTransaction | US5 · No consumer outside `status/` and documented coordination plumbing calls `BookkeepingTransaction` directly. | Medium | Open |
| FR-020 | Full-sequence ratchet | US2 · `test_execution_context_parity.py` exercises the full `next → implement → move-task → review → status` sequence (not only status read+write). | High | Open |
| FR-021 | All three execution modes | US2 · The ratchet exercises repository-root-checkout CWD, lane-worktree CWD, and direct-to-target (no worktree). | High | Open |
| FR-022 | Parity assertions + negative control | US2 · The ratchet asserts identical WP identity, lane transitions, and status output across modes, and includes a non-vacuous negative control. | High | Open |
| FR-023 | De-overclaim docstring | US2 · The ratchet docstring is corrected to state its real coverage; it no longer implies coverage it lacks. | Medium | Open |
| FR-024 | CI gate registration | US2 · The ratchet is a required gate for PRs touching the canonical module, `status/`, `runtime/next/`, or `cli/commands/agent/`. | Medium | Open |
| FR-025 | Carry identity on reconstruction | US6 · `MissionRunSnapshot` reconstructions at `runtime_bridge.py:1723` and `:1860` carry `mission_id`/`mission_slug` through (currently dropped). | High | Open |
| FR-026 | Field-drop regression test | US6 · A regression test asserts mission identity survives the auto-complete reconstruction path. | Medium | Open |
| FR-027 | Close #1663 | US6 · #1663 is closeable: all snapshot construction and reconstruction sites preserve mission identity. | Low | Open |
| FR-028 | Scope backfill-awareness | US7 · `migration/backfill_ownership.py`'s "already present" guard and write step account for `scope`; a backfill re-run on an already-backfilled WP persists `scope: codebase-wide` instead of dropping it. | Medium | Open |
| FR-029 | Scope is human-authored | US7 · `ownership/inference.py::infer_ownership` documents that `scope` has no inference path (explicit no-op note); inferred manifests stay narrow by design. | Low | Open |
| FR-030 | from_frontmatter dict-path symmetry | US7 · the raw-`dict` branch of `OwnershipManifest.from_frontmatter` normalizes `authoritative_surface` with `... or ""` so the `WPMetadata` and raw-dict inputs are provably equivalent (a present-but-`None` no longer leaks through). | Low | Open |
| FR-031 | Frontmatter-source port for finalize ownership | US7 · the finalize ownership resolve→validate path (`build_wp_manifests` + `read_wp_frontmatter`) is driven through a single frontmatter-source port so the whole path is testable without stubbing the reader (epic #1666 one-owning-port). | Medium | Open |
| FR-032 | Canonical per-mission event-rebuild entry | US8 · a per-mission canonical event-rebuild entry on `mission_state` returns event counts (`events_generated`/`events_corrected`/`errors`/`warnings`). **Decision (2026-06-07):** add the per-mission entry rather than retiring the runner onto `repair_repo` — `repair_repo` is repo-level and drops the per-feature event-count reporting the runner needs; full retirement is deferred to a separate fixture-backed change. | High | Open |
| FR-033 | Migrate legacy rebuild callers | US8 · `migration/normalize_mission_lifecycle.py` and `migration/runner.py` (Step 4) no longer depend on the deprecated `rebuild_event_log`; the deprecated symbol is removed or kept only as a thin shim with no live callers, and `migration/__init__.__all__` no longer lists an unbound lazy symbol that static analyzers flag (#1757.4). | High | Open |
| FR-034 | Legacy migration fixtures + behavior preservation | US8 · migration fixtures cover the per-mission rebuild path; legacy missions migrate unchanged and event counts/transformations are equivalent to the deprecated path. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior preservation | Strangling is behavior-preserving across all execution modes; zero behavioral regressions on the existing integration + architectural suites. | Reliability | High | Open |
| NFR-002 | Leanness (Randy Reducer IC) | Each execution-context/path resolution concern has exactly one implementation path; zero duplicated/parallel resolvers remain (verified by review + grep). | Maintainability | High | Open |
| NFR-003 | Single ownership (Paula Patterns IC) | The canonical surface and status facade are the sole owners of their concerns; zero boundary-leak bypasses outside documented exemptions; architectural tests bite. | Maintainability | High | Open |
| NFR-004 | Backward compatibility | Legacy missions and existing on-disk `state.json` files load and operate unchanged; 100% load cleanly; legacy integration tests pass unmodified. | Compatibility | High | Open |
| NFR-005 | Boundary-test performance | The repo-wide `status/` import scan completes in ≤15 s wall-clock on the full `src/` tree in CI. | Performance | Medium | Open |
| NFR-006 | No plumbing churn | `coordination/transaction.py` (`BookkeepingTransaction`) internals are unchanged; zero diff to its internals. | Maintainability | Medium | Open |
| NFR-007 | Lint & type clean | New code passes `ruff` and `mypy` with zero issues and zero warnings. Checks MUST NOT be disabled, suppressed, or relaxed (no blanket `# noqa`, `# type: ignore`, or per-file ignore additions) to achieve this — fix the code instead. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Never mainline unauthorized | Mainline (main/master) is never bypassed or committed to without explicit operator authorization; create-a-branch guidance always applies (operator ruling 2026-06-07). | Governance | High | Open |
| C-002 | Execution-mode policy | Planning happens on the coordination branch; a direct-to-target run may use the target branch directly with no worktree. | Process | High | Open |
| C-003 | Ratchet-gated strangling | The full e2e ratchet (FR-020..FR-024) must be green before any FR-007..FR-019 strangling change is considered complete. | Process | High | Open |
| C-004 | Plumbing exemption | `coordination/status_transition.py` and `coordination/transaction.py` remain exempt from the status boundary test (internal plumbing, not fixed). | Technical | High | Open |
| C-005 | No mission_number selector | `mission_number` is never used as a selector or identity in new/modified code; lookup is by `mission_id` or `mission_slug` only. | Technical | High | Open |
| C-006 | ADR before mass code | The new module name and API shape are ratified in a design ADR before the bulk of strangling lands (DIRECTIVE_032). | Governance | High | Open |
| C-007 | Bulk-edit guardrail | The #1664 import-path migration changes the same `specify_cli.status.<sub>` strings across many files; the mission runs in `change_mode: bulk_edit` and produces an `occurrence_map.yaml` (DIRECTIVE_035). | Process | High | Open |
| C-008 | Out of scope | Actor-kind vocabulary normalization, Effector type materialization, CommitTarget atomicity (step 7), and communication-artefact consolidation (step 5) are excluded. | Technical | Medium | Open |
| C-009 | Persona ICs mandatory | Shaping work packages carry explicit Randy-Reducer and Paula-Patterns implementation contracts governing leanness and single-ownership. | Process | High | Open |
| C-010 | Folded-in follow-ups | US7/US8 (#1757, #1754) are follow-ups surfaced by the #1756 (#1753) review that unblocked this mission's own `finalize-tasks`; they are in scope as natural extensions of the execution-environment remediations, not separate missions. | Process | Medium | Open |

### Key Entities

- **Canonical execution-state module**: New domain umbrella (expected `mission_runtime/`) owning execution-context/path/workspace resolution behind a published API; layer-registered.
- **`resolve_action_context`**: The canonical entry point relocated into the module; the only sanctioned execution-context resolver.
- **`ExecutionContext` / `ActionContext`**: The resolved per-domain context object callers receive.
- **Status facade**: `specify_cli.status` public API; the only sanctioned way to reach status behavior from outside `status/`.
- **`MissionStatus`**: Authoritative status read+write aggregate (#1667); consumers route mission-level status access through it.
- **e2e parity ratchet**: Extended `test_execution_context_parity.py` proving CWD/mode-invariant behavior across the full command sequence.
- **`MissionRunSnapshot`**: Run snapshot whose `mission_id`/`mission_slug` must survive all reconstruction sites.
- **occurrence_map.yaml**: Bulk-edit classification artifact covering the status import-path + path-builder migrations.
- **Frontmatter-source port**: The single IO boundary that supplies WP frontmatter to the finalize resolve→validate path (`build_wp_manifests`), so ownership resolution is testable without stubbing `read_wp_frontmatter`.
- **`scope` field (`codebase-wide`)**: The ownership-overlap exemption flag; human-authored only, carried through `from_frontmatter`, `backfill_ownership`, and validation by one canonical owner.
- **Canonical event-rebuild entry**: The per-mission `mission_state` entry point that supersedes the deprecated `rebuild_event_log` for legacy-project migration, returning event counts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single canonical execution-state module exists and is layer-registered — new module present; `test_no_unregistered_src_packages` and new architectural tests green.
- **SC-002**: The full-sequence ratchet passes across all three execution modes; the negative control fails when re-derivation is injected.
- **SC-003**: Repo-wide `status/` boundary enforced with zero violations — `grep -rn "from specify_cli\.status\." src/` outside `status/` (excluding exemptions) returns zero; boundary test green over all of `src/specify_cli`.
- **SC-004**: Path-builder residue eliminated — zero `main_repo_root / "kitty-specs" / mission_slug`-class constructions outside the canonical module and `status/`; the 8 duplicate feature-dir resolvers collapsed to one.
- **SC-005**: `MissionStatus` is the consistent status entry point — zero direct `BookkeepingTransaction`/`emit` calls outside `status/` and documented plumbing.
- **SC-006**: Mission identity survives reconstruction — `runtime_bridge.py:1723/:1860` carry `mission_id`/`mission_slug`; regression test green; #1663 closeable.
- **SC-007**: Leanness holds — zero duplicated/parallel resolvers remain; Randy-Reducer + Paula-Patterns review sign-off on shaping WPs.
- **SC-008**: No regressions — full existing integration + architectural suite passes; `ruff` + `mypy` clean (zero issues/warnings, no disabled checks — NFR-007) on touched modules.
- **SC-009**: Ownership `scope` is single-ported and backfill-aware — a `scope: codebase-wide` added to an already-backfilled WP survives a `backfill_ownership` re-run; `from_frontmatter` is provably symmetric across input shapes; the finalize resolve→validate path is exercised through the frontmatter-source port without stubbing the reader (#1757).
- **SC-010**: Legacy migration rebuild is single-ported — `migration/runner.py` and `normalize_mission_lifecycle.py` rebuild via the canonical `mission_state` entry (not `rebuild_event_log`); fixtures prove behavior preservation; the deprecated symbol has no live callers (#1754).

<!--
  Domain Language (terminology discipline): canonical terms — "execution-state domain
  surface", "canonical entry point" (resolve_action_context), "status facade",
  "MissionStatus aggregate", "execution mode" {planning | direct-to-target | worktree},
  "mode-correct target branch". Avoid: "core helpers", "path utils", "worktree-vs-main"
  binary, deep status.* imports.

  Assumptions: design basis is #1666 docs 01–17 (esp. doc 06 §4, doc 17); predecessor
  mission 01KT6HVH landed MissionStatus (#1667), resolve_action_context (#1673 entry),
  the narrowed ratchet, and the WP03-scoped boundary test; counts (225 bypass imports;
  ~125 path-builders/~160 files) measured 2026-06-07 and re-verified at implementation;
  runtime_bridge.py is both the #1673 residue hotspot and the #1663 field-drop site;
  run-through time/token cost are secondary to thorough remediation (operator direction).
-->
