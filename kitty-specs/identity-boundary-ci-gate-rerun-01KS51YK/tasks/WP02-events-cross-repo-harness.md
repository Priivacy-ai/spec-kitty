---
work_package_id: WP02
title: spec-kitty-events cross-repo-harness-tests workflow + README
dependencies: []
requirement_refs:
- FR-002
- FR-004
- FR-005
- FR-006
- FR-008
- NFR-002
- NFR-004
- C-001
- C-002
- C-006
- C-007
- C-008
planning_base_branch: mission/identity-boundary-ci-gate-rerun
merge_target_branch: mission/identity-boundary-ci-gate-rerun
branch_strategy: "Planning artifacts for this mission were generated on mission/identity-boundary-ci-gate-rerun in spec-kitty. The WP itself implements in a worktree on Priivacy-ai/spec-kitty-events (a different repo) on lane branch mission/identity-boundary-ci-gate-events-rerun. NOTE: The PR target for this WP is the sibling repo's main (Priivacy-ai/spec-kitty-events:main), NOT this planning branch. The runtime-tracked merge_target_branch above is the in-mission state-machine target; the operational truth is the cross-repo PR."
base_branch: kitty/mission-identity-boundary-ci-gate-rerun-01KS51YK
base_commit: 421dbc0feaadfed8cd8a30947dcef86df6a68209
created_at: '2026-05-21T10:59:51.964252+00:00'
subtasks:
- T005
- T006
- T007
- T008
agent: "claude"
shell_pid: "81066"
history: []
agent_profile: implementer-ivan
authoritative_surface: spec-kitty-events:.github/workflows/
execution_mode: code_change
owned_files:
- spec-kitty-events:.github/workflows/cross-repo-harness-tests.yml
- spec-kitty-events:README.md
role: implementer
tags:
- ci
- workflow
- spec-kitty-events
- cross-repo
---

## ⚡ Do This First: Load Agent Profile

Before reading the rest of this WP, load the implementer profile so you adopt the right identity and boundaries:

- Run the `/ad-hoc-profile-load` skill with profile `implementer-ivan` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/built-in/implementer-ivan.agent.yaml`.
- After load, restate your identity, governance scope, and boundaries in one short paragraph before continuing.

## Objective

Add a workflow file in `Priivacy-ai/spec-kitty-events` that clones the e2e harness at pinned SHA `4d5206e08a30bf23ae4dabae532dc0e355078e16` and runs the harness's identity-boundary unit tests on every PR. The workflow exposes a single, stable job named `cross-repo-harness-tests`.

## Context

- The events repo has no existing identity-boundary CI; today a breaking envelope change ships and only the manually-run canary catches it.
- The e2e harness has two test directories that pin the SaaS-side identity-resolution contract: `tests/unit/identity_boundary/` and `tests/identity_boundary/unit/`. Both exist at the pinned SHA (verified).
- Pinned SHA: `4d5206e08a30bf23ae4dabae532dc0e355078e16` (HEAD of `Priivacy-ai/spec-kitty-end-to-end-testing@main` at planning time).
- Cross-repo checkout uses `actions/checkout@v4` with `repository:` + `ref:`.
- Filename collision context: no open events PRs at planning time; safe to use `.github/workflows/cross-repo-harness-tests.yml`.

## Subtasks

### T005: Create canonical-repo worktree for spec-kitty-events

**Purpose**: Get a clean worktree on a NEW lane branch so commits don't pollute canonical main locally, and so a previous-attempt branch (`mission/identity-boundary-ci-gate-events`) is not reused.

**Steps**:
1. From the canonical sibling path (`/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-events`):
   ```bash
   git fetch origin
   git -C /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-events worktree add \
     /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-events.worktrees/canary-gate-rerun \
     -b mission/identity-boundary-ci-gate-events-rerun origin/main
   ```
2. `cd` into the worktree.
3. `git branch --show-current` MUST report `mission/identity-boundary-ci-gate-events-rerun`. If it reports `main`, STOP — you accidentally checked out canonical.

### T006: Author `.github/workflows/cross-repo-harness-tests.yml`

**Purpose**: Pin the harness identity-boundary unit tests as a required-check for every events PR.

**Steps**:
1. In the events worktree, create `.github/workflows/cross-repo-harness-tests.yml`:

```yaml
# .github/workflows/cross-repo-harness-tests.yml
#
# Identity-Boundary CI Gate — spec-kitty-events repo
#
# Tracker: https://github.com/Priivacy-ai/spec-kitty/issues/1247
#
# Clones the e2e harness at a pinned SHA and runs the
# identity-boundary unit tests with the PR's HEAD copy of
# spec_kitty_events installed via `uv pip install -e`. If the PR
# breaks SaaS-side resolution assumptions, the unit suite turns red
# and merge is blocked.
#
# Pinned SHA: 4d5206e08a30bf23ae4dabae532dc0e355078e16
# SHA-bump procedure: see README.md > "Identity-Boundary CI Gate".

name: cross-repo-harness-tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

concurrency:
  group: cross-repo-harness-tests-${{ github.ref }}
  cancel-in-progress: true

jobs:
  cross-repo-harness-tests:
    name: cross-repo-harness-tests
    runs-on: ubuntu-latest
    timeout-minutes: 6
    steps:
      - name: Checkout spec-kitty-events (PR head)
        uses: actions/checkout@v4
        with:
          path: events

      - name: Checkout spec-kitty-end-to-end-testing (pinned SHA)
        uses: actions/checkout@v4
        with:
          repository: Priivacy-ai/spec-kitty-end-to-end-testing
          ref: 4d5206e08a30bf23ae4dabae532dc0e355078e16
          path: e2e

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Install harness dependencies (frozen)
        working-directory: e2e
        run: uv sync --frozen

      - name: Override spec_kitty_events with PR head
        working-directory: e2e
        run: uv pip install -e ../events

      - name: Run identity-boundary unit tests
        working-directory: e2e
        run: uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/ -v

      - name: Upload artifacts on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: identity-boundary-failure-artifacts
          path: e2e/artifacts/sync_identity_boundary/
          if-no-files-found: ignore
```

2. Verify job name and job id are both `cross-repo-harness-tests`.

### T007: Add "Identity-Boundary CI Gate" README section to events

**Purpose**: Document the gate, the pinned SHA, and the bump procedure.

**Steps**:
1. Open `README.md` in the events worktree.
2. Add `## Identity-Boundary CI Gate` near existing CI / contributing content with:
   - One-paragraph what (cross-repo gate; clones e2e at pinned SHA; runs identity-boundary unit tests).
   - The current pinned SHA: `4d5206e08a30bf23ae4dabae532dc0e355078e16`.
   - **SHA-bump procedure** (verbatim, this is load-bearing):
     ```
     When an intentional, breaking contract change ships in this repo
     that requires a matching harness update:
     1. Get the new e2e SHA after the harness update lands:
        unset GITHUB_TOKEN
        gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/commits/main --jq .sha
     2. Verify the new SHA still contains tests/unit/identity_boundary/
        and tests/identity_boundary/unit/.
     3. Update the `ref:` field in
        .github/workflows/cross-repo-harness-tests.yml.
     4. Open the bump PR; CI will exercise the new SHA against the new
        contract before merge.
     ```
   - Sibling gates: link spec-kitty `drift-detector` and saas `identity-boundary-canary` workflows, cite `#1247`.
   - Admin action required: register `cross-repo-harness-tests` as a required check on `main` at https://github.com/Priivacy-ai/spec-kitty-events/settings/branches.

### T008: Validate events workflow YAML and pinned-SHA correctness

**Purpose**: Catch typos and SHA mismatches before the PR.

**Steps**:
1. Validate YAML:
   ```bash
   python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/cross-repo-harness-tests.yml')); j=d['jobs']['cross-repo-harness-tests']; assert j['name']=='cross-repo-harness-tests'; assert any(s.get('with',{}).get('ref')=='4d5206e08a30bf23ae4dabae532dc0e355078e16' for s in j['steps']); print('OK')"
   ```
2. Verify the pinned SHA is exactly `4d5206e08a30bf23ae4dabae532dc0e355078e16` (no typo, no `ref: main`).
3. (Optional) `actionlint .github/workflows/cross-repo-harness-tests.yml` if installed.

## Files

- `.github/workflows/cross-repo-harness-tests.yml` — NEW, ~55 lines
- `README.md` — patched with ~40 new lines

## Validation

- [ ] Worktree is on `mission/identity-boundary-ci-gate-events-rerun`, NOT `main`.
- [ ] Workflow file exists and parses as YAML.
- [ ] Job name is exactly `cross-repo-harness-tests`.
- [ ] Pinned SHA is exactly `4d5206e08a30bf23ae4dabae532dc0e355078e16`.
- [ ] README has the "Identity-Boundary CI Gate" section with the SHA-bump procedure.
- [ ] No other files modified.

## Edge cases / risks

- **`uv pip install -e ../events` install conflict**: If events' pyproject.toml drifts in a way that conflicts with the harness's frozen lockfile, this step fails. That IS the contract — it means a breaking change shipped that the harness can't accommodate. Reviewer should treat as expected fail-fast behavior.
- **Pinned SHA goes away** (force-push to e2e main): out of scope; e2e main is not force-pushed in practice.
- **uv cache poisoning between events checkouts**: `setup-uv@v3` cache is per-lockfile-hash; not a risk in normal operation.

## Definition of Done

- All four subtasks complete.
- Workflow file and README diff staged on `mission/identity-boundary-ci-gate-events-rerun`.
- YAML validation script returned `OK`.
- WP moves to `for_review` via `spec-kitty next`.

## Reviewer guidance

Reviewer checks:
- Job name match.
- Pinned SHA character-exact (`4d5206e08a30bf23ae4dabae532dc0e355078e16`).
- `uv pip install -e ../events` step is present (otherwise the harness tests run against the released events, not the PR head — defeats the gate).
- README SHA-bump procedure is complete (all four steps).
- No drift into other workflows.

## Activity Log

- 2026-05-21T10:59:53Z – claude – shell_pid=81066 – Assigned agent via action command
- 2026-05-21T11:01:32Z – claude – shell_pid=81066 – WP02 implementation complete in spec-kitty-events worktree (cross-repo); YAML valid, pinned SHA verified. Lane-b spec-kitty worktree intentionally empty — diff lives in spec-kitty-events:mission/identity-boundary-ci-gate-events-rerun.
- 2026-05-21T11:02:01Z – claude – shell_pid=81066 – Renata pass 1: APPROVED. Pinned SHA exact, uv install step present, README complete. Cross-repo diff on events:mission/identity-boundary-ci-gate-events-rerun.
