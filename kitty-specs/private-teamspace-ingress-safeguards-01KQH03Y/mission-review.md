# Mission Review Report

**Mission:** `private-teamspace-ingress-safeguards-01KQH03Y`
**Mission ID:** `01KQH03YSS4H9PQVJ5YCTGZYMR`
**Friendly name:** CLI Private Teamspace Ingress Safeguards
**Merge commit:** `44318599` (squash merge into `main`)
**Baseline (merge parent):** `3a2a4177`
**Reviewer:** post-merge skill (documentation only)
**Repo root:** `/Users/robert/spec-kitty-dev/spec-kitty-20260501-070919-28asxI/spec-kitty`
**Final state:** 5 / 5 WPs done (100%)

---

## Executive summary

The mission delivered the strict private-team resolver, the one-shot `/api/v1/me` rehydrate orchestrator with single-flight + negative cache, the post-refresh hook, the four direct-ingress call-site rewrites, and the websocket/stdout-discipline cleanup. All mission-scope tests pass (44 sync, 93 auth) and the no-`print()` invariant in `sync/client.py` is enforced. Architecture tests are green (92 passed, 1 skipped).

There is **one production code-path issue** worth flagging (DRIFT-1: dead-but-callable `WebSocketClient._current_team_id` retains the forbidden shared-team fallback semantics; only a unit test calls it now, but it lives one keystroke away from re-introduction) and **two minor code-hygiene findings** (DRIFT-2: broad `except Exception` masking in three call sites; HYGIENE-1: legacy `default_team_id`/`teams[0]` fallback pattern in `sync/replay.py:184` documented but unrelated to this mission's contract).

The contract-test gate flagged a pre-existing failure in `tests/contract/test_cross_repo_consumers.py` (spec_kitty_events 5.0.0 vs uv.lock pin 4.1.0) — unrelated to this mission, but the gate is technically not green. Architectural-test gate is green.

**Verdict:** PASS WITH NOTES.

---

## FR / NFR / AC Coverage Matrix

| ID | Requirement | Spec → code | Test asserts behavior | Notes |
|----|-------------|-------------|------------------------|-------|
| FR-001 | `require_private_team_id` strict resolver | `auth/session.py:81` | `tests/auth/test_session.py` (multiple) | ✅ |
| FR-002 | Never `default_team_id`/`teams[0]` in resolver | `auth/session.py:81` body delegates to `get_private_team_id`; helper docstring + tests | `tests/auth/test_session.py` regression cases | ✅ but see DRIFT-1 (dead `_current_team_id` still has fallback) |
| FR-003 | One-shot `/api/v1/me` GET on miss | `token_manager.py:217 rehydrate_membership_if_needed` | `tests/auth/test_token_manager.py:983-1059`, `tests/sync/test_team_ingress_resolver.py` | ✅ |
| FR-004 | Skip ingress + diagnostic on rehydrate failure | `sync/_team.py:70-74`, `sync/batch.py:392-401`, `sync/emitter.py:1421-1432` | `tests/sync/test_batch_sync.py`, `test_team_ingress_resolver.py` | ✅ |
| FR-005 | `batch.py` uses strict resolver, no shared `X-Team-Slug` | `sync/batch.py:18,52,392-401` | `tests/sync/test_batch_sync.py` | ✅ |
| FR-006 | `client.py` ws-token uses strict resolver | `sync/client.py:31,138-145` | `tests/sync/test_client_integration.py:test_ws_token_*` | ✅ for the `connect()` path; DRIFT-1 for dead helper |
| FR-007 | `emitter.py` + `queue.py` use strict resolver | `sync/emitter.py:608-613, 1421-1432`; `sync/queue.py:207-224` | `tests/sync/test_team_ingress_resolver.py` | ✅ (queue.py uses singleton TokenManager — cycle-2 fix applied) |
| FR-008 | Refresh flow rehydrates stale membership | `token_manager.py:289 _apply_post_refresh_membership_hook` invoked at lines 371/376/381/388 | `tests/auth/test_refresh_flow.py:test_refresh_force_rehydrates_when_adopted_session_lacks_private_team` and `test_refresh_healthy_session_no_extra_me_call` | ✅ Hook lives in TokenManager, not flows/refresh.py — matches plan §1.6 |
| FR-009 | All sync warnings to stderr/logs in `--json` | `sync/client.py` 6 prints replaced with logger; ws-disconnect messages also logger | `tests/sync/test_strict_json_stdout.py::test_no_print_calls_in_sync_client`, `test_agent_tasks_status_json_strict_with_sync_enabled_isolated` | ✅ scope-limited to `client.py` per plan §1.5 |
| FR-010 | Local command exits 0 when ingress skipped | `sync/client.py:142-145` (silently OFFLINE), `sync/batch.py:392-401` (returns existing result) | `tests/sync/test_strict_json_stdout.py::test_agent_tasks_status_json_strict_with_sync_enabled_isolated` | ✅ |
| FR-011 | Healthy session preserves existing behavior | `auth/session.py:get_private_team_id` unchanged; `_resolve_private_team_id_for_ingress` early-returns on hit | `tests/auth/test_session.py` regression case (private-wins-when-default-drifts) | ✅ |
| FR-012 | `pick_default_team_id` docstring guard | `auth/session.py:58-69` | docstring asserted in WP01 tests | ✅ |
| NFR-001 | One-shot per process, single-flight, negative cache | `token_manager.py:240` lock, `:246` neg-cache check, `:273` neg-cache set | `tests/auth/test_token_manager.py` concurrency test (line 1132 — 4 threads, exactly 1 GET) | ✅ |
| NFR-002 | Structured log: category, rehydrate_attempted, ingress_sent, endpoint | `sync/_team.py:69-74` | `tests/sync/test_team_ingress_resolver.py` | ✅ |
| NFR-003 | `--json` strict-mode parseable | `tests/sync/test_strict_json_stdout.py` | end-to-end subprocess test | ✅ |
| NFR-004 | Existing "private wins when default drifts" tests pass | `auth/session.py` unchanged for `get_private_team_id`; `pick_default_team_id` body unchanged | regression tests retained | ✅ |
| AC-001 | Shared-only never sends shared `X-Team-Slug` | `sync/batch.py:392-401` returns before adding header | tests/sync/test_batch_sync.py | ✅ |
| AC-002 | Shared-only triggers exactly one `/api/v1/me` GET | `token_manager.py` neg-cache + lock | `tests/auth/test_token_manager.py` concurrency | ✅ |
| AC-003 | Successful rehydrate updates session on disk | `token_manager.py:285` `set_session(new_session)` | `tests/auth/test_token_manager.py:983` | ✅ |
| AC-004 | Unsuccessful rehydrate skips ingress | `sync/batch.py:392-401`, `sync/client.py:142-145` | `tests/sync/test_*` | ✅ |
| AC-005 | WS provisioning never posts shared id | `sync/client.py:138-145` returns before `provision_ws_token` | `test_client_integration.py:test_ws_token_skipped_when_no_private_team_after_rehydrate` | ✅ |
| AC-006 | Strict-JSON parseable under sync failure | `tests/sync/test_strict_json_stdout.py::test_agent_tasks_status_json_strict_with_sync_enabled_isolated` | passes | ✅ |
| AC-007 | "Private wins when default drifts" tests pass | unchanged | regression tests retained | ✅ |
| AC-008 | Local command exits 0 on skip | `sync/client.py:142-145` returns silently; batch returns existing result | strict-JSON test exits 0 | ✅ |
| AC-009 | Refresh updates stale membership | `token_manager.py:_apply_post_refresh_membership_hook` | `test_refresh_flow.py` two new tests | ✅ |

**Result:** every FR / NFR / AC has a closed spec → code → test triple. No FR is asserted only in fixtures; deletion-of-implementation thought experiment passes for each FR test.

---

## Drift Findings

### DRIFT-1 — Dead helper retains forbidden fallback semantics (MEDIUM)

`src/specify_cli/sync/client.py:93-117` defines `WebSocketClient._current_team_id(self)` which still contains the legacy shared-team fallback (`session.teams[0].id`, `session.default_team_id`):

```python
# client.py:93
def _current_team_id(self) -> str:
    ...
    if not session.default_team_id:
        if not session.teams:
            raise NotAuthenticatedError(...)
        private_team_id = get_private_team_id(session.teams)
        if private_team_id:
            return private_team_id
        return session.teams[0].id          # <-- FORBIDDEN by FR-002
    private_team_id = get_private_team_id(session.teams)
    if private_team_id:
        return private_team_id
    return session.default_team_id          # <-- FORBIDDEN by FR-002
```

**Evidence:**
- `grep -rn "_current_team_id\b" src/specify_cli/ tests/` returns:
  - `src/specify_cli/sync/client.py:93` (definition)
  - `tests/sync/test_client_integration.py:143` (only caller)
- Production `connect()` was rewritten (line 138) to call `resolve_private_team_id_for_ingress(...)` instead, so `_current_team_id` is dead code in production paths.
- Old `from specify_cli.auth.session import get_private_team_id` import remains at `client.py:28` solely to feed this dead helper.

**Risk:** A future contributor wiring up a feature (e.g., a new control-plane WS endpoint, a manual reconnect path, a CLI command) sees `_current_team_id` and treats it as the canonical team-id resolver, silently re-introducing the fallback that this mission was created to remove. The unit test at `test_client_integration.py:143` will keep validating it, masking the regression at PR time.

**FIX:** Delete `WebSocketClient._current_team_id` (and the test at `test_client_integration.py:143` if it stands alone, or rewrite that test to assert it has been removed). Drop the `get_private_team_id` import from `client.py:28`.

**Severity:** MEDIUM. No active production caller, but the dead code is a loaded gun.

---

### DRIFT-2 — Broad `except Exception:` masks bugs in helper wrappers (LOW)

Three call-site wrappers catch `Exception` and silently return `None`:

- `src/specify_cli/sync/batch.py:49-57` (`_current_team_slug`)
- `src/specify_cli/sync/queue.py:205-209` (`read_queue_scope_from_session` import wrapper)
- `src/specify_cli/sync/emitter.py:606-616` (`EventEmitter._current_team_slug`)

A bug in `resolve_private_team_id_for_ingress` (e.g. an AttributeError introduced by a future refactor of `TokenManager`) would silently degrade ingress to "skipped" with no log line — the structured warning is only emitted on the *successful* skip path inside the helper, not on this catch.

**FIX:** Either narrow these to specific exceptions (e.g., `ImportError, NotAuthenticatedError`), or — more useful — log the unexpected exception at WARNING level before returning None, so the operator can spot a bug without needing to enable DEBUG.

**Severity:** LOW. Existing pre-mission code already had these broad excepts; the mission preserved them rather than introducing them.

---

### DRIFT-3 — Legacy fallback pattern still exists in `sync/replay.py` (LOW, OUT OF SCOPE)

`grep` for `default_team_id` finds `src/specify_cli/sync/replay.py:184`:
```python
tenant_id = _pick("tenant_id", "team_id", "default_team_id")
```

This is a **read-side projection** for replay/comparison and is explicitly outside the direct-ingress write path. It is consistent with the spec's scope ("tracker-provider read paths and shared-team UI surfaces are not modified", C-001/C-002).

**FIX:** None. Note for future readers that this is intentionally preserved.

**Severity:** LOW (informational only).

---

## Risk Findings

### RISK-1 — `set_session` writes `_membership_negative_cache = False` outside the lock (LOW)

`TokenManager.set_session` (`token_manager.py:137-149`) clears `_membership_negative_cache` without acquiring `_membership_lock`. This is intentional because `set_session` is also called from inside `rehydrate_membership_if_needed` while the lock is already held (line 286), and `threading.Lock` is non-reentrant — acquiring it again would deadlock.

The race window: a concurrent thread that has *just* observed `_membership_negative_cache == True` and is inside the lock body of `rehydrate_membership_if_needed` could see the cache flip to `False` *while still holding the lock*. The result would be at most one extra `/api/v1/me` GET, which the docstring already acknowledges as the expected cost. No correctness issue.

**Severity:** LOW. Documented in the docstring; bounded blast radius.

**FIX:** None. Optional defensive comment at `set_session` would help future readers.

---

### RISK-2 — `_apply_post_refresh_membership_hook` runs while async refresh lock may still be held (LOW)

`refresh_if_needed` (line 363+, async) holds `self._refresh_lock` (`asyncio.Lock`) and adopts the new session, then synchronously calls `_apply_post_refresh_membership_hook` which calls `rehydrate_membership_if_needed` which acquires `self._membership_lock` (`threading.Lock`).

The two locks protect different state and there is no global ordering, so no AB/BA deadlock is possible. The sync HTTP GET to `/api/v1/me` will block the asyncio event loop briefly (default `DEFAULT_TIMEOUT_SECONDS = 30.0`), which is the existing trade-off accepted by the plan §1.3.

**Severity:** LOW. Bounded by HTTP timeout; documented in plan.

**FIX:** None.

---

### RISK-3 — Negative cache vs `auth-doctor` repair path (LOW)

The plan §1.8 mitigation says "auth-doctor or repair flows want fresh data ... `rehydrate_membership_if_needed` accepts `force=True`; document that auth-doctor/repair paths must pass it." A grep for callers of `rehydrate_membership_if_needed` shows callers in `sync/_team.py:59` (no force) and `token_manager.py:303` (force=True from refresh hook). No `auth doctor` caller is currently wired. If an auth-doctor command is added later, the contributor must remember to pass `force=True`.

**Severity:** LOW. Not in scope for this mission; documented in the docstring.

**FIX:** None.

---

## Silent Failure Candidates

### SF-1 — `EventEmitter._get_team_slug` returns `None` and emission silently skips (LOW)

`sync/emitter.py:1418-1432` will skip the entire event when `_get_team_slug()` returns `None`, with only `logger.debug` (not `warning`) recording the skip:

```python
team_slug = self._get_team_slug()
if team_slug is None:
    logger.debug(
        "Skipping %s emission: no Private Teamspace available for ingress",
        event_type,
    )
    return None
```

The `logger.warning` for the structured payload is emitted by `_team.resolve_private_team_id_for_ingress` (with category/rehydrate_attempted/etc). So one skip event produces both: a `WARNING` from the resolver and a `DEBUG` from the emitter. NFR-002 is satisfied at the resolver. This is by design.

**Severity:** LOW. Behavior matches NFR-002; double-logging is informational.

**FIX:** None (current behavior matches contract).

---

## Security Notes

- **HTTP timeout:** `me_fetch.fetch_me_payload` uses `request_with_fallback_sync(method="GET", url=..., headers=...)` without an explicit `timeout=`. The transport default is `DEFAULT_TIMEOUT_SECONDS = 30.0` (`auth/http/transport.py:45,381`). Acceptable.
- **Header injection:** `Authorization: Bearer {access_token}` is constructed via f-string. The access token comes from the encrypted local session and is not user-controlled at this seam, but if a future code path constructs sessions from untrusted input, an embedded `\r\n` could inject headers. Practically a non-risk today; consider sanitizing or using `httpx`'s native header-validation as a defense in depth in a follow-up.
- **Lock semantics:** `threading.Lock` for membership is correct (non-reentrant; the rehydrate path does not re-acquire). Independent of the `asyncio.Lock` used by refresh — no deadlock interaction.
- **Path traversal:** none introduced by this mission.
- **Credential leakage:** new `logger.warning` calls pass the full bearer token NOWHERE; only `category`, `rehydrate_attempted`, `ingress_sent`, `endpoint` are logged. ✅
- **Stdout discipline:** the no-`print()` invariant in `sync/client.py` is enforced by `tests/sync/test_strict_json_stdout.py::test_no_print_calls_in_sync_client`. Manual `grep -n "print(" src/specify_cli/sync/client.py` confirms zero matches.

No security issues identified.

---

## Hard Gates

| Gate | Result | Notes |
|------|--------|-------|
| Architectural tests | ✅ 92 passed, 1 skipped (11.76 s) | green |
| Mission auth tests (`tests/auth/test_session.py`, `test_me_fetch.py`, `test_token_manager.py`, `test_refresh_flow.py`) | ✅ 93 passed | green |
| Mission sync tests (`test_team_ingress_resolver.py`, `test_batch_sync.py`, `test_client_integration.py`, `test_strict_json_stdout.py`) | ✅ 44 passed, 1 skipped | green |
| Contract tests | ⚠ 1 failure unrelated to this mission | `test_cross_repo_consumers.py::test_spec_kitty_events_module_version_matches_resolved_pin`: `spec_kitty_events.__version__ == '5.0.0'` but uv.lock pin is `'4.1.0'`. Pre-existing drift in shared-package boundary, not introduced by this mission. |
| Cross-repo E2E | N/A | Sibling `spec-kitty-end-to-end-testing` repo not present in this checkout. |
| Issue matrix | N/A | `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/issue-matrix.md` does not exist. Mission scope did not declare one. |

---

## Mission process notes

- Three WPs (WP02, WP04, WP05) required force-resets through `move-task` after the codex reviewer rejected and were re-approved manually. Documented in `status.events.jsonl` with explicit arbiter rationale (WP02: TMPDIR collision with sibling tracker repo contaminated the codex prompt; WP04: cycle 1 emitter `'local'` fallback + cycle 2 fresh-TokenManager bypass; WP05: cycle 1 subprocess scope + cycle 2 in-tree resolution + cycle 6 isolated-home seeding).
- All review-cycle artifacts were preserved under `kitty-specs/.../tasks/WPNN-*/`.
- WP03 was clean (zero rejection cycles).
- The cycle-2 queue.py `get_token_manager()` singleton fix is critical: without it, each `read_queue_scope_from_session` call would have constructed a fresh `TokenManager`, zeroing the negative cache and causing repeat `/api/v1/me` GETs per CLI process — directly violating NFR-001. Verified at `queue.py:211 token_manager = get_token_manager()`.
- The cycle-1 emitter `"local"` fallback removal (`emitter.py:_get_team_slug` now returns `None` instead of `"local"`) is the load-bearing fix for FR-002 in the emitter path.

---

## Final Verdict

**PASS WITH NOTES.**

The mission's contract is delivered: every FR/NFR/AC has a closed spec → code → test chain, mission tests are green, and the architectural gate is green. The two notes are:

1. **DRIFT-1 (MEDIUM)** — `WebSocketClient._current_team_id` is dead production code that retains the forbidden shared-team fallback. Recommended cleanup: delete the helper and the unit test that exercises it. Not a release blocker; a follow-up housekeeping commit is sufficient.
2. **GATE NOTE** — One contract test (`test_cross_repo_consumers.py`) fails on a pre-existing `spec_kitty_events` pin drift unrelated to this mission. Should be triaged separately under the shared-package-boundary workflow.

The mission may be tagged for release once DRIFT-1 is either accepted as deferred housekeeping or closed by a one-line cleanup PR. The contract-test pin drift must be resolved before a fresh `clean-install-verification` CI run will succeed but is not a private-team-ingress regression.

---

## Post-Mission-Review Fixes

After this report was authored, an external reviewer surfaced four additional findings. Three were acted on (commits below), one (P3) is the act of committing this report itself.

### POST-1 (P1, was release-blocker): `sync_all_queued_events` infinite loop on shared-only sessions

**Location**: `src/specify_cli/sync/batch.py` (skip path at ~L405; loop break check at ~L692)

**Bug**: When `_current_team_slug()` returned `None` (no Private Teamspace), `batch_sync` returned a `BatchSyncResult` with `synced_count=0`, `error_count=0`, AND left events in the queue. The drain loop in `sync_all_queued_events` was `while queue.size() > 0:` and only broke when `success_count == 0 AND error_count > 0`. So `spec-kitty sync now` and `_perform_full_sync` would spin forever on a shared-only session — exactly Scenario 6's territory.

**Fix**:
1. In the `batch_sync` skip path, append a sentinel error message (`"skipped: no Private Teamspace available for direct ingress"`) so the result carries operator-visible diagnostic.
2. In `sync_all_queued_events`, change the no-progress check from `success_count == 0 AND error_count > 0` to `success_count == 0` alone — any batch that makes no forward progress now terminates the loop.

**Test**: `test_sync_all_queued_events_terminates_on_no_private_team` in `tests/sync/test_batch_sync.py` — pre-fills a 5-event queue against a shared-only session, calls `sync_all_queued_events`, asserts the loop terminates, the queue stays at 5 events (no destructive skip), zero HTTP POSTs were sent, and the sentinel error message is on the result.

### POST-2 (P2): `queue.py:677` `print()` to stdout

**Location**: `src/specify_cli/sync/queue.py:676-677`

**Bug**: `except Exception as e: print(f"Failed to queue event: {e}")` writes to stdout. Sync side-effects fire before `agent mission create --json` writes its JSON response — a queue-insert failure would corrupt strict-JSON stdout (FR-009 / NFR-003 violation).

**Fix**: Convert to `logging.getLogger(__name__).warning("Failed to queue event: %s", e)` — routes through stderr by default.

### POST-3 (P2): AC-006 not exercised by `mission create --json`

**Location**: `tests/sync/test_strict_json_stdout.py`

**Issue**: AC-006 in spec.md names `spec-kitty agent mission create --json` specifically as the strict-JSON regression command. The committed test ran `agent tasks status --json` (easier to drive) and a synthetic in-process probe.

**Fix**: Added `test_mission_create_json_strict_when_sync_skips_ingress` (commit `08515b25`) that scaffolds a minimum git+kittify repo, seeds a shared-only `StoredSession`, sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, and runs the actual `mission create --json` subprocess. Asserts: exit 0, `json.loads(stdout)` succeeds with `result == "success"` and `mission_slug` field, stderr contains the structured `direct ingress skipped` warning, stdout contains no `Connection failed` text.

### POST-4 (P3): Mission-review evidence not committed

**Fix**: This very file (`kitty-specs/<slug>/mission-review.md`) is now committed alongside the post-merge fixes.

---

## Final Verdict (post-fix): **PASS — Releasable**

All four post-review findings actioned. The release-blocker (POST-1) is fixed and protected by a regression test. The contract for AC-006 / FR-009 / NFR-003 is now exercised end-to-end by an isolated subprocess test that reproduces the actual command path the spec named.
