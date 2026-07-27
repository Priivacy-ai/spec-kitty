# Charter Golden-Path E2E (Tranche 1)

| Field | Value |
|---|---|
| Mission ID | `01KQ806XN4TTJRAQGZWVPQP7V7` |
| Mission slug | `charter-golden-path-e2e-tranche-1-01KQ806X` |
| Mission type | `software-dev` |
| Branch (planning, base, target) | `test/charter-e2e-827-tranche-1` |
| Primary issue | https://github.com/Priivacy-ai/spec-kitty/issues/827 |
| Parent epic | https://github.com/Priivacy-ai/spec-kitty/issues/461 |
| Created | 2026-04-27 |

## Purpose

**TLDR.** Prove the shipped Charter epic works through public CLI from a fresh project, with no source-checkout pollution.

**Context.** Issue #827 needs a deterministic operator-path E2E spine before the rest of the P0/P1/P2 matrix can be built on top. This tranche delivers one product-repo test that drives Charter setup, bundle validation, synthesis, status, lint, mission advancement via `spec-kitty next`, and retrospect summary — all through public commands — and asserts the source checkout is unchanged afterward, so future tranches can extend the spine without fighting hidden helpers.

## User Scenarios & Testing

### Primary actor

A Spec Kitty maintainer or a CI runner executing the product test suite. They consume the test as evidence that the Charter epic still works the way an external operator uses it.

### Primary scenario (happy path)

1. The maintainer / CI runner runs `pytest tests/e2e/test_charter_epic_golden_path.py`.
2. The test materialises a **fresh project** at a temp path that lives **outside** the source checkout, performs `git init`/config, and seeds it solely via public CLI: `spec-kitty init . --ai codex --non-interactive`.
3. The test exercises Charter setup as an operator would, in order: charter interview (`--profile minimal --defaults --json`), charter generate (`--from-interview --json`), charter bundle validate (`--json`), charter synthesize (`--dry-run --json`), charter synthesize (`--json`), charter status (`--json`), charter lint (`--json`).
4. The test scaffolds the smallest deterministic composed mission (preference order: `software-dev` → `documentation` → minimal custom mission that still walks the public runtime composition path), then advances it: `spec-kitty next --agent test-agent --mission <handle> --json`, then `spec-kitty next --agent test-agent --mission <handle> --result success --json`.
5. The test runs `spec-kitty retrospect summary --json` against the temp project and parses the returned envelope.
6. The test compares a `git status --short` snapshot of the source checkout taken before step 2 against one taken after step 5 and asserts they match exactly.

### Primary exception (acceptable structured outcome)

If a public CLI step legitimately produces a documented non-error structured block — for example, `next --result success` reports an intentional missing guard artifact for the chosen mission — the test accepts that outcome and asserts the structured shape, **without** swallowing real product regressions. Any failure that would only pass by monkeypatching the dispatcher, step contract executor, DRG resolver, or frozen-template loader is reported as a test failure with full diagnostics (see FR-019).

### Always-true invariants

- The test only exercises **public** CLI surfaces. It does not import or call `decide_next_via_runtime`, `_dispatch_via_composition`, `StepContractExecutor`, `run_terminus`, `apply_proposals`, or any other private helper.
- The temp project lives **outside** the source checkout for every assertion.
- After the test finishes (pass **or** fail), the source checkout has zero new or modified tracked / untracked files in `kitty-specs/`, `.kittify/`, `.worktrees/`, `docs/`, `profile-invocations/`, or any other path inside the source repo.
- The new test is marked `@pytest.mark.e2e` and `@pytest.mark.slow`.

## Domain Language

| Canonical term | Meaning | Avoid as synonym |
|---|---|---|
| **Operator path** | The sequence of public `spec-kitty` CLI commands an external user runs | "agent path", "internal flow" |
| **Private helper** | Any in-process Python function not exposed via the published CLI | "internal API", "utility" |
| **Guard artifact** | A file or state the runtime requires before it will advance an action via `next` | "input artifact", "precondition file" |
| **Lifecycle record** | A paired pre/post entry in `.kittify/events/profile-invocations/*.jsonl` for an issued action | "event line", "log entry" |
| **Source checkout** | The repository working tree that contains the test code itself | "main repo", "repo root" |
| **Fresh project** | A temp directory initialized from scratch via `spec-kitty init`, never via fixture-copy of `.kittify` | "scaffold project", "blank project" |

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | A new test file `tests/e2e/test_charter_epic_golden_path.py` SHALL exist and SHALL be marked `@pytest.mark.e2e` and `@pytest.mark.slow`. | Approved |
| FR-002 | The test SHALL drive the entire scenario through public CLI subprocess invocations, reusing the existing isolation helpers (`tests/conftest.py::run_cli` and `tests/test_isolation_helpers.py::run_cli_subprocess`). | Approved |
| FR-003 | The test SHALL use a new fresh-project fixture (e.g. `fresh_e2e_project`) added to `tests/e2e/conftest.py` that initializes a temp project from scratch via `spec-kitty init . --ai codex --non-interactive`, rather than copying `.kittify` from the source checkout. | Approved |
| FR-004 | The test SHALL execute, in order: `init`, `charter interview --profile minimal --defaults --json`, `charter generate --from-interview --json`, `charter bundle validate --json`, `charter synthesize --dry-run --json`, `charter synthesize --json`, `charter status --json`, `charter lint --json`. | Approved |
| FR-005 | The test SHALL choose the smallest deterministic composed mission that exercises the public runtime / `next` composition path (preference order: `software-dev` → `documentation` → minimal custom mission) and SHALL document the chosen mission in the test file. | Approved |
| FR-006 | The test SHALL issue exactly one composed action via `spec-kitty next --agent test-agent --mission <handle> --json`, and SHALL advance that action via `spec-kitty next --agent test-agent --mission <handle> --result success --json`. | Approved |
| FR-007 | The test SHALL run `spec-kitty retrospect summary --json` against the temp project and SHALL parse the returned envelope. | Approved |
| FR-008 | The test SHALL assert that every `--json` output produced by an expected-success command is parseable JSON and contains the documented public field names for that command. | Approved |
| FR-009 | The test SHALL assert that `.kittify/charter/charter.md` exists in the temp project after the charter generate step. | Approved |
| FR-010 | The test SHALL assert that `charter bundle validate --json` reports a success / compliance state. | Approved |
| FR-011 | The test SHALL assert that `charter synthesize --dry-run --json` reports planned work and does NOT mutate `.kittify/doctrine` in the temp project. | Approved |
| FR-012 | The test SHALL assert that `charter synthesize --json` writes `.kittify/doctrine` and provenance / manifest state in the temp project. | Approved |
| FR-013 | The test SHALL assert that `charter status --json` reports a non-error state and that `charter lint --json` exits successfully or returns a documented warning-only status; warnings MUST NOT be silently downgraded. | Approved |
| FR-014 | The test SHALL assert that the issued step from `next --json` exposes a non-null prompt-file path when the public JSON exposes a prompt-file field. | Approved |
| FR-015 | The test SHALL assert that `next --result success` either advances exactly one action OR returns a documented structured block describing an intentionally missing guard artifact for the chosen mission. | Approved |
| FR-016 | The test SHALL assert that `.kittify/events/profile-invocations/*.jsonl` in the temp project contains paired pre/post lifecycle records for the issued action, and that the recorded action name equals the actual mission step / action name (not a role-default verb such as `analyze` or `audit`, unless the step is literally `audit`). | Approved |
| FR-017 | The test SHALL capture a baseline snapshot of `git status --short` in the source checkout before any temp-project work begins, and SHALL assert the post-test value matches the baseline. | Approved |
| FR-018 | The test SHALL additionally assert that no new or modified files appear inside the source checkout under `kitty-specs/`, `.kittify/`, `.worktrees/`, `docs/`, or any `profile-invocations/` path, even if `.gitignore` would mask them from `git status`. | Approved |
| FR-019 | On any subprocess failure, the test SHALL include in the assertion message the command, cwd, return code, stdout, and stderr; and MAY render a compact (non-recursive-by-default) tree of the temp project. | Approved |
| FR-020 | The fresh-project fixture SHALL clean up its temp directory after the test, regardless of pass or fail. | Approved |
| FR-021 | If the public CLI surface differs from the recommended flow (different flag names, missing public alternative for a step, etc.), the test SHALL be adjusted to use the actual public surface, and the deviation SHALL be recorded in the PR description as a finding. | Approved |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The test SHALL complete on a current CI runner within a deterministic budget. | ≤ 180 seconds wall-clock per run, median across 5 consecutive runs. | Approved |
| NFR-002 | The test SHALL be deterministic across runs on the same commit. | 0 spurious failures across 20 consecutive local runs on a clean source checkout. | Approved |
| NFR-003 | The test code SHALL pass the project's standard quality gates. | `uv run ruff check tests/e2e/test_charter_epic_golden_path.py tests/e2e/conftest.py` exits 0; `uv run mypy --strict tests/e2e/test_charter_epic_golden_path.py` exits 0. | Approved |
| NFR-004 | The test SHALL be diagnosable on first failure without rerunning. | A single failed run captures command, cwd, return code, stdout, and stderr for the failing step in the assertion message. | Approved |
| NFR-005 | The test SHALL operate fully offline. | Zero outbound network calls; `SPEC_KITTY_ENABLE_SAAS_SYNC` is not set; "Not authenticated, skipping sync" or equivalent benign output is acceptable. | Approved |
| NFR-006 | The new test SHALL coexist with the existing E2E and integration regression slices. | Running `uv run pytest tests/e2e/ tests/next/ tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q` on the branch passes with no previously-green test newly failing. | Approved |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | The test MUST NOT call any private helper, including but not limited to `decide_next_via_runtime`, `_dispatch_via_composition`, `StepContractExecutor`, `run_terminus`, and `apply_proposals`. | Approved |
| C-002 | The test MUST NOT monkeypatch the dispatcher, step contract executor, DRG resolver, or frozen-template loader to make the flow pass. | Approved |
| C-003 | The test MUST NOT modify the existing `e2e_project` fixture or the existing `tests/e2e/test_cli_smoke.py` legacy smoke behaviour. | Approved |
| C-004 | The test MUST NOT use deprecated hidden CLI aliases when a public alternative exists. | Approved |
| C-005 | The test MUST NOT depend on SaaS sync, hosted auth, or remote tracker connectivity. | Approved |
| C-006 | All files written by the test MUST live under the temp project directory. Nothing may be written into the source checkout, including under ignored paths inside the source checkout. | Approved |
| C-007 | The test file's pytest markers MUST place it in the existing `e2e-cross-cutting` CI lane, OR the PR MUST explicitly propose and justify a different gate. | Approved |
| C-008 | The deliverables of this tranche are limited to (a) the new test file and (b) minimal additive helpers / fixtures in `tests/e2e/conftest.py`. No production behaviour changes, unless the E2E exposes a real blocking bug — in which case the bug is reported and tracked as a follow-up rather than fixed inside this tranche. | Approved |
| C-009 | The test MUST NOT silently skip locally or in CI when it cannot establish a fresh project; if a public CLI command required by the flow cannot run from a fresh project, the test fails loudly and the failure is escalated as a product finding. | Approved |

## Success Criteria

- **SC-001** A maintainer running the verification commands listed in `start-here.md` from a clean checkout of `test/charter-e2e-827-tranche-1` sees the new golden-path test pass with exit code 0.
- **SC-002** After the test passes, `git status --short` in the source checkout shows zero new or modified entries.
- **SC-003** A reviewer can read the PR description and find: which public CLI commands the golden path executes, which Charter epic surfaces are covered by this tranche, which #827 items remain for follow-up, whether any product defects were discovered while writing the E2E, and the exact verification commands and results.
- **SC-004** The new test runs alongside the existing E2E suite without breaking any previously-green test in `tests/e2e/`, `tests/next/`, `tests/integration/test_documentation_runtime_walk.py`, or `tests/integration/test_research_runtime_walk.py`.
- **SC-005** A subsequent tranche of #827 can extend this spine (additional missions, dashboard coverage, plain-English scenarios, external canaries) without first having to refactor this tranche's test to use private helpers.

## Key Entities

- **Temp project** — a per-test directory outside the source checkout where the entire operator-path scenario plays out.
- **Fresh-project fixture** — the new pytest fixture in `tests/e2e/conftest.py` that builds the temp project from `spec-kitty init`, never via fixture-copy of `.kittify` from the source checkout.
- **Source-pollution baseline** — the `git status --short` snapshot captured in the source checkout before the test runs; the post-test snapshot must equal this baseline.
- **Lifecycle record file** — `.kittify/events/profile-invocations/*.jsonl` in the temp project; each issued action produces a paired pre/post entry whose action name matches the actual mission step.
- **Mission handle** — the value passed to `spec-kitty next --mission <handle>`; may be `mission_id` (ULID), `mid8`, or `mission_slug`. Resolver disambiguates by `mission_id`; ambiguity is a structured error, not a silent fallback.

## Assumptions

- **Default test agent identifier** is `test-agent`, matching the flow shape recommended in `start-here.md`.
- **Default charter interview profile** is `minimal` with `--defaults`, yielding a deterministic charter for any project that does not require human-supplied governance content.
- The chosen composed mission can be advanced through at least one `next` issue + result cycle without requiring large generated content. If the preferred `software-dev` mission requires more artifact scaffolding than is reasonable here, the test falls back to `documentation`, then to a minimal custom mission, in that order — and the final choice is documented in the test.
- The existing subprocess isolation pattern (`run_cli` / `run_cli_subprocess`) is sufficient for CLI invocations in this tranche; no new isolation helper is required.
- The `e2e-cross-cutting` CI lane currently runs tests marked `@pytest.mark.e2e` + `@pytest.mark.slow`. If that mapping has changed, the PR notes will document the corrected gate (per C-007).
- `SPEC_KITTY_ENABLE_SAAS_SYNC` is **not** set during this test; charter / next / retrospect paths are exercised in their local-only mode.

## Out of Scope (this tranche)

- External canaries living in the `spec-kitty-end-to-end-testing` repo.
- Plain-English scenarios in `spec-kitty-plain-english-tests`.
- Full CLI subprocess walks for every built-in mission type.
- Browser- or dashboard-level coverage of Charter surfaces.
- Any production behaviour rewrite, **unless** the E2E exposes a blocking bug whose minimum fix is also in scope; that case is called out explicitly in the PR.
- Retrospective coverage beyond a single `retrospect summary --json` invocation.
- Multi-mission or multi-action runtime walks.

## Decisions

- **DM-01KQ807NKAS36HJPG6WBQN5C6G — Resolved.** Use a new `fresh_e2e_project` fixture (option A). The existing `e2e_project` fixture, which copies `.kittify` from the source checkout, is **not** acceptable for this tranche. Reusing it would weaken the operator-path proof and preserve the exact class of hidden-coupling failures the tranche is meant to surface.

No open `[NEEDS CLARIFICATION]` markers.
