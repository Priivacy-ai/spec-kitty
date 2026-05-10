# TeamSpace Mission-State Repair

Spec Kitty can repair historical `kitty-specs/` mission state before a repository is connected to TeamSpace. The repair is deterministic and writes only repository-local mission artifacts plus a manifest under `.kittify/migrations/mission-state/`.

Run the audit first:

```bash
spec-kitty doctor mission-state --audit --json
```

For a launch/readiness gate, fail on TeamSpace blockers:

```bash
spec-kitty doctor mission-state --audit --fail-on teamspace-blocker
```

`teamspace-blocker` includes all error findings plus warning-level
historical shapes that TeamSpace must not import as authoritative state:
legacy keys, forbidden typed side-log keys, snapshot drift, corrupt JSONL,
missing/invalid identity, and duplicate mission IDs. JSON reports include
`repo_summary.teamspace_blockers` and
`repo_summary.missions_with_teamspace_blockers`.

To verify the packaged survey fixture pack used by the audit contract:

```bash
spec-kitty doctor mission-state --audit --include-fixtures --json
```

The repository also ships an opt-in GitHub Actions gate,
`TeamSpace Mission-State Readiness`, which can be run manually from Actions.
It runs the same audit with a selectable `--fail-on` threshold and uploads
`mission-state-audit.json` even when the gate fails.

Then repair the repository:

```bash
spec-kitty doctor mission-state --fix
```

After repair, validate the TeamSpace import shape without sending anything to the server:

```bash
spec-kitty doctor mission-state --teamspace-dry-run --json
```

The dry-run synthesizes canonical Spec Kitty event envelopes in memory and validates them with `spec-kitty-events` 5.0.0. The on-wire `schema_version` remains `3.0.0`; package version `5.0.0` is the contract-library release that defines and validates that canonical envelope.

## Distributed Git Safety

`--fix` refuses to run when relevant mission paths are dirty unless `--allow-dirty` is supplied. It also checks linked worktrees that share the same Git common directory and takes an exclusive `.git/spec-kitty-mission-state.lock` while writing.

For teams, use this sequence:

1. Ask contributors to stop editing `kitty-specs/` temporarily.
2. Pull the target branch everywhere.
3. Run `spec-kitty doctor mission-state --audit --fail-on teamspace-blocker --json` and save the report.
4. Run `spec-kitty doctor mission-state --fix`.
5. Review the generated manifest and mission diffs.
6. Run `spec-kitty doctor mission-state --teamspace-dry-run --json`.
7. Commit the repair as one coordinated migration commit.

If another contributor has mission changes in flight, merge those changes first and rerun the repair. Do not hand-edit the generated manifest; it is checksum evidence for the repair.

## What The Repair Canonicalizes

- `meta.json` receives canonical `mission_id`, `mission_slug`, `slug`, mission number, and branch metadata when recoverable.
- Legacy keys such as `feature_slug`, `feature_number`, `mission_key`, and `legacy_aggregate_id` are removed.
- `status.events.jsonl` rows are normalized from historical status-row shapes to current status event fields.
- Known lane aliases such as `doing` are normalized to current lane names.
- `status.json` is regenerated with the same production reducer/materializer semantics used by normal status writes.
- Typed side-log rows found in `status.events.jsonl` are quarantined under the migration manifest directory instead of being imported into TeamSpace.

Runtime and decision side logs are launch-local evidence. The dry-run reports them with an explicit skipped disposition; they are not treated as TeamSpace status authority during the launch migration.

## Cross-Repo Rehearsal

The launch rehearsal for historical mission-state import is encoded in
`tests/migration/test_teamspace_migration_rehearsal.py`. It creates two
independent clones of the same historical fixture repository, runs repair on
both, verifies byte-identical local migration diffs, reruns repair to prove
idempotency, and validates that TeamSpace dry-run output is identical across
clones. It also proves raw historical status rows are rejected by the
`spec-kitty-events` 5.0.0 envelope model before they can reach live ingress.

Run the CLI-side rehearsal with:

```bash
uv run pytest tests/migration/test_teamspace_migration_rehearsal.py -q
```

Then run the SaaS import/idempotency side from `spec-kitty-saas`:

```bash
make local-db-bootstrap
make test-pytest ARGS='apps/sync/tests/test_cutover_contract.py apps/sync/tests/test_batch_sync.py apps/sync/tests/test_projection_pipeline.py -q'
make local-db-down
```

Those SaaS tests validate canonical historical preflight, import
deduplication, no persistence for rejected raw rows, and canonical mission
identity behavior when the CLI supplies a mission ID.
