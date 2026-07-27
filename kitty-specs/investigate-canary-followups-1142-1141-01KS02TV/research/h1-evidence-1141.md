# #1141 Hypothesis 1 (CLI regression) — MOST LIKELY (not fully bisected)

**Claim**: `spec-kitty agent tasks move-task --to planned` from `in_review` does not reliably enqueue a `WPStatusChanged` row to the offline queue.

## Code path under test

The full intended emission pipeline for a backward `in_review → planned` transition is:

```
spec-kitty agent tasks move-task <wp> --to planned --note "<feedback>"
└─ src/specify_cli/cli/commands/agent/tasks.py:1751
   └─ if not force and _is_backward_transition(old_lane, canonical_lane):
        emit_force = True; emit_reason = "backward rewind: in_review -> planned: ..."
   └─ emit_status_transition(...) [src/specify_cli/status/emit.py:259]
      ├─ Step 5: _store.append_event_verified(feature_dir, event)   # writes to status.events.jsonl
      └─ Step 7: _saas_fan_out(event, mission_slug, repo_root, ...) [emit.py:483]
         └─ fire_saas_fanout(**kwargs) [src/specify_cli/status/adapters.py:112]
            └─ for handler in _saas_handlers: handler(**kwargs)
               └─ _saas_fanout_handler [sync/__init__.py, late-binding]
                  └─ emit_wp_status_changed(**kwargs) [src/specify_cli/sync/events.py:204]
                     └─ get_emitter().emit_wp_status_changed(...)
                        └─ OfflineQueue.enqueue(...)  # the row the canary peek expects
```

Every link in this chain is currently present in `main` (`commit 2881dfe94`).

## Git-log walk (commits touching the emission surface since 2026-02)

```
9713f9ea0  CLI Backward-Transition Emit Path (planning#16, Mission 2 of 4)
717c75185  Thread StatusEvent.at through SaaS fan-out (#1064)
b134bac59  Quality & DevEx Hardening 3.2 — epic #822 (mission 117)
3becc09f5  feat(kitty/mission-stable-320-p1-release-confidence-01KQTPZC): squash merge
9d95db33c  fix: allow sync controls with transition requests
03af0d62a  fix: include status metadata in saas fanout
... (and earlier)
```

`9713f9ea0` is the commit that introduced the backward-transition auto-promote in `tasks.py:1751-1759`. No commits *since the parent mission landed (`fdca93e14`)* have touched `src/specify_cli/status/emit.py`, `src/specify_cli/status/adapters.py`, `src/specify_cli/sync/__init__.py` or `src/specify_cli/sync/events.py`. **The pipeline as-shipped on `origin/main` is the same as when the canary captured its failure.**

## What the failure shape tells us

The peeked row is `for_review → in_review`, not `in_review → planned`. Per `h3-evidence-1141.md`, the peek operates on a settled SQLite WAL via a serialized subprocess — there is no race. So the rollback row is **simply not in the offline queue**.

Three sub-hypotheses for why it's not:

1. **Silent fan-out failure** (`fire_saas_fanout` swallows all exceptions per `adapters.py:121-126`):

   ```python
   for handler in _saas_handlers:
       try:
           handler(**kwargs)
       except Exception:
           logger.warning("SaaS fan-out handler failed; canonical status log unaffected", exc_info=True)
   ```

   If `_saas_fanout_handler` → `emit_wp_status_changed` → queue write raises (e.g., DB locked, schema mismatch, auth failure on first write), the warning is logged but the canary's later peek sees no row. **This is consistent with all observed evidence.**

2. **Guard refusal before emission**. `emit_status_transition` calls `validate_transition` at Step 3 (`emit.py:425`). If the guard returns `False` for an `in_review → planned` transition without `force=True`, the function raises `TransitionError` before either local persistence or fan-out. However, the auto-promote at `tasks.py:1751` sets `emit_force = True` before calling `emit_status_transition`, so the guard SHOULD permit. Worth verifying that the `force` kwarg actually reaches `emit_status_transition` (need to read the caller, ~`tasks.py:1789-1820`).

3. **Daemon ensure failure**. `_saas_fan_out` is called with `ensure_sync_daemon=True` by default. If `ensure_daemon=True` triggers a daemon-start which fails (auth required, network down, etc.), `fire_saas_fanout` would short-circuit. In the canary's environment, `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set and SaaS is reachable, but the actor's first call may legitimately fail to spin up.

## Why this WP can't fully bisect

Pinning the exact root cause requires:

- A trusted-runner workstation with `flyctl auth whoami` set up against `spec-kitty-dev.fly.dev`
- The ability to re-run scenario 4 (or just the `move-task --to planned` sequence) with `--verbose` / debug logging enabled
- Inspection of the offline queue SQLite DB between move-task exit and peek invocation
- A possible `pdb` checkpoint in `_saas_fan_out` / `emit_wp_status_changed`

This investigation mission was chartered to identify the root-cause direction, not to perform the bisect. Per C-003 of `spec.md`, the actual fix lands in a separate 1-WP follow-up mission.

## Verdict

**LIKELY** — H1 (CLI regression / silent fan-out failure on backward emission to the offline queue) is the most plausible explanation given the captured evidence. Sub-hypothesis 1 (silent fan-out swallow) fits all observed evidence best.

## Recommendation

**A — open a new mission.** The follow-up scope:

1. Add a logging breadcrumb between `_saas_fanout_handler` invocation and `emit_wp_status_changed` so silent fan-out failures surface in operator logs.
2. Trace the failing path in a trusted-runner environment using scenario 4 as the harness; either fix the silent-failure source or document a guarded fall-through.
3. Add a unit test that asserts a backward `in_review → planned` transition writes one and only one new row to a temp OfflineQueue.
4. Re-run scenario 4 against the merged-mission CLI to confirm green.

Estimated scope: 1 WP, 3-5 subtasks, ~1–2 operator days.
