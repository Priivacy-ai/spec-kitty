# Quickstart: Do Dispatch Open-Op Lifecycle

Verify the mission end-to-end in a scratch spec-kitty project:

```bash
# 1. Dispatch — Op opens, does NOT close
spec-kitty do "fix the flaky retry test" --json | tee /tmp/do.json
# expect: "status": "open", a close_contract object, and kitty-ops/<id>.jsonl
# containing exactly one started event (no completed event)

ID=$(jq -r .invocation_id /tmp/do.json)

# 2. Doctor sees the orphan
spec-kitty doctor ops --json   # expect: <id> listed, exit 1

# 3. Agent closes with a real outcome
spec-kitty profile-invocation complete --invocation-id "$ID" --outcome done
# expect: completed event with outcome=done, closed_by=agent;
# auto-commit "op(<profile>): <action> [<id8>]" in git log

# 4. Double close is refused
spec-kitty profile-invocation complete --invocation-id "$ID" --outcome done
# expect: AlreadyClosedError, exit 1

# 5. Stale sweep
spec-kitty do "another task" --json   # leave open
spec-kitty doctor ops --close-stale --threshold 0 --json
# expect: swept=1, outcome=abandoned, closed_by=doctor_sweep, auto-committed

# 6. Session presence (Claude Code project)
spec-kitty session-start
# with an open Op present: orientation lists it with the close command

# 7. Migration idempotency (repo with legacy kitty-ops records)
spec-kitty upgrade   # runs op-record schema v2 migration
spec-kitty upgrade   # second run: no changes (idempotent)
```

Test suite anchors: `tests/specify_cli/invocation/cli/test_do.py` (open-Op dispatch), `tests/specify_cli/invocation/test_doctor_ops.py` (sweep), `tests/upgrade/` (migration), `tests/specify_cli/invocation/test_propagator*.py` (envelope v2).
