# Quickstart: Runtime-State Corpus Cutover

Operator + maintainer runbook for the #2816 cutover. (Developer test discipline at the bottom.)

## Operator: migrate a corpus manually

```bash
# 1. Preview — seeds nothing, flips nothing; shows per-mission would-seed counts.
spec-kitty migrate backfill-runtime-state --dry-run

# 2. Real run — seeds events, verifies count+value parity vs the old reader,
#    flips status_phase ONLY for missions that pass. Non-zero exit if any fail.
spec-kitty migrate backfill-runtime-state

# 3. Scope to one mission if needed (mission_id / mid8 / slug).
spec-kitty migrate backfill-runtime-state --mission <handle>
```

- **Idempotent**: re-running seeds nothing and re-flips nothing.
- **Fail-closed**: a parity mismatch (or a fault-injected corrupt seed) aborts *that mission's* flip and
  exits non-zero, naming the mismatch. No unverified mission is ever flipped.

## Upgrading user: automatic migration

`spec-kitty upgrade` runs the runtime-state backfill+verify as an auto-discovered migration:

- **Legacy deployment** → corpus is backfilled, verified, and flipped as part of the upgrade.
- **Fresh install** (no `kitty-specs/` or no legacy runtime state) → no-op.
- **Verify failure** → the migration step aborts with an operator-actionable message; the deployment is
  left in a consistent, non-partially-flipped state. Investigate the named mission, re-run
  `spec-kitty upgrade` (or the CLI) after resolving.

**Precondition**: do not run other `spec-kitty` runtime commands concurrently with `spec-kitty upgrade`
(the migration closes the new-code-meets-un-backfilled-corpus window inside the upgrade command itself —
see research D-02).

## What changes for you after cutover

- Runtime WP state (`shell_pid`, `agent`/`assignee`, `tracker_refs`, subtask completion, review) is read
  from the **event log**, not `tasks/WP##.md`. A runtime transition writes **0 bytes** to the WP file.
- The phase-1 `status_phase` flag no longer gates anything — the snapshot is always authority.
- Nothing changes for the `lane` field (still frontmatter-authored; separate follow-up).

## Verify the end-state

```bash
# predicate is gone (expect 0 hits):
grep -rn "phase1_snapshot_authority_active" src/ ; echo "exit $?"

# #2093 invariant passes with an empty tolerated set:
uv run --extra test python -m pytest -p no:cacheprovider tests/architectural/test_2093_authority_invariant.py

# dead-symbol gate green (frozenset un-pinned):
uv run --extra test python -m pytest -p no:cacheprovider tests/architectural/test_no_dead_symbols.py
```

## Developer test discipline (CRITICAL)

- **Always** `uv run --extra test python -m pytest -p no:cacheprovider <FILE>` — bare `python` resolves a
  sibling checkout and yields false greens.
- **Never** run the whole `tests/architectural/` directory — it hangs. Per-file, each with a timeout.
- **Pre-existing reds** (`SYNC_DISABLE_ENV_VARS` arch-adversarial phantom; ADR-2026-07-17-1 known P0s)
  are NOT this mission's — confirm on the merge-base before attributing a red to this diff.
- `test_no_dead_symbols.py` pins by **content hash** — editing a pinned symbol's body breaks its pin;
  here we *remove* the pins (the symbols gain callers), which is the intended un-pin.
