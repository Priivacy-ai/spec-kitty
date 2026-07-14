# Contract — Explicit shard-registry seam (IC-10 / FR-011, #2621)

## Behaviour
- GIVEN the shard registry is assembled via explicit `register(group)` calls (not import side-effect),
  WHEN a row owner registers a `ShardGroup`,
  THEN `all_groups()` returns it; `register` is idempotent and rejects a duplicate key.
- GIVEN a group named in the expected-group manifest is NOT registered,
  WHEN the completeness guard runs,
  THEN it fails with a diagnosable "group `<name>` not registered" — NEVER a bare `KeyError`.
- GIVEN the `tests/next` root has no registered group,
  WHEN collection marks tests,
  THEN the guard fails loud (no test universe is silently left unmarked).

## Non-fakeable evidence
- A regression that removes the `_next_shard_map` registration asserts the guard emits the diagnosable message (assert on the message, not just "raises").
- A regression that asserts an unmarked `tests/next` universe fails, not passes.

## Anti-goals
- Do NOT keep the `# noqa: F401` import-for-side-effect line as the assembly mechanism.
- Do NOT collapse `arch` and `next` ownership into one module — keep row-owners separate, registered through the seam.
