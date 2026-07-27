# Data Model — Landing-Pass Campsite Follow-ups

This is a test-infrastructure + CLI-internals mission; it introduces no
persistent domain entities. The only "model" changes are the small structural
elements below.

## SG-1 — `ShardGroup.default_fallback` (new optional field)

- **Where**: `tests/_shard_registry.py` (the `ShardGroup` dataclass).
- **Type**: `bool`, default `False`.
- **Meaning**: when `True`, `shard_for(path)` returns a deterministic
  hash-bucket shard for any under-root file not present in `file_assignment`,
  instead of `None`.
- **Invariant**: explicit `file_assignment` entries are checked first and always
  win; the fallback only fires for unlisted under-root files; the group's shard
  union still covers the full root universe (GC-1 union invariant).
- **Consumers**: the `arch` row (`tests/_arch_shard_map.py`) opts in; the `next`
  row is unaffected unless it also opts in.

## LN-1 — `Lane.UNINITIALIZED` (new canonical member)

- **Where**: `src/specify_cli/status/models.py` (add member), consumed via
  `src/specify_cli/status/lane_reader.py`.
- **Change**: add a NEW `Lane.UNINITIALIZED = "uninitialized"` member and return
  it from `get_wp_lane()` instead of the bare string `LEGACY_UNINITIALIZED_SENTINEL`,
  so the loader's return type is a pure `Lane`.
- **Why a new member, NOT reuse of `Lane.GENESIS`**: the two are semantically
  distinct. `get_wp_lane` returns the sentinel when a WP is **absent from the
  snapshot** (empty event log, or WP not present); `GENESIS` is a WP that **is**
  seeded but has no explicit lane (`lane_reader.py:72` default). Collapsing them
  onto `GENESIS` regresses `worktree_topology.py:81` (unseeded→"planned") and
  `merge/done_bookkeeping.py` (done-detection). Verified in code.
- **Invariant**: the StrEnum value stays `"uninitialized"`, so existing
  `== "uninitialized"` equality (via StrEnum) and any serialized form remain
  behavior-identical. `UNINITIALIZED` is a **non-display, non-transitionable**
  read sentinel (like `GENESIS`). Full, verified blast radius (post-tasks squad):
  - **FSM (`wp_state.py`)**: add a **dedicated `UninitializedState` with
    `allowed_targets() -> frozenset()` (EMPTY)** and register it in
    `_STATE_MAP`/`_FACTORY_ALIASES` — NOT an alias to `GenesisState`. Aliasing to
    genesis (targets `{PLANNED, CANCELED}`) would inject 2 edges into the
    import-time `ALLOWED_TRANSITIONS` build (`transitions.py:43-48`) → the ==29
    count test fails AND the sentinel becomes transitionable. An unmapped member
    crashes `transitions.py:44` at import.
  - **Display filters** must exclude UNINITIALIZED at **five** sites (route
    through a canonical non-display-lane authority): `reducer.py:134,166`,
    `wp_metadata.py:385`, `tasks_status_view.py:163`, and `lifecycle.py:119`
    (the last has no genesis filter today — it already emits `"genesis": 0`).
  - **`CANONICAL_LANES` parity (`status_lanes.py`)**: `test_parity.py:812`
    requires every non-genesis member in `CANONICAL_LANES`. UNINITIALIZED is
    **exempted** like genesis (non-display) — update the parity exemption, do NOT
    add it to the tuple.
  - **~12 lane-roster tests** across `tests/status/`, `tests/specify_cli/status/`,
    `tests/specify_cli/cli/commands/agent/`, `tests/integration/`,
    `tests/test_dashboard/` derive "all non-genesis lanes" or a hardcoded roster
    and must also exclude/extend for UNINITIALIZED.
  - **Consumer contract (WP06)**: `coordination/status_transition.py:557` and
    `merge/done_bookkeeping.py:151` both rely on `Lane("uninitialized")` RAISING
    today; once it is a member the `except` goes dead — preserve the
    GENESIS-fallback / force-done=`False` contract explicitly.
- **Effect**: removes the `Lane | str` union at its source; `get_all_wp_lanes`
  annotation → `dict[str, Lane]` (verify `workspace/context.py:497,513` does not
  surface a new diagnostic). Requires behavior tests on the unseeded path — the
  regression is type-invisible because consumers already `str(...)`-coerce.

## RR-1 — Remediation registry

- **Where**: `src/specify_cli/sync/preflight.py`.
- **Change**: all remediation sentences become named module constants; a single
  `ALL_REMEDIATION_TEXTS` collection is the canonical set. Both `_REMEDIATION_HINTS`
  (field → remedy) and `_build_remediation_lines()` (trigger → bullet) reference
  the constants.
- **Invariant**: the command-name validation guard scans `ALL_REMEDIATION_TEXTS`
  (the full set), not just the dict; every referenced command resolves under
  `--help`. Rendered output is byte-identical to today.

## No API contracts

No external route, request/response body, auth header, websocket, sync payload,
or tracker control-plane semantics change → `contracts/` is intentionally empty
(recorded in plan.md).
