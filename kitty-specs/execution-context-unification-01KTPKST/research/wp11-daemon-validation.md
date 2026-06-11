# WP11 Validation — daemon singleton + status-write routing (debugger-debby + reducer-randy)

Two independent validation agents inspected the live `sync/` + `dashboard/` code against the proposed
WP11 / FR-014. **Both converged on the same verdict and corrections.** Verdict: **SOUND-WITH-CHANGES**,
with one materially wrong premise that must be fixed before implementation.

## The false premise (both agents, independently)
**The sync daemon writes NO tracked status.** Grep of `src/specify_cli/sync/` shows zero
`materialize`/`status.json`/`emit_status_transition` calls — it only owns the SaaS event queue +
WebSocket. So "route the sync daemon's status writes through the facade" (T035) is a **no-op against a
write path that does not exist.**

**The actual background status writer is the DASHBOARD** — a separate process (port range 9237–9337,
distinct from the sync daemon's 9400–9450). It writes tracked `status.json` on **every kanban request**
via the **writing** `materialize()` (`status/reducer.py:318-346`, atomic replace, **no git-op guard, no
staleness gate**) from:
- `src/specify_cli/dashboard/handlers/features.py:169`
- `src/specify_cli/dashboard/scanner.py:557`

Note this is `materialize()`, **not** `materialize_if_stale()` (`status/views.py:131`) — so WP07's FR-005
git-op guard does **not** automatically cover the dashboard clobber.

So #1789 is genuinely **two different processes**: the **sync daemon** = the singleton leak (9400-9450);
the **dashboard** = the status-clobber-during-git-ops (9237-9337). The WP conflated them into one "daemon".

## Singleton-leak root cause (debugger-debby)
- Singleton is keyed on `DAEMON_STATE_FILE = ~/.spec-kitty/sync-daemon` → effectively keyed on **`$HOME`**
  (`sync/daemon.py:73-90`). The daemon is **intentionally machine-global / missionless** (spawned detached
  via `_background_script` with `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` — no CLI/mission graph at startup).
- Leak mechanism: `_reuse_or_cleanup_existing_daemon` recycles on `_daemon_version_matches` mismatch
  (`daemon.py:289-305,980-1012`). Two interpreters (editable vs pipx) ⇒ each sees the other's daemon as a
  version mismatch, kills the **one** recorded PID, spawns its own on a fresh port (`_find_free_port`
  9400→9450). The state file remembers only the last PID, so the rest become untracked orphans → fan-out.
- `scan_sync_daemons` / `cleanup_orphan_sync_daemons` (`daemon.py:1131-1214`) exist but are
  **diagnostic-only** — NOT wired into the `ensure_sync_daemon_running` spawn hot path. Nothing reaps at spawn.

## Corrected design (both agents)
1. **Singleton key is NOT a per-action ExecutionContext.** The detached daemon has no mission/WP/context at
   startup and cannot derive `primary_root` from WP03. The correct identity is the daemon's **own scope/
   registry** — `DaemonOwnerRecord` (`sync/owner.py:113-124`: auth_scope / queue_db_path /
   source_checkout_path). Fix = wire `cleanup_orphan_sync_daemons` / `orphan_sweep.sweep_orphans` into the
   `ensure_sync_daemon_running` spawn path, scoped by executable/auth-identity (so it doesn't kill
   legitimately-separate `$HOME`/container daemons).
2. **Status-write fix target is the dashboard, not `sync/`.** Switch the dashboard's bare `materialize()`
   to a non-writing read (`materialize_snapshot`, `reducer.py:289`) and/or the git-op-guarded path — so
   background processes stop writing tracked status. This is the real FR-014 substance.
3. **Facade shape mismatch:** `MissionStatus` (`status/aggregate.py`) is a **transition** API
   (emit event → materialize), NOT a "refresh my read snapshot" API. The dashboard does not emit
   transitions; it only reads. So "route dashboard writes through `MissionStatus.transition`" is a semantic
   mismatch — the correct alignment is "background reads use the read-only snapshot; nobody writes tracked
   status as a side-effect of a read," which honours the single-surface intent without abusing the facade.

## owned_files / dependency corrections (both agents agree)
- **REMOVE** `src/specify_cli/sync/runtime.py` (SyncRuntime WebSocket lifecycle — no status write, no
  singleton surface; scope creep).
- **ADD (mandatory, not out-of-map)** `src/specify_cli/dashboard/handlers/features.py` +
  `src/specify_cli/dashboard/scanner.py` — the real `materialize()` clobber sites.
- **KEEP** `sync/owner.py`, `sync/orphan_sweep.py`, `sync/daemon.py` (singleton/reaper consolidation).
- **Dependencies:** **add WP07** (the dashboard fix consumes its git-op guard / shares detection — else
  duplicate = C-005 violation). **Drop the hard WP03 dep** (singleton must not use per-action context).
  **WP02 is soft** — keep for conformance only; do NOT push the dashboard through `MissionStatus.transition`.

## C-005 net-subtraction prize (reducer-randy)
There are **three** sync-daemon orphan-reaping implementations today — `owner.py:is_orphan/list_orphan_records`
(~40 LOC), `orphan_sweep.py:enumerate_orphans/sweep_orphans/_sweep_one` (~250 LOC), and
`daemon.py:scan_sync_daemons/cleanup_orphan_sync_daemons/_iter_sync_daemon_processes` (~100 LOC) — plus a
duplicated `_is_process_alive` and health-probe across `sync/` and `dashboard/lifecycle.py`. WP11 should
**collapse to one reaper** keyed on the owner record (feeds NFR-005), not add a fourth.

## OPEN DECISION (both agents flagged — operator/architect call)
**One-per-host vs one-per-checkout.** The existing code is deliberately **machine-global** (one daemon per
`$HOME`/auth-scope). The WP says **one per checkout**. These conflict. #1071's leak is that different
checkouts/`$HOME`s each spawn one; "one per checkout" may be the *opposite* of the existing intent. This
must be resolved explicitly before implementation — it changes the singleton key.

## Risks the WP prompt missed
- An implementer would hunt `sync/` for a status write that doesn't exist, "out-of-map" the wrong dashboard
  file (`server.py` has no `materialize`), and the grep acceptance check would pass while the clobber survives.
- Reaper blast radius: `_iter_sync_daemon_processes` matches any `run_sync_daemon` cmdline host-wide — must
  scope by executable/auth identity or it regresses legitimate multi-user/container usage.
