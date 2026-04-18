# Glossary Functional Module Extraction

**Mission ID**: `01KPDYM9H8WGXC6HH6YKEQR9Q6`
**Mission slug**: `glossary-functional-module-extraction-01KPDYM9`
**Mission type**: `software-dev`
**Change mode**: `bulk_edit` (import-path migration across internal callers mirroring charter extraction pattern)
**Target branch**: `main`
**Created**: 2026-04-17
**Trackers**: [#613 — Extract glossary into a first-class functional module](https://github.com/Priivacy-ai/spec-kitty/issues/613)
**Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**Upstream dependencies**: `functional-ownership-map-01KPDY72` (#610), `migration-shim-ownership-rules-01KPDYDW` (#615), and ideally `runtime-mission-execution-extraction-01KPDYGW` (#612) merged. Plan may overlap the review phase of #612 if #612 acceptance is close.
**Downstream dependents**: #461 Phase 5 (glossary as DRG-resident runtime middleware).

---

## Primary Intent

Glossary is already a runtime concern. The existing semantic-integrity pipeline under `src/specify_cli/glossary/` performs validation, scope handling, conflict detection, runtime terminology checks, and rendering for the command surface. But its posture treats glossary as "some commands plus helpers" rather than a first-class knowledge subsystem with a clean module boundary.

This mission gives glossary a coherent canonical module boundary — `src/glossary/` — before #461 Phase 5 turns it into runtime middleware. The extraction mirrors the charter and runtime patterns exactly: canonical implementation in a top-level package, thin re-export shim in `src/specify_cli/glossary/`, `DeprecationWarning` on import, one-release deprecation window, removal at the registered target release. Shim contract and registry entry follow the #615 rulebook.

The extraction preserves all existing glossary behaviour end-to-end. No new features, no UX changes. Rendering concerns stay in the CLI adapter layer; runtime-facing behaviour (store, scope, conflict detection, terminology checks, integrity middleware) moves to the canonical package.

The mission adds one dedicated work package ahead of the move: a **cross-module entanglement audit** that greps every call site and shortcut into the current `specify_cli/glossary/` namespace across the whole repository and produces an inventory committed into the migration document. The audit reduces the chance that the plan under-estimates the cross-slice surface.

Out of scope for this mission: the graph-backed addressing seam. The draft suggested scaffolding a protocol + stub. Per discovery, the seam is **not** scaffolded here — #461 DRG work will introduce it when the actual implementation arrives. This mission treats glossary as a conventional Python module with well-defined public functions and types, nothing more.

---

## User Scenarios & Testing

### Primary actors

- **CLI end users** — run `spec-kitty glossary *` commands and rely on terminology validation during mission workflows. Behaviour must be identical.
- **Spec Kitty contributors** — authoring features that touch glossary (new term sources, conflict-resolution strategies, additional command surface) consume the canonical module rather than importing scattered helpers.
- **#461 Phase 5 implementers** — receive a clean glossary module to wire in as DRG-resident runtime middleware.
- **External Python importers** of `specify_cli.glossary.*` — get a `DeprecationWarning` with migration guidance; imports continue to resolve during the deprecation window.
- **Runtime callers** (post-#612) — consume glossary via the canonical import, following the seam documented in the ownership map.

### Acceptance scenarios

1. **CLI glossary commands behave identically**
   - **Given** the full `spec-kitty glossary *` command surface (list, add, resolve, check, etc.) exercised by integration tests and by a representative reference project checked into `tests/regression/glossary/fixtures/`
   - **When** each command runs against the reference project before and after extraction
   - **Then** stdout, stderr, exit codes, and JSON outputs (where applicable) match exactly (normalized for timestamp/path variation).

2. **Canonical module owns glossary behaviour**
   - **Given** `src/glossary/` after extraction
   - **When** a reader inspects it
   - **Then** it contains: store and state reconstruction, scope handling, conflict detection/resolution, runtime terminology checks (semantic integrity middleware), and the public API surface for term CRUD. Rendering/presentation helpers do not move into the canonical package.

3. **CLI adapter layer owns rendering**
   - **Given** `src/specify_cli/cli/commands/glossary/*` (or equivalent CLI surface) and the post-extraction adapter path
   - **When** a reviewer reads the CLI modules
   - **Then** they parse arguments, call canonical glossary services, and format output using Rich / emit JSON — no integrity logic, no scope handling, no conflict detection embedded inline.

4. **Shim contract matches the #615 rulebook**
   - **Given** the shim at `src/specify_cli/glossary/`
   - **When** imported
   - **Then** module attributes include `__deprecated__ = True`, `__canonical_import__ = "glossary"`, `__removal_release__` set per #615, `__deprecation_message__`, and a `DeprecationWarning` is emitted on import with `stacklevel=2`. A registry entry exists in `architecture/2.x/shim-registry.yaml`.

5. **Entanglement audit is complete and committed**
   - **Given** the audit work package runs before code moves
   - **When** its output is committed as `docs/migration/glossary-extraction.md#entanglement-inventory`
   - **Then** the inventory enumerates every repository-wide call site and shortcut touching `specify_cli.glossary`, each row tagged `migrate` (move to canonical), `adapter` (stays in CLI), or `grandfathered` (documented exception with rationale).

6. **Integrity pipeline continues to enforce**
   - **Given** the existing semantic integrity test suite under `tests/` exercising glossary conflict detection and strictness levels
   - **When** it runs against the post-extraction tree
   - **Then** every currently-passing integrity test continues to pass with no modifications to expected outputs.

7. **Runtime seam is honoured**
   - **Given** the ownership map (#610) specifies how runtime may invoke glossary
   - **When** post-#612 runtime code calls glossary
   - **Then** it uses the canonical `glossary.*` import path; the dependency-rules test (from #612) permits this edge.

8. **PR cites the exemplars**
   - **Given** the merge PR description
   - **When** a reviewer reads it
   - **Then** it cites `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` as the pattern template, the #615 rulebook for the shim contract, and the specific ownership-map glossary slice entry this PR lands under.

### Edge cases

- A CLI helper that currently imports private glossary internals (underscore-prefixed functions). Resolution: plan phase either promotes the helper to the public canonical API or keeps it private and migrates the importing call site to use a public equivalent.
- A test fixture that seeds the glossary store via direct internal access. Resolution: fixtures use the canonical public constructors; any direct-access fixture is updated as part of the bulk-edit.
- Glossary middleware that is invoked at runtime boot by code outside `specify_cli.glossary`. Resolution: the entanglement audit names the call sites; each migrates to `from glossary import ...` under the bulk-edit occurrence map.
- A rendering helper that both formats glossary output **and** enforces truncation rules that are semantically significant (e.g., max-term-length warnings). Resolution: truncation rules move to canonical glossary; purely visual formatting stays in CLI adapters.
- The pre-existing `glossary/` directory at the repo root (term content, not code) must not be affected. Resolution: the canonical Python package lives at `src/glossary/`; content at `glossary/` remains untouched.

---

## Requirements

### Functional Requirements

| ID       | Requirement                                                                                                                                                                                         | Status    |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| FR-001   | Canonical glossary package exists at `src/glossary/` (this is pre-committed; not deferred to the ownership map).                                                                                     | Confirmed |
| FR-002   | Canonical package owns: glossary store and state reconstruction, scope handling, conflict detection and resolution, runtime terminology checks (semantic integrity middleware), and public API for term CRUD. | Confirmed |
| FR-003   | Rendering/presentation code (Rich formatting, JSON emission helpers for CLI output) stays in or moves to the CLI adapter layer; it does not live under `src/glossary/`.                               | Confirmed |
| FR-004   | `src/glossary/` never imports from `specify_cli.cli.*`, `rich.*`, or `typer.*`. Enforced by an architectural pytest.                                                                                | Confirmed |
| FR-005   | CLI glossary commands under `src/specify_cli/cli/commands/glossary/*` (or equivalent surface) become thin adapters: argument parsing → canonical glossary call → rendering/JSON emission → exit-code mapping. | Confirmed |
| FR-006   | Thin deprecation shim at `src/specify_cli/glossary/` matches the #615 shim contract (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`, `DeprecationWarning` on import, `stacklevel=2`). | Confirmed |
| FR-007   | Shim has a registry entry in `architecture/2.x/shim-registry.yaml`; entry passes the #615 CI check.                                                                                                 | Confirmed |
| FR-008   | Dedicated **entanglement audit** work package runs before the code move. Output is an inventory table committed to `docs/migration/glossary-extraction.md#entanglement-inventory` listing every call site and shortcut touching `specify_cli.glossary` across the whole repo, each tagged `migrate` / `adapter` / `grandfathered`. | Confirmed |
| FR-009   | Bulk-edit `occurrence_map.yaml` generated in plan phase enumerates every import migration from `specify_cli.glossary.*` to `glossary.*`.                                                              | Confirmed |
| FR-010   | Regression fixtures: `tests/regression/glossary/fixtures/` holds baseline snapshots of `spec-kitty glossary *` commands' outputs on a representative reference project. Captured pre-extraction.      | Confirmed |
| FR-011   | Regression test asserts post-extraction glossary CLI outputs match the fixtures; existing integrity tests pass unchanged.                                                                              | Confirmed |
| FR-012   | Migration documentation at `docs/migration/glossary-extraction.md` including (a) entanglement inventory, (b) import-path translation table for external callers, (c) deprecation window and removal release. | Confirmed |
| FR-013   | Remaining cross-module shortcuts that cannot be cleanly migrated in this mission are listed in the PR description (not silently carried forward). Each listed item has a follow-up tracker or a `grandfathered` rationale in the audit table. | Confirmed |
| FR-014   | PR description and merge commit cite `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` as exemplar and link the #610 ownership-map glossary slice entry.                              | Confirmed |

### Non-Functional Requirements

| ID       | Requirement                                                                                                                                                        | Status    |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| NFR-001  | Glossary CLI command latency unchanged to within ±10% on a representative reference project (measured wall-clock over 10 warm runs of `spec-kitty glossary list`).   | Confirmed |
| NFR-002  | Zero regressions across the existing test suite.                                                                                                                    | Confirmed |
| NFR-003  | Regression snapshot test completes in ≤15 seconds on CI.                                                                                                            | Confirmed |
| NFR-004  | Architectural pytest (no Rich/Typer/CLI imports in `src/glossary/`) completes in ≤3 seconds.                                                                         | Confirmed |
| NFR-005  | `DeprecationWarning` from shim imports is visible in pytest output but does not convert to errors under existing warning configurations.                             | Confirmed |

### Constraints

| ID     | Constraint                                                                                                                                                                      | Status    |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| C-001  | No new glossary features. No new commands, no new term sources, no new conflict-resolution strategies. Pure extraction.                                                          | Confirmed |
| C-002  | No graph-backed addressing seam. Neither a protocol nor a stub is introduced in this mission. #461 DRG work adds the seam when it lands.                                         | Confirmed |
| C-003  | No DRG-resident runtime middleware implementation (#461 Phase 5).                                                                                                               | Confirmed |
| C-004  | No CLI UX changes beyond the structural adapter conversion.                                                                                                                       | Confirmed |
| C-005  | The mission runs under `change_mode: bulk_edit`; plan phase produces `occurrence_map.yaml`.                                                                                      | Confirmed |
| C-006  | Terminology canon applies: **Mission** (not "feature"), **Work Package** (not "task").                                                                                            | Confirmed |
| C-007  | `src/glossary/` must not depend on `specify_cli.*` (no back-edge into the CLI shell). Enforced by the architectural test.                                                         | Confirmed |
| C-008  | No version bump — `pyproject.toml` untouched; upstream maintainers cut the release.                                                                                              | Confirmed |
| C-009  | The repo-root `glossary/` directory (term content) is untouched; the canonical Python package goes to `src/glossary/`.                                                            | Confirmed |

---

## Success Criteria

1. **Behaviour invariance** — All `spec-kitty glossary *` commands produce identical stdout/stderr/JSON/exit codes before and after extraction, verified by regression snapshots.
2. **Boundary cleanness** — Architectural pytest confirms zero forbidden imports (no Rich/Typer/CLI in `src/glossary/`; no back-edge from glossary into `specify_cli.*`).
3. **Adapter conversion complete** — CLI glossary commands are thin adapters; no integrity/scope/conflict logic inline. Verified by code-review walkthrough during `/spec-kitty.review`.
4. **Entanglement audit published** — `docs/migration/glossary-extraction.md#entanglement-inventory` lists every call site pre-extraction, with disposition; the PR description references the inventory.
5. **Deprecation contract honoured** — Shim at `src/specify_cli/glossary/` emits `DeprecationWarning`, has all required attributes, is registered in the shim registry, and the #615 CI check passes.
6. **Downstream seam ready** — #461 Phase 5 can start as a separate mission that wires glossary as DRG-resident middleware without further glossary refactor.
7. **Zero regression** — Full existing test suite passes; no test modifications outside the bulk-edit occurrence map and new regression fixtures.

---

## Key Entities

- **Glossary canonical package** — `src/glossary/`, owning store, scope, conflict detection, runtime terminology checks, public term CRUD API.
- **Glossary CLI adapter layer** — `src/specify_cli/cli/commands/glossary/*`, owning Typer/Rich presentation.
- **Semantic integrity middleware** — the runtime-facing terminology-check layer currently under `src/specify_cli/glossary/middleware.py`; moves to `src/glossary/middleware.py`.
- **Glossary store** — persistent state for terms and term relations.
- **Scope** — the namespace / project / language-scope modifier applied to a term (existing concept).
- **Conflict detection** — existing logic identifying contradicting terms or strictness violations.
- **Entanglement inventory** — the audit table produced by the dedicated pre-move work package.
- **Shim** — the re-export module at `src/specify_cli/glossary/`, per #615 rulebook.
- **Occurrence map** — the bulk-edit artefact enumerating internal call-site migrations.

---

## Dependencies & Assumptions

### Upstream (must land before this mission starts)

- **#610 ownership map** — pins the glossary slice's adapter responsibilities vs canonical responsibilities.
- **#615 shim rulebook and registry** — provides the shim contract and CI check.
- **#612 runtime extraction** (ideally) — stable runtime interface means the glossary extraction doesn't have to coordinate with a moving runtime target. Plan may overlap #612's review/accept phase if timelines compress.
- **Regression baseline capture** — a pre-move work package in this mission captures `spec-kitty glossary *` baseline snapshots before any glossary code moves.

### Downstream

- **#461 Phase 5** (glossary as DRG-resident runtime middleware) — consumes the clean module boundary.
- Post-#612 runtime code paths that call glossary — migrate to canonical `glossary.*` imports via this mission's occurrence map.

### Assumptions

- A1. `src/glossary/` is available as a path — the repo-root `glossary/` directory (term content) does not collide because it is not a Python package and is unrelated code.
- A2. The existing `src/specify_cli/glossary/` surface is fully enumerable in an audit pass; no dynamic import magic obscures the call graph. Plan-phase research confirms this.
- A3. The glossary integrity pipeline is implementation-entangled with CLI render helpers only in ways enumerable by grep; there is no runtime reflection requiring deeper analysis.
- A4. External downstream Python importers are rare; the deprecation window (one release) plus the `DeprecationWarning` is adequate grace. If evidence of heavy external use surfaces during audit, the window may be extended per the #615 extension mechanism.
- A5. Rendering vs integrity separation is cleanly achievable. If a helper straddles the boundary, plan phase picks the side based on whether the logic is semantically significant (integrity) or purely visual (adapter).

---

## Out of Scope

- Any new glossary feature or command.
- Graph-backed addressing seam (neither protocol nor stub).
- DRG-resident runtime middleware implementation (#461 Phase 5).
- CLI UX changes beyond structural adapter conversion.
- Version bump or release automation changes.
- Modifications to the repo-root `glossary/` content directory.
- Rewriting or refactoring semantic-integrity strictness semantics.

---

## Open Questions

None at spec time. Plan phase determines:

- The exact shim contract removal release (picks a concrete value per #615 rules, likely one minor release after the shim lands).
- Whether the CLI adapter layer currently under `src/specify_cli/cli/commands/glossary/*` (or equivalent path) is already cleanly separated or whether some inline logic needs lifting during extraction.
- The precise public-API surface `src/glossary/` exports vs internal (underscore-prefixed) helpers.
- Whether any existing fixture fixtures require updating beyond the bulk-edit occurrence map.
