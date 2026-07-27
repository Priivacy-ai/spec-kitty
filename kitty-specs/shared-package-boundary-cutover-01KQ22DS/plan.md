# Implementation Plan: Shared Package Boundary Cutover

**Branch contract**: planning/base `main` → merge target `main` (single branch; no divergence)
**Date**: 2026-04-25
**Spec**: [./spec.md](./spec.md)
**Mission ID**: `01KQ22DSP6D1F7QCF7N87T8B66` · **mid8**: `01KQ22DS`
**Change mode**: `code_change` (not bulk-edit; no single string is renamed across many files — this is a structural cutover with import-path changes touching ≤8 source consumers)
**Trackers**:
- [Priivacy-ai/spec-kitty#781](https://github.com/Priivacy-ai/spec-kitty/issues/781) — CLI: cutover to shared package boundary
- [Priivacy-ai/spec-kitty-events#16](https://github.com/Priivacy-ai/spec-kitty-events/issues/16)
- [Priivacy-ai/spec-kitty-tracker#12](https://github.com/Priivacy-ai/spec-kitty-tracker/issues/12)
- [Priivacy-ai/spec-kitty-runtime#16](https://github.com/Priivacy-ai/spec-kitty-runtime/issues/16)
**Supersedes**: [Priivacy-ai/spec-kitty#779](https://github.com/Priivacy-ai/spec-kitty/pull/779) (rejected for preserving the hybrid model)
**Cross-repo upstream**:
- `spec-kitty-events`: mission `events-pypi-contract-hardening-01KQ1ZK7` — merged on main at sha `81d5ccd4`
- `spec-kitty-tracker`: mission `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` — implement-review (in flight)
- `spec-kitty-runtime`: mission `runtime-standalone-package-retirement-01KQ20Z8` — implement-review (in flight)

---

## Summary

This mission completes the cutover to the shared package boundary defined by the
upstream events / tracker / runtime missions. After it lands:

- The CLI repository **owns its own runtime** for `spec-kitty next` and mission
  execution. Every behavior currently obtained from `from spec_kitty_runtime ...` is
  replaced by a CLI-internal module under `src/specify_cli/next/_internal_runtime/`.
- The CLI **consumes events as an external PyPI package**: every consumer imports
  `spec_kitty_events.*`. The vendored tree at `src/specify_cli/spec_kitty_events/` is
  removed from production package paths.
- The CLI **consumes tracker as an external PyPI package**: imports remain rooted at
  `spec_kitty_tracker.*`; consumer tests pin the contract surface CLI flows actually
  use.
- Package metadata, lockfiles, drift checks, release docs, and CI reflect the new
  boundaries: compatible-range constraints in `pyproject.toml`, exact pins in
  `uv.lock`, no `[tool.uv.sources]` editable / path entries on the production config
  path, no `spec-kitty-runtime` dependency anywhere.
- A clean-install CI verification proves `spec-kitty next` runs against a fixture
  mission in a fresh venv without `spec-kitty-runtime` installed.
- An architectural enforcement test (`pytestarch` per ADR 2026-03-27-1) fails when any
  production module re-introduces a `spec_kitty_runtime` import.

This mission deliberately does **not** preserve the hybrid model that PR #779 was
rejected for. The cutover is a single mission landing on `main`.

## Technical Context

**Language/Version**: Python 3.11+ (existing CLI charter requirement).
**Primary Dependencies (post-cutover)**:
- Runtime production: `typer`, `rich`, `pygments`, `httpx[socks]`, `platformdirs`,
  `readchar`, `truststore`, `pyyaml`, `ruamel.yaml`, `pydantic`, `packaging`,
  `psutil`, **`spec-kitty-events`** (compatible range, e.g. `>=4.0.0,<5`),
  **`spec-kitty-tracker`** (compatible range, e.g. `>=0.4,<0.5`), `websockets`,
  `toml`, `filelock`, `requests`, `transitions`, `jsonschema`, `python-ulid`,
  `google-re2`, `cryptography`.
- **Removed**: every direct or transitive runtime path that requires
  `spec-kitty-runtime` at production import time. The PyPI distribution may still be
  installable in a user's environment; it is simply no longer imported.
- Test/lint: existing — `pytest`, `pytestarch` (per ADR 2026-03-27-1), `mypy --strict`,
  `ruff`, `respx`, `diff-cover`, `build` (for wheel packaging tests).

**Storage**: Filesystem only. No on-disk schema changes. Run state continues to live
under `.kittify/runtime/runs/<run_id>/` exactly as `runtime_bridge.py` writes it
today; the only difference is who owns the code that writes it.

**Testing**:
- New `tests/contract/spec_kitty_events_consumer/` and
  `tests/contract/spec_kitty_tracker_consumer/` consumer-test packages pin the
  events / tracker public-surface contracts the CLI actually uses.
- New `tests/architectural/test_shared_package_boundary.py` extends the existing
  `pytestarch` infrastructure (per ADR 2026-03-27-1) to assert (a) no production
  module imports `spec_kitty_runtime`, (b) no production module imports
  `specify_cli.spec_kitty_events.*`, (c) tracker is consumed only via
  `spec_kitty_tracker.*`.
- New `tests/integration/test_clean_install_next.py` documents the clean-install
  contract; the actual CI gate runs in a fresh venv via a new GitHub Actions job.
- New `tests/contract/test_packaging_no_vendored_events.py` builds the wheel and
  asserts the wheel does not contain `specify_cli/spec_kitty_events/` paths.

**Target Platform**: Developer machines and CI (Linux + macOS).
**Project Type**: Single Python package (CLI). Top-level `src/` layout under
`specify_cli`, `kernel`, `doctrine`, `charter`, plus the new
`src/specify_cli/next/_internal_runtime/` module added by this mission.

**Performance Goals**:
- `spec-kitty next` end-to-end latency: no regression > 20% versus pre-cutover
  baseline measured against the same fixture (NFR-003).
- Clean-install CI job: ≤5 minutes wall-clock end-to-end (NFR-004).
- New `pytestarch` rule runs in the fast / unit gate in ≤30 seconds (NFR-006).

**Constraints**:
- C-001..C-011 from `spec.md`. The hard ones the plan must structurally enforce:
  - **C-001**: zero `spec_kitty_runtime` production imports.
  - **C-002**: no vendored `spec-kitty-events` tree under production paths.
  - **C-007**: cutover lands as a single mission on `main`.
  - **C-009**: integrate with existing `src/specify_cli/` module conventions; do
    **not** add a new top-level package. The internalized runtime lives at
    `src/specify_cli/next/_internal_runtime/` (sibling of the existing
    `runtime_bridge.py`, decision builder, prompt builder) so the existing layer
    rules continue to apply unchanged.
  - **C-011**: compatibility ranges follow upstream public-surface docs.

**Scale/Scope**:
- 7 production source files import `spec_kitty_runtime` today (ranged across
  `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/cli/commands/next_cmd.py`)
  — total ~8 import sites to rewrite, plus all internal call sites of those imports.
- 7 production files import the vendored events tree (`src/specify_cli/decisions/emit.py`,
  `src/specify_cli/glossary/events.py`, `src/specify_cli/sync/diagnose.py`, plus
  internal references inside the vendored tree itself).
- ~14 test files import `spec_kitty_runtime`; all are quarantined to migration /
  removal-assertion fixtures or rewritten to use the internalized runtime.
- 4 test files import the vendored events tree; all rewritten to use the public
  package.
- 1 `pyproject.toml` change (deps + uv.sources + classifiers stay).
- 1 `uv.lock` regeneration.
- 1 `constraints.txt` update (or removal — see research.md decision).
- 4 new CI artifacts:
  1. `tests/architectural/test_shared_package_boundary.py`
  2. `tests/contract/test_packaging_no_vendored_events.py`
  3. `tests/contract/spec_kitty_events_consumer/`
  4. `tests/contract/spec_kitty_tracker_consumer/`
- 1 new GitHub Actions job (clean-install verification) added to `ci-quality.yml`.
- Updates to `CHANGELOG.md`, `README.md`, `CLAUDE.md`, and `docs/development/`
  references that mention installing `spec-kitty-runtime`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-evaluated after Phase 1 design.*

| Directive / Policy | Applies? | Compliance plan |
|---|---|---|
| **DIRECTIVE_003** — Decision Documentation | Yes | Three material decisions captured in `research.md` and referenced from this plan: (1) internalized-runtime location (`src/specify_cli/next/_internal_runtime/`), (2) compatibility-range strategy for events/tracker, (3) clean-install CI implementation strategy. ADR `2026-04-25-1-shared-package-boundary.md` records the cross-cutting boundary decision. |
| **DIRECTIVE_010** — Specification Fidelity | Yes | All 20 FRs, 7 NFRs, and 11 constraints in `spec.md` map to WPs in `tasks.md` after `/spec-kitty.tasks`. FR-to-WP coverage verified by `/spec-kitty.analyze` before merge. |
| **DIRECTIVE_035** — Bulk-edit classification | No | Mission is `change_mode: code_change`. No single identifier / string is renamed across many files. Import-path rewrites are import-target changes (e.g. `from spec_kitty_runtime import X` → `from specify_cli.next._internal_runtime import X`) limited to ≤8 production import sites; the bulk-edit gate's classification table does not apply. Confirmed via the bulk-edit detection rule in `/spec-kitty.specify`. |
| **Charter test coverage ≥ 90%** on new code | Yes | Applies to `src/specify_cli/next/_internal_runtime/` and to the consumer-test contract modules. Wheel-shape and clean-install assertions are exercised by full-path fixture / build tests. |
| **`mypy --strict` must pass** | Yes | All new modules ship with full type annotations; CI's existing strict gate enforces. |
| **Integration tests for CLI commands** | Yes | The clean-install verification job is itself the canonical integration test for `spec-kitty next` post-cutover. Existing `tests/next/test_next_command_integration.py` is rewritten against the internalized runtime. |
| **Terminology canon** | Yes | All new artifacts use **Mission**, **Work Package**, **Internalized Runtime**, **Public Surface**, **Consumer Test**, **Clean-install Verification**. |
| **Architectural ADR 2026-03-27-1 (pytestarch)** | Yes | The `pytestarch` infrastructure is the enforcement layer for C-001 / C-002. The new architectural test extends the existing `_DEFINED_LAYERS` model with rules that target external package names (`spec_kitty_runtime`) rather than internal layers. |

**Result**: GATE PASSES. No exceptions filed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/shared-package-boundary-cutover-01KQ22DS/
├── plan.md              # This file
├── spec.md              # Mission specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1: structural model of the cutover
├── quickstart.md        # Phase 1: how to verify the cutover locally
├── contracts/
│   ├── events_consumer_surface.md   # Pinned events public-surface subset
│   ├── tracker_consumer_surface.md  # Pinned tracker public-surface subset
│   └── internal_runtime_surface.md  # Internalized runtime API contract
├── checklists/
│   └── requirements.md  # Spec validation checklist (already passes)
└── tasks/               # Created by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── next/
│   ├── __init__.py
│   ├── decision.py
│   ├── prompt_builder.py
│   ├── runtime_bridge.py            # rewritten: imports _internal_runtime, no spec_kitty_runtime
│   └── _internal_runtime/           # NEW — CLI-owned internalized runtime
│       ├── __init__.py              # public surface for next/runtime_bridge
│       ├── engine.py                # internalized snapshot reader (replaces spec_kitty_runtime.engine)
│       ├── planner.py               # internalized step planner (replaces spec_kitty_runtime.planner)
│       ├── schema.py                # internalized ActorIdentity, mission template loader
│       ├── models.py                # DiscoveryContext, MissionPolicySnapshot, MissionRunRef, NextDecision
│       ├── emitter.py               # NullEmitter and the runtime emitter Protocol
│       └── lifecycle.py             # next_step, provide_decision_answer, start_mission_run
├── cli/commands/
│   └── next_cmd.py                  # rewritten: imports _internal_runtime, no spec_kitty_runtime
├── decisions/
│   └── emit.py                      # rewritten: imports spec_kitty_events.* (PyPI package)
├── glossary/
│   └── events.py                    # rewritten: imports spec_kitty_events.* (PyPI package)
├── sync/
│   └── diagnose.py                  # rewritten: imports spec_kitty_events.* (PyPI package)
└── spec_kitty_events/               # REMOVED — vendored tree deleted from production tree

tests/
├── architectural/
│   └── test_shared_package_boundary.py   # NEW — pytestarch rules for C-001/C-002
├── contract/
│   ├── spec_kitty_events_consumer/       # NEW — events public-surface consumer tests
│   │   └── test_consumer_contract.py
│   ├── spec_kitty_tracker_consumer/      # NEW — tracker public-surface consumer tests
│   │   └── test_consumer_contract.py
│   └── test_packaging_no_vendored_events.py   # NEW — wheel-shape assertion
└── integration/
    └── test_clean_install_next.py        # NEW — local-runnable clean-install test
                                          #       paired with a CI job in ci-quality.yml

.github/workflows/
└── ci-quality.yml                        # extended: new clean-install job

pyproject.toml                            # rewritten: compatible ranges, no editable sources
uv.lock                                   # regenerated
constraints.txt                           # removed or rewritten — see research.md
CHANGELOG.md                              # documents migration
README.md                                 # documents new install command surface
CLAUDE.md                                 # documents new boundary
docs/development/mission-next-compatibility.md   # rewritten or marked historical
docs/development/mutation-testing-findings.md    # references updated
```

**Structure Decision**: The cutover lives entirely under `src/specify_cli/`. No new
top-level package is introduced. The internalized runtime is a new module
`src/specify_cli/next/_internal_runtime/` colocated with the existing `next/`
runtime-bridge code, so the established layer rules from
`tests/architectural/test_layer_rules.py` continue to apply unchanged. The
underscore prefix marks the module as CLI-internal: it is not part of the public
CLI Python import surface, even though it is shipped in the wheel.

## Phase 0: Research outline

The research log lives at [./research.md](./research.md). It resolves three open
questions before implementation begins:

1. **R0-1**: Where exactly should the internalized runtime live, and what is its
   import surface?
2. **R0-2**: What is the compatibility range strategy for events / tracker, given
   the upstream missions still in flight?
3. **R0-3**: How does the clean-install CI job structurally guarantee absence of
   `spec-kitty-runtime`?

## Phase 1: Design outputs

- `data-model.md` — structural model of the cutover (what existed pre-cutover, what
  exists post-cutover, what the call graph looks like).
- `contracts/events_consumer_surface.md` — the exact subset of
  `spec_kitty_events.*` symbols CLI uses; consumer tests pin these.
- `contracts/tracker_consumer_surface.md` — the exact subset of
  `spec_kitty_tracker.*` symbols CLI uses; consumer tests pin these.
- `contracts/internal_runtime_surface.md` — the exact API the new
  `_internal_runtime` module exposes to `runtime_bridge.py` and `next_cmd.py`,
  matching what was previously imported from `spec_kitty_runtime`.
- `quickstart.md` — local verification recipe (build wheel in a fresh venv, run
  `spec-kitty next` against the fixture mission, assert no `spec-kitty-runtime` is
  installed).

## Implementation phasing (high-level — WPs land in `/spec-kitty.tasks`)

The mission breaks into ~9 work packages that **must** land in dependency order so
the hybrid state never appears on `main`:

| WP | Title | Depends on | Rationale |
|----|-------|------------|-----------|
| WP01 | Internalize runtime surface (engine, planner, schema, lifecycle) into `src/specify_cli/next/_internal_runtime/` | — | Foundation: the new code must exist before any consumer can switch to it. Behavior equivalence proven against current `spec_kitty_runtime` v0.4.3 via golden snapshot fixtures captured in this WP. |
| WP02 | Cut over `runtime_bridge.py` and `next_cmd.py` to `_internal_runtime` (FR-001, FR-002) | WP01 | Removes the only production importers of `spec_kitty_runtime` in one atomic change. |
| WP03 | Add architectural enforcement test (`pytestarch`) for C-001 (no `spec_kitty_runtime` production imports) (FR-011) | WP02 | Locks the boundary. If a future commit reintroduces the import, CI fails. |
| WP04 | Migrate events consumers to public `spec_kitty_events.*` imports (FR-004, FR-018) | — (parallel with WP01) | The 3 production consumers (`decisions/emit.py`, `glossary/events.py`, `sync/diagnose.py`) and 4 test files switch in lockstep. Fully parallel with the runtime track. |
| WP05 | Remove vendored `src/specify_cli/spec_kitty_events/` tree and update wheel build (FR-003, FR-019) | WP04 | Removal happens only after every consumer is on the public package. |
| WP06 | Add packaging / drift assertion: wheel must not contain `specify_cli/spec_kitty_events/` (FR-019, FR-012) | WP05 | Locks the deletion. |
| WP07 | Add events + tracker consumer-test contracts (FR-009) | WP04, WP02 | Pins the public-surface subset CLI uses; consumer tests fail intentionally on upstream contract change. Tracker consumer test uses the published `spec-kitty-tracker` 0.4.x line and accepts the in-flight upstream mission's contract delta on rebase. |
| WP08 | Update `pyproject.toml` (drop hybrid notes, add compatible ranges, remove editable `[tool.uv.sources]`), regenerate `uv.lock`, decide `constraints.txt` fate (FR-006, FR-007, FR-008, FR-013) | WP02, WP05 | Metadata change must follow the source change so partial states never appear on `main`. |
| WP09 | Add clean-install CI verification job + local test (FR-010) | WP08 | Runs only after metadata reflects the new boundary. |
| WP10 | Documentation cutover: CHANGELOG, README, CLAUDE.md, `docs/development/*.md`, supersede note in PR #779 (FR-014, FR-015, NFR-007) | WP02..WP09 | Operator-facing docs land last so the migration story is accurate. |

WPs ship in two parallel lanes during implementation:
- **Lane A (runtime track)**: WP01 → WP02 → WP03
- **Lane B (events track)**: WP04 → WP05 → WP06
- **Convergence**: WP07 (depends on both lanes), WP08, WP09, WP10 ship serially.

This is the lane structure `tasks-finalize` will produce; the actual numbering and
exact dependencies are confirmed in `/spec-kitty.tasks`.

## Risks and mitigations (from spec, refined here)

| Risk | Mitigation |
|------|------------|
| R-1 (runtime surface larger than expected) | WP01 captures golden snapshots from current `spec_kitty_runtime` 0.4.3 against the reference fixture mission; any behavior delta caught by snapshot comparison forces the surface to be expanded inside WP01 before WP02 starts. |
| R-2 (hidden internal events consumer) | WP05 deletion is gated by WP04 grep + import-graph audit + wheel build test. WP06 packaging assertion locks the deletion. |
| R-3 (compatible ranges too loose) | WP07 consumer tests pin the public-surface subset. Range tightening is a one-line `pyproject.toml` change protected by the consumer-test gate. |
| R-4 (future hybrid regression) | WP03 enforces zero `spec_kitty_runtime` imports; WP06 enforces zero vendored events tree; WP07 catches re-export attempts via consumer-test contract. |
| R-5 (clean-install CI flakiness) | WP09 caps job at 5 minutes (NFR-004), uses uv-cached wheels where possible, and treats flakiness as a P0 blocker per existing CI hardening missions. |
| R-6 (editable overrides leak in) | WP08 removes the existing `spec-kitty-events = { path = "../spec-kitty-events", editable = true }` entry. WP03's pytestarch test set is extended with a config-shape assertion that `[tool.uv.sources]` does not contain a path entry for events or tracker on the production path. |

## Decisions log

| Decision | Choice | Reasoning | Captured in |
|----------|--------|-----------|-------------|
| Internalized runtime location | `src/specify_cli/next/_internal_runtime/` | Colocated with existing `runtime_bridge.py`; respects existing layer rules; no new top-level package. | research.md R0-1 |
| Internalized runtime public surface | Mirrors what `runtime_bridge.py` and `next_cmd.py` import today (`DiscoveryContext`, `MissionPolicySnapshot`, `MissionRunRef`, `NextDecision`, `NullEmitter`, `next_step`, `provide_decision_answer`, `start_mission_run`, `engine._read_snapshot`, `planner.plan_next`, `schema.ActorIdentity`, `schema.load_mission_template_file`) | Direct call-site driven; no scope expansion. | contracts/internal_runtime_surface.md |
| Events / tracker compatibility ranges | `spec-kitty-events>=4.0.0,<5.0.0`, `spec-kitty-tracker>=0.4,<0.5` | Aligns with upstream events SemVer policy from `events-pypi-contract-hardening-01KQ1ZK7`; tracker mission is in flight, so range is conservative until that mission's contract is finalized. | research.md R0-2 |
| `[tool.uv.sources]` policy | Empty in committed `pyproject.toml`; developer overrides documented in `docs/development/local-overrides.md` (new) | Editable overrides committed today are exactly the pattern PR #779 was rejected for. | research.md R0-2 |
| `constraints.txt` fate | Removed | The constraint existed to paper over the `spec-kitty-runtime` transitive events pin conflict. Once `spec-kitty-runtime` is no longer a dependency, the constraint is no longer needed. | research.md R0-2 |
| Clean-install CI mechanism | New job in `ci-quality.yml` running in a fresh `python:3.12-slim` container with `uv pip install spec-kitty-cli` against the built wheel | Avoids reusing the main test environment that has dev overrides; structurally proves clean-install works. | research.md R0-3 |
| Hybrid-model superseding | This mission's closing PR description names PR #779 explicitly as superseded. | Keeps governance graph traceable. | plan.md, spec.md DoD |

## Complexity tracking

No charter violations to justify. No exception filings.

## Branch contract (restated)

- Current branch at plan start: `main`
- Planning / base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: true

This mission lands as a single PR on `main`.

## Stop point

Plan and Phase 1 design artifacts are complete. The next supported step is
`/spec-kitty.tasks` to generate the WP outline.
