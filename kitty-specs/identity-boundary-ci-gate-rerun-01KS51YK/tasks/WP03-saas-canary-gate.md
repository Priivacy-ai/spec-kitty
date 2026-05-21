---
work_package_id: WP03
title: spec-kitty-saas canary-gate workflow + README
dependencies: []
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-004
- C-001
- C-002
- C-003
- C-004
- C-006
- C-007
- C-008
planning_base_branch: mission/identity-boundary-ci-gate-rerun
merge_target_branch: mission/identity-boundary-ci-gate-rerun
branch_strategy: "Planning artifacts for this mission were generated on mission/identity-boundary-ci-gate-rerun in spec-kitty. The WP itself implements in a worktree on Priivacy-ai/spec-kitty-saas (a different repo) on lane branch mission/identity-boundary-ci-gate-saas-rerun. NOTE: The PR target for this WP is the sibling repo's main (Priivacy-ai/spec-kitty-saas:main), NOT this planning branch. The runtime-tracked merge_target_branch above is the in-mission state-machine target; the operational truth is the cross-repo PR."
base_branch: kitty/mission-identity-boundary-ci-gate-rerun-01KS51YK
base_commit: 421dbc0feaadfed8cd8a30947dcef86df6a68209
created_at: '2026-05-21T11:02:10.765478+00:00'
subtasks:
- T009
- T010
- T011
- T012
agent: "claude"
shell_pid: "83157"
history: []
agent_profile: implementer-ivan
authoritative_surface: spec-kitty-saas:.github/workflows/
execution_mode: code_change
owned_files:
- spec-kitty-saas:.github/workflows/canary-gate.yml
- spec-kitty-saas:README.md
role: implementer
tags:
- ci
- workflow
- spec-kitty-saas
- cross-repo
- canary
---

## ⚡ Do This First: Load Agent Profile

Before reading the rest of this WP, load the implementer profile so you adopt the right identity and boundaries:

- Run the `/ad-hoc-profile-load` skill with profile `implementer-ivan` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/built-in/implementer-ivan.agent.yaml`.
- After load, restate your identity, governance scope, and boundaries in one short paragraph before continuing.

## Objective

Add a workflow file in `Priivacy-ai/spec-kitty-saas` that runs the identity-boundary canary in `--single` mode against deployed-dev on every saas PR. The workflow exposes a single, stable job named `identity-boundary-canary`. README documents the secret-name contract and SHA-bump procedure.

## Context

- The canary script (`scripts/run-sync-identity-boundary-canary.sh`) lives in the e2e repo and is the closed artifact of `e2e#41`. It MUST NOT be modified by this mission.
- The script's CI contract (from its header): `--single` for one-shot, `--yes` for non-TTY trusted-runner assertion, env `SPEC_KITTY_ENABLE_SAAS_SYNC=1` mandatory, env `SPEC_KITTY_E2E_TRUSTED_RUNNER=1` mandatory (or `--yes` flag), exit 2 = preflight, non-zero = canary fail.
- The brief forbids ephemeral Fly app spin-up per PR. Target is deployed-dev (`spec-kitty-dev.fly.dev`). Canary-only credentials in CI secrets.
- Pinned e2e SHA: `4d5206e08a30bf23ae4dabae532dc0e355078e16`.
- Filename collision context: sibling open PRs are `canonical-producer-lint.yml` (#260) and `sunset-check.yml` (#262). Our file MUST be named `canary-gate.yml`.
- Secret-name contract: `SPEC_KITTY_CANARY_TOKEN` (and any subordinate canary-auth env vars the SaaS client library reads).

## Subtasks

### T009: Create canonical-repo worktree for spec-kitty-saas

**Steps**:
1. From the canonical sibling path:
   ```bash
   git -C /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-saas fetch origin
   git -C /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-saas worktree add \
     /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-saas.worktrees/canary-gate-rerun \
     -b mission/identity-boundary-ci-gate-saas-rerun origin/main
   ```
2. `cd` into the worktree.
3. `git branch --show-current` MUST report `mission/identity-boundary-ci-gate-saas-rerun`. If it reports `main`, STOP — you accidentally checked out canonical.

### T010: Author `.github/workflows/canary-gate.yml`

**Steps**:
1. Create `.github/workflows/canary-gate.yml`:

```yaml
# .github/workflows/canary-gate.yml
#
# Identity-Boundary CI Gate — spec-kitty-saas repo
#
# Tracker: https://github.com/Priivacy-ai/spec-kitty/issues/1247
#
# Runs the 4-run identity-boundary canary protocol in --single mode
# against deployed-dev (spec-kitty-dev.fly.dev) on every saas PR. Red
# canary blocks merge. The canary script itself lives in the e2e repo;
# we pin to a specific SHA to keep the contract stable.
#
# Pinned e2e SHA: 4d5206e08a30bf23ae4dabae532dc0e355078e16
# SHA-bump procedure: see README.md > "Identity-Boundary CI Gate".
#
# Secret-name contract:
#   SPEC_KITTY_CANARY_TOKEN — canary-only SaaS API token. If unset, the
#   canary script will fail fast with a clear preflight error; the
#   repo admin provisions on first failure.

name: canary-gate

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

concurrency:
  # Serialize against deployed-dev to avoid concurrent-canary daemon races.
  group: identity-boundary-canary
  cancel-in-progress: false

jobs:
  identity-boundary-canary:
    name: identity-boundary-canary
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      SPEC_KITTY_ENABLE_SAAS_SYNC: "1"
      SPEC_KITTY_E2E_TRUSTED_RUNNER: "1"
      SPEC_KITTY_CANARY_TOKEN: ${{ secrets.SPEC_KITTY_CANARY_TOKEN }}
    steps:
      - name: Checkout spec-kitty-saas (PR head)
        uses: actions/checkout@v4
        with:
          path: saas

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

      - name: Run identity-boundary canary (single-run mode against deployed-dev)
        working-directory: e2e
        run: ./scripts/run-sync-identity-boundary-canary.sh --single --yes

      - name: Upload canary run artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: identity-boundary-canary-runs
          path: e2e/artifacts/sync_identity_boundary/
          if-no-files-found: ignore
```

2. Verify the job name and job id are both `identity-boundary-canary`.
3. Verify no Fly-app spin-up step is present (no `flyctl`, no `fly apps create`).

### T011: Add "Identity-Boundary CI Gate" README section to saas

**Steps**:
1. Open `README.md` in the saas worktree.
2. Add `## Identity-Boundary CI Gate` with:
   - One-paragraph what (saas-side gate; runs canary --single against deployed-dev on every PR; red blocks merge).
   - **Secret-name contract** (verbatim — load-bearing for admins):
     - `SPEC_KITTY_CANARY_TOKEN` — canary-only API token for deployed-dev. Provision as a GitHub Actions secret on this repo.
   - The current pinned e2e SHA: `4d5206e08a30bf23ae4dabae532dc0e355078e16`.
   - **SHA-bump procedure** (same four-step block as the events README, adjusted for saas: bump the `ref:` in `.github/workflows/canary-gate.yml`).
   - **Why not ephemeral Fly per PR**: state that deployed-dev is the target by design; the canary's own pre-run hygiene gate (rogue-daemon check) mitigates concurrent-PR races; CI concurrency is serialized via `group: identity-boundary-canary`.
   - Sibling gates: link spec-kitty `drift-detector` and events `cross-repo-harness-tests`, cite `#1247`.
   - Admin action required: register `identity-boundary-canary` as a required check on `main` at https://github.com/Priivacy-ai/spec-kitty-saas/settings/branches.

### T012: Validate saas workflow YAML; assert no Fly spin-up

**Steps**:
1. YAML validation:
   ```bash
   python3 -c "
   import yaml,sys
   d=yaml.safe_load(open('.github/workflows/canary-gate.yml'))
   j=d['jobs']['identity-boundary-canary']
   assert j['name']=='identity-boundary-canary'
   # Pinned SHA check:
   assert any(s.get('with',{}).get('ref')=='4d5206e08a30bf23ae4dabae532dc0e355078e16' for s in j['steps'])
   # Env contract check:
   env=j.get('env',{})
   for k in ('SPEC_KITTY_ENABLE_SAAS_SYNC','SPEC_KITTY_E2E_TRUSTED_RUNNER','SPEC_KITTY_CANARY_TOKEN'):
       assert k in env, f'missing env: {k}'
   # No Fly spin-up:
   yaml_text=open('.github/workflows/canary-gate.yml').read().lower()
   assert 'flyctl' not in yaml_text and 'fly apps create' not in yaml_text, 'fly spin-up forbidden'
   print('OK')
   "
   ```
2. (Optional) `actionlint .github/workflows/canary-gate.yml`.

## Files

- `.github/workflows/canary-gate.yml` — NEW, ~75 lines
- `README.md` — patched with ~50 new lines

## Validation

- [ ] Worktree on `mission/identity-boundary-ci-gate-saas-rerun`, NOT `main`.
- [ ] Workflow file exists and parses.
- [ ] Job name is `identity-boundary-canary` exactly.
- [ ] All three env vars present (`SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_E2E_TRUSTED_RUNNER`, `SPEC_KITTY_CANARY_TOKEN`).
- [ ] Pinned SHA exact.
- [ ] No `flyctl` / `fly apps create` anywhere in the workflow.
- [ ] Concurrency group `identity-boundary-canary` to serialize against deployed-dev.
- [ ] README has the "Identity-Boundary CI Gate" section with secret-name contract, pinned SHA, SHA-bump procedure, and admin action.

## Edge cases / risks

- **`SPEC_KITTY_CANARY_TOKEN` unset on first PR**: workflow fails clearly because the SaaS client library can't auth. README documents the secret-name contract so the admin knows what to provision. Reviewer treats this as expected first-run behavior, not a workflow bug.
- **deployed-dev is itself down**: the workflow can't distinguish "saas PR broke contract" from "deployed-dev is sick". Both fail the gate. PR author should rerun once the canary script's preflight passes.
- **Concurrent saas PRs**: `concurrency.group: identity-boundary-canary` (NOT keyed by ref) serializes all canary runs against deployed-dev — only one PR's canary runs at a time. `cancel-in-progress: false` so an in-flight canary isn't aborted by a newer PR. Trade-off: slow under high PR throughput; acceptable for the saas repo's actual PR volume.
- **Rogue `run_sync_daemon` on the GHA runner**: not possible (fresh runner per job).

## Definition of Done

- All four subtasks complete.
- Workflow file and README diff staged on `mission/identity-boundary-ci-gate-saas-rerun`.
- YAML validation script returned `OK`.
- WP moves to `for_review` via `spec-kitty next`.

## Reviewer guidance

Reviewer checks:
- Job name match.
- Pinned SHA character-exact.
- All three env vars present.
- No Fly spin-up logic.
- Concurrency group is NOT keyed by ref (must be the literal string so all PRs serialize).
- README secret-name contract is the FIRST load-bearing fact in the section.
- LOC delta within ~120 lines budget.

## Activity Log

- 2026-05-21T11:02:12Z – claude – shell_pid=83157 – Assigned agent via action command
