# Implementation Plan — Charter Golden-Path E2E (Tranche 1)

| Field | Value |
|---|---|
| Mission ID | `01KQ806XN4TTJRAQGZWVPQP7V7` |
| Mission slug | `charter-golden-path-e2e-tranche-1-01KQ806X` |
| Mission type | `software-dev` |
| Branch — current | `test/charter-e2e-827-tranche-1` |
| Branch — planning / base | `test/charter-e2e-827-tranche-1` |
| Branch — final merge target | `test/charter-e2e-827-tranche-1` |
| `branch_matches_target` | true |
| Date | 2026-04-27 |
| Spec | [spec.md](./spec.md) |
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/cli-flow-contract.md](./contracts/cli-flow-contract.md) |
| Quickstart | [quickstart.md](./quickstart.md) |
| Primary issue | https://github.com/Priivacy-ai/spec-kitty/issues/827 |
| Parent epic | https://github.com/Priivacy-ai/spec-kitty/issues/461 |

## Summary

Deliver a single product-repo, public-CLI E2E test (`tests/e2e/test_charter_epic_golden_path.py`) plus one new fresh-project fixture in `tests/e2e/conftest.py`. The test drives the operator path through `spec-kitty init → charter interview → generate → bundle validate → synthesize (--adapter fixture) → status → lint → agent mission create → setup-plan → seed → finalize-tasks → next (issue) → next (advance) → retrospect summary` against a temp project outside the source checkout, and asserts the source checkout is byte-identical before and after.

The test pins to the `software-dev` composed mission (per resolved DM-01KQ80QCTTFP9KJZTFTQY363QJ), uses `--adapter fixture` for `synthesize` (deviation from `start-here.md`'s recommended flow, documented under spec FR-021 — see research.md R-002), and proves the spine without calling any forbidden private helper (`decide_next_via_runtime`, `_dispatch_via_composition`, `StepContractExecutor`, `run_terminus`, `apply_proposals`).

## Technical Context

| Aspect | Value |
|---|---|
| Language/Version | Python 3.11+ (existing project requirement) |
| Primary dependencies | `pytest`, `subprocess` (stdlib), `pathlib` (stdlib), `json` (stdlib); existing test helpers (`tests/conftest.py::run_cli`, `tests/test_isolation_helpers.py::run_cli_subprocess`) |
| Storage | filesystem only (per project standards); test writes only inside `tmp_path` |
| Testing | `pytest` with `@pytest.mark.e2e` + `@pytest.mark.slow`; existing `e2e-cross-cutting` CI lane |
| Target platform | Linux + macOS (CI runners and developer machines) |
| Project type | Single project (CLI tool); test asset added under `tests/e2e/` |
| Performance goal | ≤ 180 s wall-clock per run, median across 5 runs (NFR-001) |
| Constraints | Fully offline (NFR-005); no SaaS sync; `mypy --strict` + `ruff` green (NFR-003) |
| Scale/scope | One test file (~250–400 LOC estimate) + ~50–80 LOC of fixture additions in `tests/e2e/conftest.py` |

No `[NEEDS CLARIFICATION]` markers. All ambiguities resolved during Phase 0 research (research.md R-001..R-010).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter exists at `.kittify/charter/charter.md`; loaded via `spec-kitty charter context --action plan`.

### Charter directives applicable to this mission

| ID | Title | How this plan complies |
|---|---|---|
| **DIRECTIVE_003** | Decision Documentation Requirement | Two material decisions are recorded with full context: DM-01KQ807NKAS36HJPG6WBQN5C6G (fresh-project fixture choice) and DM-01KQ80QCTTFP9KJZTFTQY363QJ (single-mission pin vs. fallback chain). Each has a resolved answer and rationale. Research findings R-001..R-010 are also recorded as durable context. |
| **DIRECTIVE_010** | Specification Fidelity Requirement | Plan + research + contract derive directly from spec FRs/NFRs/Cs. The one documented deviation from `start-here.md` (R-002, `synthesize --adapter fixture`) is recorded as a finding under spec FR-021 with explicit PR-disclosure obligation. |

### Charter policy summary check

| Charter requirement | Compliance |
|---|---|
| `pytest` for testing | ✓ — test uses pytest with `@pytest.mark.e2e` + `@pytest.mark.slow`. |
| `mypy --strict` must pass | ✓ — NFR-003 makes this a delivery gate; verified in quickstart command 3. |
| 90%+ test coverage for new code | ✓ — the deliverable IS the test; coverage tooling does not apply to the test itself, but the test itself is the coverage instrument for the Charter epic operator path. |
| Integration tests for CLI commands | ✓ — this test is precisely an integration / E2E test against the public CLI surface. |

### Charter-related open gaps

None. All directives and policy items are covered.

### Re-check after Phase 1 design

Re-evaluated after writing data-model.md, contracts/cli-flow-contract.md, and quickstart.md. No new gaps surfaced. Charter Check still passes.

## Project Structure

### Documentation (this feature)

```
kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/
├── spec.md                # /spec-kitty.specify output
├── plan.md                # this file
├── research.md            # Phase 0 output
├── data-model.md          # Phase 1 output
├── quickstart.md          # Phase 1 output
├── contracts/
│   └── cli-flow-contract.md  # Phase 1 output — public CLI contract for the test
├── checklists/
│   └── requirements.md    # /spec-kitty.specify quality checklist (passing)
├── decisions/
│   ├── DM-01KQ807NKAS36HJPG6WBQN5C6G.md   # fixture choice (resolved)
│   └── DM-01KQ80QCTTFP9KJZTFTQY363QJ.md   # mission strategy (resolved)
├── meta.json
└── tasks/
    └── README.md          # placeholder; tasks.md created by /spec-kitty.tasks
```

### Source code (repository root) — files added or touched

```
tests/
└── e2e/
    ├── conftest.py                              # MODIFIED: add fresh_e2e_project fixture (additive only)
    └── test_charter_epic_golden_path.py         # NEW: the golden-path E2E test
```

No production source files are added or modified by this mission. No `src/specify_cli/` files are touched. No CI workflow files are touched (the test rides the existing `e2e-cross-cutting` lane via its `@pytest.mark.e2e` + `@pytest.mark.slow` markers, per spec C-007).

**Structure decision.** Single-project layout. The deliverable is a test asset; it lives under `tests/e2e/` alongside `test_cli_smoke.py` and shares the same `e2e-cross-cutting` CI lane.

## Phase 0 Outline (research.md)

Phase 0 is complete. See [research.md](./research.md) for the full record. Highlights:

- **R-001** pins the composed mission to `software-dev`.
- **R-002** documents the `--adapter fixture` deviation from `start-here.md`.
- **R-003** locks the public-CLI mission scaffolding flow (`agent mission create / setup-plan / finalize-tasks`).
- **R-004** documents `next` issue + advance shape, including FR-014/015/016 verification owed at implementation time.
- **R-005** specifies the two-layer source-checkout pollution guard (git-status + path-inventory).
- **R-006** confirms `run_cli` (60 s per-call timeout, isolated env) is the right harness.
- **R-007** specifies the `fresh_e2e_project` fixture shape (init → git init → spec-kitty init → commit; no `.kittify` copy).
- **R-008** locks `retrospect summary --project <temp> --json` as the retrospect call.
- **R-009** is the premortem: six sabotage attempts and their defences.
- **R-010** enumerates what is explicitly out of Phase 0 scope.

All `NEEDS CLARIFICATION` items are resolved before Phase 1.

## Phase 1 Outline (data-model.md, contracts/, quickstart.md)

Phase 1 is complete. See [data-model.md](./data-model.md), [contracts/cli-flow-contract.md](./contracts/cli-flow-contract.md), and [quickstart.md](./quickstart.md).

- **data-model.md** describes the test-visible entities (E-001 temp project, E-002 source-checkout pollution baseline, E-003 lifecycle record file, E-004 mission handle), the JSON envelope expectations per CLI command, allowed mission-state transitions (read-only assertions), and four invariants (I-001..I-004).
- **contracts/cli-flow-contract.md** is the authoritative contract between the test and the public CLI. It enumerates the forbidden surface (C-001/C-002), the allowed in-flow subprocess invocations with expected exit codes and post-state, the failure-diagnostics contract (FR-019), and explicit non-contract behaviours the test must NOT depend on.
- **quickstart.md** gives a reviewer the exact three commands to validate the deliverable, restates which Charter epic surfaces are under coverage, restates what is out of scope, and surfaces the documented `--adapter fixture` deviation.

## Premortem Summary

Per the `premortem-risk-identification` tactic, six failure modes are identified and defended (full table in research.md R-009):

1. Future change to `init` adds a hidden interactive prompt → defended by `run_cli` 60 s per-call timeout + diagnostics in assertion message.
2. Future change to `synthesize --adapter fixture` removes the offline path → surfaces as product finding via FR-021.
3. `next` quietly returns `blocked` without an action field → FR-015 splits acceptable outcomes; FR-008 catches missing fields.
4. Stray write to source-checkout `profile-invocations` masked by `.gitignore` → defended by R-005 layer 2 (path inventory, not just `git status`).
5. Test author imports a forbidden private helper "for convenience" → defended by C-001/C-002; optional polish: scan test file imports.
6. Lifecycle record `action` is a role-default verb (`analyze`/`audit`) instead of the issued step → FR-016 explicit comparison vs. issued step ID.

## Risks and follow-ups (Eisenhower-style)

| Item | Importance | Urgency | Disposition |
|---|---|---|---|
| Live-CLI envelope shapes for charter commands not yet observed in detail | High | Medium | Implementer verifies during coding; widens/narrows assertions per actual envelope; records mismatches under FR-021. |
| `next` envelope's prompt-file field name is unconfirmed | High | Medium | Implementer prints first `next --json` envelope at debug verbosity to lock the field name once; then asserts on it. |
| Future `software-dev` mission scaffolding regression could break the test for the right reasons | High | Low | This is the desired behaviour, not a risk to mitigate. The test failing loudly here is the operator-path proof working. |
| `.kittify/events/profile-invocations/` writer behaviour for `software-dev` `specify` step not yet observed | Medium | Medium | Implementer confirms at impl time; adjusts assertion if writer skips a record. |
| New fixture extracts `--ai codex` only; if codex agent install changes, the fixture needs to follow | Medium | Low | Acceptable; matches `start-here.md` recommendation. |

## Implementation phasing

This plan ends at Phase 1. The next phase is task generation via `/spec-kitty.tasks`, which the user must invoke explicitly. The expected work-package decomposition (advisory only, NOT prescriptive — `/spec-kitty.tasks` is authoritative):

- Likely one work package: write the fresh-project fixture + the golden-path test together, since they are tightly coupled, the test is the only consumer of the fixture, and shipping them in two passes adds no review value.

## Complexity Tracking

No Charter Check violations; this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| _none_ | _n/a_ | _n/a_ |

## Branch contract (repeat #2 — final report)

- Current branch: `test/charter-e2e-827-tranche-1`
- Planning / base branch: `test/charter-e2e-827-tranche-1`
- Final merge target: `test/charter-e2e-827-tranche-1`
- `branch_matches_target`: true ✓
- Branch strategy summary (verbatim from `setup-plan --json`): "Current branch at workflow start: test/charter-e2e-827-tranche-1. Planning/base branch for this feature: test/charter-e2e-827-tranche-1. Completed changes must merge into test/charter-e2e-827-tranche-1."
