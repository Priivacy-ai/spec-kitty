# Implementation Plan: Mutant Slaying in Core Packages

**Branch**: `feature/711-mutant-slaying` | **Date**: 2026-04-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/mutant-slaying-core-packages-01KPNFQR/spec.md`

## Summary

Kill the assertion-strength gaps surfaced by the 2026-04-20 whole-`src/` mutmut run. Work is test-only: new or strengthened `pytest` cases in `tests/specify_cli/compat/`, `tests/kernel/`, `tests/doctrine/`, and `tests/charter/`, plus narrow `# pragma: no mutate` annotations on equivalent-mutant lines. No production-code refactors; no public-API changes; no CI integration. Execution is phased across three waves (P1 compat+kernel → P2 doctrine core → P3 charter core), each shipping one or more PRs onto the mission branch. Reviewers validate kills via commit-message mutant-ID citations and pattern-name callouts, not by re-running mutmut.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase — no new language requirement).
**Primary Dependencies**: `mutmut>=3.5.0`, `pytest>=9.0.3`, `pytest-timeout>=2.2.0` (all already in `[project.optional-dependencies.test]`). No new runtime dependencies. No new test-side dependencies.
**Storage**: Filesystem only. Test sources under `tests/`. Mutmut sandbox under `mutants/` (gitignored). Durable results cached per-file in `mutants/**/*.meta` (JSON with `exit_code_by_key`). Residual findings appended to `docs/development/mutation-testing-findings.md`.
**Testing**: pytest for unit/integration tests; mutmut for assertion-strength measurement. Patterns sourced from `src/doctrine/styleguides/shipped/mutation-aware-test-design.styleguide.yaml` (Boundary Pair, Non-Identity Inputs, Bi-Directional Logic). Workflow from `src/doctrine/tactics/shipped/mutation-testing-workflow.tactic.yaml`. Operator reference in `src/doctrine/toolguides/shipped/PYTHON_MUTATION_TOOLS.md`.
**Target Platform**: Linux (primary) and macOS (supported) developer machines. mutmut requires `fork()` — Windows is not in scope for mutation runs, but test additions land uniformly (`pytestmark = pytest.mark.windows_ci` already handles Windows-specific test coverage elsewhere and is untouched by this mission).
**Project Type**: Single. Test-only. No source-code reorganisation; no new packages.
**Performance Goals**: NFR-004 — scoped re-run per sub-module completes in ≤ 15 min on 32-core / 16 GB dev hardware. NFR-007 — baseline refresh cadence ≤ 7 days for Phase 2/3 planning.
**Constraints**: C-001 local-only (no CI); C-002 migration packages excluded; C-003 no public-API changes; C-004 no stylistic refactors; C-005 no 100% chasing; C-006 `non_sandbox`/`flaky` marker discipline preserved; C-007 WP PRs land on `feature/711-mutant-slaying`, final mission PR targets `main`.
**Scale/Scope**: ~1,800 actionable survivors across 4 packages and 12 named sub-modules at baseline snapshot. Mission stops when per-sub-module score targets are met (≥ 80% core, ≥ 60% supporting) — not at zero survivors.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Mandatory directives (from `spec-kitty charter context --action plan`):

- **DIRECTIVE_001 (Architectural Integrity Standard)** — ✅ Mission does not introduce new architectural surface. Test additions live under `tests/` following the repo's existing test-organisation layout. No new modules, interfaces, or cross-layer dependencies.
- **DIRECTIVE_003 (Decision Documentation Requirement)** — ✅ Mission scope, stop conditions, and per-sub-module targets are recorded in `spec.md`. Residual-list decisions (why a survivor is accepted as equivalent) are documented inline (`# pragma: no mutate` + reason) and summarised in `docs/development/mutation-testing-findings.md` per WP.
- **DIRECTIVE_010 (Specification Fidelity Requirement)** — ✅ Per-WP acceptance requires the survivor count post-WP to match the spec's FR target. Deviations (e.g., a sub-module that cannot hit 60% without structural changes) require WP prompt amendment before merge.
- **DIRECTIVE_018 (Doctrine Versioning Requirement)** — ✅ The mission cites doctrine artefacts by their stable IDs (`tactic:mutation-testing-workflow`, `styleguide:mutation-aware-test-design`, `toolguide:python-mutation-tools`). Any modification of those artefacts during the mission requires ADR supersession (recorded in Dependencies).
- **DIRECTIVE_024 (Locality of Change)** — ✅ Test changes are scoped to the sub-module under test. WP boundaries prohibit cross-package churn; cross-package helper additions require explicit justification in the WP prompt.
- **DIRECTIVE_025 (Boy Scout Rule)** — ✅ Mission is itself a Boy Scout expansion of #711. WPs may take opportunistic cleanup in the test files they touch, but not in unrelated source files (C-004).
- **DIRECTIVE_028 (Efficient Local Tooling)** — ✅ Scoped `mutmut run "<sub-module>*"` plus `.meta` cache invalidation via per-file deletion satisfies the ≤ 15 min per-rerun budget (NFR-004). Toolguide documents the workflow.
- **DIRECTIVE_029 (Agent Commit Signing Policy)** — ✅ No changes to signing workflow. Commits follow the existing `Co-Authored-By` convention.
- **DIRECTIVE_030 (Test and Typecheck Quality Gate)** — ✅ Mission explicitly strengthens this gate by raising mutation score per-sub-module. NFR-005 keeps main-suite collection green throughout.
- **DIRECTIVE_031 (Context-Aware Design)** — ✅ Test conventions documented in `spec.md` (Test Annotation Conventions subsection) mirror the patterns already visible in `tests/specify_cli/compat/`, `tests/kernel/`, `tests/doctrine/`, and `tests/charter/`.
- **DIRECTIVE_032 (Conceptual Alignment)** — ✅ Every WP cites the `mutation-aware-test-design` styleguide pattern it applies; no bespoke assertion styles are introduced.
- **DIRECTIVE_033 (Targeted Staging Policy)** — ✅ Per-PR commits are scoped to the sub-module under test. Cross-module staging is prohibited.
- **DIRECTIVE_034 (Test-First Development)** — ✅ Core anchor of the mission. Kill-the-survivor work is test-first by construction — the survivor-mutant IS the failing specification the new test must kill.
- **DIRECTIVE_035 (Bulk-Edit Occurrence Classification)** — ✅ N/A; mission is not a bulk edit.
- **DIRECTIVE_036 (Black-Box Integration Testing)** — ✅ Compatible. Mutation-aware patterns apply to black-box and unit tests uniformly. Integration tests in `tests/specify_cli/cli/commands/` are partially in scope for kills where assertions match against observable CLI output; structural CLI tests that only assert exit codes are left as-is (the underlying logic tests carry the kill weight).
- **DIRECTIVE_037 (Living Documentation Sync)** — ✅ `docs/development/mutation-testing-findings.md` is updated at each phase boundary per SC-006. `CHANGELOG.md` is appended once at mission merge, not per WP.

**Conflicts / unjustified gates**: None. Charter check passes.

## Project Structure

### Documentation (this feature)

```
kitty-specs/mutant-slaying-core-packages-01KPNFQR/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — no open unknowns)
├── spec.md              # Input spec
├── meta.json            # Mission metadata (target_branch = feature/711-mutant-slaying)
├── checklists/
│   └── requirements.md  # Spec quality checklist (validated green)
├── status.events.jsonl  # Runtime status log
├── status.json          # Materialised status snapshot
└── tasks/               # Populated by /spec-kitty.tasks
    └── README.md
```

No `data-model.md`, `contracts/`, or `quickstart.md` will be produced — this mission introduces no new entities, no API surface, and no user-facing workflow. The `mutation-testing-workflow` tactic and `PYTHON_MUTATION_TOOLS` toolguide serve as the "quickstart" for contributors.

### Source Code (repository root)

Test-only changes in the four in-scope package trees. No new directories.

```
tests/
├── specify_cli/
│   └── compat/
│       ├── test_registry.py       # extended for Phase 1 survivors in _validate_entry,
│       │                          # _validate_canonical_import, _validate_version_order,
│       │                          # validate_registry, load_registry, RegistrySchemaError
│       └── test_doctor.py         # untouched unless Phase-1 survivor analysis extends here
├── kernel/
│   ├── test__safe_re.py           # extended for the 26 _safe_re survivors (Phase 1)
│   ├── test_paths.py              # extended for 17 paths survivors (Phase 1)
│   ├── test_atomic.py             # extended for 13 atomic survivors (Phase 1)
│   └── test_glossary_runner.py    # touched only if its 1 survivor is actionable
├── doctrine/
│   ├── test_resolver.py           # extended for resolver survivors (Phase 2)
│   ├── test_profile_repository.py # extended for agent_profiles survivors (Phase 2)
│   ├── test_mission_*.py          # extended for missions survivors (Phase 2)
│   └── ...                        # shared/, drg/, directives/ as prioritised
└── charter/
    ├── test_resolver.py           # extended for resolver survivors (Phase 3)
    ├── test_context.py            # extended (Phase 3; already has non_sandbox marker)
    ├── synthesizer/               # subdirectory — extended per sub-sub-module (Phase 3)
    └── evidence/                  # extended (Phase 3)

src/
├── specify_cli/compat/            # source — unchanged except for rare `# pragma: no mutate`
├── kernel/                        # source — unchanged except for rare `# pragma: no mutate`
├── doctrine/                      # source — unchanged except for rare `# pragma: no mutate`
└── charter/                       # source — unchanged except for rare `# pragma: no mutate`

docs/development/
└── mutation-testing-findings.md   # appended with per-phase snapshots and residual lists

mutants/                           # gitignored; local per-developer; .meta cache for scoped reruns
```

**Structure Decision**: Extend existing test-file hierarchy; no new test directories. Kill-the-survivor tests co-locate with the unit tests they supplement so that the full context of a sub-module's assertion coverage lives in one file. This mirrors `tests/specify_cli/compat/test_registry.py`'s existing pattern of grouping by source module rather than by concern.

## Complexity Tracking

No Charter Check violations. Section intentionally empty.

## Phase outputs

### Phase 0 — Research

See `research.md`. Minimal by design: every open question in this mission was resolved during the Intent Summary or by reference to existing doctrine. Only two research notes recorded:

1. **Residual list format** — decision: inline `# pragma: no mutate` annotation plus a per-WP bullet in `docs/development/mutation-testing-findings.md`. Rejected: per-WP YAML sidecar (format proliferation, tests/doctrine already carry enough YAML surface).
2. **Baseline re-sample trigger** — decision: manual `mutmut run` at each phase boundary, documented in the findings doc with a date. Rejected: automated cron (out of scope per C-001); rejected: tying to CI job (out of scope per ADR 2026-04-20-1).

### Phase 1 — Design & Contracts

**No data-model.md, no contracts/, no quickstart.md.** The mission's "design" is the test-file layout documented in the Source Code section above. Per-WP prompts (generated by `/spec-kitty.tasks` in a later step) will include:

- The dotted-name pattern for the mutmut scoped rerun (e.g., `specify_cli.compat*`).
- The list of survivor mutant IDs in scope for that WP, pulled from `mutmut results` at planning time.
- The target mutation-aware pattern(s) to apply.
- The residual-list guidance if the WP's sub-module will not hit target.

**Agent context update**: deferred — no new technologies, no new dependencies, no new architectural concepts. The agent context files (`CLAUDE.md`, etc.) already document mutmut via the earlier doctrine commit; no regeneration needed.

Re-evaluated Charter Check post-design: still passes. No new gates triggered.
