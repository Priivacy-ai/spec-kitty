# Implementation Plan: Identity-Boundary CI Gate (Rerun)

**Branch**: `mission/identity-boundary-ci-gate-rerun`
**Date**: 2026-05-21
**Spec**: `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/spec.md`
**Mission ID**: `01KS51YKDSHF73EBDMFSFH3RMP`
**Tracker**: [`Priivacy-ai/spec-kitty#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247)

## Summary

Add three GitHub Actions workflow files, one per repo (`spec-kitty`,
`spec-kitty-events`, `spec-kitty-saas`), so that every PR opened against
any of them runs the appropriate slice of the identity-boundary canary
protocol before merge. Each workflow exposes a stable, named job that a
human admin can register as a required check on the `main` branch.
Update each repo's README with a discoverable section that documents
the gate and the pinned-SHA bump procedure.

This mission is a re-run of a prior attempt (PRs spec-kitty#1252,
saas#261, events#35 — all CLOSED) that bypassed formal ceremony. This
attempt uses the full specify → plan → tasks → analyze → Renata →
implement-review → mission-review chain.

## Technical Context

**Language/Version**: YAML 1.2 for workflows; bash for inline shell;
Python 3.11+ for the existing `tests/sync/test_diagnose.py` (already
on main of spec-kitty).
**Primary Dependencies**: GitHub Actions runtime (`ubuntu-latest`);
`actions/checkout@v4` for both same-repo and cross-repo checkouts;
`astral-sh/setup-uv@v3` for installing uv; the e2e repo's
`scripts/run-sync-identity-boundary-canary.sh` (referenced by SHA, not
copied).
**Storage**: N/A — workflows are stateless CI scaffolding. Artifacts
written during a run land under `artifacts/sync_identity_boundary/`
inside the job's workspace, optionally uploaded via
`actions/upload-artifact@v4` for post-mortem.
**Testing**: Each workflow's "test" is structural: the YAML is parsed
by GitHub Actions on push, and the named job appears in the PR checks
list. For the spec-kitty workflow, a local sanity command verifies the
pinned test passes today: `uv run pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v`.
**Target Platform**: GitHub Actions hosted runners (`ubuntu-latest`).
The saas canary job needs network reachability to
`spec-kitty-dev.fly.dev`; standard GitHub Actions egress satisfies
this.
**Project Type**: CI / infrastructure-as-code. No application source
code changes.
**Performance Goals**:
- saas canary workflow: p95 < 8 minutes (matches e2e#41 evidence cadence).
- events cross-repo workflow: p95 < 4 minutes (clone + uv sync + 2 small unit-test directories).
- spec-kitty drift-detector workflow: p95 < 2 minutes (one discrete pytest invocation, no matrix).
**Constraints**:
- No SaaS DB / queue / readiness / ingress mutation.
- No ephemeral Fly app spin-up per PR.
- No mutation of branch-protection rules via `gh api`.
- All workflow files must have distinct names from sibling-mission
  workflows already on open PRs (see C-001).
- Planning commits must not land on local or remote `main` of any
  repo (see C-009 + planning-branch mitigation below).
**Scale/Scope**: Three workflow files + three README sections + one
cross-repo manifest in the mission directory. Approximately 200-300
lines of YAML + 100-200 lines of Markdown across all three repos. Zero
lines of Python or production code changed.

## Charter Check

The Spec Kitty Charter (loaded via `spec-kitty charter context --action
plan --json`, mode=compact) declares:

- **Template set**: software-dev-default → matches our software-dev mission type.
- **Tools**: git, mypy, pytest, ruff, spec-kitty → workflows invoke
  uv + pytest only (saas canary script handles its own pytest call;
  events workflow invokes pytest directly; spec-kitty workflow invokes
  pytest directly). mypy and ruff are out of scope (no Python code
  added by this mission).
- **Languages**: python → not modified; workflows reference existing
  Python tests.
- **Directives**: DIR-001 through DIR-013 — none of these directives
  conflict with adding net-new CI workflow files in cross-repo siblings.
  In particular, no directive prohibits cross-repo workflows; the
  identity-safety rules apply to identifier renames (not relevant here);
  the canonical-producer rule applies to event emission (not relevant
  to CI scaffolding).
- **Tactics**: none active for this action.

**Verdict (entry gate)**: PASS — no charter violations.

**Verdict (post-design re-check)**: PASS — design surfaces only YAML
workflow files and README markdown. No source code, no canonical
producer touched, no identifier renamed, no DB or ingress affected.

## Architecture

### Workflow #1: spec-kitty `drift-detector.yml`

**Repo**: `Priivacy-ai/spec-kitty`
**Path**: `.github/workflows/drift-detector.yml`
**Job name** (for branch protection): `drift-detector`
**Trigger**: `pull_request` against `main`; `push` to `main`.
**Steps**:
1. Checkout PR head.
2. Install uv via `astral-sh/setup-uv@v3`.
3. `uv sync --frozen --extra dev` (matches existing CI lockfile contract).
4. `uv run pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v`.
5. Exit code propagates as job status.

**Why a discrete workflow file and not a `ci-quality.yml` job?**
`ci-quality.yml` runs a matrix where job names vary per slice
(`test (3.11)`, `test (3.12)`, etc.). Branch protection requires
naming an exact check string; matrix-varying names are brittle for
required-check registration. A discrete workflow gives us one stable
job name (`drift-detector`) that admins can register once and forget.

### Workflow #2: spec-kitty-events `cross-repo-harness-tests.yml`

**Repo**: `Priivacy-ai/spec-kitty-events`
**Path**: `.github/workflows/cross-repo-harness-tests.yml`
**Job name**: `cross-repo-harness-tests`
**Trigger**: `pull_request` against `main`; `push` to `main`.
**Pinned e2e SHA**: `4d5206e08a30bf23ae4dabae532dc0e355078e16`
**Steps**:
1. Checkout the spec-kitty-events PR head into `./events`.
2. Checkout the e2e harness at the pinned SHA into `./e2e` via
   `actions/checkout@v4` with `repository: Priivacy-ai/spec-kitty-end-to-end-testing`
   and `ref: 4d5206e08a30bf23ae4dabae532dc0e355078e16`.
3. Install uv. `cd e2e && uv sync --frozen` to install the harness deps.
4. Override the locally-installed `spec-kitty-events` package with the
   PR's HEAD via `uv pip install -e ../events` so the harness tests run
   against the new envelope shape.
5. `uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/ -v`.
6. Upload `artifacts/sync_identity_boundary/` on failure (best-effort).

**SHA bump procedure** (documented in README): when an intentional
contract change ships in spec-kitty-events that is incompatible with
the pinned harness, bump the SHA in this workflow in the same PR that
ships the contract change. Reviewer must verify the new SHA's
identity-boundary tests reflect the new contract.

### Workflow #3: spec-kitty-saas `canary-gate.yml`

**Repo**: `Priivacy-ai/spec-kitty-saas`
**Path**: `.github/workflows/canary-gate.yml`
**Job name**: `identity-boundary-canary`
**Trigger**: `pull_request` against `main`; `push` to `main`.
**Steps**:
1. Checkout PR head into `./saas`.
2. Checkout the e2e harness at the pinned SHA into `./e2e`.
3. Install uv. `cd e2e && uv sync --frozen`.
4. Export `SPEC_KITTY_ENABLE_SAAS_SYNC=1`,
   `SPEC_KITTY_E2E_TRUSTED_RUNNER=1`,
   `SPEC_KITTY_CANARY_TOKEN=${{ secrets.SPEC_KITTY_CANARY_TOKEN }}`.
5. Invoke `./scripts/run-sync-identity-boundary-canary.sh --single --yes`
   from inside `./e2e`. The script handles its own preflight (env, TTY,
   rogue-daemon check) and exits non-zero on canary failure.
6. Upload `artifacts/sync_identity_boundary/runs/` on success or failure.

**Why deployed-dev and not ephemeral Fly?** The brief's operating rule
explicitly forbids ephemeral Fly per-PR. deployed-dev is the cheap,
fast, isolated target. Race conditions between concurrent PR canary
runs are mitigated by the canary's own pre-run hygiene gate (rogue
`run_sync_daemon` detection).

**Secret-name contract** (documented in PR body for admin):
- `SPEC_KITTY_CANARY_TOKEN` — canary-only API token for the SaaS
  deployed-dev instance. If unset, the workflow fails clearly; the
  admin provisions on first failure.

## Project Structure

### Documentation (this feature)

```
kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/
├── plan.md                      # This file
├── spec.md                      # Mission spec
├── tasks.md                     # Phase 2 output (tasks command)
├── meta.json                    # Mission identity metadata
├── status.events.jsonl          # Append-only WP state log
├── tasks/                       # Per-WP files (WP##.md)
├── analyze-run-N.md             # Per-iteration analyze captures
├── renata-review-N.md           # Per-iteration Renata captures
├── mission-review.md            # Final mission-review verdict
├── intent-vs-outcome.md         # Final manual gate
├── retrospective.md             # Closing artifact
└── cross-repo-manifests/
    ├── spec-kitty.md
    ├── spec-kitty-events.md
    └── spec-kitty-saas.md
```

### Source (changes per repo)

```
# Priivacy-ai/spec-kitty (this repo)
.github/workflows/drift-detector.yml   # NEW
README.md                              # +1 section "Identity-Boundary CI Gate"

# Priivacy-ai/spec-kitty-events
.github/workflows/cross-repo-harness-tests.yml   # NEW
README.md                                        # +1 section

# Priivacy-ai/spec-kitty-saas
.github/workflows/canary-gate.yml   # NEW
README.md                           # +1 section
```

**Structure Decision**: Multi-repo CI scaffolding. The mission directory
in `spec-kitty/kitty-specs/` is the planning home; the implementation
hunks land in three sibling repos via three separate PRs from three
distinct lane branches (one per repo).

## Phase 0: Research

Open questions consolidated in `research.md`:

1. **Is the pinned e2e SHA stable?** → Yes. Verified
   `gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/commits/main --jq .sha`
   returns `4d5206e08a30bf23ae4dabae532dc0e355078e16` at planning time.
   The contents at that SHA include both
   `tests/unit/identity_boundary/` and `tests/identity_boundary/unit/`.
2. **Does `TestCanonicalRegistryRecognition` exist and pass on
   spec-kitty main?** → Yes. `tests/sync/test_diagnose.py` line 417
   defines `class TestCanonicalRegistryRecognition`. Will run locally
   to confirm pass.
3. **What is the canary script's CI contract?** → Documented in
   `scripts/run-sync-identity-boundary-canary.sh` header:
   - `--single` runs once (smoke); `--yes` bypasses TTY confirm.
   - Requires `SPEC_KITTY_ENABLE_SAAS_SYNC` and
     `SPEC_KITTY_E2E_TRUSTED_RUNNER`.
   - Exit 2 = preflight failure; non-zero (other) = canary failure.
4. **Sibling-PR workflow-file collisions?** → Confirmed distinct names:
   - spec-kitty#1250 uses `canonical-producer-lint.yml`.
   - saas#260 uses `canonical-producer-lint.yml`.
   - saas#262 (sunset carve-out) uses `sunset-check.yml`.
   - Our names: `drift-detector.yml`, `cross-repo-harness-tests.yml`,
     `canary-gate.yml`. No overlap.

## Phase 1: Design & Contracts

**Data model**: N/A — CI scaffolding has no data model.
**Contracts**: The "contracts" are the workflow job names that branch
protection registers:
- `drift-detector` (spec-kitty)
- `cross-repo-harness-tests` (spec-kitty-events)
- `identity-boundary-canary` (spec-kitty-saas)

These names are the immutable contract between this mission's PRs and
the post-merge branch-protection registration step the admin will do.
Captured in `contracts/check-names.md` (Phase 1 output).

**Quickstart**: `quickstart.md` will document the
local-engineer-rerunning-the-gate procedure:
1. How to invoke each workflow's underlying command locally.
2. How to read a red canary's `runs/run-1.json` and diagnose.
3. How to bump the pinned e2e SHA.

## Complexity Tracking

No charter violations to justify.
