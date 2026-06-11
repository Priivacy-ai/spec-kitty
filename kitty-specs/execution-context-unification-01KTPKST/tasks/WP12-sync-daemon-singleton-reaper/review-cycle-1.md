# WP12 Review — Cycle 1 (reviewer-renata, architect-alphonso process-lifecycle lens)

**Verdict: REJECT — one blocking issue. The reaper consolidation is architecturally sound and the
safety guard is correct; the block is a single, easily-fixable mypy regression on a changed line of an
owned file that violates the binding zero-mypy charter rule and was mis-reported as "clean".**

The collapse itself is genuinely good work — I want to be explicit that everything below the one blocker
passed. Fix the single issue and this is an approve.

---

## BLOCKING

### Issue 1 — New `[no-any-return]` mypy error introduced at `src/specify_cli/sync/orphan_sweep.py:116`

`mypy src/specify_cli/sync/orphan_sweep.py` now reports:

```
src/specify_cli/sync/orphan_sweep.py:116: error: Returning Any from function declared to return "dict[str, Any] | None"  [no-any-return]
```

This is a **WP12-introduced regression, NOT pre-existing.** I verified by checking out the base-branch
copy of `orphan_sweep.py` in place and running mypy on it:

```
git show kitty/mission-execution-context-unification-01KTPKST:src/specify_cli/sync/orphan_sweep.py
  → mypy: "Success: no issues found in 1 source file"
WP12 HEAD orphan_sweep.py
  → mypy: 1 error (no-any-return at line 116)
```

**Root cause:** `_probe_health` was rewritten from an inline implementation (whose body ended with
`return data if isinstance(data, dict) else None`, which mypy accepts) to a delegation:

```python
return _fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=_HEALTH_PROBE_TIMEOUT_S)
```

Although `daemon._fetch_health_payload` is annotated `-> dict[str, Any] | None`, `daemon.py` itself fails
mypy (the pre-existing `daemon.py:1059` `Popen[bytes]` vs `Popen[str]` error makes the module
partially-typed), so mypy treats the imported symbol's return as `Any`, and the bare `return` of an
`Any` into a `dict[str, Any] | None`-typed function trips `[no-any-return]`.

**Why this blocks (charter, binding — Code Quality):** *"New code MUST pass ruff and mypy with zero
issues and zero warnings. Do NOT disable, suppress, or relax checks to achieve this — fix the code
instead."* This is a changed line in an owned file (`orphan_sweep.py` is in `owned_files`).

**How to fix (pick one, no `# type: ignore`):**
- Narrow at the call site, restoring the explicit guard the inline version had:
  ```python
  data = _fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=_HEALTH_PROBE_TIMEOUT_S)
  return data if isinstance(data, dict) else None
  ```
  (Cheapest, behavior-identical, and re-asserts the dict contract locally.)
- OR make `daemon._fetch_health_payload` mypy-clean so its annotation is honoured downstream. Note the
  same delegation in `dashboard/lifecycle.py:160` is currently mypy-clean, so the minimal local narrow
  above is sufficient and lowest-risk.

**Note on the completion claim:** the implementer's WP note said *"ruff+mypy clean on changed code
(pre-existing daemon.py Popen + 2 dashboard-cli + 1 token-manager failures unrelated)."* This
`orphan_sweep.py:116` error is on changed code and was **not** disclosed. Per the charter's Pre-existing
Failure Reporting Rule, re-run `mypy` on each owned file after the fix and confirm zero issues before
re-submitting.

---

## EVERYTHING ELSE PASSED (recorded for the next cycle)

### 3→1 reaper collapse preserves all three behaviors (FR-015 / C-004) — PASS
The single canonical reaper `owner.reap_orphan_daemons` + single kill path `owner._sweep_daemon_process`
genuinely subsume the three prior reapers; behaviors verified individually:
- **Record-based** (`owner.is_orphan`/`list_orphan_records`): retained; the canonical reaper keys on
  daemon identity and excludes the recorded singleton via `scan_sync_daemons` (daemon.py:1187,
  `state_pid` exclusion).
- **Port-scan** (`orphan_sweep._sweep_one`): retained as a delegating shim. Crucially the
  **port-close success criterion is preserved** — `_sweep_one` still calls `_wait_for_port_close`
  after delegating signal escalation to `_sweep_daemon_process`, and still does the
  HTTP-shutdown-first step (which the canonical reaper deliberately does not). The
  `_port_closed_after_process_disappeared` helper was removed but its race semantics are folded into the
  new flow (process-gone → confirm port closed).
- **Cmdline-scan** (`daemon.scan_sync_daemons`/`cleanup_orphan_sync_daemons`): retained. Discovery still
  host-wide via `_iter_sync_daemon_processes`; `cleanup_orphan_sync_daemons` now delegates its kill to
  `_sweep_daemon_process` and keeps the documented "operator sees ALL their orphans regardless of
  interpreter" non-scoped diagnostic contract — correctly distinct from the scoped spawn-path reaper.

### Reaper-over-kill guard (THE safety issue) — SOUND
`reap_orphan_daemons` reaps a discovered `run_sync_daemon` process **only** when
`_process_executable_scope(proc) == canonical_executable_scope()` (symlink-resolved interpreter path).
Every fail-open path is closed:
- `proc_scope is None` (can't resolve `exe()`/cmdline) → `skipped_out_of_scope`, never killed.
- `psutil.AccessDenied` on lookup → `skipped_out_of_scope`, never killed.
- Different `$HOME`/venv/container interpreter → scope mismatch → skipped.
Proven by `test_reaper_skips_other_executable_daemons` driving the real code path (foreign
`/opt/other-venv/bin/python` daemon left untouched; `terminated is False`, `killed is False`). This is
the high-blast-radius gate and it holds.

### Singleton one-per-host/auth-scope (FR-014b, #1071) — PASS
`_ensure_sync_daemon_running_locked` calls `_reap_same_executable_orphans()` before spawn; it is
best-effort (`except Exception` → DEBUG log, swallow) so a reaper hiccup never blocks startup. Scoped by
executable identity, not per-checkout/per-context — matches the binding research
(`research/wp11-daemon-validation.md`) and the operator's one-per-host decision. The detached daemon
correctly keys on `DaemonOwnerRecord`/interpreter identity, not a `MissionExecutionContext`.

### C-005 / NFR-005 net-subtraction — PASS (real consolidation, not a 4th reaper)
After the change there is exactly one kill escalation (`owner._sweep_daemon_process`), one reaper entry
(`owner.reap_orphan_daemons`), one real `_is_process_alive` (daemon.py; dashboard delegates), and one
real localhost health-probe (`daemon._fetch_health_payload`; `orphan_sweep._probe_health` and
`dashboard._fetch_dashboard_json_payload` delegate). owner.py grows because it *hosts* the one canonical
reaper the others delegate to — confirmed via grep: only one `def _sweep_daemon_process`, one
`def reap_orphan_daemons` across `sync/` + `dashboard/`. Dashboard's `_fetch_dashboard_features_payload`
contract checks (`features` list) correctly remain in the caller, not the transport helper.

### SC-6b / SC-7 tests — PASS (genuine, no synthetic fixtures, no daemon leak)
`tests/sync/test_daemon_singleton_reaper_consolidation.py`: 8/8 green. SC-6b tests drive the real
`reap_orphan_daemons`/`_sweep_daemon_process` against in-memory fake psutil processes (no real
`run_sync_daemon` spawned → no test-induced leak). SC-7 tests are real source-inspection
(`def`-count over actual files) — they would fail if a duplicate reaper/probe were reintroduced.

### Gates re-run
- `pytest tests/sync tests/specify_cli/coordination` → **1784 passed, 6 skipped**.
- New WP12 test → **8 passed**.
- `ruff check` on all 4 owned files + new test → **All checks passed**.
- `mypy`: owner.py / lifecycle.py / new test → clean. orphan_sweep.py → **1 error (the blocker above)**.
- Pre-existing-failure confirmation: `daemon.py:1059` `Popen[bytes]`/`Popen[str]` confirmed pre-existing
  (function at base line 1015, untouched by WP12).

### Anti-pattern checklist
1. Dead code — PASS (`reap_orphan_daemons` wired into the spawn hot path via
   `_reap_same_executable_orphans`; `canonical_executable_scope`/`ReapResult` exported and consumed).
2. Synthetic-fixture test — PASS (tests exercise real production paths).
3. Silent empty return — PASS (the `except Exception` in `_reap_same_executable_orphans` is documented
   best-effort with a DEBUG log and an inline rationale; not a silent failure).
4. FR coverage — PASS (FR-014/FR-015 asserted by SC-6b/SC-7 tests against behavior, not comments).
5. Frozen surface — N/A.
6. Locked decision — PASS (one-per-host/auth-scope honoured; no per-action context).
7. Shared-file ownership — PASS (WP12 owns lane-l alone; all 4 files in `owned_files`).
8. Production fragility — PASS (no new bare `raise` on a transient race; spawn-path reap is swallowed).

### Scope — PASS
Diff touches exactly the 4 owned files + the new test. No terminology (`--feature`) regressions.
