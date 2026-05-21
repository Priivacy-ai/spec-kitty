# Identity-Boundary CI Gate (Rerun)

**Mission ID:** `01KS51YKDSHF73EBDMFSFH3RMP`
**Mission Slug:** `identity-boundary-ci-gate-rerun-01KS51YK`
**Mission Type:** software-dev
**Tracker:** [`Priivacy-ai/spec-kitty#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247)
**Status:** specifying

## Purpose

Pin the 4-run identity-boundary canary protocol (that closed
[`spec-kitty-end-to-end-testing#41`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/41))
as a required CI gate on every PR opened against the three repos that can
break the SaaS identity-boundary contract silently:

- `spec-kitty` (CLI / canonical registries)
- `spec-kitty-events` (canonical pydantic envelopes the SaaS consumes)
- `spec-kitty-saas` (the strict consumer)

Today the canary is operator-driven and runs only when someone remembers.
Tomorrow's PR can break it silently. This mission installs a per-repo
required-check workflow that fails fast at PR time.

## User Scenarios & Testing

### Primary scenario

**Actor:** An engineer opens a PR against `Priivacy-ai/spec-kitty-saas` that
inadvertently changes the SaaS-side identity resolution code.

**Trigger:** PR is opened or pushed.

**Happy path:**
1. GitHub Actions runs `.github/workflows/canary-gate.yml`.
2. The workflow opts into the trusted-runner contract with canary-only
   credentials, invokes
   `./scripts/run-sync-identity-boundary-canary.sh --single` against the
   `spec-kitty-dev.fly.dev` deployed-dev target by cloning the e2e harness
   at a pinned SHA.
3. The single canary run produces `outcome=pass`; the job exits 0; the
   `identity-boundary-canary` required check turns green; PR can be merged.

**Failure path:**
1. The change broke an identity resolution invariant.
2. The canary run produces `outcome=fail`; the job exits non-zero; the
   required check turns red; merge is blocked until the contract is
   restored or the change is reverted.

### Sibling scenarios

**spec-kitty-events PR:** A PR is opened that changes a pydantic envelope.
`.github/workflows/cross-repo-harness-tests.yml` clones the e2e repo at a
pinned SHA and runs the harness-side unit tests
(`tests/unit/identity_boundary/`, `tests/identity_boundary/unit/`). If the
envelope drift breaks SaaS-side resolution assumptions, the unit suite
turns red; merge is blocked.

**spec-kitty PR:** A PR is opened that changes the canonical registry or
the diagnostic code path. `.github/workflows/drift-detector.yml` runs
`tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition` (and any
future drift-detector tests) as a stable, named required check. If the
canonical-registry recognition drifts, the check turns red; merge is
blocked.

### Edge cases

- **Pinned SHA goes stale (intentional contract change shipped to e2e):**
  Documented procedure in each repo's README explains how to bump the
  pinned SHA and what to verify before doing so.
- **deployed-dev is unreachable:** The saas canary workflow propagates
  the script's exit code; a transient outage is surfaced as a red check.
  The operator-facing retry path is the normal PR-recheck button.
- **Required-check registration:** GitHub branch protection cannot be
  mutated without admin scope on the protection API. The mission PR
  documents the exact required-check name to add and the URL to add it,
  but does not attempt to mutate protection rules via API.

## Domain Language

- **Identity-boundary canary:** The four-run protocol in
  `spec-kitty-end-to-end-testing/scripts/run-sync-identity-boundary-canary.sh`
  that verifies the SaaS identity-resolution contract end-to-end against
  deployed-dev. "--single" mode runs once; full protocol runs four times.
- **Pinned e2e SHA:** The specific commit on
  `Priivacy-ai/spec-kitty-end-to-end-testing@main` that the events workflow
  clones for cross-repo test execution. Today: `4d5206e08a30bf23ae4dabae532dc0e355078e16`.
- **Drift detector:** A class of tests (currently
  `TestCanonicalRegistryRecognition`) that asserts canonical registries in
  spec-kitty match the downstream consumer's expectations.
- **Required check:** A GitHub branch-protection rule that names a CI job;
  the PR cannot merge while the check is red or pending.

## Functional Requirements

| ID      | Description                                                                                                                                                                                                                                                                  | Status   |
|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-001  | A workflow file `.github/workflows/canary-gate.yml` exists in `Priivacy-ai/spec-kitty-saas` that runs the identity-boundary canary in `--single` mode against deployed-dev on every PR.                                                                                       | accepted |
| FR-002  | A workflow file `.github/workflows/cross-repo-harness-tests.yml` exists in `Priivacy-ai/spec-kitty-events` that clones `spec-kitty-end-to-end-testing` at SHA `4d5206e08a30bf23ae4dabae532dc0e355078e16` and runs harness identity-boundary unit tests on every PR.            | accepted |
| FR-003  | A workflow file `.github/workflows/drift-detector.yml` exists in `Priivacy-ai/spec-kitty` that runs `tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition` as a discrete, named job on every PR.                                                                     | accepted |
| FR-004  | Each of the three workflows emits a stable, branch-protection-friendly job name that an admin can register as a required check: `identity-boundary-canary` (saas), `cross-repo-harness-tests` (events), `drift-detector` (spec-kitty).                                       | accepted |
| FR-005  | Each repo's `README.md` gains a section ("Identity-Boundary CI Gate" or equivalent) explaining what the gate enforces, where the canary lives, how to bump the pinned e2e SHA when an intentional contract change ships, and the exact required-check name the admin must add. | accepted |
| FR-006  | Each PR body documents the explicit branch-protection action a repo admin must take after merge (which check name to register on `main`), since GitHub branch protection cannot be mutated without admin scope.                                                              | accepted |
| FR-007  | The saas workflow uses canary-only credentials sourced from GitHub Actions secrets (`SPEC_KITTY_CANARY_TOKEN`, etc.) — it must not require ephemeral Fly app spin-up per PR.                                                                                                  | accepted |
| FR-008  | The events workflow uses `actions/checkout` with `repository:` pinning + an explicit `ref:` to fetch the e2e harness at the pinned SHA, then runs the harness tests via `uv run pytest`.                                                                                      | accepted |
| FR-009  | The spec-kitty workflow exists as a discrete file from `ci-quality.yml` (which is matrix-sliced and has unstable per-slice job names that are brittle for required-check registration).                                                                                       | accepted |

## Non-Functional Requirements

| ID      | Description                                                                                                                                          | Status   |
|---------|------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| NFR-001 | The saas canary workflow completes within 8 minutes p95 on deployed-dev (single-run mode; matches script's measured cadence in `e2e#41` evidence). | accepted |
| NFR-002 | The events cross-repo workflow completes within 4 minutes p95 (clone + uv sync + pytest of two unit-test directories).                              | accepted |
| NFR-003 | The spec-kitty drift-detector workflow completes within 2 minutes p95 (single discrete pytest invocation, no matrix).                                 | accepted |
| NFR-004 | The workflow files are auditable to a human reader: each has a header comment describing the gate, the tracker issue, and the procedure for SHA bumps. | accepted |

## Constraints

| ID    | Description                                                                                                                                                                                                                                                                                                       | Status   |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| C-001 | Workflow file names MUST be distinct from sibling-mission workflows already on open PRs: `canonical-producer-lint.yml` (spec-kitty#1248, saas#260), `sunset-check.yml` (saas#258). Use `drift-detector.yml` (spec-kitty), `canary-gate.yml` (saas), `cross-repo-harness-tests.yml` (events).                       | accepted |
| C-002 | The mission MUST NOT change the canary script itself (`scripts/run-sync-identity-boundary-canary.sh` lives in e2e and is the closed artifact of e2e#41).                                                                                                                                                          | accepted |
| C-003 | The mission MUST NOT mutate GitHub branch-protection rules via API destructively. Document the required-check registration as a human-admin follow-up in each PR body.                                                                                                                                            | accepted |
| C-004 | The mission MUST NOT mutate the SaaS production or staging DB, queue, readiness counters, or ingress limits to make any check pass.                                                                                                                                                                               | accepted |
| C-005 | The mission MUST NOT cut a final `3.2.0` release; RCs only.                                                                                                                                                                                                                                                       | accepted |
| C-006 | All `gh` writes against `Priivacy-ai/*` MUST be prefixed with `unset GITHUB_TOKEN` so the keyring token is used.                                                                                                                                                                                                  | accepted |
| C-007 | The workflows are CI scaffolding; they are NOT event producers. Any inline data structures must carry the marker `# canonical-producer-exempt: #1247 — workflow scaffold, not an event producer`. (In practice the workflows have no inline event dicts; this constraint is precautionary against future drift.) | accepted |
| C-008 | The mission MUST be runnable end-to-end without admin scope on the GitHub API. The mission delivers the workflows; a human admin enables protection separately.                                                                                                                                                   | accepted |
| C-009 | The spec-kitty CLI's known planning-commit behavior commits to whichever local branch the canonical repo is on. The mission MUST set the canonical repo to a planning branch (`mission/identity-boundary-ci-gate-rerun`) before invoking planning commands, so local `main` is not polluted by ceremony commits.   | accepted |

## Success Criteria

- **SC-001:** When the three PRs merge, opening a deliberately-broken
  identity-resolution PR on saas (synthetic violation) results in the
  `identity-boundary-canary` required check turning red within 8 minutes.
- **SC-002:** When a deliberately-broken envelope PR is opened on events,
  the `cross-repo-harness-tests` required check turns red within 4 minutes.
- **SC-003:** When a deliberately-broken canonical-registry PR is opened
  on spec-kitty, the `drift-detector` required check turns red within
  2 minutes.
- **SC-004:** Each repo's README has a discoverable section describing
  the gate; a new engineer can find the SHA-bump procedure without
  reading source.
- **SC-005:** No planning ceremony commit lands on local or remote
  `main` of any of the three repos.

## Key Entities

- **GitHub Actions workflow file** (per repo) — declarative CI specification.
- **Pinned e2e SHA** — a single immutable commit pointer embedded in the events workflow.
- **README section** (per repo) — operator documentation.

## Assumptions

- Canary-only credentials are already provisioned as repo secrets in
  `Priivacy-ai/spec-kitty-saas` (`SPEC_KITTY_CANARY_TOKEN`,
  `SPEC_KITTY_E2E_TRUSTED_RUNNER` accepted at the script's `--yes` flag).
  If they are not yet provisioned, the workflow will be merged with the
  secret-name contract documented; an admin provisions on first failure.
- The e2e repo's `tests/unit/identity_boundary/` and
  `tests/identity_boundary/unit/` directories continue to exist at the
  pinned SHA (verified: SHA `4d5206e08a30bf23ae4dabae532dc0e355078e16`
  contains both).
- The drift-detector test
  `tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition` is
  stable; current code passes it (verified locally).

## References

- Tracker: [`spec-kitty#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247)
- Drift-class epic: [`spec-kitty#1198`](https://github.com/Priivacy-ai/spec-kitty/issues/1198)
- Launch-gate closing comment: [`e2e#41`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/41#issuecomment-4506163993)
- Workflow doctrine: `spec-kitty-mission-workflow.md`
- Program plan: `ci-start-here.md`
- Prior closed PRs (do not reuse branches): spec-kitty#1252, saas#261, events#35
