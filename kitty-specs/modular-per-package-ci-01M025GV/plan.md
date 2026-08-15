# Implementation Plan: Modular per-package CI + automated asset/prompt regeneration

**Branch**: `mission/modular-per-package-ci` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/modular-per-package-ci-01M025GV/spec.md`
**Research**: [research.md](./research.md) (Phase 0 — both load-bearing decisions settled)

## Summary

Extract `kernel`, `doctrine`, and `packs` into self-contained reusable workflows (`on: workflow_call`) invoked
as ordered `uses:` jobs inside `ci-quality.yml` (decision **D1(a)**), so each module has its own build boundary
while coverage still aggregates in one run and Sonar stays a single scan. In parallel, add a standalone
`spec-kitty regen [--check]` that regenerates the 168 committed generated fixtures (144 command baselines + 24
skill snapshots) from source templates, wire it into trust-tiered CI (same-repo auto-commit / fork check-only /
`regen`-label PAT-push), narrow the byte-grid gates to structural invariants + one canonical snapshot, and
re-home the completeness baselines to the module partition. Approach and evidence are settled in `research.md`.

## Technical Context

**Language/Version**: Python 3.11+ (CLI); GitHub Actions YAML (CI).
**Primary Dependencies**: typer, existing render surfaces (`render_command_template`, `command_renderer`);
GitHub Actions `workflow_call` / `pull_request_target`.
**Storage**: Filesystem fixtures under `tests/specify_cli/**`; committed workflow YAML under `.github/workflows/`.
**Testing**: pytest (targeted module packages per WP); GitHub Actions dry-runs via PRs; `ruff` + `mypy --strict`.
**Target Platform**: GitHub-hosted CI runners (Linux).
**Project Type**: single (CLI + CI infra).
**Performance Goals**: ci-quality wall-clock within ~5% of baseline (NFR-002); reusable workflows run same-run.
**Constraints**: preserve `coverage-*.xml` / `<slug>-reports` names (C-004); `quality-gate` stays the pinned
required check (C-005); no wheel-publish gate (C-002); Sonar scope unchanged (C-007); no red merge-blocking
gate (C-001).
**Scale/Scope**: 3 module workflows + 1 new CLI command + 1 CI automation workflow + gate narrowing + baseline
re-homing. ~5–6 work packages.

## Charter Check

*GATE: passed at plan time; re-check after design.*

- **Canonical sources (DIRECTIVE_044)**: reuse `render_command_template` / `command_renderer`; model `regen`
  on `spec-kitty doctrine regenerate-graph --check`; lift existing CI job bodies verbatim. ✅ no improvisation.
- **ATDD-first (C-011)**: every implementation WP lands a failing-first test (regen fidelity test, coverage
  aggregation assertion, check-only exit-code test) RED on base, GREEN on final commit. ✅ captured per-WP.
- **Red-main / no red gate (ADR 2026-07-17-1)**: new gates land green or non-blocking; the PAT-push workflow
  ships disabled until NFR-003 sign-off. ✅
- **Shared Package Boundary (ADR 2026-04-25-1)**: per-package `pyproject.toml`s stay dormant; no wheel-publish
  gate. ✅
- **Architectural gate discipline (DIRECTIVE_043)**: CI-model guards updated non-vacuously to understand
  `uses:` jobs; coverage-name preservation asserted by construction. ✅
- **Terminology canon**: Mission (not Feature); guard with `tests/architectural/test_no_legacy_terminology.py`
  before pushing prose/doctrine. ✅

## Project Structure

### Documentation (this mission)

```
kitty-specs/modular-per-package-ci-01M025GV/
├── plan.md              # This file
├── research.md          # Phase 0 (decisions settled)
├── data-model.md        # Entity sketch
├── research/            # evidence-log.csv, source-register.csv
├── spec.md              # Mission spec
└── tasks/               # Phase 2 (WP files) — created by /spec-kitty.tasks
```

### Source Code (repository root)

```
.github/workflows/
├── ci-quality.yml           # MODIFY: replace kernel/doctrine/packs job bodies with `uses:` callers
├── module-kernel.yml        # NEW: on: workflow_call — lifted kernel-tests steps
├── module-doctrine.yml      # NEW: on: workflow_call — doctrine fast + integration legs
├── module-packs.yml         # NEW: on: workflow_call — lifted fast-tests-corpus
└── regen-assets.yml         # NEW: trust-tiered regen automation

src/specify_cli/
├── cli/commands/regen.py    # NEW: `spec-kitty regen [--check] [--json]`
├── cli/commands/__init__.py # MODIFY: register regen alongside materialize
├── template/asset_generator.py     # REUSE: render_command_template()
└── skills/command_renderer.py      # REUSE: render().to_skill_md()
                                    # + NEW shared version-pin constants module

tests/
├── specify_cli/regression/         # twelve-agent gate + baselines (narrow + re-home)
├── specify_cli/skills/             # command_renderer gate + snapshots (narrow + re-home)
├── architectural/                  # CI-model guards (update for uses: jobs) + marker/collection oracles
└── specify_cli/cli/commands/       # NEW: test_regen.py
```

**Structure Decision**: single-project layout; CI infra under `.github/workflows/`, CLI under
`src/specify_cli/`, tests mirror source. No new top-level packages (per-package pyprojects stay dormant).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New privileged PAT secret (NFR-003) | Operator chose label→PAT-push fork UX for best contributor DevEx | Check-only-only rejected by operator; PAT is the only way to write to a fork branch from CI |
| First `workflow_call` files in repo | D1(a) requires reusable workflows; none exist yet | `workflow_run` (b) fragments Sonar single-run context — rejected in research |

## Implementation Concern Map

> Concerns are architectural areas, not WPs. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Kernel reusable-workflow POC + coverage-aggregation proof

- **Purpose**: Prove D1(a) end-to-end on the smallest package: kernel steps run inside a `workflow_call` file,
  coverage still aggregates in one run and reaches diff-coverage + the nightly Sonar scan.
- **Relevant requirements**: FR-001, FR-002; NFR-001, NFR-002; C-004, C-005.
- **Affected surfaces**: `.github/workflows/module-kernel.yml` (new), `ci-quality.yml` (kernel-tests job →
  `uses:` caller), the coverage-name preservation assertion.
- **Sequencing/depends-on**: none (first slice).
- **Risks**: required-check pinning (verify `quality-gate` is the pinned check); architectural CI-model guards
  may assume inline `steps:` — may need a small guard update even for the POC.

### IC-02 — Standalone regen tool + shared version pins

- **Purpose**: A single `spec-kitty regen [--check]` that regenerates the 168 fixtures from source, byte-identical
  to a `PYTEST_UPDATE_SNAPSHOTS=1` run, with a followable check-mode failure.
- **Relevant requirements**: FR-003, FR-004, FR-005; NFR-004, NFR-005; C-006.
- **Affected surfaces**: `src/specify_cli/cli/commands/regen.py` (new), `__init__.py` (register), new shared
  version-pin constants module, reuses `asset_generator.render_command_template` + `command_renderer.render`.
- **Sequencing/depends-on**: none (independent of the workflow split — can proceed in parallel with IC-01).
- **Risks**: version-pin asymmetry (3.1.2a3 vs 3.0.0) — must be reproduced exactly via the shared constants,
  proven by a fidelity test comparing regen output to a pytest-update run.

### IC-03 — Doctrine + packs reusable workflows + CI-model guard updates

- **Purpose**: Generalize the proven POC to doctrine (fast + integration legs) and packs (corpus group), and
  update the architectural guards that parse the job graph so they tolerate `uses:` caller jobs.
- **Relevant requirements**: FR-006, FR-007, FR-008; NFR-001; C-004.
- **Affected surfaces**: `module-doctrine.yml`, `module-packs.yml` (new); `ci-quality.yml`; the five CI-model
  guards (`test_ci_collection_completeness`, `test_ci_quality_path_filters`, `_gate_coverage`,
  `test_coverage_root_collisions`, `test_release_ci_ownership`).
- **Sequencing/depends-on**: IC-01 (mechanism validated).
- **Risks**: doctrine's two legs + any future sharding must keep coverage names unique; guard updates must stay
  non-vacuous.

### IC-04 — Trust-tiered regen CI automation

- **Purpose**: Keep fixtures fresh automatically per trust tier: same-repo/dispatch auto-commit, fork check-only,
  `regen`-label PAT-push into the fork branch.
- **Relevant requirements**: FR-009, FR-010, FR-011; NFR-003; C-003.
- **Affected surfaces**: `.github/workflows/regen-assets.yml` (new), modeled on `all-contributors-normalize.yml`.
- **Sequencing/depends-on**: IC-02 (the tool must exist).
- **Risks**: security — `pull_request_target` trusted-tooling pattern mandatory; PAT least-privilege; ship the
  PAT-push path disabled until the NFR-003 sign-off is recorded.

### IC-05 — Narrow the drift gates

- **Purpose**: Replace the 144+24 byte grid with structural invariants + one canonical snapshot per suite, so a
  one-line source edit stops fanning out to ~14 fixture failures.
- **Relevant requirements**: FR-012; SC-005.
- **Affected surfaces**: `test_twelve_agent_parity.py`, `test_command_renderer.py` (+ their fixtures).
- **Sequencing/depends-on**: IC-02 (regen proven equivalent first, so narrowing can't hide a real regression).
- **Risks**: narrowing must not lose real drift-detection coverage — keep the canonical snapshot + invariants
  strong enough that a genuinely wrong render still fails.

### IC-06 — Re-home completeness baselines to the module partition

- **Purpose**: Relocate golden-count ceilings, CI path filters, and marker/shard maps to match the module-owned
  split; ensure every relocated test resolves to exactly one CI home.
- **Relevant requirements**: FR-013.
- **Affected surfaces**: golden-count assertions, `ci-quality.yml` path filters, `tests/_shard_registry.py` /
  `_arch_shard_map.py` / `_next_shard_map.py`, marker/collection completeness oracles.
- **Sequencing/depends-on**: IC-03 + IC-05 (partition + gate shape final).
- **Risks**: the double-marker CI-home trap (`test_marker_job_completeness.py`) — a relocated test with no home
  or two homes reds; verify each relocation resolves to exactly one gate.
