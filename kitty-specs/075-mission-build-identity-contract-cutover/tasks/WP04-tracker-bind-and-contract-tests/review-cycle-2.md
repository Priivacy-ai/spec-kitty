---
affected_files: []
cycle_number: 2
mission_slug: 075-mission-build-identity-contract-cutover
reproduction_command:
reviewed_at: '2026-04-08T06:09:05Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
---

# WP04 Review Cycle 1 — Changes Requested

## Blocker 1 — identity_aliases.py re-added (same issue as WP03 cycle 1)

WP04 commit `c3a68500` adds `src/specify_cli/core/identity_aliases.py` back to the lane.
This file was deleted by WP02 (`0f37df1e`) and must stay deleted.
The commit message explicitly says "Restore ... removed out-of-scope by WP03, required by status/models.py" — this reasoning is wrong.
The cross-lane test collection failure from `status/models.py` importing the deleted module is EXPECTED and DOCUMENTED.
It must not be fixed by re-adding the stub.

Fix: `git rm src/specify_cli/core/identity_aliases.py && git commit -m "fix(WP04): remove re-added identity_aliases stub"`

## Blocker 2 — Out-of-scope test file modified

`tests/sync/tracker/test_saas_client_origin.py` is not in WP04's owned files list.
Revert it: `git checkout kitty/mission-075-mission-build-identity-contract-cutover -- tests/sync/tracker/test_saas_client_origin.py`
(If this causes a test failure due to the signature change, the existing test is a pre-existing problem outside WP04's scope.)

## What is correct in WP04

- `SaaSTrackerClient.bind_mission_origin()` extended with `build_id: str` — correct
- `origin.py` loads `ProjectIdentity` via `ensure_identity()` and passes `build_id` — correct
- `test_origin_bind.py` test asserting `build_id` in SaaS call — correct
- `test_contract_gate.py` provenance test — correct
