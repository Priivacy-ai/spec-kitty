# Implementation Plan: Charter E2E #827 Follow-ups (Tranche A)

**Branch**: `fix/charter-e2e-827-followups` (to be created at `/spec-kitty.implement`) | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/charter-e2e-827-followups-01KQAJA0/spec.md`

## Summary

Close four #827 follow-up defects as one stabilization PR, in this fixed order: **#848 first** (review-gate hygiene — protects every other check), then **#844** (charter E2E mandates a real prompt file), **#845** (dossier snapshots stop self-blocking transitions), **#846** (specify/plan auto-commit is gated on substantive content). #847 is closed; the #822 stabilization backlog is excluded.

Engineering thesis: each defect is a **localized contract tightening**, not a redesign. The runtime architecture, lane state machine, merge engine, shared-package boundary, and dependency-management policy stay untouched. The fix patterns are: a new architectural pytest for #848; a non-null-and-resolvable assertion for #844 (the wire fields `prompt_file` / `prompt_path` already exist); a single explicit ownership policy + preflight exclusion for #845; and an "is this content substantive?" gate before auto-commit for #846.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, pytest-arch (for architectural tests), httpx/requests as already used. External shared packages: `spec-kitty-events`, `spec-kitty-tracker` (PyPI; pin contract governed by `uv.lock`).
**Storage**: Filesystem only. No database. `.kittify/` directory tree, `kitty-specs/` artifacts, `status.events.jsonl` event log.
**Testing**: pytest (existing). E2E suite at `tests/e2e/`, contract tests at `tests/contract/`, architectural tests at `tests/architectural/`, unit tests under `tests/specify_cli/`.
**Target Platform**: Cross-platform Python CLI (mac, Linux, Windows). No platform-specific code added by this mission.
**Project Type**: Single project (existing layout under `src/specify_cli/`). No new packages.
**Performance Goals**: New drift check (#848) must complete in < 5 seconds on a clean install (NFR-001). All other fixes are correctness-only — no performance budget changes.
**Constraints**: `mypy --strict` passes (NFR-004); existing coverage gate still met (NFR-004); all NFR-003 verification commands green on the merging branch.
**Scale/Scope**: Four issues, one PR. Touched code is concentrated in: `src/specify_cli/next/{decision,prompt_builder,runtime_bridge}.py`, `src/specify_cli/dossier/snapshot.py`, `src/specify_cli/cli/commands/agent/{mission,tasks}.py`, mission command templates under `src/specify_cli/missions/**/command-templates/`, doctrine assets under `src/doctrine/skills/spec-kitty-runtime-next/`, and tests under `tests/{e2e,contract,architectural,integration,specify_cli}/`. Estimated diff: low-hundreds of lines plus tests.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter context loaded via `spec-kitty charter context --action plan --json`. Active directives that bear on this plan:

- **DIRECTIVE_003 (Decision Documentation)** — every taste-call in this plan is documented in `research.md` with rationale and rejected alternatives.
- **DIRECTIVE_010 (Specification Fidelity)** — implementation must match the FRs/NFRs/Cs in `spec.md`. The "no dependency-management redesign" guardrail (C-004) is binding.
- Active tactics applied here: **adr-drafting-workflow** (each material decision gets an ADR-style block in `research.md`); **premortem-risk-identification** (Risks section below); **requirements-validation-workflow** (each FR is mapped to a verification path in `quickstart.md`).

**Quality bars** (from charter policy summary):
- pytest with 90%+ coverage for new code → applied to new architectural test, new commit-boundary guard, and new dossier-preflight regression.
- `mypy --strict` clean → no new untyped code paths.
- Integration tests for CLI commands → covered by `tests/integration -k 'specify or plan or auto_commit or mission'` and dossier tests.

**Charter-check verdict (pre-Phase-0):** PASS. No conflicts with active directives. No widening required.

## Project Structure

### Documentation (this feature)

```
kitty-specs/charter-e2e-827-followups-01KQAJA0/
├── plan.md              # This file
├── spec.md              # Mission specification (already committed)
├── research.md          # Phase 0 output — engineering decisions
├── data-model.md        # Phase 1 output — entities & invariants
├── quickstart.md        # Phase 1 output — verification walkthrough
├── contracts/           # Phase 1 output — wire/format contracts
│   ├── next-prompt-file-contract.md
│   ├── dossier-snapshot-ownership.md
│   └── specify-plan-commit-boundary.md
├── checklists/
│   └── requirements.md  # Already passing (from /spec-kitty.specify)
└── tasks.md             # Phase 2 output — created later by /spec-kitty.tasks
```

### Source Code (repository root)

The mission edits existing trees only. Concrete touched directories:

```
src/specify_cli/
├── next/
│   ├── decision.py            # Tighten prompt_file contract (#844)
│   ├── prompt_builder.py      # Already returns a Path; ensure callers cannot null it for kind=step
│   └── runtime_bridge.py      # Audit every site that constructs a step decision; require non-null prompt
├── dossier/
│   └── snapshot.py            # Apply chosen ownership policy (#845)
├── cli/commands/agent/
│   ├── mission.py             # Snapshot-write site + setup-plan auto-commit gating (#845, #846)
│   └── tasks.py               # move-task pre-flight: ignore dossier snapshot when applying chosen policy (#845)
├── missions/<mission-type>/command-templates/
│   ├── specify.md             # Substantive-content gate documented (#846)
│   └── plan.md                # Same (#846)
└── (no new packages)

src/doctrine/skills/spec-kitty-runtime-next/
└── SKILL.md                   # Remove any host guidance that legitimizes null prompts (#844)

tests/
├── e2e/
│   └── test_charter_epic_golden_path.py    # Tighten prompt assertion (#844)
├── architectural/
│   └── test_uv_lock_pin_drift.py           # NEW — drift detector (#848)
├── contract/
│   └── (existing tests stay; cross_repo_consumers smoke remains green)
├── integration/
│   ├── (new) test_dossier_snapshot_no_self_block.py  # #845 regression
│   └── (new) test_specify_plan_commit_boundary.py    # #846 regression
└── specify_cli/cli/commands/agent/
    └── (extend existing mission/tasks tests for the new behaviors)

docs/
└── development/
    └── review-gates.md        # NEW or updated — names the documented sync command (#848 / FR-002)
```

**Structure Decision**: keep the existing single-project layout. No new packages, no new top-level directories. New tests slot into existing `tests/architectural/`, `tests/integration/`, and `tests/e2e/` trees.

## Implementation Approach

### Issue #848 — `uv.lock` pin-drift detection (lands first)

- **Detection mechanism**: a new pytest at `tests/architectural/test_uv_lock_pin_drift.py` that (a) parses `uv.lock` to find the resolved version of `spec-kitty-events` (and any other shared package whose pin contract is governed by `uv.lock`), (b) inspects `importlib.metadata.version(...)` for the same packages installed in the venv, and (c) fails when they disagree, naming each offending package and including the documented sync command in the failure message.
- **Sync command**: `uv sync --frozen` (or `uv sync` if frozen is the wrong UX — confirmed by the existing `clean-install-verification` CI job which uses `uv sync --frozen`). Documented in `docs/development/review-gates.md` and printed in the test's failure output.
- **CI integration**: the new test runs alongside other architectural tests under `pytest tests/architectural`. The existing `clean-install-verification` workflow job continues to enforce the boundary in CI; the new test catches drift inside developer-laptop review-gate runs that may bypass the CI job.
- **Issue-matrix correction**: any row under `kitty-specs/**/issue-matrix.md` that says #848 is `verified-already-fixed` for environment hygiene is updated to reflect the real status (FR-003).
- **Scope guardrail (C-004)**: this is a single new test plus one doc page. No changes to `pyproject.toml` `[project.dependencies]` shape, no replacement of `uv.lock`, no new package-management abstractions.

### Issue #844 — Charter E2E mandates a real prompt file

- **Wire field**: keep both existing field names (`prompt_file` and `prompt_path`) — they already exist in `src/specify_cli/next/decision.py:61` and `src/specify_cli/next/runtime_bridge.py`. Choose `prompt_file` as the **canonical** public name; `prompt_path` continues to work as an alias (backwards-compat).
- **Tighten the contract** in `src/specify_cli/next/decision.py`:
  - For decisions with `kind == "step"` (composed step), `prompt_file` MUST be a non-empty string and MUST resolve to an existing file when serialized.
  - Validation runs at the point of envelope construction (e.g. when `to_dict()` / JSON emit happens). A `kind=step` with a missing prompt is a programmer error — the runtime returns `kind=blocked` with a reason instead.
- **Tighten E2E assertion** in `tests/e2e/test_charter_epic_golden_path.py` — replace the current "key exists" check with: for every issued decision where `kind == "step"`, assert (a) `prompt_file` (or `prompt_path`) is present, (b) the value is non-null and non-empty, and (c) `Path(value).is_file()` is true.
- **Doctrine**: scrub `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any inline comment in `src/specify_cli/next/decision.py:79` ("advance mode populates this") that legitimizes `null` for `kind=step`. Replace with: "null is only legal for non-`step` kinds; a `kind=step` envelope without a resolvable prompt is a runtime invariant violation".

### Issue #845 — Dossier snapshot ownership

- **Ownership policy chosen: EXCLUDE** the snapshot path from the worktree dirty-state pre-flight used by `agent tasks move-task` and related transitions. Rationale: `snapshot-latest.json` is named "latest" — it is inherently mutable and not a versioned artifact. Tracking it would create constant commit churn with zero review value. (See research.md for rejected alternatives.)
- **Implementation**:
  - Add `*/.kittify/dossiers/*/snapshot-latest.json` to `.gitignore` (root). This is sufficient if the dirty-state pre-flight uses `git status --porcelain` semantics that respect `.gitignore`.
  - In addition, the pre-flight code path in `src/specify_cli/cli/commands/agent/tasks.py` (and any helper in `src/specify_cli/status/` that drives transition pre-flight) explicitly filters paths matching the dossier-snapshot pattern when computing "is the worktree dirty for the purposes of this transition?". Belt-and-suspenders: the gitignore covers ad-hoc human use; the explicit filter covers any code path that sidesteps gitignore.
- **Regression coverage**: a new integration test at `tests/integration/test_dossier_snapshot_no_self_block.py` that (a) drives a mission command which writes `snapshot-latest.json`, (b) immediately invokes `agent tasks move-task` on the same WP/worktree, and (c) asserts the move-task call does **not** error with a self-inflicted dirty-state failure. The test exercises the exact path that previously blocked.

### Issue #846 — Specify/plan auto-commit boundary

- **"Substantive content" definition (operational)**: a spec.md (or plan.md) is substantive when **either** (a) its byte-length exceeds the byte-length of the canonical scaffold the create command writes by a fixed threshold (default: 256 bytes; tunable by config but with a sensible default), **or** (b) it contains all required mandatory sections expected for that artifact (spec: at minimum a non-empty Functional Requirements table; plan: at minimum a non-empty Technical Context section). Both checks are cheap, deterministic, and resistant to drift.
- **Implementation**:
  - Add a `_is_substantive(file_path: Path, kind: Literal["spec", "plan"]) -> bool` helper in `src/specify_cli/cli/commands/agent/mission.py` (or a new `src/specify_cli/missions/_substantive.py` if it grows).
  - In the auto-commit decision branch of `setup-plan` and the equivalent specify auto-commit branch, gate the commit on `_is_substantive(...)`. If false, do **not** auto-commit a "success" envelope — instead emit a documented prompt to the agent that the spec/plan needs substantive content before the workflow can advance.
  - Workflow status reporting (whatever `mission setup-plan --json` emits, plus the dashboard) treats a non-substantive-but-committed-scaffold state as **incomplete**, not "spec/plan ready".
- **Templates** under `src/specify_cli/missions/<mission-type>/command-templates/{specify,plan}.md` add an explicit "commit boundary" section so future agents understand why their empty-scaffold commit is being blocked.
- **Regression coverage**: a new integration test at `tests/integration/test_specify_plan_commit_boundary.py` that asserts (a) running specify-with-empty-content does not auto-commit a success state, (b) running specify with substantive content does auto-commit, and (c) workflow status correctly distinguishes the two.

### Suggested execution order (informational; lane plan is for `/spec-kitty.tasks`)

1. #848 — drift detector (lands first per operator instruction; protects all later runs).
2. #844 — prompt_file contract + E2E tightening.
3. #845 — dossier snapshot ownership + regression test.
4. #846 — specify/plan commit boundary + regression test.
5. PR closeout — issue references, status notes, verification command run.

`/spec-kitty.tasks` will translate this into work packages with explicit dependencies. Items 2/3/4 are independent in code-touch terms (different subsystems) and may be parallel lanes; item 1 is a strict prerequisite at PR-open time but not at branch-fork time.

## Risks & Premortem

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| #848 drift check is flaky on clean installs (false positive) | Medium | Medium | Add a `pytest.mark.skipif` for environments where `uv` is not on PATH; rely on `clean-install-verification` CI job for full enforcement. |
| #844 tightening breaks legitimate non-step decisions that currently emit `kind=step` with null prompt | Low | High | Audit every site in `src/specify_cli/next/runtime_bridge.py` that constructs a decision; convert any "step with no prompt" to `kind=blocked` with reason. Run `tests/next -q` and `tests/contract/test_next_no_implicit_success.py` / `test_next_no_unknown_state.py` as smoke. |
| #845 gitignore alone is insufficient because some preflight paths read `git status` ignoring `.gitignore` | Medium | Medium | Belt-and-suspenders: add explicit path filter in the preflight code path in addition to gitignore. Regression test exercises the exact pre-flight path. |
| #846 substantive-content threshold rejects a legitimately small spec | Low | Medium | Use OR-logic between byte-length and required-section presence; the section check passes for any valid spec regardless of size. |
| Scope creep on #848 toward "fix all of dependency management" | Medium | High | C-004 is enforced at review time; this plan explicitly limits #848 to one new pytest + one doc page. |
| Hidden coupling: changing `next` envelope assertions surfaces flakes in unrelated tests | Low | Medium | Run the full `tests/next` and `tests/contract/test_next_*` suites before opening PR; `tests/integration` smoke covers downstream consumers. |

## Verification Strategy

Single source of truth: NFR-003 commands. The merging branch must be green on **all** of:

```bash
uv lock --check
PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q
uv run pytest tests/contract/test_cross_repo_consumers.py -q
uv run pytest tests/next -q
uv run pytest tests/specify_cli/cli/commands/agent -q
uv run pytest tests/integration -k 'dossier or move_task or dirty or transition' -q
uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q
```

Plus the new architectural test for #848:

```bash
uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q
```

`mypy --strict` and the project's existing coverage gate also stay green. The full local quickstart walkthrough is in `quickstart.md`.

## Complexity Tracking

*No charter-check violations.* Table left empty intentionally.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|

## Branch Contract (re-stated)

- **Current branch at plan start**: `main`
- **Planning/base branch for this mission**: `main`
- **Final merge target for completed changes**: `main`
- **`branch_matches_target`**: true ✅
- **Suggested feature branch (created at `/spec-kitty.implement`)**: `fix/charter-e2e-827-followups`
