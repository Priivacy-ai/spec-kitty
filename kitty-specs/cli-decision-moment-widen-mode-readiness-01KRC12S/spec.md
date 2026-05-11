# Feature Specification: CLI Decision Moment Widen Mode Readiness

**Mission ID**: 01KRC12SN9TNDD11SPPRRJRZ1C
**Slug**: cli-decision-moment-widen-mode-readiness
**Type**: software-dev
**Priority**: P0 release blocker

## Why this exists (Purpose)

**TL;DR:** Make CLI Decision Moment creation, Widen Mode, plan-side write-back, and local-close behavior release-ready across `charter`, `specify`, and `plan` commands.

**Context:** Teamspace MVP launch is gated on Decision Moment widen-mode reliability. The plan-widen test fixtures currently fail at the new "repo must be initialized" gate (the assert_initialized guard introduced earlier this cycle) before they exercise the widen path, leaving Mission 2 (SaaS Slack closure) and Mission 3 (Live E2E) without trustworthy CLI coverage. Closes Priivacy-ai/spec-kitty#757, #758.

## User Scenarios & Testing

### Primary actor
A developer running `spec-kitty plan` inside an initialized project who wants to widen an unresolved planning question into a Teamspace Slack thread instead of resolving it locally.

### Happy-path scenario
1. The user invokes `spec-kitty plan` inside a project that has `.kittify/config.yaml` and `kitty-specs/`.
2. The plan-widen interview offers `[w]iden` when SaaS prereqs (Teamspace, Slack, reachable SaaS) are satisfied.
3. The user picks `w → CONTINUE` and the question is parked as a `WidenPendingEntry` (deterministic write-back).
4. A subsequent local answer for the same slot closes the widened entry (or records closure intent if the wider Slack flow is still open).

### Exception / edge-case scenarios
- **No prereqs:** Widen affordance must not appear. Plan still completes; no pending entries.
- **Cancel:** `w → CANCEL` re-prompts the same question; final answer reaches the answers file deterministically.
- **Block path:** `w → BLOCK` enters the blocked-prompt loop and resolves via a local answer; pending entry reflects closure.
- **Stricter init gate:** Plan exits with `SPEC_KITTY_REPO_NOT_INITIALIZED` when run outside a Spec Kitty project. Tests for widen-mode must satisfy this gate.

### Rule that must always hold (init gate)

The plan/charter/tasks commands MUST refuse to side-effect when invoked outside an initialized Spec Kitty project. The test suite MUST set up the minimum initialization markers before invoking the CLI.

### Rule that must always hold
The `plan` (and `charter`, `tasks`) Typer command MUST refuse to side-effect any filesystem when invoked outside an initialized Spec Kitty project (`<root>/.kittify/config.yaml` missing). Tests for widen-mode MUST therefore set up a minimum initialized project before invoking the CLI.

## Domain Language

- **Decision Moment (DM):** Canonical interview/plan question with a stable `decision_id` that can be resolved, deferred, cancelled, or widened.
- **Widen Mode:** Affordance to push an unresolved DM to a Teamspace Slack thread for asynchronous discussion.
- **WidenPendingEntry:** Local sidecar record (in `widen-pending.jsonl`) capturing a DM that has been widened but not yet closed.
- **Local-close:** Resolving a widened DM by typing an answer locally, which must also close (or record closure intent for) the Slack-side discussion.

## Requirements

### Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The `_setup_repo` helper used by `tests/specify_cli/cli/commands/test_plan_widen.py` MUST produce a directory tree that passes `assert_initialized(require_specs=True)` (i.e. write a minimal valid `.kittify/config.yaml` and ensure `kitty-specs/` exists). | Pending |
| FR-002 | The 4 currently-failing tests in `test_plan_widen.py` (Absent/Cancel/Continue/Block) MUST pass without weakening their assertions about widen affordance, prereq gating, store writes, and answer-file write-back. | Pending |
| FR-003 | `charter`, `specify`, and `plan` MUST each surface first-class Decision Moment artifacts (events recorded via `spec-kitty agent decision`) and MUST preserve local-only behavior when `SPEC_KITTY_ENABLE_SAAS_SYNC` is unset. | Pending |
| FR-004 | Resolving a widened DM locally MUST either close the corresponding `WidenPendingEntry` or record a closure-intent marker that downstream sync can act on, with deterministic write-back to `answers.yaml` / `plan-answers.*`. | Pending |
| FR-005 | The full acceptance test set MUST pass: `tests/specify_cli/cli/commands/test_charter_widen.py`, `tests/specify_cli/cli/commands/test_plan_widen.py`, `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py`, `tests/specify_cli/cli/commands/test_charter_prereq_suppression.py`, `tests/status/test_read_events_tolerates_decision_events.py`. | Pending |

### Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The acceptance test set executes deterministically without contacting SaaS. | 100 % runs pass with `SPEC_KITTY_ENABLE_SAAS_SYNC` unset. | Pending |
| NFR-002 | Fixture changes do not introduce shared mutable state or filesystem leakage between tests. | Each test uses an isolated `tmp_path` with no cross-test config bleed. | Pending |
| NFR-003 | Test run latency for the acceptance set stays within current bounds. | Total wall-clock ≤ 30 s on a standard laptop. | Pending |

### Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | MUST NOT weaken `assert_initialized` or the initialized-repo invariant in production code paths. | Pending |
| C-002 | MUST NOT modify charter-widen tests (they already pass); fixes are scoped to plan-widen fixture and any minimal production-side adjustments required for FR-003/FR-004. | Pending |
| C-003 | Any SaaS-touching validation MUST run only under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; default test path stays local-only. | Pending |

## Success Criteria

- **SC-001:** `uv run pytest tests/specify_cli/cli/commands/test_charter_widen.py tests/specify_cli/cli/commands/test_plan_widen.py tests/specify_cli/cli/commands/test_decision_widen_subcommand.py tests/specify_cli/cli/commands/test_charter_prereq_suppression.py tests/status/test_read_events_tolerates_decision_events.py -q` exits with code 0.
- **SC-002:** GitHub issues Priivacy-ai/spec-kitty#757 and #758 can be closed or narrowed to non-release follow-up.
- **SC-003:** Re-running the broader CLI slice (`uv run pytest tests/specify_cli/cli/commands -q`) shows no regressions versus the 51-passing baseline.

## Assumptions

- The 4 failing tests fail solely due to the missing `.kittify/config.yaml` in `_setup_repo`; deeper production-side widen-mode bugs are not present (validated by the fact that the equivalent `_setup_repo` in `test_charter_widen.py` does pass the gate when `charter` is invoked, because the charter call-path differs).
- Local-only behavior of `charter`/`specify`/`plan` is already implemented; this mission verifies and documents it but does not add a new product surface.
- No SaaS-side changes are required from this mission; Mission 2 owns SaaS-side reliability.

## Key Entities

- **`_setup_repo` (test helper):** Bootstraps a minimal Spec Kitty project on disk for widen tests.
- **`WidenPendingStore` / `WidenPendingEntry`:** Local persistence layer for widened DMs.
- **`assert_initialized`:** The repo-init guard that requires `<root>/.kittify/config.yaml` (and optionally `<root>/kitty-specs/`) before plan/charter/tasks side effects.

## Out of Scope

- Production-side widen flow rewrites.
- SaaS Slack projection/closure (owned by Mission 2).
- Live E2E coverage (owned by Mission 3).
