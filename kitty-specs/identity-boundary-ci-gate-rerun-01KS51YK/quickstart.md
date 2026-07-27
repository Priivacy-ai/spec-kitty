# Quickstart: Identity-Boundary CI Gate

## I am an engineer; my PR's gate is red. What do I do?

### spec-kitty `drift-detector` red

Rerun the test locally:

```bash
cd Priivacy-ai/spec-kitty
uv sync --frozen --extra dev
uv run pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v
```

If it fails locally too, your change broke the canonical-registry
recognition contract. Read the test source at
`tests/sync/test_diagnose.py:417` and either restore the contract
or, if your contract change is intentional, update the test in the
same PR (and add a CHANGELOG entry explaining the contract bump).

### spec-kitty-events `cross-repo-harness-tests` red

The e2e harness can't resolve your new envelope shape. Rerun the
harness locally against your branch:

```bash
cd Priivacy-ai/spec-kitty-end-to-end-testing
git checkout 4d5206e08a30bf23ae4dabae532dc0e355078e16
uv sync --frozen
uv pip install -e /path/to/your/spec-kitty-events-checkout
uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/ -v
```

The failing assertion will name the field that broke. Either restore
backward compatibility or bump the pinned SHA in
`.github/workflows/cross-repo-harness-tests.yml` AND ship the
matching harness update in the e2e repo in the same coordinated drop.

### spec-kitty-saas `identity-boundary-canary` red

Download the workflow's `artifacts/sync_identity_boundary/runs/`
artifact from the failing job's summary page. Inspect
`run-1.json`:

```bash
jq '.outcome, .failure_reason' run-1.json
```

If `outcome == "fail"`, the canary detected an identity-boundary
violation against deployed-dev. Common causes:
- SaaS DB has stale rows (do NOT delete; consult the orchestrator).
- Identity-resolution code changed and dropped a field the canary
  pins (`project_uuid`, `mission_slug`, `aggregate_type`,
  `aggregate_id`, `content_hash`).
- The SaaS deployed-dev instance is itself down or behind on a
  recent backend change.

## I need to bump the pinned e2e SHA. How?

1. Get the new SHA:
   ```bash
   unset GITHUB_TOKEN
   gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/commits/main --jq .sha
   ```
2. Verify the new SHA still contains the directories / scripts the
   workflows reference:
   ```bash
   gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/contents/tests/unit/identity_boundary --ref <NEW_SHA>
   gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/contents/tests/identity_boundary/unit --ref <NEW_SHA>
   gh api repos/Priivacy-ai/spec-kitty-end-to-end-testing/contents/scripts/run-sync-identity-boundary-canary.sh --ref <NEW_SHA>
   ```
3. Update the `ref:` field in:
   - `Priivacy-ai/spec-kitty-events/.github/workflows/cross-repo-harness-tests.yml`
   - `Priivacy-ai/spec-kitty-saas/.github/workflows/canary-gate.yml`
4. Open one PR per repo. CI will exercise the new SHA on the bump
   PR itself before merge.

## I need to register the required check after a PR merges. How?

See `contracts/check-names.md` for the exact admin steps.
