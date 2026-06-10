# Contract: `spec-kitty doctor ops` Stale Sweep

## Report mode (default, unchanged + extended)

`spec-kitty doctor ops [--json]` lists **all** open Ops (started, no completed event) with `invocation_id`, `profile_id`, `started_at`, and age. Exit 1 when any open Op exists (existing behavior).

## Sweep mode (new)

`spec-kitty doctor ops --close-stale [--threshold <hours>] [--json]`

- Closes every open Op with `started_at` older than `<hours>` (default **24**; `--threshold 0` closes all open Ops).
- Each close goes through the canonical executor close path: `OpCompletedEvent` with `outcome="abandoned"`, `closed_by="doctor_sweep"`, followed by close-time auto-commit.
- Ops younger than the threshold: reported, never closed.
- Race with concurrent manual close (`AlreadyClosedError`): reported as `already_closed`, sweep continues, not a failure.
- Exit codes: 0 when sweep completes (even if some were already closed); 1 only on write/IO errors. When open-but-fresh Ops remain after sweep, report them and exit 1 (consistent with report mode).

## JSON shape

```json
{
  "open_ops": [{"invocation_id": "01KT…", "profile_id": "…", "started_at": "…", "age_hours": 3.2, "action_taken": "none|closed_abandoned|already_closed"}],
  "swept": 2,
  "skipped_fresh": 1,
  "threshold_hours": 24
}
```

## Performance

Sweep completes in <5 s at 10,000 Op files (NFR-002); orphan detection uses the existing file-scan path (`list_orphan_ops`).

## Session presence (Claude Code)

- `spec-kitty session-start` output appends, when open Ops exist: count, ids with ages, and the close + sweep commands.
- Stop hook entry (registrar-generalized) prints a non-blocking reminder listing open Ops; always exits 0.
