# Research — sync-strict-json-auth-01KWA6KN (issue #2254)

Phase 0 output. Resolves FR-001 (root-cause determination) and feeds the deferred
CI-trigger-scope decision `01KWA6Q7SPH9ZN20CH6EW68QDM`.

## Decision: test-seeding drift, NOT a product regression — fix the test

**Verdict:** The `final_sync` `sync.server_auth_failure` is caused by the test seeding its
encrypted `StoredSession` to a directory production no longer reads. The seeded session is
invisible to the subprocess, so it is unauthenticated, so the direct-ingress-skip path is
silently bypassed and `final_sync` falls to its auth-failure gate. Production behavior is
correct and intentional. **Fix the test seeding; do not touch production auth.**

This is the §4 "stale → re-pin" case (judge the test, not git-blame): the test's *intent*
(exercise the ingress-skip path) is valid and its diagnostic assertion is a good non-vacuous
guard — it correctly caught that the session was not loaded. Only the seed *path* is stale.

## The smoking gun

| Side | Directory used |
|------|----------------|
| Test seeds session at | `fake_home/.spec-kitty/auth/` (HOME-derived; `tests/sync/test_strict_json_stdout.py:267`) |
| Production reads session from | `$SPEC_KITTY_HOME/auth` = `fake_home/.kittify/auth/` (`auth/secure_storage/file_fallback.py:51` → `paths/windows_paths.py:78`) |

The test sets `SPEC_KITTY_HOME = fake_home/.kittify` (`test_strict_json_stdout.py:315,323`)
but hardcodes the seed path to `.spec-kitty/auth` (`:267`). Mismatch → `_session is None`.

## Chain of causation (live-code traced)

1. `_seed_shared_only_session` writes a valid `StoredSession` (non-private `Team(is_private_teamspace=False)`, `access_token="fake-access-token"`, `expires_at = now+1h`) via `FileFallbackStorage(base_dir=fake_home/".spec-kitty"/"auth")` (AES-256-GCM, scrypt key from `hostname:uid`, same-machine decryptable). `test_strict_json_stdout.py:240-297`.
2. Production `get_token_manager()` → `SecureStorage.from_environment()` → `FileFallbackStorage()` with no `base_dir` → `default_store_dir()` = `get_runtime_root().base/"auth"`, and `get_runtime_root()` honors `SPEC_KITTY_HOME` verbatim. So it reads `fake_home/.kittify/auth/session.json`, which does not exist → `read()` returns `None`.
3. `TokenManager._session is None` → `is_authenticated == False` (`background.py:125`, `token_manager.py`).
4. Batch path emits `_unauthenticated_sync_result` with `_UNAUTHENTICATED_SYNC_ERROR = "Not authenticated: no valid access token. Run \`spec-kitty auth login\`."` (`background.py:51-53`).
5. `_emit_final_sync_failure_diagnostic` → `classify_sync_error` maps substring `"no valid access token"` → category `unauthenticated` → `SyncDiagnosticCode.SERVER_AUTH_FAILURE` (`batch.py:57,747-754`; `diagnostics.py:24`). **Exact observed failure.**
6. The ingress-skip diagnostic is never emitted because `resolve_private_team_id_for_ingress` (`sync/_team.py`) only warns `direct ingress skipped` when `session is not None`; a `None` session returns silently. So a missing session bypasses the skip path entirely.

## Drift evidence (git history)

- Test file last meaningful change: `bbe416e59` (2026-06-20).
- Breaking production change: **`a75174917` — "fix(2171): SPEC_KITTY_HOME isolates all sync/auth/tracker/daemon state (#2182)"** (2026-06-26). It changed `default_store_dir()` in `file_fallback.py` from `Path.home()/".spec-kitty"/"auth"` to `get_runtime_root().base/"auth"` (honors `SPEC_KITTY_HOME`).
- The test seeded a path production accepted *before* 2026-06-26 and stopped accepting after — classic intentional-change-induced test drift, not a regression.

## Fix (Phase 1 design input)

In `_build_isolated_home` / `_seed_shared_only_session`: derive the seed directory from the
same `SPEC_KITTY_HOME` the subprocess uses — `auth_dir = Path(env["SPEC_KITTY_HOME"]) / "auth"`
— and pass it to the seeder. Also correct the now-stale docstrings (`:244-262`) that claim
resolution via `Path.home()/".spec-kitty"/"auth"`.

Preserve every existing assertion (exit 0, single JSON object on stdout with `result==success`
+ `mission_slug`, no diagnostic prose on stdout, and the diagnostic-fired stderr guard). The
guard must stay — it is what proves the genuine ingress-skip path fired (§4, C-002).

## CI-trigger-scope decision input (01KWA6Q7…)

This drift sat undetected from 2026-06-26 until surfaced by PR #2172 — precisely because
`integration-tests-sync` is path-filtered on `changes.outputs.sync == true`. Commit
`a75174917` touched `auth/` and `paths/`, not the `sync/` filter globs that gate this test,
so the gate stayed `SKIPPED` and never ran the now-broken test. This is concrete evidence for
the #2034 direction (a periodic/full run, or widening the filter so auth/paths changes also
trigger the sync gate). **Recommendation:** keep the core fix tightly scoped to the test; treat
the CI-trigger broadening as a real but separable concern — strong candidate to fold into #2034
rather than balloon this mission. Final call pending the user's post-research decision.

## Live-verification update (2026-06-29) — FR-001 conclusion CORRECTED/EXPANDED

The static verdict above ("test-seeding drift only") was **incomplete**. Live verification (T004)
after re-pinning the seeding proved the auth failure is gone (the session now loads — the negative
auth pin passes), but exposed a deeper, real **production** bug that the issue and the static trace
missed:

1. **Misclassification (operator-facing bug, now fixed):** a benign "no Private Teamspace → skip
   ingress" reaches `final_sync` and its diagnostic was classified by the catch-all in
   `classify_sync_error` (`sync/diagnostics.py`) as `sync.server_auth_failure`, dropping the
   canonical `direct_ingress_missing_private_team` category. That wrongly signals an auth failure
   (and tells the operator to run `spec-kitty auth login`) for a benign skip.
2. **Logging reachability:** the `_team.py` "sole skip diagnostic" WARNING
   (`specify_cli.sync._team`) does not reach the `mission create` subprocess stderr, so the skip was
   invisible to anything parsing stderr (including this test).

**Fix landed (user-approved, FR-005):** added
`SyncDiagnosticCode.DIRECT_INGRESS_MISSING_PRIVATE_TEAM = "sync.direct_ingress_missing_private_team"`
and a `classify_sync_error` branch that detects the skip text *before* the auth/catch-all, so the
stderr diagnostic now carries `diagnostic_code=sync.direct_ingress_missing_private_team`. This both
fixes the real misclassification and lets the test assert the genuine skip path. Blast radius
verified low: no existing test pinned the skip case to `server_auth_failure`; the `network down` /
`401` / `token` / `no valid access token` assertions are unaffected. Contract tests updated (enum
now has six members) + focused `test_classify_direct_ingress_missing_private_team` added.

**Corrected FR-001 verdict:** the failure was BOTH (a) test-seeding drift from `a75174917`/#2182
(re-pinned) AND (b) a pre-existing production misclassification of the benign ingress skip (fixed).
The seeding re-pin alone was necessary but insufficient — live evidence, not static reading, caught
the residual (§4).

## Alternatives considered

- *Fix production to read the old path*: rejected — would revert the intentional `SPEC_KITTY_HOME`
  isolation (#2171/#2182) and re-break auth-state isolation.
- *Set `SPEC_KITTY_HOME = fake_home/.spec-kitty` so the old seed path matches*: works, but couples
  the test to a legacy layout; deriving the seed dir from `SPEC_KITTY_HOME` is the durable fix.
- *Weaken/remove the diagnostic-fired assertion*: rejected (C-002, §4) — it is the non-vacuous
  guard that gives the test its value.
