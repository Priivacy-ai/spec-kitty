# Contract: Birth-Cutover Seed Ordering

## Inputs

- PRIMARY mission directory containing legacy WP artifacts and `meta.json`.
- Canonical status directory containing transition and annotation events.
- Deterministic mission/WP/field seed identity.

## Invariants

1. For each WP with existing history, every newly-created migration transition seed key is strictly less than
   every existing transition key for that WP.
2. For each WP with existing history, every newly-created migration annotation seed key is strictly less than
   every existing annotation key for that WP.
3. A cutover never changes the WP's pre-cutover canonical lane.
4. A cutover never replaces a later legitimate runtime-slot value.
5. Each non-null legacy `shell_pid`, `shell_pid_created_at`, and `agent` value is present in the raw
   seed evidence. It equals the reduced snapshot when no later legitimate writer owns that slot;
   otherwise the later legitimate value wins.
6. New seed IDs remain deterministic. An old colliding seed is repaired by a distinct deterministic
   compatibility identity that restores the state reduced with migration seeds excluded. Neither
   path rewrites an event or appends a duplicate on a second invocation.
7. Verification failure prevents `status_phase` from flipping.

## Caller Coverage

The same contract applies to:

- accept commit mode;
- merge birth cutover;
- upgrade migration;
- `migrate backfill-runtime-state` single mission;
- `migrate backfill-runtime-state` corpus mode.

`accept --no-commit` and diagnose validate convergence only; they do not exercise the stamp.

## Already-Seeded Compatibility

An event stream containing the pre-fix seed payload and its original terminal or runtime history is
the mandatory compatibility fixture. Re-appending the seed ID is not a repair: reducer deduplication
retains the first row. The implementation must append a separately namespaced deterministic repair
event only when the old seed currently corrupts a lane or slot. Its payload restores the value
obtained by reducing legitimate history with migration seeds excluded. A legitimate writer later
than the old seed remains authoritative. Verification accepts the historical seed only together
with the converged repair witness, and a byte-for-byte rerun appends nothing.

## Failure Contract

Unreadable or lower-bound timestamps, corrupt event streams, an unprovable strict floor, or a
missing claim-slot/repair witness fail closed through existing cutover result/error surfaces before
any partial append or `status_phase` flip. No caller may bypass the guard.
