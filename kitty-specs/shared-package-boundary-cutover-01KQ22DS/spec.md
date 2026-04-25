# Mission Specification: Shared Package Boundary Cutover

**Mission ID:** `01KQ22DSP6D1F7QCF7N87T8B66`
**Mission slug:** `shared-package-boundary-cutover-01KQ22DS`
**Mission type:** software-dev
**Created:** 2026-04-25
**Branch contract:** planning base `main`, merge target `main`

---

## Summary

The Spec Kitty CLI must complete the long-deferred cutover to the new shared package
boundary. After this mission, the CLI repository owns its own runtime end-to-end,
consumes `spec-kitty-events` and `spec-kitty-tracker` only as external PyPI packages
through their public import surfaces, and no longer ships, vendors, mirrors, or imports
the standalone `spec-kitty-runtime` package from production code paths. The CLI's
package metadata, lockfiles, drift checks, release docs, and CI must reflect the new
boundaries, and a clean-install verification proves `spec-kitty next` works without the
retired runtime package.

This mission deliberately **does not** preserve the hybrid model that PR #779 was
rejected for. PR #779 attempted to ship runtime-shaped code in the CLI tree while
keeping standalone `spec_kitty_runtime` production imports alive; that arrangement
created cross-package release lockstep and CI failure. This mission performs the actual
cutover.

## Background

The CLI is currently between models:

- It already contains runtime-shaped code in `src/specify_cli/next/` (notably
  `runtime_bridge.py`) and asset-runtime code under `src/specify_cli/runtime/`, but
  several production code paths still `from spec_kitty_runtime import ...` (engine,
  schema, planner) — leaking a hard dependency on the standalone runtime package even
  though `pyproject.toml` does not list it as a runtime dependency.
- It vendors event-package code under `src/specify_cli/spec_kitty_events/` and
  consuming modules import the vendored copy through `specify_cli.spec_kitty_events.*`
  rather than through the public `spec_kitty_events` PyPI package.
- The tracker integration imports both the public `spec_kitty_tracker` package
  (correctly) and the CLI-internal `specify_cli.tracker` adapter; the boundary is
  intact for tracker but the consumer-test contract is missing.
- Release docs and drift checks still encode exact sibling-package release gates that
  no longer match the post-cutover architecture.

Three cross-repo missions establish the world this mission lands in:

| Repo | Mission | Status | What it gives this mission |
|------|---------|--------|----------------------------|
| `spec-kitty-events` | `events-pypi-contract-hardening-01KQ1ZK7` | Merged on main at sha `81d5ccd4` | Canonical PyPI contract; `docs/public-surface.md` defines the import surface CLI must use. |
| `spec-kitty-tracker` | `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` | Implement-review (in flight) | Tracker is an independent PyPI SDK; CLI consumes only `spec_kitty_tracker.*`. |
| `spec-kitty-runtime` | `runtime-standalone-package-retirement-01KQ20Z8` | Implement-review (in flight) | Inventories the public API used by CLI; confirms the package is being retired. CLI must internalize that surface. |

PR `Priivacy-ai/spec-kitty#779` was rejected because it preserved standalone
`spec_kitty_runtime` production imports while moving runtime-shaped code into the CLI
tree. This mission must not repeat that mistake.

## In-scope

- Internalize all runtime behavior the CLI requires for `spec-kitty next` and mission
  execution into CLI-owned modules.
- Replace every production `from spec_kitty_runtime ...` import in the CLI source tree
  with a CLI-owned equivalent.
- Remove the vendored / mirrored `spec-kitty-events` tree from CLI production package
  paths and update every consumer to import from the public `spec_kitty_events`
  package.
- Continue consuming `spec-kitty-tracker` only through its public `spec_kitty_tracker`
  imports; add consumer tests that pin the contract surface CLI flows actually use.
- Update CLI package metadata (`pyproject.toml`), lockfiles (`uv.lock`), `constraints.txt`,
  release docs, and drift checks to reflect the new boundaries.
- Replace exact sibling-package release pins for events/tracker with compatible-range
  constraints in `pyproject.toml` (exact pins live in lockfiles only) where compatibility
  allows; events/tracker compatibility ranges must follow the contract documented in the
  upstream public-surface docs.
- Add a clean-install CI verification that proves `spec-kitty next` runs against a
  fixture mission in a clean virtual environment without `spec-kitty-runtime` installed.
- Update `[tool.uv.sources]` so editable / path overrides for events/tracker are dev-only
  and never committed for production paths.
- Update CLAUDE.md / README / CHANGELOG / migration docs that reference the old hybrid
  model so external operators know the runtime package is no longer required.

## Out of scope

- Re-architecting the CLI's mission step contracts, mission DSL, or invocation pipeline
  beyond what is required to internalize the runtime surface.
- Adding new CLI commands or removing existing ones.
- Republishing the retired `spec-kitty-runtime` package; that mission is owned by the
  runtime repo.
- Touching agent surface configs (`.claude`, `.cursor`, `.gemini`, `.kilocode`, etc.)
  except to the minimum extent required to keep them in sync with template source files
  the cutover already edits.
- Changing the CLI's hosted-services / SaaS sync wire formats or semantics.
- Migrating consumer projects of CLI to the new boundary; this mission only ships the
  CLI side of the cutover.

## Stakeholders & users

- **CLI maintainers** — own the CLI repo; need a clean dependency graph and CI that
  passes without cross-package release lockstep.
- **CLI end users (operators running `spec-kitty next`)** — must keep getting working
  mission execution; the cutover must be transparent at the command layer.
- **Events package maintainers** — own the PyPI contract; need CLI to consume only the
  documented public surface.
- **Tracker package maintainers** — own the SDK contract; need consumer tests on the
  CLI side so SDK changes can be screened against real usage.
- **Runtime package maintainers** — retiring the package; need confirmation that no
  CLI production path imports it.

## User scenarios & testing

### Primary flow: clean-install user runs `spec-kitty next`

1. A new operator creates a fresh virtual environment.
2. They install only the CLI: `pip install spec-kitty-cli` (no `spec-kitty-runtime`).
3. They scaffold a fixture mission and run `spec-kitty next --agent claude`.
4. The runtime loop advances correctly using CLI-internal runtime code; events are
   emitted via `spec_kitty_events` from the public PyPI package; tracker calls (when
   configured) reach `spec_kitty_tracker` from the public PyPI package.
5. No `ModuleNotFoundError: spec_kitty_runtime` and no behaviour change versus
   pre-cutover CLI for the user's mission flow.

### Maintainer flow: CI gate

1. CI installs CLI in a clean container without `spec-kitty-runtime`.
2. CI runs the unit / integration / consumer-test suites.
3. Drift checks pass without sibling-package exact-version gates.
4. The clean-install verification job runs `spec-kitty next` against a fixture mission
   and asserts the loop advances at least one step.

### Edge case: dev workflow with editable sibling packages

1. A maintainer working across spec-kitty-events / spec-kitty-tracker locally uses
   `[tool.uv.sources]` editable overrides in a developer-only configuration (for
   example `pyproject.dev.toml` or an explicit local override mechanism).
2. The committed `pyproject.toml` and `uv.lock` do not include those overrides.
3. CI rejects PRs that introduce path/editable overrides for events or tracker into the
   committed production configuration.

### Edge case: stale install with `spec-kitty-runtime` still present

1. A pre-cutover user upgrades CLI without uninstalling `spec-kitty-runtime`.
2. CLI must still function: production code paths use the CLI-internal runtime, the
   stale package is simply not imported.
3. CLI emits a one-time deprecation notice (when feasible without runtime imports)
   pointing operators at the migration doc.

### Negative case: re-introducing a `spec_kitty_runtime` import

1. A future contributor adds `from spec_kitty_runtime ...` to a CLI production module.
2. An architectural enforcement test (using `pytestarch` per ADR 2026-03-27-1) fails CI
   with a clear message naming the offending file and the rule it violates.

### Negative case: re-introducing vendored events code

1. A future contributor restores `src/specify_cli/spec_kitty_events/` as a vendored
   copy.
2. A drift / packaging check fails CI with a clear message stating that events must be
   consumed via the `spec_kitty_events` PyPI package only.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The CLI MUST internalize, into CLI-owned modules, every behavior currently obtained from `spec_kitty_runtime` that is required to execute `spec-kitty next` and mission execution. | Required |
| FR-002 | The CLI MUST remove every production-code import of `spec_kitty_runtime` (i.e. every `from spec_kitty_runtime ...` or `import spec_kitty_runtime` outside `tests/`). | Required |
| FR-003 | The CLI MUST remove the vendored / mirrored `spec-kitty-events` tree from production package paths (specifically `src/specify_cli/spec_kitty_events/`) and from the wheel build configuration. | Required |
| FR-004 | The CLI MUST consume events behavior only through public imports rooted at `spec_kitty_events` (the PyPI package), never through `specify_cli.spec_kitty_events.*`. | Required |
| FR-005 | The CLI MUST consume tracker behavior only through public imports rooted at `spec_kitty_tracker` (the PyPI package); CLI-internal `specify_cli.tracker` adapters MAY remain, but they must not re-export tracker public surface from a different namespace. | Required |
| FR-006 | The CLI's `pyproject.toml` MUST NOT list `spec-kitty-runtime` as a runtime dependency, optional dependency, or tool source. | Required |
| FR-007 | The CLI's `pyproject.toml` MUST list `spec-kitty-events` and `spec-kitty-tracker` using compatible-range constraints (e.g. `>=X,<Y` matching documented compatibility), not exact `==X.Y.Z` pins. | Required |
| FR-008 | Exact pinned versions for events / tracker MUST live in `uv.lock` (and any other lockfile artifacts), not in `pyproject.toml`. | Required |
| FR-009 | The CLI MUST add consumer tests that pin the events public-surface and tracker public-surface contracts the CLI actually uses, so upstream contract changes break this test suite explicitly. | Required |
| FR-010 | The CLI MUST add a clean-install CI verification job that creates a fresh virtual environment, installs CLI without `spec-kitty-runtime`, and runs `spec-kitty next` against a fixture mission, asserting the loop advances and emits status events. | Required |
| FR-011 | The CLI MUST add an architectural enforcement test (using the existing `pytestarch` infrastructure per ADR 2026-03-27-1) that fails when any production module imports `spec_kitty_runtime`. | Required |
| FR-012 | The CLI MUST add a drift / packaging check that fails when `src/specify_cli/spec_kitty_events/` reappears in production package paths. | Required |
| FR-013 | The CLI MUST update `[tool.uv.sources]` so editable / path overrides for `spec-kitty-events` and `spec-kitty-tracker` are not committed in production configuration; any developer-only overrides must live in a separate, uncommitted (or explicitly dev-marked) configuration. | Required |
| FR-014 | The CLI MUST update release docs (`docs/release/*`, `CHANGELOG.md`, README install instructions) and drift checks so they no longer encode exact sibling-package release gates for events / tracker / runtime. | Required |
| FR-015 | The CLI MUST update CLAUDE.md and any operator-facing migration documentation to document the new boundary: events / tracker are external PyPI dependencies, runtime is internal, and `spec-kitty-runtime` is no longer required. | Required |
| FR-016 | Test fixtures that intentionally exercise migration / removal assertions MAY reference `spec_kitty_runtime` only when (a) the file is under `tests/`, (b) the import is inside a clearly named migration / removal assertion fixture, and (c) the fixture is time-bound by a comment naming the mission slug and the cutover removal milestone. | Required |
| FR-017 | The CLI MUST keep `spec-kitty next --agent <name>` end-to-end behavior unchanged for the user across the cutover (same step advancement semantics, same status event shapes, same exit codes). | Required |
| FR-018 | The CLI MUST update every CLI-source consumer of vendored events imports (`specify_cli.spec_kitty_events.*` callers in `src/specify_cli/decisions/emit.py`, `src/specify_cli/glossary/events.py`, `src/specify_cli/sync/diagnose.py`, and any others) to use `spec_kitty_events.*` public imports. | Required |
| FR-019 | The CLI MUST verify, via at least one packaging / build test, that the wheel artifact does not ship the `specify_cli/spec_kitty_events/` tree in production package paths after the cutover. | Required |
| FR-020 | The CLI MUST emit, where feasible without re-introducing runtime imports, a single one-time operator notice on first post-cutover invocation if `spec-kitty-runtime` is still installed in the user's environment, pointing them at the migration doc. | Required |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for new CLI-internal runtime modules introduced by this mission. | ≥90% line coverage on each new module, per the project charter `pytest` coverage gate. | Required |
| NFR-002 | Type safety of new and modified production code. | `mypy --strict` passes with zero new errors on changed files. | Required |
| NFR-003 | `spec-kitty next` end-to-end latency for a single step in the clean-install fixture verification. | No regression > 20% versus pre-cutover baseline measured on the same fixture. | Required |
| NFR-004 | Clean-install CI job runtime budget. | ≤5 minutes including venv creation, install, and one fixture-mission step. | Required |
| NFR-005 | Lockfile reproducibility. | `uv.lock` resolves deterministically from `pyproject.toml` + a fresh `uv lock --check` run, with zero diff. | Required |
| NFR-006 | Architectural enforcement runtime. | The `pytestarch` rule that forbids `spec_kitty_runtime` production imports must run in the fast / unit gate (≤30s) so CI catches regressions early. | Required |
| NFR-007 | Documentation surface change scope. | All operator-facing docs that mention the retired hybrid model must be updated; zero stale references to "install spec-kitty-runtime" remain in `docs/` or `README.md`. | Required (verifiable via grep gate) |

## Constraints

| ID | Constraint | Rationale |
|----|-----------|-----------|
| C-001 | The CLI MUST NOT import `spec_kitty_runtime` from any production code path. | The package is retiring; importing it re-creates the cross-package release lockstep that PR #779 was rejected for. |
| C-002 | The CLI MUST NOT vendor or mirror `spec-kitty-events` source under any production package path. | The events package is the canonical PyPI contract; vendoring forks the contract and breaks downstream operators. |
| C-003 | The CLI MUST NOT introduce a new private re-export of tracker public surface. | The tracker SDK is the contract; private re-exports invite drift and reintroduce the same hybrid pattern. |
| C-004 | `pyproject.toml` MUST NOT pin events or tracker to an exact version (`==X.Y.Z`). | Exact pins create cross-package release lockstep; lockfiles are the right place for exact pins. |
| C-005 | Editable / path / git overrides for events or tracker MUST NOT be committed in the production `pyproject.toml`. | Editable overrides are a dev convenience; committing them breaks PyPI installs. |
| C-006 | Test fixtures that reference `spec_kitty_runtime` MUST be quarantined under `tests/` and time-bound by an explicit comment naming the cutover mission slug. | Without quarantine, "test imports" silently become "production imports" again. |
| C-007 | The cutover MUST be a single mission landing on `main`; partial / reverted cutovers re-create the rejected hybrid state. | PR #779 was rejected for shipping a partial cutover. |
| C-008 | Agent surface configs (`.claude`, `.cursor`, `.gemini`, `.kilocode`, etc.) MUST NOT be touched by this mission except where the source-template change forces a regenerated copy. | These are generated copies; agent-surface drift is a separate mission concern. |
| C-009 | The mission MUST integrate with existing module boundaries in `src/specify_cli/` rather than introducing a new top-level package; CLI-internal runtime code lives under `src/specify_cli/next/` (or a clearly scoped sibling module) using existing module conventions. | The repo has ~80 prior missions; new top-level packages explode review surface. |
| C-010 | Existing infrastructure (`Dockerfile.web`, `Makefile`, CI configuration) MUST keep working post-cutover. | These are operator-facing surfaces; breakage means a regression for everyone running the CLI today. |
| C-011 | Cross-package version compatibility ranges MUST follow the documented public-surface contract from `spec-kitty-events/docs/public-surface.md` and the equivalent tracker contract; the CLI does not invent its own compatibility window. | The shared-package program's whole point is that contracts are owned upstream. |

## Key entities

- **CLI runtime (internal)** — CLI-owned modules under `src/specify_cli/` that provide
  the runtime behavior previously obtained from `spec_kitty_runtime`. After the
  cutover, this is the only runtime the CLI uses.
- **Events public surface** — the import surface rooted at `spec_kitty_events` (PyPI),
  documented in `spec-kitty-events/docs/public-surface.md`.
- **Tracker public surface** — the import surface rooted at `spec_kitty_tracker`
  (PyPI), documented in the tracker repo's public-surface docs.
- **CLI consumer test contract** — the consumer-test suite this mission adds, that
  pins the subset of events / tracker public surface CLI actually uses, so upstream
  contract changes break the suite intentionally rather than silently.
- **Clean-install verification job** — a CI job that installs CLI in a fresh venv
  without `spec-kitty-runtime` and runs `spec-kitty next` against a fixture mission.
- **Architectural enforcement test** — a `pytestarch`-based test that forbids
  `spec_kitty_runtime` production imports.
- **Drift / packaging check** — a build-time check that the wheel artifact and source
  tree do not contain a vendored events tree.

## Acceptance criteria

A1. `spec-kitty next` runs successfully against a fixture mission from a clean install
of CLI without `spec-kitty-runtime` installed (covered by FR-010, FR-017).

A2. CLI package metadata (`pyproject.toml`) does not list `spec-kitty-runtime` as a
dependency in any form (covered by FR-006).

A3. CLI runtime code has zero production imports from `spec_kitty_runtime` (covered by
FR-002, FR-011).

A4. CLI code imports events through `spec_kitty_events` public PyPI imports and
tracker through `spec_kitty_tracker` public PyPI imports; no production module imports
either through a vendored or re-exported namespace (covered by FR-003, FR-004, FR-005,
FR-018).

A5. Consumer tests cover the events and tracker contract surface CLI flows actually
use, and these tests fail explicitly when the upstream contract changes (covered by
FR-009).

A6. CI passes without shared-package drift failures caused by the old hybrid model;
the clean-install job and architectural enforcement test both pass (covered by FR-010,
FR-011, FR-014).

A7. Lockfiles (`uv.lock`, `constraints.txt` if present) carry exact pins; `pyproject.toml`
carries compatible-range constraints (covered by FR-007, FR-008).

A8. Release docs, CHANGELOG, README, and CLAUDE.md no longer instruct operators to
install `spec-kitty-runtime` and document the new boundary (covered by FR-014, FR-015,
NFR-007).

A9. The mission lands as a single change on `main`; the hybrid model is not preserved
mid-flight (covered by C-007).

## Assumptions

- The runtime repo's mission `runtime-standalone-package-retirement-01KQ20Z8` has, by
  the time this mission lands, completed its public-API inventory, and that inventory
  is the authoritative list of behavior CLI must internalize.
- The events repo at sha `81d5ccd4` is the source of truth for the events public
  surface; CLI consumes only what `docs/public-surface.md` documents.
- The tracker repo's public-surface contract from
  `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` is stable enough at implement-review
  time to pin compatibility ranges in CLI's `pyproject.toml`. If tracker's contract
  shifts before this mission lands, the plan's rebase / sync step picks up the change.
- Operators upgrading from a pre-cutover release accept a one-version migration step
  documented in `CHANGELOG.md`; existing installations of `spec-kitty-runtime` remain
  installable but unused after the cutover.
- The CLI's existing `pytestarch` infrastructure (per ADR 2026-03-27-1) is the right
  enforcement layer for the architectural rule that forbids `spec_kitty_runtime`
  production imports.
- The repo's `Makefile`, `Dockerfile.web`, and CI configuration accept new test jobs
  (clean-install verification) without architectural changes.

## Risks

| ID | Risk | Mitigation |
|----|------|------------|
| R-1 | The runtime public-API surface this mission must internalize is larger than the implement-review inventory suggests, blocking the cutover mid-flight. | Plan WPs in dependency order so the largest surface (engine, planner, schema) is internalized first, behind a feature-flagged switch, and tracked against the upstream inventory. |
| R-2 | Removing the vendored events tree breaks a hidden internal consumer not surfaced by import grep. | Add a packaging test that builds the wheel and runs the existing test suite against it, plus the clean-install verification job, before merging. |
| R-3 | Compatible-range constraints in `pyproject.toml` are too loose and pull in an incompatible events / tracker release at install time. | Pair the range with the consumer-test contract (FR-009) so any incompatible upstream release breaks CI explicitly; tighten the range only when the contract regresses. |
| R-4 | A future contributor reintroduces a hybrid pattern (re-export, conditional import) and the architectural test misses it. | The architectural rule must check (a) `spec_kitty_runtime` production imports, (b) `specify_cli.spec_kitty_events` re-introduction, and (c) tracker re-export from a CLI namespace; all three are enforced. |
| R-5 | The clean-install job is slow / flaky and gets disabled. | NFR-004 caps runtime at ≤5 minutes; the job uses cached wheels where possible; flakiness is treated as a P0 mission-blocker per existing CI hardening missions (`080-ci-hardening-and-lint-cleanup`). |
| R-6 | Editable overrides leak into committed `pyproject.toml` (the same failure mode that contributed to PR #779). | Add a CI gate that fails when `[tool.uv.sources]` contains a path/editable entry for `spec-kitty-events` or `spec-kitty-tracker` on the production-config path. |

## Success criteria (measurable)

- 100% of CLI production modules import zero symbols from `spec_kitty_runtime`,
  measured by the new architectural enforcement test.
- 0 files under `src/specify_cli/spec_kitty_events/` after merge (the directory is
  removed from the production tree).
- The clean-install CI job advances `spec-kitty next` by at least one step against the
  fixture mission, in ≤5 minutes wall-clock, on every PR.
- Consumer-test suite breakage rate when upstream events / tracker ship a contract
  change: 100% (it is the entire point of the consumer tests).
- Operator-visible install command after merge: `pip install spec-kitty-cli` (no
  separate `pip install spec-kitty-runtime` step), confirmed by README and CHANGELOG.

## Cross-repo coordination

- This mission depends on the events repo at `81d5ccd4` already merged on main —
  satisfied at planning time.
- This mission depends on the tracker repo's implement-review mission landing before
  this mission's implement phase reaches the consumer-test WP. If tracker has not
  landed when CLI reaches that WP, the mission pauses that WP and proceeds with
  others; the orchestrator picks the work back up when tracker is green.
- This mission depends on the runtime repo's implement-review mission having published
  its public-API inventory before this mission's first internalization WP. If the
  inventory is incomplete, this mission's WPs treat the inventory as the contract
  and file deltas against the runtime mission rather than expanding scope locally.

## Definition of Done

- All FRs marked Required are implemented and verified in tests.
- All NFR thresholds are met or have documented, reviewed exceptions.
- All Constraints hold on `main` after merge.
- All Acceptance criteria pass.
- The mission lands as a single change on `main` and the prior hybrid PR (#779) is
  formally superseded in the closing PR description.
