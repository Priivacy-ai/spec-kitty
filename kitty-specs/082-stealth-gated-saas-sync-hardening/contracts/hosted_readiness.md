# Contract: Hosted Readiness Evaluator

**Module**: `src/specify_cli/saas/readiness.py`
**Stability**: Internal CLI surface, public to all of `src/specify_cli/`. Stable contract.

---

## Types

- `ReadinessState` (Enum) — see [data-model.md §2](../data-model.md)
- `ReadinessResult` (frozen dataclass) — see [data-model.md §3](../data-model.md)

---

## Function: `evaluate_readiness`

```python
def evaluate_readiness(
    *,
    repo_root: Path,
    feature_slug: str | None = None,
    require_mission_binding: bool = False,
    probe_reachability: bool = False,
) -> ReadinessResult: ...
```

### Inputs

| Parameter | Required | Default | Description |
|---|---|---|---|
| `repo_root` | yes | — | Absolute path to the repo root; used to locate auth, config, and bindings. |
| `feature_slug` | no | `None` | Active feature slug. Required when `require_mission_binding=True`. |
| `require_mission_binding` | no | `False` | When `True`, an absent mission binding causes `MISSING_MISSION_BINDING`; otherwise binding is not checked. |
| `probe_reachability` | no | `False` | When `True`, issue a single bounded HTTP `HEAD` against `SyncConfig.server_url`; otherwise reachability is never checked. |

### Output

A `ReadinessResult`. Always one of the six `ReadinessState` members. **The function never raises** — internal exceptions are converted into `HOST_UNREACHABLE` results with the exception type captured in `details["error"]`.

### Check Order (short-circuits on first failure)

1. `is_saas_sync_enabled()` → `ROLLOUT_DISABLED`
2. Auth lookup → `MISSING_AUTH`
3. `specify_cli.auth.config.get_saas_base_url()` — if this raises `ConfigurationError` (because `SPEC_KITTY_SAAS_URL` is unset or empty) → `MISSING_HOST_CONFIG`. The returned URL is the value used for reachability in step 4 and for the `HOST_UNREACHABLE` failure message. **This check does not consult `SyncConfig.get_server_url()` — per decision D-5 in `src/specify_cli/auth/config.py`, `SPEC_KITTY_SAAS_URL` is the authoritative host URL surface.**
4. (only if `probe_reachability=True`) HEAD probe against the URL from step 3 → `HOST_UNREACHABLE`
5. (only if `require_mission_binding=True`) binding lookup → `MISSING_MISSION_BINDING`
6. `READY`

### Performance Budget

| Step | Budget |
|---|---|
| Steps 1–3, 5 (local I/O only) | < 50 ms typical, < 200 ms worst case |
| Step 4 (reachability) | ≤ 2,000 ms total (single attempt, no retry) |

### Failure Message Contract (NFR-002)

For every non-`READY` state, the result MUST satisfy:
- `message` names the prerequisite explicitly (e.g., "No SaaS authentication token is present", not "not ready").
- `next_action` provides one concrete actionable step (e.g., "Run `spec-kitty auth login`").
- `details` MAY contain structured context but MUST NOT be the only source of human-readable information.

### Stable wording (asserted by tests)

| State | `message` template | `next_action` template |
|---|---|---|
| `ROLLOUT_DISABLED` | "Hosted SaaS sync is not enabled on this machine." | "Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in." |
| `MISSING_AUTH` | "No SaaS authentication token is present." | "Run `spec-kitty auth login`." |
| `MISSING_HOST_CONFIG` | "No SaaS host URL is configured." | "Set `SPEC_KITTY_SAAS_URL` in your environment." |
| `HOST_UNREACHABLE` | "The configured SaaS host did not respond within 2 seconds." | "Check network connectivity to `{server_url}` and retry." |
| `MISSING_MISSION_BINDING` | "No tracker binding exists for feature `{feature_slug}`." | "Run `spec-kitty tracker bind` from this repo." |

---

## Caller Contract

### Tracker CLI commands (`src/specify_cli/cli/commands/tracker.py`)

- The current generic `_require_enabled()` callback is REPLACED with per-command calls that pass:
  - `require_mission_binding=True` for: `discover`, `status`, `map add`, `map list`, `sync pull`, `sync push`, `sync run`, `sync publish`, `unbind`
  - `require_mission_binding=False` for: `providers`, `bind`
  - `probe_reachability=True` for: `sync pull`, `sync push`, `sync run`, `sync publish` (commands that immediately need the network)
  - `probe_reachability=False` for everything else
- On non-`READY` results, the command exits with code `1` and prints `result.message` followed by a blank line and `result.next_action`.
- On `ROLLOUT_DISABLED` specifically, the command exits with code `1` — note that this state is *normally unreachable from a tracker CLI command* because the conditional registration in `cli/commands/__init__.py` hides the group entirely. The check remains as a defense-in-depth assertion in case the gate flips between import and invocation.

### Programmatic callers (dashboard, daemon)

- MAY call `evaluate_readiness()` to render status panels.
- MUST NOT use the result to *decide* whether to start the daemon — that decision is owned by `ensure_sync_daemon_running()` and its `DaemonIntent` argument (see [background_daemon_policy.md](background_daemon_policy.md)).

---

## Test Requirements

`tests/saas/test_readiness_unit.py` (stubs):
- Each `ReadinessState` has at least one positive test (the state is reached).
- Wording is asserted byte-for-byte against the table above.
- Order is asserted by combining failures and verifying the earlier check wins.
- Reachability probe stub is called iff `probe_reachability=True`.
- Binding probe stub is called iff `require_mission_binding=True`.
- An exception inside any prerequisite probe yields `HOST_UNREACHABLE` (not a raised exception).

`tests/saas/test_readiness_integration.py` (real evaluator):
- Uses `tmp_path` fixtures for auth/config/binding state.
- Drives at least one happy path (`READY`) and three failure paths (`MISSING_AUTH`, `MISSING_HOST_CONFIG`, `MISSING_MISSION_BINDING`).
- Reachability is exercised against a local stub server (no real network) — opt-in via `probe_reachability=True`.
- Both rollout-on and rollout-off modes exercised via the shared fixtures.

`tests/agent/cli/commands/test_tracker.py` (parametrized):
- Each tracker command has a row for `rollout_disabled` (asserts hidden) and `rollout_enabled` × prerequisite-state matrix (asserts the right per-prerequisite message reaches stdout).
