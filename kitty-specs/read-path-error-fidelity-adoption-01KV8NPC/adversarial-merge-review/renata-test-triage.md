# Renata — Test Integrity & Suite-Failure Triage

**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**Branch:** `feat/read-path-error-fidelity` (all 9 WPs merged, HEAD `ce68f4311`)
**Lens:** Test integrity + suite-failure triage (function-over-form, anti-gaming)
**Date:** 2026-06-16
**Reviewer:** reviewer-renata

## Method

- Ran every flagged test on the **merged tree** (HEAD) and on the **pre-mission base**
  (`b76473d5d` — merge-base of `feat` with upstream/main, the state before any mission lane branched).
- Base run executed in a throwaway worktree (`git worktree add /tmp/base-check b76473d5d`),
  removed after triage.
- Interpreter: `/home/stijn/.pyenv/versions/3.11.15/bin/python`, `PWHEADLESS=1`.
- For the analyzer-flagged literal removals, traced each removed literal
  (`lanes.json`, escape-check `"/"`, "no workspace") to the test(s) that assert on it
  and ran those tests directly.
- Cross-checked the mission's actual source diff scope (`git diff b76473d5d HEAD --stat -- src/`)
  against the failure root causes to attribute drift.

## Headline

| Bucket | Count |
|--------|-------|
| **MISSION-CAUSED** failures | **0** |
| **PRE-EXISTING** failures | **31** (25 parity + 6 acceptance) |
| Analyzer-flagged "stale assertions" actually broken | **0** (all PASS on both trees) |

**No test fixes are required for this mission.** Every failure in the spot run reproduces identically
on the pre-mission base and is attributable to other missions / environment, not to
`read-path-error-fidelity`.

## Triage Table

| Failing test | Verdict | Root cause | Remediation |
|---|---|---|---|
| `test_twelve_agent_parity.py::test_command_output_unchanged[analyze-*]` (12) | PRE-EXISTING | Snapshot baseline drift. Produced output now contains `--mission <mission-slug>`; baseline lacks it. The `--mission` flag was added to the plan/analyze command templates by commit `0527fcb69` ("feat(naming-rider): #2007 Focus-A command-drift guard"), a **different mission** already present in the base tree. Baseline was never regenerated. | Pre-existing, not ours. (Owner fix: `PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/` under the naming-rider/#2007 follow-up.) |
| `test_twelve_agent_parity.py::test_command_output_unchanged[plan-*]` (12) | PRE-EXISTING | Same snapshot drift as above (`up-plan --json` baseline vs `up-plan --mission <mission-slug> --json` produced). Diff confirmed identical on base. | Pre-existing, not ours. |
| `test_twelve_agent_parity.py::test_non_migrated_agents_count` | PRE-EXISTING | `NON_MIGRATED_AGENTS` has 12 entries; assertion expects 13 (Kiro registration, PR #626 context in the test docstring). Fails identically on base with the exact same tuple. Mission did not touch agent config or `AGENT_COMMAND_CONFIG`. | Pre-existing, not ours. (Owner fix: register Kiro into `NON_MIGRATED_AGENTS` or correct the count — agent-config domain.) |
| `test_acceptance_regressions.py::test_perform_acceptance_persists_accept_commit` | PRE-EXISTING | `perform_acceptance` raises `AcceptanceError("Acceptance checks failed…")` in the test fixture. Identical failure + identical error on base. Symptom: fixture warns `Config file not found: …/.kittify/config.yaml` — test-environment/isolation issue, not read-path logic. | Pre-existing, not ours. |
| `test_acceptance_regressions.py::TestIntegrationBranchGuard::test_branch_main_no_merge_guidance` | PRE-EXISTING | Same `AcceptanceError` in fixture; identical on base. | Pre-existing, not ours. |
| `test_acceptance_regressions.py::TestIntegrationBranchGuard::test_branch_2x_no_merge_guidance` | PRE-EXISTING | Same. | Pre-existing, not ours. |
| `test_acceptance_regressions.py::TestIntegrationBranchGuard::test_pr_mode_integration_branch_no_push_branch` | PRE-EXISTING | Same. | Pre-existing, not ours. |
| `test_acceptance_regressions.py::TestIntegrationBranchGuard::test_feature_branch_still_gets_merge_guidance` | PRE-EXISTING | Same. | Pre-existing, not ours. |
| `test_acceptance_regressions.py::TestIntegrationBranchGuard::test_well_known_branch_without_meta_target` | PRE-EXISTING | Same. | Pre-existing, not ours. |

## Analyzer-Flagged "Stale Assertion" Candidates — Cleared

The post-merge stale-assertion analyzer flagged candidate lines because the mission removed
certain literals from source (`lanes.json` from `mission_runtime/context.py`, the escape-check
`"/"` from `decision.py`, etc.). Each flagged test was run directly to confirm it is NOT actually broken:

| Analyzer flag | Status | Evidence |
|---|---|---|
| `mission_step_contracts/test_research_composition.py:203` | PASS (both trees) | The asserted literal is a DRG node URN / artifact-set check, not the removed source literal. 24 passed. |
| `test_accept_gate_convergence.py:150` | PASS (both trees) | Asserts `summary1.ok == summary2.ok` (idempotence), unrelated to removed literals. 24 passed. |
| `test_twelve_agent_parity.py:135` | n/a | Line 135 is the snapshot-compare `assert produced == expected` message body — the parity failure is the pre-existing baseline drift above, not a literal the mission removed. |
| `test_acceptance_regressions.py:848 / 857 / 881` (`lanes.json`) | PASS | These `lanes.json` corruption assertions are in tests within the 36-passing set of that file. The mission's read-path changes preserved the `lanes.json` "corrupt or malformed" activity-issue contract. The `lanes.json` literal removed from `context.py:798` was a *different* (resolution-path) usage, not the acceptance-gate diagnostic string. |
| `decision.py` escape-check `"/"` removal | PASS | `tests/specify_cli/cli/commands/test_decision.py` (which the mission also edited, +7 lines) — 23 passed. The escape-check removal is intentional and its test green. |
| `workflow.py` "no workspace" literal | PASS | `tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py` — 4 passed; the contract is that implement MUST NOT raise "no workspace could be resolved" on the verified read-path. Behavior intact. |

**Conclusion on the analyzer flags:** these are false positives from the literal-diff heuristic.
The literals were removed from source, but the tests do not assert on those exact removed
occurrences — the contracts the tests guard remain satisfied. No assertion needs updating, and
nothing was deleted to make a test pass. (Function-over-form check: PASS — the mission's
intentional literal changes did not strip any contract a test depended on.)

## What the mission actually touched (for attribution)

`git diff b76473d5d HEAD --stat -- src/` — 15 files, all in the read-path / resolution /
orchestrator-api / decision / workflow surfaces. **None** of:
- `tests/specify_cli/regression/__snapshots__` (parity baselines)
- `src/doctrine/**` (command templates that produce the `--mission` flag)
- agent-config / `AGENT_COMMAND_CONFIG` / `NON_MIGRATED_AGENTS`
- the acceptance-gate fixture setup

…were modified by this mission. Hence none of the 31 failures can be mission-caused.

## Precise fix list for the orchestrator

**For THIS mission: nothing to remediate.** All 31 spot-run failures are pre-existing and
out of scope. The merged tree introduces no new test failures attributable to
`read-path-error-fidelity-adoption-01KV8NPC`.

Out-of-scope pre-existing debt the orchestrator may want to file/route separately (NOT this mission):
1. **Parity snapshot regeneration** (24 `analyze-*`/`plan-*` cases) — owned by the naming-rider/#2007
   `--mission` template change; regenerate baselines with `PYTEST_UPDATE_SNAPSHOTS=1`.
2. **`test_non_migrated_agents_count`** (12 vs 13) — Kiro registration gap in `NON_MIGRATED_AGENTS`;
   agent-config domain.
3. **`test_acceptance_regressions` 6 failures** — `perform_acceptance` fixture raises
   `AcceptanceError`; likely test-isolation / `.kittify/config.yaml` setup regression, independent
   of read-path. Reproduces on clean upstream base.
