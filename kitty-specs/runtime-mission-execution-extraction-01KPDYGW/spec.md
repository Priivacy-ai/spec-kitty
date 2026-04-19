# Runtime Mission Execution Extraction

**Mission ID**: `01KPDYGWKZ3ZMBPRX9RYMWPR1A`
**Mission slug**: `runtime-mission-execution-extraction-01KPDYGW`
**Mission type**: `software-dev`
**Change mode**: `bulk_edit` (import-path migration across internal callers mirroring charter extraction pattern)
**Target branch**: `main`
**Created**: 2026-04-17
**Trackers**: [#612 — Extract runtime/mission execution into a canonical functional module](https://github.com/Priivacy-ai/spec-kitty/issues/612)
**Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**Upstream dependencies**: `functional-ownership-map-01KPDY72` (#610) merged and `migration-shim-ownership-rules-01KPDYDW` (#615) merged.
**Downstream dependents**: #461 Phase 4 (ProfileInvocationExecutor), #461 Phase 6 (StepContractExecutor), #613 (glossary extraction — benefits from stable runtime interface).

---

## Primary Intent

Runtime is Spec Kitty's execution core: mission discovery, canonical next-state decisioning, execution sequencing, interaction with the execution layer, invocation of profiles and actions, active-mode handling (HiC vs autonomous), and retrieval of charter artefacts. Today this logic is scattered across `src/specify_cli/next/`, `src/specify_cli/cli/commands/agent/`, and adjacent subtrees under `specify_cli/`.

This mission moves the canonical implementation to a single top-level package (path decided by mission #610's ownership map — `src/runtime/` is the working candidate) while leaving CLI routing, argument parsing, Rich rendering, exit-code mapping, and user-facing presentation in `src/specify_cli/` as thin adapters. The extraction mirrors the charter pattern exactly: canonical implementation in a top-level package, thin re-export shim in `src/specify_cli/*`, `DeprecationWarning` on import, one-release deprecation window, removal at the registered target release. The shim contract and registry entry follow the #615 rulebook.

**Scope boundary for the runtime package (confirmed during discovery):**

- Runtime **owns** mission discovery, state sequencing, state-transition decisioning, interaction with the execution layer, profile/action invocation, active-mode handling (HiC vs autonomous), and retrieval of charter artefacts.
- The **content** of the next step (the actual step definition the user is told to perform) continues to live in mission artefacts (step contracts, mission templates).
- The **logic that decides which state transition is next** stays in the runtime layer.

Runtime is the heart of every CLI command; extraction must preserve existing semantics bit-for-bit. `spec-kitty next`, `spec-kitty implement`, `spec-kitty review`, `spec-kitty merge`, and their `--json` outputs, exit codes, and error messages must behave identically before and after.

The mission also ships a **dependency-rules document** specifying what runtime may call and what may call into runtime, with automated enforcement via `tests/architectural/test_layer_rules.py` (pytestarch), extended to add a `runtime` layer. The closed issue #395 originally tracked fragile layer matching; that concern is resolved by the pytestarch infrastructure already in the repo and is an AC of this mission.

---

## User Scenarios & Testing

### Primary actors

- **CLI end users** — every command that transitions mission state depends on runtime. Behaviour must be identical.
- **Spec Kitty contributors** — authoring new commands, runtime features, or mission types. Consume the clean runtime interface rather than embedding decisioning in command modules.
- **#461 Phase 4/6 implementers** — build `ProfileInvocationExecutor` and `StepContractExecutor` against the clean seam this mission scaffolds.
- **External Python importers** of `specify_cli.next.*` — get a `DeprecationWarning` with clear migration guidance; imports continue to resolve during the deprecation window.

### Acceptance scenarios

1. **CLI behaviour preserved**
   - **Given** a representative reference mission checked into `tests/regression/runtime/fixtures/`
   - **When** `spec-kitty next --agent <name> --mission <handle> --json`, `spec-kitty agent action implement WP01 --json`, `spec-kitty agent action review WP01 --json`, and `spec-kitty merge <handle> --json` run against that fixture
   - **Then** each command's JSON output matches the pre-extraction baseline snapshot (captured and committed before any code moves), exit codes match, and stderr messages match (normalized for timestamp/path variation).

2. **Runtime package owns state-transition decisioning**
   - **Given** a reader opens the new canonical runtime package (path per ownership map)
   - **When** they look for the function that decides "what state transition comes next?"
   - **Then** the function is defined in the runtime package; CLI command modules call it and never re-implement the decision.

3. **CLI command modules are thin adapters**
   - **Given** `src/specify_cli/cli/commands/agent/*.py` and `src/specify_cli/next/*.py` after the mission
   - **When** a reviewer reads a command module
   - **Then** the module: parses Typer arguments, calls the runtime service, formats the result with Rich or emits `--json`, and maps the result to exit codes. No state-machine branching or domain decisioning appears inline.

4. **Shim contract matches the #615 rulebook**
   - **Given** the shim at `src/specify_cli/next/` (and any additional shim paths identified during plan)
   - **When** a Python script inspects the module
   - **Then** it finds `__deprecated__: True`, `__canonical_import__` pointing at the canonical package, `__removal_release__` set per #615 rules, a `DeprecationWarning` emitted on import with `stacklevel=2`, and a registry entry in `architecture/2.x/shim-registry.yaml`.

5. **Dependency rules are enforced**
   - **Given** the dependency-rules document at the path specified in the ownership map for the runtime slice
   - **When** a PR introduces an import from runtime into a disallowed slice, or an import from a disallowed slice into runtime
   - **Then** CI fails. Enforcement is implemented via `tests/architectural/test_layer_rules.py` (pytestarch), extended with a `runtime` layer. No dependency on any external issue.

6. **Scaffolding seam present for Profile/Action invocation**
   - **Given** runtime defines the execution-layer invocation seam
   - **When** #461 Phase 4 starts implementing `ProfileInvocationExecutor`
   - **Then** the seam is a documented abstract interface (or typed callable) that Phase 4 implements — no runtime refactor is needed to install the executor.

7. **Existing integration tests pass unchanged**
   - **Given** the full `tests/` suite as it exists at mission start
   - **When** it runs against the post-extraction tree
   - **Then** every currently-passing test passes with no modifications to expected outputs. Tests that import from `specify_cli.next` either continue to work through the shim (emitting a `DeprecationWarning`) or are updated to the canonical import as part of the bulk-edit occurrence map.

8. **PR description cites the charter exemplar**
   - **Given** the PR opened for this mission's merge
   - **When** a reviewer reads the PR description
   - **Then** it names `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` as the template pattern, points at the #615 rulebook for the shim contract, and links the specific ownership-map slice entry this PR lands under.

### Edge cases

- A runtime code path that legitimately needs access to charter data. Resolution: runtime calls `charter.build_charter_context()` through the public interface; this is a permitted seam and is named in the dependency-rules document.
- A CLI command that adds genuinely CLI-specific behaviour (e.g., progress spinner wrapping) around a runtime call. Resolution: permitted — this is adapter work, not decisioning.
- A subtle difference in JSON output between pre- and post-extraction (e.g., key ordering). Resolution: baseline snapshots are dict-equal compared, not string-equal; key ordering is normalized by the test harness.
- A test fixture that depends on a private helper currently living under `specify_cli/next/`. Resolution: the helper moves to runtime and either becomes public API or stays private with an explicit pytest allowlist for the fixture.
- A runtime operation that must call back into a CLI presentation hook. Resolution: runtime defines an abstract `PresentationSink` protocol; CLI commands inject a Rich-backed implementation; runtime itself never imports Rich.

---

## Requirements

### Functional Requirements

| ID       | Requirement                                                                                                                                                                                                | Status    |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| FR-001   | Canonical runtime package exists at the path specified in the #610 ownership map for the runtime slice (working candidate: `src/runtime/`). Plan phase pins the final path.                                  | Confirmed |
| FR-002   | Runtime owns: mission discovery, state sequencing, state-transition decisioning, interaction with the execution layer, profile/action invocation, active-mode handling (HiC vs autonomous), retrieval of charter artefacts. | Confirmed |
| FR-003   | The actual step content (step definitions the user executes) continues to live in mission artefacts (step contracts, mission templates). Runtime orchestrates, it does not author step content.             | Confirmed |
| FR-004   | CLI command modules under `src/specify_cli/cli/commands/agent/` and `src/specify_cli/next/` are reduced to thin adapters: argument parsing, runtime service call, Rich rendering, JSON emission, exit-code mapping. No inline state-machine decisioning. | Confirmed |
| FR-005   | Thin deprecation shim(s) at the legacy `specify_cli` path(s), matching the #615 shim contract exactly (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`, `DeprecationWarning` on import). | Confirmed |
| FR-006   | Each shim has a registry entry in `architecture/2.x/shim-registry.yaml`; the registry entry passes the #615 CI check.                                                                                      | Confirmed |
| FR-007   | Dependency rules for the runtime slice are recorded in the #610 ownership map's runtime slice entry (per #610 FR-004). This mission does **not** author a separate dependency-rules document; it consumes the map's rules as the normative source and ensures they are complete enough to drive the enforcement in FR-008. Any gaps surfaced during plan are fixed by amending the ownership map, not by creating a parallel doc. | Confirmed |
| FR-008   | Dependency-rules enforcement: extend `tests/architectural/test_layer_rules.py` to add a `runtime` layer and assert forbidden edges (no `specify_cli.cli.*`, `rich.*`, `typer.*` imports into runtime; no imports from runtime into disallowed slices). The pytestarch infrastructure already in the repo covers this need — the mission does not depend on any external issue for this. | Confirmed |
| FR-009   | Scaffolding seam for profile/action invocation: runtime exposes a typed interface (protocol or abstract executor) that #461 Phase 4 `ProfileInvocationExecutor` implements without further runtime refactor. | Confirmed |
| FR-010   | Scaffolding seam for step-contract execution: runtime exposes the execution-layer entry point that #461 Phase 6 `StepContractExecutor` wires into.                                                           | Confirmed |
| FR-011   | Regression fixtures: JSON snapshots at `tests/regression/runtime/fixtures/` capture pre-extraction `--json` output for `spec-kitty next`, `spec-kitty agent action implement`, `spec-kitty agent action review`, and `spec-kitty merge` on a representative reference mission.  | Confirmed |
| FR-012   | Regression test asserts post-extraction `--json` output matches the fixtures (dict-equal) and that exit codes and stderr messages match (normalized).                                                         | Confirmed |
| FR-013   | `PresentationSink` (or equivalently-named) protocol is defined in runtime; runtime never imports `rich.*`. CLI adapters inject the Rich-backed implementation.                                              | Confirmed |
| FR-014   | Migration documentation at `docs/migration/runtime-extraction.md` following the template established for charter, including import-path translation table for external callers.                               | Confirmed |
| FR-015   | Bulk-edit occurrence map (`occurrence_map.yaml`) generated in plan phase enumerates every internal caller migrated from `specify_cli.next.*` to the canonical runtime import path.                             | Confirmed |
| FR-016   | PR description and merge commit cite mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` as the exemplar pattern and link to the ownership-map runtime slice entry.                    | Confirmed |

### Non-Functional Requirements

| ID       | Requirement                                                                                                                                                                          | Status    |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| NFR-001  | Behaviour-preservation regression test completes in ≤30 seconds on CI.                                                                                                                | Confirmed |
| NFR-002  | Zero regressions across the existing test suite; all currently-passing tests continue to pass.                                                                                         | Confirmed |
| NFR-003  | `spec-kitty next`, `implement`, `review`, `merge` CLI latency unchanged to within ±10% on a representative reference mission (measured wall-clock over 10 warm runs).                   | Confirmed |
| NFR-004  | `DeprecationWarning` from shim imports is visible in standard pytest runs but does not cause warnings-as-errors failures in existing test configurations.                               | Confirmed |
| NFR-005  | Dependency-rules pytest completes in ≤5 seconds.                                                                                                                                     | Confirmed |

### Constraints

| ID     | Constraint                                                                                                                                                                                             | Status    |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| C-001  | No semantic changes to `next` decisioning, mission state machine, or lane arbitration. Pure move + adapter conversion.                                                                                  | Confirmed |
| C-002  | No `ProfileInvocationExecutor` or `StepContractExecutor` implementations in this mission — only the scaffolding seams they plug into.                                                                    | Confirmed |
| C-003  | No glossary runtime middleware (that belongs to #613 / #461 Phase 5).                                                                                                                                   | Confirmed |
| C-004  | No CLI UX changes (command names, argument shapes, output formats stay identical).                                                                                                                       | Confirmed |
| C-005  | No model-discipline doctrine port.                                                                                                                                                                      | Confirmed |
| C-006  | No version bump — `pyproject.toml` stays untouched; upstream maintainers cut the release.                                                                                                               | Confirmed |
| C-007  | The mission runs under `change_mode: bulk_edit`; plan phase produces `occurrence_map.yaml`.                                                                                                             | Confirmed |
| C-008  | Terminology canon applies: **Mission** (not "feature"), **Work Package** (not "task").                                                                                                                   | Confirmed |
| C-009  | Runtime must not import from `specify_cli.cli.*` or any Rich/Typer symbol. Enforced by the dependency-rules test.                                                                                         | Confirmed |

---

## Success Criteria

1. **Behaviour invariance** — All four regression-fixture commands produce identical `--json` output, exit codes, and stderr (normalized) before and after extraction.
2. **Package boundary cleanness** — Runtime module graph (as measured by the dependency-rules pytest) contains zero forbidden edges.
3. **Adapter conversion complete** — A code-review walkthrough confirms no CLI command module embeds state-transition decisioning; every command is a thin adapter.
4. **Deprecation contract honoured** — Every legacy import path emits `DeprecationWarning` with correct migration guidance; every shim is registered; the #615 CI check passes.
5. **Downstream seams usable** — #461 Phase 4 and Phase 6 can be opened as separate missions that implement against the scaffolded seams without further runtime refactor (validated by drafting a minimal stub implementation in plan/research that compiles and type-checks).
6. **Zero regression** — Full test suite passes with no test modifications outside the bulk-edit occurrence map and the new regression fixtures.
7. **Migration doc and PR citations in place** — `docs/migration/runtime-extraction.md` exists; PR description cites the exemplar and ownership-map slice.

---

## Key Entities

- **Runtime package** — the canonical top-level package owning execution-core logic.
- **State-transition decisioning** — the function(s) computing the next mission state from the current state plus inputs.
- **Execution layer** — the subsystem that runs profile invocations and step contracts; runtime interacts with it via the scaffolded seam.
- **Active mode** — HiC (human-in-the-loop) vs autonomous execution mode.
- **PresentationSink** — the protocol runtime uses to surface output without depending on Rich.
- **Regression fixture** — a checked-in reference mission plus baseline `--json` snapshots under `tests/regression/runtime/`.
- **Dependency-rules document** — the list of allowed/forbidden cross-slice imports for the runtime package.
- **Shim** — the re-export module at the legacy `specify_cli.next` / `specify_cli.cli.commands.agent.*` paths, per #615 rulebook.
- **Occurrence map** — the bulk-edit artefact enumerating every internal call site migrated to canonical imports.

---

## Dependencies & Assumptions

### Upstream (must land before this mission starts)

- **#610 ownership map** — pins the canonical runtime package path and the dependency-rules seam.
- **#615 shim rulebook** — provides the shim contract, registry, and CI check this mission's shims plug into.
- **Regression baseline capture** — a pre-extraction work package runs the four CLI commands on the reference mission and commits the JSON snapshots **before** any code moves. This is a work package within this mission; the baseline is not captured by an external mission.

### Downstream

- **#461 Phase 4** (ProfileInvocationExecutor) — implements against the scaffolded invocation seam.
- **#461 Phase 6** (StepContractExecutor) — implements against the scaffolded execution seam.
- **#613 glossary extraction** — benefits from the stable runtime interface when wiring glossary middleware later.

### Assumptions

- A1. The canonical runtime path from #610's ownership map is `src/runtime/` (working candidate). If the ownership map picks a different path, this spec's path references update accordingly during plan.
- A2. The four representative CLI commands (`next`, `implement`, `review`, `merge`) plus `--json` mode exercise enough runtime surface to prove behaviour preservation. Plan-phase audit confirms no runtime-dependent command is omitted.
- A3. The `rich`/`typer` separation boundary is realistic — runtime currently has limited or no direct Rich usage; any existing offenders are enumerated in plan and rewritten through `PresentationSink`.
- A4. The bulk-edit occurrence map is generated during plan and reviewed under the `spec-kitty-bulk-edit-classification` skill workflow.
- A5. Dependency-rules enforcement is implemented via the existing `tests/architectural/test_layer_rules.py` pytestarch infrastructure. The closed issue #395 (fragile layer matching) is the historical predecessor; its concern is resolved by pytestarch and is an AC of this mission. No external issue is a prerequisite.

---

## Out of Scope

- Any implementation of `ProfileInvocationExecutor` or `StepContractExecutor` (#461 Phase 4/6).
- Any glossary runtime middleware (#613, #461 Phase 5).
- CLI UX changes of any kind.
- Model-discipline doctrine port.
- Version bump or release automation changes.
- Refactoring mission state machine semantics or lane arbitration.
- Extending `spec-kitty` CLI command surface (no new commands).

---

## Open Questions

None at spec time. Plan phase determines:

- The final canonical runtime package path (per #610 ownership map).
- The full enumeration of shim locations (likely `specify_cli.next` plus additional paths under `specify_cli.cli.commands.agent.*`).
- The precise shape of the `PresentationSink` protocol and the profile-invocation seam.
- The precise shape of the `PresentationSink` protocol and the profile-invocation seam.
- Whether additional CLI commands beyond `next`/`implement`/`review`/`merge` need regression snapshots.
