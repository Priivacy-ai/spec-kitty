# Dual-mode dispatch evidence (WP11, T060)

**Status: PENDING — to be captured on first live dispatch post-merge.**

This mission (`ci-pipeline-reinstatement-01M1X35E`) *reinstates* CI: the
workflows this document verifies (`ci-router.yml`, `ci-modules.yml`,
`module-tests.yml`, and — once their owning WPs land — `ci-aggregate.yml`,
`sonar.yml`, `ci-nightly.yml`, `packs.yml`) only go **live** on GitHub Actions
once this mission's branch is merged upstream and a pull request or push
event actually triggers them. There is no live CI in this development
environment. **No dispatched run has been performed for this document — the
procedure and expected outcomes below are documented ahead of that run; they
are not a report of one that happened.** Do not read anything below this
line as a completed run.

The static wiring (mode threading, `workflow_dispatch` presence, the
terminal-gate skipped-vs-failed evaluation logic) is proven today by the
in-repo contract test `tests/architectural/test_dual_mode_contract.py`
(WP11, T056-T059). What that test *cannot* prove — because it is GitHub
*host* behavior, not something expressible as a static YAML assertion — is
covered by this document: SC-009 (PR mode runs strictly fewer jobs than a
failing full run; full mode runs 100% of jobs) and the practical
merge-eligibility consequence of FR-019 (a short-circuit-skipped/cancelled
successor is not mergeable-green).

## Why this can't be produced now

- SC-009 and the skipped-not-green invariant are properties of how GitHub
  Actions schedules, cancels, and reports job/check status for a real
  workflow run against a real event (`pull_request`, `push`, or
  `workflow_dispatch`) — none of which exist until this mission's workflows
  are live on `main` (or a PR branch based on it).
- Fabricating job counts or check statuses here would misrepresent
  something that did not happen. Per this mission's honesty requirement
  (mirrored from the WP11 task brief), this document instead specifies the
  exact procedure and the pass/fail criteria so the first person who runs it
  post-merge can fill in real evidence rather than write it from scratch.

## Procedure — to run once these workflows are live

### 1. PR-mode fail-fast: strictly fewer jobs on an early red

1. Open a PR against `main` from a branch whose diff deliberately introduces
   a failure in a cheap, early gate that other jobs are `needs:`-scoped
   behind, or a shard whose failure is expected to fail-fast-cancel sibling
   matrix legs (e.g. break one `ci-modules.yml` module's tests while leaving
   `ci-modules.yml`'s `strategy.fail-fast` at its default — PR events do not
   pass `workflow_dispatch.inputs.mode`, so `mode` resolves to `pr` and
   `fail-fast` resolves `true`).
2. Record, from the Actions run summary for `CI Modules` (`ci-modules.yml`):
   - total matrix legs in the generated matrix (from `generate-matrix`'s
     "generated N shard leaves across M registry modules" log line),
   - how many actually executed (`success`/`failure`) vs. were
     `cancelled` once the first leg failed.
3. **Expected outcome:** executed-plus-cancelled leg count is less than or
   equal to the full matrix size, with at least one leg showing `cancelled`
   (not `success` or `skipped`) — proving PR mode ran strictly fewer jobs to
   completion than a full run would (SC-009, NFR-008).
4. For `ci-router.yml`: since its own shift-left/tests-* jobs are gated on
   `needs.changes.outputs.<group>` (path-scoping), record which named jobs
   ran vs. were skipped by `changes` output false, and confirm the total
   executed-job count for this PR is less than the full-mode count captured
   in step 2 of the next section.

### 2. Full mode: run-all-regardless, reports every failure

1. Dispatch `CI Modules` and `CI Router` manually via **Actions → (workflow
   name) → Run workflow**, setting the `mode` input to `full` on a ref that
   contains ≥2 deliberately-introduced failures in independent
   shards/groups (e.g. one failing test in two different module registry
   entries, or one failing shard plus one failing path-scoped group).
2. Record the total job/matrix-leg count for each workflow and how many
   executed to completion (`success` or `failure`, never `cancelled` for
   this reason).
3. **Expected outcome:** 100% of jobs/matrix legs execute to completion
   regardless of the ≥2 injected failures (`ci-modules.yml`'s
   `strategy.fail-fast: false` when `mode == 'full'`; `module-tests.yml`'s
   per-shard run step converts a shard failure to a warning and continues
   in full mode; `ci-router.yml`'s `changes` job forces every group's
   output `true` in full mode so every shard job's `if:` condition is
   satisfied). Both injected failures must be visible in the run's failure
   summary — full mode must not mask either one.

### 3. Skipped/cancelled successor is not merge-eligible-green

1. On the PR run from step 1, inspect the PR's "Checks" list (or the
   branch-protection required-checks view once configured).
2. For `ci-router.yml`: confirm the `router-gate` check's own conclusion is
   `failure` when any of its `needs:` report `failure`/`cancelled` — the
   embedded evaluation script only excludes genuinely-`skipped` (i.e.
   not-selected-by-path) dependencies from blocking (proven statically by
   `tests/architectural/test_dual_mode_contract.py::test_router_gate_treats_failure_and_cancelled_as_blocking`
   and its `test_router_gate_treats_merely_skipped_dependency_as_not_blocking`
   sibling). Confirm the live run's `router-gate` conclusion matches: it
   must be `failure`, not `success`, whenever a genuine failure/cancellation
   occurred upstream.
3. For `ci-modules.yml`'s fail-fast-cancelled matrix legs (step 1 of
   section 1): confirm each cancelled leg's own GitHub check (e.g.
   `module-tests (foo shard 2/3)`) reports conclusion `cancelled`, and that
   this PR is **not** shown as mergeable (or is blocked once that leg's
   check name — or the router's aggregate — is added to the repository's
   required-status-checks list in branch protection).
4. **Expected outcome:** no check produced by this PR reports `success` for
   a job that was skipped or cancelled due to an upstream failure; the PR
   is not mergeable while any such check is outstanding.

## Required branch-protection configuration (repo settings, not YAML)

The skipped-not-green invariant's *merge-blocking* half depends on which
checks are marked "required" in GitHub branch protection — this is
repository configuration, not something expressible in the workflow YAML
files themselves (per this WP's Risk note). Once these workflows are live,
the required-status-checks list must include either:

- the aggregate checks that already fold sibling results into one verdict
  (`router-gate` for `ci-router.yml`), and/or
- the per-leg checks for workflows with no such aggregate today
  (`ci-modules.yml`'s per-`(module, shard)` `module-tests (...)` checks —
  see the WP11 task's Risk note; `ci-aggregate.yml`, once WP10 lands, is the
  natural place for a fold-in aggregate across `ci-modules.yml`'s legs).

Confirm this configuration as part of capturing the evidence above, and
record the actual required-checks list alongside the run results.

## Fill in after the first live dispatch

| Item | Expected | Observed | Run link |
|---|---|---|---|
| PR-mode job count vs. full-mode job count (strictly fewer) | fewer | _pending_ | _pending_ |
| Full run with ≥2 failures executes 100% of jobs | 100% | _pending_ | _pending_ |
| Cancelled/skipped-due-to-failure check reports non-`success` | non-`success` | _pending_ | _pending_ |
| PR blocked while such a check is outstanding | blocked | _pending_ | _pending_ |
| Required-status-checks list includes the right aggregate/per-leg checks | configured | _pending_ | _pending_ |
