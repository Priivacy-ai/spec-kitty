# Tasks: CLI Private Teamspace Ingress Safeguards

**Mission**: `private-teamspace-ingress-safeguards-01KQH03Y`
**Mission ID**: `01KQH03YSS4H9PQVJ5YCTGZYMR`
**Branch**: `main` | **Date**: 2026-05-01 | **Plan**: [plan.md](./plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `require_private_team_id(session)` strict resolver in `auth/session.py` | WP01 |  | [D] | [D] | [D] |
| T002 | Tighten `pick_default_team_id` docstring with "not for direct ingress" guard | WP01 | [D] |
| T003 | Unit tests for `require_private_team_id` (positive, no-private, default-points-shared) | WP01 | [D] |
| T004 | Regression test: "Private wins even when default drifts" still passes | WP01 | [D] |
| T005 | Create `src/specify_cli/auth/http/me_fetch.py` with `fetch_me_payload(transport, access_token)` | WP02 |  | [D] |
| T006 | Add `_membership_negative_cache` field + `rehydrate_membership_if_needed` method on `TokenManager` | WP02 |  | [D] |
| T007 | Add identity-change cache-bust logic in `TokenManager.set_session()` | WP02 |  | [D] |
| T008 | Unit tests for `me_fetch.fetch_me_payload` (success, 401, network error) | WP02 | [D] |
| T009 | Unit tests for `rehydrate_membership_if_needed` (early-return, GET success, GET no-private + cache, cache hit no GET, force=True bypass) | WP02 | [D] |
| T010 | Concurrent-callers test (single-flight via lock — exactly one HTTP GET observed) | WP02 | [D] |
| T011 | Add post-refresh rehydrate hook in `TokenManager.refresh_if_needed()` (the actual adoption boundary) — sync call to `self.rehydrate_membership_if_needed(force=True)` after each `self._session = result.session` line when adopted session lacks a Private Teamspace | WP02 |  | [D] |
| T012 | Tests for refresh-and-force-rehydrate path (drives `await token_manager.refresh_if_needed()`, asserts one `/api/v1/me` GET + private team in resulting session) | WP03 | [D] |
| T013 | Tests confirming healthy refresh stays a single round trip (no extra `/api/v1/me`) | WP03 | [D] |
| T014 | Create `src/specify_cli/sync/_team.py` with shared `_resolve_private_team_id_for_ingress(token_manager, *, endpoint)` async helper that emits structured warnings | WP04 |  | [D] |
| T015 | Update `sync/batch.py` to use the shared helper, remove `default_team_id` ingress lookup | WP04 |  | [D] |
| T016 | Update `sync/queue.py` to use the shared helper for ingress team metadata | WP04 |  | [D] |
| T017 | Update `sync/emitter.py` to use the shared helper for ingress team metadata | WP04 |  | [D] |
| T018 | Tests in `tests/sync/test_batch_sync.py`: shared-only triggers single rehydrate, success path, skip-on-fail, negative cache honored across batches | WP04 | [D] |
| T019 | Tests for queue/emitter ingress paths (per-existing test files; structured warning shape asserted) | WP04 | [D] |
| T020 | Update `sync/client.py` ws-token provisioning to use the shared `_team` helper | WP05 |  | [D] |
| T021 | Replace 6 `print()` calls in `sync/client.py:141, 146, 178, 184, 186, 193` with `logger.warning`/`logger.info` | WP05 |  | [D] |
| T022 | Tests in `tests/sync/test_client_integration.py`: ws-token rehydrate path, skip on rehydrate fail, never-shared-id assertion | WP05 | [D] |
| T023 | New file `tests/sync/test_strict_json_stdout.py`: end-to-end strict-JSON regression for `agent mission create --json` with sync failure injection (covers AC-006, NFR-003) | WP05 | [D] |
| T024 | Test guarding the no-`print()`-in-sync-package invariant (single test asserts `grep` returns empty) | WP05 | [D] |

**Total**: 24 subtasks across 5 work packages.

---

## Phase 1 — Foundation (parallelizable)

### WP01 — Strict private-team resolver

**Goal**: Provide the canonical `require_private_team_id(session) -> str | None` helper in `auth/session.py` and lock down `pick_default_team_id` against ingress misuse.

**Priority**: P0 (every other WP that touches ingress depends on this).

**Independent test**: New tests in `tests/auth/test_session.py` exercise the resolver in isolation (no I/O, no other modules).

**Estimated prompt size**: ~280 lines.

**Included subtasks**:

- [x] T001 Add `require_private_team_id(session)` strict resolver in `auth/session.py` (WP01)
- [x] T002 Tighten `pick_default_team_id` docstring with "not for direct ingress" guard (WP01)
- [x] T003 Unit tests for `require_private_team_id` (positive, no-private, default-points-shared) (WP01)
- [x] T004 Regression test: "Private wins even when default drifts" still passes (WP01)

**Implementation sketch**:
1. Add the new pure function next to existing `get_private_team_id` in `auth/session.py`.
2. Replace its body with the contract from `contracts/api.md` §1.
3. Update `pick_default_team_id` docstring per FR-012.
4. Author tests in `tests/auth/test_session.py` covering the four cases.

**Dependencies**: none.

**Risks**: minimal — pure function. The only failure mode is grandfathering an ambiguous test fixture; the regression test (T004) covers that.

**Prompt file**: [tasks/WP01-strict-private-team-resolver.md](./tasks/WP01-strict-private-team-resolver.md)

---

### WP02 — Rehydrate orchestrator on `TokenManager` + refresh hook

**Goal**: Add the **sync** one-shot `/api/v1/me` rehydrate path with `threading.Lock` single-flight and process-lifetime negative cache, plus the small **sync** `me_fetch` helper. Also add the post-refresh rehydrate hook inside `TokenManager.refresh_if_needed()` (the actual adoption boundary; `flows/refresh.py` only returns sessions, it does not adopt or persist).

**Priority**: P0.

**Independent test**: New cases in `tests/auth/test_token_manager.py` and a new `tests/auth/test_me_fetch.py`.

**Estimated prompt size**: ~700 lines (sync rewrite + T011 hook).

**Included subtasks**:

- [x] T005 Create `src/specify_cli/auth/http/me_fetch.py` with sync `fetch_me_payload(saas_base_url, access_token)` using `request_with_fallback_sync` (WP02)
- [x] T006 Add `_membership_negative_cache: bool` + `_membership_lock: threading.Lock` fields, and sync `rehydrate_membership_if_needed(*, force=False)` method on `TokenManager`. On success, recompute `default_team_id` via `pick_default_team_id(new_teams)` (the SaaS does NOT return that field) (WP02)
- [x] T007 Cache-bust unconditionally in `TokenManager.set_session()` — captures every login/repair/identity boundary (WP02)
- [x] T008 Unit tests for sync `me_fetch.fetch_me_payload` (success, 401, Authorization header verification) (WP02)
- [x] T009 Unit tests for sync `rehydrate_membership_if_needed` (early-return, GET success with `default_team_id` recomputed, GET no-private + cache set, cache hit no GET, force=True bypass, HTTP error leaves cache untouched, set_session unconditionally clears cache) (WP02)
- [x] T010 Concurrent threads test (single-flight via `threading.Lock` — exactly one HTTP GET observed) (WP02)
- [x] T011 Add post-refresh rehydrate hook in `TokenManager.refresh_if_needed()` after each `self._session = result.session` adoption point — sync call to `self.rehydrate_membership_if_needed(force=True)` when adopted session lacks Private Teamspace. Closes FR-008 (WP02)

**Implementation sketch**:
1. Write `me_fetch.py` first; tiny, sync, no state.
2. Add `_membership_negative_cache: bool = False` and `_membership_lock: threading.Lock = threading.Lock()` to `TokenManager.__init__`. Thread `saas_base_url` in if not already present.
3. Implement sync `rehydrate_membership_if_needed` using the new threading.Lock (separate from the existing async refresh lock).
4. Update `set_session()` to unconditionally clear `_membership_negative_cache`.
5. Insert the hook in `refresh_if_needed()` after every adoption line (4 RefreshOutcome branches).
6. Author tests with `respx` (sync style — no `pytest.mark.asyncio` for the rehydrate tests).

**Dependencies**: none.

**Risks**: lock semantics — must early-return *inside* the lock to avoid the thundering herd doing redundant GETs. Concurrent test (T010) verifies.

**Prompt file**: [tasks/WP02-tokenmanager-rehydrate-membership.md](./tasks/WP02-tokenmanager-rehydrate-membership.md)

---

## Phase 2 — Integration (depends on Phase 1)

### WP03 — Refresh-hook integration tests (test-only)

**Goal**: Lock down the WP02-delivered post-refresh rehydrate hook with two integration tests at the `await token_manager.refresh_if_needed()` boundary. **Test-only** WP — no source files modified. The file `auth/flows/refresh.py` is **not** modified by this mission (it only returns a session; adoption happens inside `TokenManager`, which WP02 owns).

**Priority**: P1.

**Independent test**: New cases in `tests/auth/test_refresh_flow.py`.

**Estimated prompt size**: ~280 lines.

**Included subtasks**:

- [x] T012 Test: refresh adopting a shared-only session triggers the rehydrate hook (drives `await token_manager.refresh_if_needed()`, asserts one `/api/v1/me` GET, private team in resulting session, `default_team_id` recomputed) (WP03)
- [x] T013 Test: healthy refresh stays a single round trip (no extra `/api/v1/me` GET when adopted session already has a Private Teamspace) (WP03)

**Implementation sketch**:
1. Author the two `pytest.mark.asyncio` test cases in `tests/auth/test_refresh_flow.py`.
2. Drive each test through `await token_manager.refresh_if_needed()` — NOT through `TokenRefreshFlow.refresh(...)` directly (the hook only runs at the TokenManager entry).
3. Assert `me_route.call_count` and the resulting session shape.

**Dependencies**: WP02 (the hook code in `TokenManager.refresh_if_needed()` must exist).

**Risks**: tests pass even if WP02's hook is missing — mitigated by asserting `me_route.call_count == 1` (T012) and `== 0` (T013) so missing-hook causes a clear failure.

**Prompt file**: [tasks/WP03-refresh-flow-force-rehydrate.md](./tasks/WP03-refresh-flow-force-rehydrate.md)

---

### WP04 — Direct-ingress call sites: shared helper + batch + queue + emitter

**Goal**: Introduce `sync/_team.py` shared helper and rewrite ingress team-id resolution in `batch.py`, `queue.py`, and `emitter.py` to use the strict resolver + rehydrate-once path. On rehydrate failure, skip ingress and emit the structured warning.

**Priority**: P0.

**Independent test**: Updated cases in `tests/sync/test_batch_sync.py` and the existing emitter/queue test files.

**Estimated prompt size**: ~480 lines.

**Included subtasks**:

- [x] T014 Create `src/specify_cli/sync/_team.py` with shared `_resolve_private_team_id_for_ingress(token_manager, *, endpoint)` async helper that emits structured warnings (WP04)
- [x] T015 Update `sync/batch.py` to use the shared helper, remove `default_team_id` ingress lookup (WP04)
- [x] T016 Update `sync/queue.py` to use the shared helper for ingress team metadata (WP04)
- [x] T017 Update `sync/emitter.py` to use the shared helper for ingress team metadata (WP04)
- [x] T018 Tests in `tests/sync/test_batch_sync.py` (WP04)
- [x] T019 Tests for queue/emitter ingress paths (WP04)

**Implementation sketch**:
1. Author `sync/_team.py` containing the helper from `contracts/api.md` §4.
2. Visit each of the three call sites and replace the team-id lookup with `await _resolve_private_team_id_for_ingress(token_manager, endpoint=...)`. Skip the request when it returns `None`.
3. Tests assert: zero `/api/v1/events/batch/` requests when shared-only; exactly one `/api/v1/me` GET total per process; structured warning observed.

**Dependencies**: WP01, WP02.

**Risks**: subtle behavior change for users who currently get *some* ingress through (to a shared team that the old SaaS accepted before #142 landed). The skip-with-diagnostic is the explicit, spec-mandated outcome.

**Prompt file**: [tasks/WP04-direct-ingress-call-sites.md](./tasks/WP04-direct-ingress-call-sites.md)

---

### WP05 — Websocket client + stdout discipline + strict-JSON regression

**Goal**: Convert the websocket client's ws-token provisioning to the strict resolver, replace its 6 `print()` calls with `logger` calls (FR-009), and add an end-to-end strict-JSON regression test.

**Priority**: P0.

**Independent test**: Updated `tests/sync/test_client_integration.py` plus new `tests/sync/test_strict_json_stdout.py`.

**Estimated prompt size**: ~430 lines.

**Included subtasks**:

- [x] T020 Update `sync/client.py` ws-token provisioning to use the shared `_team` helper (WP05)
- [x] T021 Replace 6 `print()` calls in `sync/client.py:141, 146, 178, 184, 186, 193` with `logger.warning`/`logger.info` (WP05)
- [x] T022 Tests in `tests/sync/test_client_integration.py` (WP05)
- [x] T023 New file `tests/sync/test_strict_json_stdout.py`: strict-JSON regression for `agent mission create --json` with sync-failure injection (WP05)
- [x] T024 Test guarding the no-`print()`-in-sync-package invariant (WP05)

**Implementation sketch**:
1. Convert ws-token provisioning to use `_team` helper.
2. Replace prints with `logger = logging.getLogger(__name__)` plus appropriate level.
3. Add `tests/sync/test_strict_json_stdout.py` that subprocess-runs `spec-kitty agent mission create … --json` with a forced shared-only session, asserts `json.loads(stdout)` succeeds and the stderr contains the expected diagnostic.
4. Add T024 guard test.

**Dependencies**: WP01, WP02, WP04 (for `_team.py`).

**Risks**: the strict-JSON test may be flaky if the test harness inherits the user's real auth session; the test must use a fully isolated fixture session (no real SaaS access).

**Prompt file**: [tasks/WP05-websocket-and-stdout-discipline.md](./tasks/WP05-websocket-and-stdout-discipline.md)

---

## Lane / parallelization map

`finalize-tasks` computed a single lane (`lane-a`) for this mission. The dependency graph below shows why a two-lane split would have been desirable in theory but collapsed in practice:

| Phase | Work packages eligible to start |
|-------|---------------------------------|
| Round 1 | WP01, WP02 (no dependencies — can be co-developed by the same agent or split if a second worktree existed) |
| Round 2 | WP03 (after WP02), WP04 (after WP01 + WP02) |
| Round 3 | WP05 (after WP01 + WP02 + WP04) |

**Computed lane reality** (see [lanes.json](./lanes.json)): WP04 depends on both WP01 and WP02, which forces WP04 (and downstream WP05) to wait for both. The lane collapser merges all five WPs into a single lane with sequential ordering. The implementer should plan on **one execution worktree** progressing through the WPs in dependency order; a typical sequence is:

`WP01 → WP02 → WP03 → WP04 → WP05`

WP01 and WP02 are independent and may be implemented in either order, but they share a worktree.

---

## MVP scope

**WP01 + WP02 + WP04** is the minimum that satisfies AC-001..AC-005 and AC-008. WP03 (refresh integration) and WP05 (ws-token + stdout discipline) close out AC-006 (strict-JSON), AC-009 (refresh integration), and FR-009. The full mission requires all five.

---

## Requirement coverage (preview)

| Requirement | WPs |
|-------------|-----|
| FR-001 (canonical helper) | WP01 |
| FR-002 (no fallback) | WP01, WP04, WP05 |
| FR-003 (one-shot rehydrate) | WP02 |
| FR-004 (skip + diagnostic) | WP04, WP05 |
| FR-005 (batch.py) | WP04 |
| FR-006 (client.py ws-token) | WP05 |
| FR-007 (emitter.py + queue.py) | WP04 |
| FR-008 (refresh hook) | WP02 (hook code) + WP03 (integration tests) |
| FR-009 (stdout discipline) | WP05 |
| FR-010 (local commands succeed) | WP04, WP05 |
| FR-011 (preserve healthy session) | WP01, WP02 |
| FR-012 (`pick_default_team_id` docstring) | WP01 |
| NFR-001 (one-shot) | WP02 |
| NFR-002 (structured log shape) | WP04 |
| NFR-003 (strict-JSON) | WP05 |
| NFR-004 (existing tests pass) | WP01 |
| C-001..C-005 | enforced by spec; tests in respective WPs do not modify the protected surfaces |

`spec-kitty agent tasks map-requirements --batch ...` will register these mappings after WP files are written.

---

## Next

After all WP prompt files exist, run `spec-kitty agent mission finalize-tasks --json --mission private-teamspace-ingress-safeguards-01KQH03Y` to compute lanes, parse dependencies, and commit.
