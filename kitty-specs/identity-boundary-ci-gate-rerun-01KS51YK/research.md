# Research: Identity-Boundary CI Gate (Rerun)

## R-001: Is the pinned e2e SHA stable and contains the required test paths?

**Decision**: Pin to `4d5206e08a30bf23ae4dabae532dc0e355078e16`.

**Rationale**:
- Verified at planning time via `gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/commits/main --jq .sha`.
- Verified that the directories `tests/unit/identity_boundary/` and
  `tests/identity_boundary/unit/` exist at this SHA (both contain
  `__init__.py` and multiple `test_*.py` files).
- Verified that `scripts/run-sync-identity-boundary-canary.sh` exists
  at this SHA with the `--single --yes` flags this plan relies on.

**Alternatives considered**:
- Track `main` of the e2e repo (no pin): rejected — defeats the whole
  point of a contract gate; a flaky harness change would silently
  destabilize three sibling repos overnight.
- Pin to a tagged release: rejected — e2e does not currently cut
  semver tags; SHA pin is the only mechanism with sub-day precision.

## R-002: Does `TestCanonicalRegistryRecognition` exist and pass on spec-kitty main?

**Decision**: Yes, it exists at line 417 of
`tests/sync/test_diagnose.py`. The drift-detector workflow runs it.

**Rationale**: Verified via `grep -n "class TestCanonicalRegistryRecognition"`.
This test is the canonical drift-detector for
canonical-registry-vs-consumer-recognition.

**Alternatives considered**:
- Add a new dedicated drift-detector test: rejected — the existing
  test already covers the recognition contract and is what the brief
  explicitly names. Adding a new test is scope creep.

## R-003: What is the canary script's exact CI contract?

**Decision**: Invoke as
`./scripts/run-sync-identity-boundary-canary.sh --single --yes` with
env `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and
`SPEC_KITTY_E2E_TRUSTED_RUNNER=1`. Capture
`artifacts/sync_identity_boundary/` on success or failure.

**Rationale**: Read directly from the script (lines 1-100):
- `--single` runs once instead of the 4-run protocol.
- `--yes` skips the interactive trusted-runner confirm (mandatory in
  non-TTY CI).
- `SPEC_KITTY_ENABLE_SAAS_SYNC` is a hard preflight gate; absent → exit 2.
- `SPEC_KITTY_E2E_TRUSTED_RUNNER` is the trusted-runner gate; `--yes`
  is the explicit assertion in CI.
- Exit 2 = preflight failure (env missing, rogue daemon, etc.).
- Other non-zero = canary failure.
- Outcome artifact written to `artifacts/sync_identity_boundary/latest.json`
  then copied to `runs/run-${i}.json`.

**Alternatives considered**:
- Re-implement the canary inline in YAML: rejected — duplicates logic
  and breaks contract with the e2e repo.
- Use the 4-run protocol per-PR: rejected — too slow for CI (4x the
  wall-clock; deployed-dev shared resource pressure).

## R-004: Are sibling-PR workflow-file names collision-free?

**Decision**: Use `drift-detector.yml`, `cross-repo-harness-tests.yml`,
`canary-gate.yml`.

**Rationale**: Confirmed sibling open PRs use other names:
- spec-kitty#1250: `canonical-producer-lint.yml`
- saas#260: `canonical-producer-lint.yml`
- saas#262: `sunset-check.yml`
- events: no open PRs.

Our three filenames have zero overlap with any of the above. No
merge-conflict risk on `.github/workflows/`.

**Alternatives considered**:
- Coalesce into a single `regression-gates.yml` per repo: rejected —
  each gate is a discrete required-check name; one workflow file per
  gate keeps job naming stable.

## R-005: How should the spec-kitty CLI's local-main-commit behavior be mitigated?

**Decision**: Check out a planning branch
(`mission/identity-boundary-ci-gate-rerun`) in the canonical spec-kitty
repo BEFORE invoking `spec-kitty agent mission create` and any
follow-up planning commands. Confirmed via
`spec-kitty agent mission branch-context --json`: `current_branch`
now reports the planning branch, and all planning artifacts land
there, not on local `main`.

**Rationale**: The CLI's design is "planning happens in the
repository root checkout" — it commits to whatever branch the
canonical repo is on. By switching to a planning branch first, we
keep local `main` untouched. The prior subagent's attempts likely
ran from canonical-on-main, which is what the orchestrator brief
flagged as the leak.

**Alternatives considered**:
- Patch the CLI to refuse-on-main: rejected — out of scope for this
  mission.
- Plan entirely outside the CLI (write spec/plan/tasks manually):
  rejected — defeats the formal-ceremony requirement.

## R-006: Where does the saas canary auth token come from in CI?

**Decision**: GitHub Actions secret `SPEC_KITTY_CANARY_TOKEN`,
referenced as `${{ secrets.SPEC_KITTY_CANARY_TOKEN }}` and exported
into the job env. If the secret is unset at first run, the canary
script exits clearly because the SaaS API will reject anonymous
calls; the admin provisions on first failure.

**Rationale**: The brief explicitly forbids ephemeral Fly app spin-up
per PR; deployed-dev is the target. The canary script handles its
own SaaS auth via env vars the SaaS client library reads (the script
delegates to `uv run pytest tests/identity_boundary/`, which uses
the standard SaaS client config).

**Alternatives considered**:
- Inline-encode a service-account secret in the workflow: rejected —
  obvious security issue.
- Use OIDC federation with Fly: rejected — overkill for a single
  long-lived canary-only token.
