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
│   └── snapshot.py            # NOT modified — writer behavior unchanged (#845 fixes the consumer side, not the writer)
├── cli/commands/agent/
│   ├── mission.py             # mission-create scaffold-commit boundary + setup-plan substantive-content gates (#846)
│   └── tasks.py               # move-task pre-flight: filter dossier snapshot from dirty-state computation (#845)
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

- **Wire field reality (verified in source)**: `prompt_file` is the **only** producer-side wire field on `Decision` / `RuntimeDecision` — it appears in `src/specify_cli/next/decision.py:61` (field declaration) and is the only prompt-related key emitted by `to_dict()` (`decision.py:93`). `prompt_path` is **not** a wire field — it appears as a local variable in `prompt_builder.py` and `runtime_bridge.py:2198` only. The current E2E test accepts either key as a defensive consumer-side fallback (`tests/e2e/test_charter_epic_golden_path.py:570`); that fallback is preserved by this mission but the producer contract is **`prompt_file` only**. This mission does NOT add a `prompt_path` wire field.
- **Tighten the contract** in `src/specify_cli/next/decision.py`:
  - For decisions with `kind == "step"` (composed step), `prompt_file` MUST be a non-empty string and MUST resolve to an existing file when serialized.
  - Validation runs at envelope construction time (`__post_init__` on the decision dataclass). A `kind=step` with a missing prompt is a programmer error — the runtime catches the validator's exception and falls back to `kind=blocked` with a reason instead.
- **Tighten E2E assertion** in `tests/e2e/test_charter_epic_golden_path.py` — replace the current "key exists" check with: for every issued decision where `kind == "step"`, look up `payload.get("prompt_file") or payload.get("prompt_path")` (preserving the existing consumer-side fallback) and assert the value is non-null, non-empty, and `Path(value).is_file()` is true.
- **Doctrine**: scrub `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any inline comment in `src/specify_cli/next/decision.py` (around the `to_dict()` block — currently includes "advance mode populates this") that legitimizes `null` for `kind=step`. Replace with: "null is only legal for non-`step` kinds; a `kind=step` envelope without a resolvable prompt is a runtime invariant violation".

### Issue #845 — Dossier snapshot ownership

- **Ownership policy chosen: EXCLUDE** the snapshot path from the worktree dirty-state pre-flight used by `agent tasks move-task` and related transitions. Rationale: `snapshot-latest.json` is named "latest" — it is inherently mutable and not a versioned artifact. Tracking it would create constant commit churn with zero review value. (See research.md for rejected alternatives.)
- **Implementation**:
  - Add `*/.kittify/dossiers/*/snapshot-latest.json` to `.gitignore` (root). This is sufficient if the dirty-state pre-flight uses `git status --porcelain` semantics that respect `.gitignore`.
  - In addition, the pre-flight code path in `src/specify_cli/cli/commands/agent/tasks.py` (and any helper in `src/specify_cli/status/` that drives transition pre-flight) explicitly filters paths matching the dossier-snapshot pattern when computing "is the worktree dirty for the purposes of this transition?". Belt-and-suspenders: the gitignore covers ad-hoc human use; the explicit filter covers any code path that sidesteps gitignore.
- **Regression coverage**: a new integration test at `tests/integration/test_dossier_snapshot_no_self_block.py` that (a) drives a mission command which writes `snapshot-latest.json`, (b) immediately invokes `agent tasks move-task` on the same WP/worktree, and (c) asserts the move-task call does **not** error with a self-inflicted dirty-state failure. The test exercises the exact path that previously blocked.

### Issue #846 — Specify/plan auto-commit boundary

**Surface inventory (verified in source)** — there are two distinct auto-commit paths today, and the bug shows up at *both*:

1. **`mission create`** (in `src/specify_cli/cli/commands/agent/mission.py`) auto-commits the empty `spec.md` scaffold along with `meta.json`. We observed this concretely while building this mission: an empty `spec.md` was committed before any substantive content was written. **This is the primary defect surface.**
2. **`setup-plan`** (`mission.py` around line 973: `_commit_to_branch(plan_file, ...)`) auto-commits `plan.md` after the agent populates it from the `/spec-kitty.plan` slash-template flow.
3. **`/spec-kitty.specify` slash-template** instructs the agent to populate `spec.md` and then commit; today the slash template owns the substantive commit, not Python. The bug surface is therefore the *initial* scaffold commit (path #1) plus any workflow command that reports "spec phase ready" while the substantive spec is still untracked (FR-014).

- **"Substantive content" definition (operational, revised)**: a spec.md (or plan.md) is substantive iff it contains the required mandatory sections for that artifact (spec: at least one non-empty Functional Requirements row with an `FR-###` ID; plan: a populated Technical Context section, *not* template placeholders like `[e.g., Python 3.11 …]` or `[NEEDS CLARIFICATION …]`). The earlier byte-length OR has been **dropped** — see research R7 (revised). Byte-length is too easy to satisfy with arbitrary filler that recreates the failure mode.
- **Implementation**:
  - Add a pure helper `is_substantive(file_path: Path, kind: Literal["spec", "plan"]) -> bool` in a new module `src/specify_cli/missions/_substantive.py`. Section-presence only.
  - **Fix 1 (`mission create` boundary)**: change the create flow in `mission.py` so the auto-commit at create time **does not include `spec.md`** (only `meta.json` and the other supporting scaffolding). The agent commits the populated `spec.md` themselves after writing substantive content (existing slash-template behavior) — but only that *substantive* content lands on the branch, not the empty scaffold.
  - **Fix 2 (`setup-plan` entry gate)**: at the top of `setup-plan`, check `is_substantive(spec_path, "spec")` AND that `spec.md` is committed (i.e., `git ls-files --error-unmatch` succeeds and the committed version is substantive). If either fails, emit `phase_complete=False / blocked_reason="spec.md must be committed and substantive before plan phase"` and return without writing or committing `plan.md`.
  - **Fix 3 (`setup-plan` exit gate)**: gate the existing `_commit_to_branch(plan_file, …)` call on `is_substantive(plan_path, "plan")`. If false, emit the same incomplete envelope and skip the commit.
  - Workflow status reporting treats a non-substantive-but-committed-scaffold state (legacy missions, or this mission's own pre-fix history) as **incomplete**, not "spec/plan ready".
- **Templates** under `src/specify_cli/missions/<mission-type>/command-templates/{specify,plan}.md` add an explicit "commit boundary" subsection so future agents understand why their empty-scaffold commit is being blocked.
- **Regression coverage**: a new integration test at `tests/integration/test_specify_plan_commit_boundary.py` that asserts (a) `mission create` does NOT commit an empty `spec.md`; (b) `setup-plan` blocks if `spec.md` is uncommitted; (c) `setup-plan` blocks if `spec.md` is committed but non-substantive; (d) `setup-plan` succeeds and commits `plan.md` only when both are substantive.

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
