---
work_package_id: WP02
title: HostedReadiness evaluator and test layers
dependencies:
- WP01
requirement_refs:
- FR-004
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "65504"
history:
- at: '2026-04-11T06:22:58Z'
  actor: claude:/spec-kitty.tasks
  event: created
  note: Generated from plan.md, data-model.md §§2–4, and contracts/hosted_readiness.md.
authoritative_surface: src/specify_cli/saas/readiness.py
execution_mode: code_change
feature_slug: 082-stealth-gated-saas-sync-hardening
owned_files:
- src/specify_cli/saas/readiness.py
- tests/saas/conftest.py
- tests/saas/test_readiness_unit.py
- tests/saas/test_readiness_integration.py
priority: P1
tags: []
---

# WP02 — HostedReadiness evaluator and test layers

## Objective

Ship the shared `HostedReadiness` evaluator that replaces ad hoc preflight checks inside enabled mode. Deliver both layers of the test pyramid specified in the mission: a unit layer that stubs individual prerequisite probes, and a smaller integration layer that exercises the real evaluator against `tmp_path`-backed auth, config, and binding fixtures. Every failure produces byte-wise stable wording that names the missing prerequisite and gives one concrete next action.

## Context

Today there is **no unified readiness evaluator** inside the CLI (research R-001, baseline map item #3). Each hosted code path checks its own prerequisites ad hoc — the tracker callback just checks the env var via `_require_enabled()` and calls it a day. That violates NFR-002 (failures must name the specific missing prerequisite) and makes it impossible for `spec-kitty tracker status` to report something more useful than "gate error" when the env var is set but, e.g., the mission has no binding yet.

This WP introduces `src/specify_cli/saas/readiness.py` alongside the rollout module that WP01 already landed. The readiness evaluator imports `is_saas_sync_enabled` from `specify_cli.saas.rollout` (not from the shims), checks each prerequisite in the contract-defined order, short-circuits on the first failure, and returns a frozen `ReadinessResult`. The stable failure-message catalog is checked-in wording; tests assert it byte-wise so nobody copy-edits it into drift.

**Callers of readiness (this WP does not touch them)** will import via the module path: `from specify_cli.saas.readiness import ReadinessState, evaluate_readiness`. This is the canonical import path for readiness and works without WP02 needing to edit `saas/__init__.py` (which is owned by WP01). If a future mission wants the package-root shortcut, it can be added in an `__init__.py`-owning WP.

**Branch strategy**: Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main. Execution worktrees are allocated per computed lane from `lanes.json`; this WP depends on WP01 and runs after it in Lane A.

## Files touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/saas/readiness.py` | **create** | `ReadinessState`, `ReadinessResult`, `evaluate_readiness`, private `_probe_*` helpers. |
| `tests/saas/conftest.py` | **create** | Shared fixtures: `rollout_enabled`, `rollout_disabled`, auth/config/binding factory fixtures. |
| `tests/saas/test_readiness_unit.py` | **create** | Stub-based coverage of every state, ordering, wording, exception conversion. |
| `tests/saas/test_readiness_integration.py` | **create** | Real evaluator against tmp_path fixtures; local HTTP stub for reachability. |

## Subtasks

### T006 — Create `src/specify_cli/saas/readiness.py` skeleton

**Purpose**: Define the public types (`ReadinessState`, `ReadinessResult`) and the entrypoint function signature, matching `data-model.md §§2–4` and `contracts/hosted_readiness.md`.

**Steps**:

1. Define `ReadinessState(str, Enum)` with exactly six members in declaration order: `ROLLOUT_DISABLED`, `MISSING_AUTH`, `MISSING_HOST_CONFIG`, `HOST_UNREACHABLE`, `MISSING_MISSION_BINDING`, `READY`. String values are the lowercase member names (e.g., `"rollout_disabled"`).
2. Define `@dataclass(frozen=True) ReadinessResult` with fields `state`, `message`, `next_action`, `details` (`Mapping[str, str]`, default empty dict via `field(default_factory=dict)`), and a computed `is_ready` property.
3. Define `evaluate_readiness(*, repo_root: Path, feature_slug: str | None = None, require_mission_binding: bool = False, probe_reachability: bool = False) -> ReadinessResult`. Leave the body as `raise NotImplementedError` in this subtask — T008 fills it in.
4. Add a module docstring pointing to `contracts/hosted_readiness.md` as the stability contract.

**Files**: `src/specify_cli/saas/readiness.py` (skeleton, ~60 lines)

**Validation**: `python -c "from specify_cli.saas.readiness import ReadinessState, ReadinessResult, evaluate_readiness"` works; mypy --strict clean.

### T007 — Stable failure-message catalog

**Purpose**: Lock the wording for every non-READY state into a module-level mapping so implementation and tests agree.

**Steps**:

1. Add a module-private mapping `_WORDING: dict[ReadinessState, tuple[str, str]]` — each entry is `(message, next_action)` matching the table in `contracts/hosted_readiness.md`:

   | State | message | next_action |
   |---|---|---|
   | `ROLLOUT_DISABLED` | `"Hosted SaaS sync is not enabled on this machine."` | `"Set \`SPEC_KITTY_ENABLE_SAAS_SYNC=1\` to opt in."` |
   | `MISSING_AUTH` | `"No SaaS authentication token is present."` | `"Run \`spec-kitty auth login\`."` |
   | `MISSING_HOST_CONFIG` | `"No SaaS host URL is configured."` | `"Set \`SPEC_KITTY_SAAS_URL\` in your environment."` |
   | `HOST_UNREACHABLE` | `"The configured SaaS host did not respond within 2 seconds."` | `"Check network connectivity to \`{server_url}\` and retry."` |
   | `MISSING_MISSION_BINDING` | `"No tracker binding exists for feature \`{feature_slug}\`."` | `"Run \`spec-kitty tracker bind\` from this repo."` |

2. Two entries contain `{server_url}` / `{feature_slug}` placeholders. Use `str.format(...)` at construction time inside `_build_result()`; do **not** use f-strings in the catalog.
3. Add a helper `_build_result(state: ReadinessState, **fmt_kwargs: str) -> ReadinessResult` that looks up the wording, formats the placeholders, and returns the dataclass instance. For `READY`, it returns `ReadinessResult(state=READY, message="", next_action=None)`.

**Files**: `src/specify_cli/saas/readiness.py` (extended, +40 lines)

**Validation**: Unit tests in T010 will assert byte-wise wording. mypy --strict clean.

### T008 — Evaluator body: ordering, short-circuit, exception conversion

**Purpose**: Wire the prerequisite probes into the contract-defined order, short-circuit on the first failure, and convert unexpected exceptions into `HOST_UNREACHABLE`.

**Steps**:

1. Define private module-level helpers. **Helpers must not raise to callers**; they catch their own exceptions and report a signal value. This is what unit tests will monkey-patch:
   - `_probe_rollout() -> bool` — calls `is_saas_sync_enabled()`
   - `_probe_auth(repo_root: Path) -> bool` — calls into the existing auth lookup used by `TrackerService`. The auth token manager lives under `src/specify_cli/auth/` (e.g., `get_token_manager()` — confirm the exact callable and `is_authenticated` property during implementation; do not refactor auth itself).
   - `_probe_host_config() -> str | None` — **calls `specify_cli.auth.config.get_saas_base_url()` and catches `ConfigurationError`, returning `None` on failure and the stripped URL string on success**. This is the authoritative source per decision D-5 at `src/specify_cli/auth/config.py:1-35`: *"there is NO hardcoded SaaS domain anywhere in the codebase — callers must set `SPEC_KITTY_SAAS_URL` in the environment."* Do **not** fall back to `SyncConfig.get_server_url()` — that method has a legacy hardcoded default and is not the spec-referenced source. The spec's Edge Case explicitly names `SPEC_KITTY_SAAS_URL`.
   - `_probe_reachability(server_url: str, timeout_s: float = 2.0) -> bool` — single HTTP `HEAD` against the URL returned by `_probe_host_config()`, with a 2-second total budget; **any** exception returns False.
   - `_probe_mission_binding(repo_root: Path, feature_slug: str | None) -> bool` — calls the existing binding lookup path (the one at `src/specify_cli/cli/commands/tracker.py:345-351` in the current codebase).

2. Write `evaluate_readiness()` to:
   - **Do not accept a `SyncConfig` parameter.** The authoritative host URL comes from `get_saas_base_url()`; the evaluator does not need `SyncConfig` for any step.
   - Wrap the entire check sequence in a `try/except Exception as exc` — on any exception, return `_build_result(HOST_UNREACHABLE, server_url="")` with `details={"error": type(exc).__name__}`.
   - Inside the try, call probes in declaration order:
     1. `_probe_rollout()` → on False return `_build_result(ROLLOUT_DISABLED)`.
     2. `_probe_auth(repo_root)` → on False return `_build_result(MISSING_AUTH)`.
     3. `server_url = _probe_host_config()` → on `None` return `_build_result(MISSING_HOST_CONFIG)`; otherwise retain `server_url` for steps 4 and 6.
     4. (if `probe_reachability=True`) `_probe_reachability(server_url)` → on False return `_build_result(HOST_UNREACHABLE, server_url=server_url)`.
     5. (if `require_mission_binding=True`) `_probe_mission_binding(repo_root, feature_slug)` → on False return `_build_result(MISSING_MISSION_BINDING, feature_slug=feature_slug or "")`.
   - After all applicable probes pass, return `_build_result(READY)`.

3. The `require_mission_binding` and `probe_reachability` flags gate steps 4 and 5 respectively — when False, skip the probe entirely and consider that state "passed".

**Note on the spec edge case "SPEC_KITTY_SAAS_URL unset"**: This mission does **not** introduce a new env var. `SPEC_KITTY_SAAS_URL` already exists in the codebase as a mandatory, no-fallback env var (see `src/specify_cli/auth/config.py`, `src/specify_cli/auth/flows/authorization_code.py:86`, `src/specify_cli/auth/flows/device_code.py:84`, `src/specify_cli/sync/runtime.py:154`). The edge case is answered by the existing decision D-5 and is surfaced via `MISSING_HOST_CONFIG`. No new reader is added; the readiness evaluator consumes the authoritative helper that already exists.

**Files**: `src/specify_cli/saas/readiness.py` (extended, +80 lines)

**Validation**: Unit tests in T010 cover every branch. mypy --strict clean.

### T009 — Shared fixtures in `tests/saas/conftest.py`

**Purpose**: Provide the dual-mode rollout fixtures plus auth/config/binding factory fixtures that both unit and integration tests consume, preventing drift between the two layers.

**Steps**:

1. Create `tests/saas/conftest.py` with:
   - `@pytest.fixture def rollout_disabled(monkeypatch): monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False); yield`
   - `@pytest.fixture def rollout_enabled(monkeypatch): monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1"); yield`
   - `@pytest.fixture def fake_auth_present(tmp_path, monkeypatch)` — monkey-patches whatever `get_token_manager().is_authenticated` consults so the auth probe returns `True`. Document the monkeypatch target in a comment.
   - `@pytest.fixture def fake_auth_absent(tmp_path, monkeypatch)` — symmetric; forces the auth probe to return `False`.
   - `@pytest.fixture def fake_host_config_present(monkeypatch, local_http_stub) -> str` — sets `SPEC_KITTY_SAAS_URL` via `monkeypatch.setenv("SPEC_KITTY_SAAS_URL", local_http_stub)`. Returns the URL. This drives `get_saas_base_url()` through the authoritative env-var path.
   - `@pytest.fixture def fake_host_config_absent(monkeypatch)` — `monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)`. This makes `get_saas_base_url()` raise `ConfigurationError` and the host-config probe return `None`.
   - `@pytest.fixture def fake_mission_binding_present(tmp_path, monkeypatch) -> str` — writes a fake binding into the repo fixture and returns the feature_slug.
   - `@pytest.fixture def fake_mission_binding_absent(tmp_path) -> str` — returns a feature_slug but establishes no binding.
   - `@pytest.fixture def local_http_stub() -> str` — starts an `http.server.HTTPServer` bound to `127.0.0.1:0`, captures the assigned port, handles `HEAD` requests with a 200, yields the URL, and shuts down the server on teardown. Use `threading.Thread(target=server.serve_forever, daemon=True)`.
2. The autouse fixture at `tests/conftest.py:57-60` (`_enable_saas_sync_feature_flag`) is **global** — `rollout_disabled` uses `monkeypatch.delenv(..., raising=False)` to override it safely inside the specific test scope.
3. **Do not** create a `SyncConfig`-based fixture. `SyncConfig.get_server_url()` is not consulted by the readiness evaluator (per decision D-5 and spec edge case — see T008).

**Files**: `tests/saas/conftest.py` (~150 lines)

**Validation**: Fixtures are consumed by T010 and T011 tests. `pytest --collect-only tests/saas/` shows them.

### T010 — Unit tests: `tests/saas/test_readiness_unit.py`

**Purpose**: Exercise every branch of the evaluator with stubbed probes so failures are fast and isolated.

**Steps**:

1. Use `monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)` (etc.) to stub each probe per test. Write one test per `ReadinessState` that produces that state via the minimum-sufficient probe rigging.
2. For each non-READY state, assert **byte-wise**:
   - `result.message` equals the exact string from the contract table
   - `result.next_action` equals the exact string from the contract table (with placeholders substituted for `HOST_UNREACHABLE` and `MISSING_MISSION_BINDING`)
3. Ordering test: combine multiple probe failures (e.g., auth fails AND host config empty) and assert the earlier-declared state wins (`MISSING_AUTH`).
4. Exception-conversion test: monkey-patch `_probe_auth` to raise `RuntimeError("boom")` and assert the result is `ReadinessState.HOST_UNREACHABLE` with `details["error"] == "RuntimeError"`. The function **must not raise**.
5. `probe_reachability=False` test: stub `_probe_reachability` to always return False; assert that when `probe_reachability=False`, the probe is never called (use a Mock with `assert_not_called()`).
6. `require_mission_binding=False` test: symmetric assertion for binding probe.
7. Parametrize over both `rollout_disabled` and `rollout_enabled` modes — in rollout-disabled mode, `evaluate_readiness()` must return `ROLLOUT_DISABLED` regardless of other stubs.

**Files**: `tests/saas/test_readiness_unit.py` (~200 lines, ~8–10 test cases)

**Validation**: `pytest tests/saas/test_readiness_unit.py -q` green; coverage report shows every branch in `readiness.py` hit.

### T011 — Integration tests: `tests/saas/test_readiness_integration.py`

**Purpose**: Drive the **real** evaluator (no probe stubs) against fixture-backed auth, config, and binding state. This is the smaller "real evaluator" layer called out in the spec.

**Steps**:

1. Import the fixture factories from `conftest.py`. **Do not** stub `_probe_*` here — that is the whole point of this layer.
2. Test cases:
   - **Happy path**: `rollout_enabled` + `fake_auth_present` + `fake_host_config_present` (sets `SPEC_KITTY_SAAS_URL` to the local HTTP stub) + `fake_mission_binding_present` + `require_mission_binding=True` + `probe_reachability=True` → `ReadinessState.READY`.
   - **MISSING_AUTH**: `rollout_enabled` + `fake_auth_absent` → returns `MISSING_AUTH` with the stable wording.
   - **MISSING_HOST_CONFIG**: `rollout_enabled` + `fake_auth_present` + `fake_host_config_absent` (`SPEC_KITTY_SAAS_URL` unset) → returns `MISSING_HOST_CONFIG` with `next_action == "Set \`SPEC_KITTY_SAAS_URL\` in your environment."`
   - **MISSING_MISSION_BINDING**: `rollout_enabled` + all earlier prerequisites present + `fake_mission_binding_absent` + `require_mission_binding=True` → returns `MISSING_MISSION_BINDING` with the feature_slug interpolated into the message.
   - **HOST_UNREACHABLE**: `rollout_enabled` + auth present + `monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "http://127.0.0.1:1")` (port 1 is unused) + `probe_reachability=True` → returns `HOST_UNREACHABLE` within ~2 seconds.
3. Each test asserts the full `ReadinessResult` shape (`state`, `message`, `next_action`) — not just the enum.
4. The `HOST_UNREACHABLE` test's 2-second timeout budget is enforced with `pytest.mark.timeout(5)` to flag any regression.

**Files**: `tests/saas/test_readiness_integration.py` (~200 lines, 5 test cases)

**Validation**: `pytest tests/saas/test_readiness_integration.py -q` green in < 10 seconds total.

## Test Strategy

Unit tests (T010) cover every branch; integration tests (T011) cover the real evaluator end-to-end against fixture state. The two layers share fixtures via `conftest.py` to prevent drift. Both layers parametrize over rollout-on and rollout-off modes. Coverage target is ≥ 90% on `src/specify_cli/saas/readiness.py`.

## Definition of Done

- [ ] `src/specify_cli/saas/readiness.py` implements `ReadinessState`, `ReadinessResult`, `evaluate_readiness`, `_WORDING`, and all `_probe_*` helpers.
- [ ] `tests/saas/conftest.py` provides all fixtures listed in T009.
- [ ] `tests/saas/test_readiness_unit.py` and `test_readiness_integration.py` exist and pass.
- [ ] Every `ReadinessState` member has at least one test asserting its byte-wise wording.
- [ ] `evaluate_readiness()` never raises, even when a probe throws — verified by test.
- [ ] `pytest -q` full suite green.
- [ ] `mypy --strict src/specify_cli/saas/readiness.py` clean.
- [ ] No files outside `owned_files` modified.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Stub and integration fixtures drift in what "auth present" means | Both layers consume the same factory fixtures from `conftest.py`. |
| Auth lookup target unknown (need to pick the right monkey-patch path) | Inspect `src/specify_cli/auth/config.py` (or wherever auth lives) during implementation; document the target in a conftest comment. If no clean monkeypatch target exists, add a minimal indirection rather than monkey-patching a private symbol. |
| Reachability stub server port conflicts | Bind to `127.0.0.1:0` and read the assigned port — never hardcode. |
| The `HOST_UNREACHABLE` test takes ~2 seconds and flakes in slow CI | The timeout is a ceiling, not a measurement. Mitigation: use `pytest.mark.timeout(5)` to fail loudly rather than hang. |
| `MISSING_MISSION_BINDING` tests the existing binding lookup which may change in a future mission | Wire the probe through a well-named helper so a future rewrite is localized. |

## Reviewer Guidance

- Verify every non-READY state has a byte-wise wording test.
- Confirm `evaluate_readiness()` has a top-level `try/except` and `_probe_*` helpers never raise.
- Confirm the check order in the implementation matches `ReadinessState` declaration order.
- Run the integration layer twice to check for flakes in the reachability probe.
- Confirm no changes to `src/specify_cli/saas/__init__.py` — that file is owned by WP01 and callers use `from specify_cli.saas.readiness import ...` in this mission.
- Scan `tests/conftest.py` to make sure the autouse fixture is not disabled; `rollout_disabled` must layer on top via monkeypatch.

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Activity Log

- 2026-04-11T08:29:51Z – claude:sonnet:python-implementer:implementer – shell_pid=55366 – Started implementation via action command
- 2026-04-11T08:40:55Z – claude:sonnet:python-implementer:implementer – shell_pid=55366 – HostedReadiness evaluator + unit/integration tests landed. All checks green.
- 2026-04-11T08:41:58Z – claude:opus-4-6:reviewer:reviewer – shell_pid=65504 – Started review via action command
- 2026-04-11T08:43:04Z – claude:opus-4-6:reviewer:reviewer – shell_pid=65504 – Review PASS (claude:opus-4-6:reviewer). HostedReadiness evaluator implemented per data-model §§2-4. ✓ 6-member ReadinessState enum, frozen ReadinessResult, _WORDING catalog with contract-exact strings (MISSING_HOST_CONFIG correctly says 'Set SPEC_KITTY_SAAS_URL in your environment'). ✓ _probe_host_config() calls auth.config.get_saas_base_url() — NOT SyncConfig.get_server_url(). Drift corrected per decision D-5. ✓ evaluate_readiness() no config parameter, top-level try/except converts any exception to HOST_UNREACHABLE, never raises. ✓ Check order correct with short-circuit semantics. ✓ 19/19 tests pass (14 unit + 5 integration, including happy path, MISSING_AUTH, MISSING_HOST_CONFIG, MISSING_MISSION_BINDING, HOST_UNREACHABLE with 2s timeout). ✓ mypy --strict clean. ✓ Clean diff — only 4 owned files touched. ✓ No changes to saas/__init__.py (owned by WP01). Ready for WP03.
