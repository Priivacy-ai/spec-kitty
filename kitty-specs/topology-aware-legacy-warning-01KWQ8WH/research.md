# Research: Topology-aware legacy warning — live-code brief (#2351)

Read-only investigation against the checkout (branch `fix/topology-aware-legacy-warning`).

## F1 — `_is_legacy_mission()` is a SHARED predicate; the split is mandatory
`_is_legacy_mission()` (`src/specify_cli/coordination/transaction.py:200-230`) returns `not coordination_branch` (reads only `coordination_branch`). Its single result `legacy_mode` (`transaction.py:718`) drives THREE consumers:
1. **Worktree routing** — `:719-730` (`_resolve_legacy_lane_destination` override vs. the coordination-worktree `else` at `:731-774`).
2. **Write-contract** — persisted at `:831` (`txn._legacy_mode`), consumed at `:909` (`primary_checkout_append` vs `coordination_transaction_append`).
3. **Warning** — `:730` calls `_emit_legacy_warning_once` (`:317-347`).

If `_is_legacy_mission()` became topology-aware and returned `False` for `single_branch`/`lanes` (which legitimately have no `coordination_branch`), `acquire()` would take the `else` arm and try to resolve a coordination worktree that does not exist → `BookkeepingWorktreeMissing`, and `append_event` would pick the wrong contract. **So the predicate stays unchanged; only the warning gets a new, narrower gate.**

## F2 — Canonical reader: `stored_topology_from_meta` (non-deriving)
`stored_topology_from_meta(meta) -> MissionTopology | None` (`src/specify_cli/missions/_read_path_resolver.py:117-135`) — PURE (no file/git), reads only `topology`, returns `None` when absent/non-string/unrecognised (`except ValueError`). **Use this.**
**Trap:** `read_topology`/`resolve_topology`/`_derive_topology` (`migration/backfill_topology.py:56-106`, `mission_runtime/resolution.py:735-774`) DERIVE a shape via `classify_topology` when absent → a genuine un-backfilled legacy mission comes back as `SINGLE_BRANCH`, indistinguishable from a created `single_branch`. Using a deriving reader would silence genuine-legacy warnings.

## F3 — `flattened` flag
Stored as `meta.json` key `"flattened"` (bool); written at create (`core/mission_creation.py:457`) and backfill (`migration/backfill_topology.py:228`). Key constant `_FLATTENED_KEY = "flattened"` (`backfill_topology.py:38`, module-private). No reader function — read inline `meta.get("flattened")`, treating falsy/absent as not-flattened.

## F4 — `MissionTopology` enum (4 members)
`src/mission_runtime/context.py:64-67`: `SINGLE_BRANCH`, `LANES`, `COORD`, `LANES_WITH_COORD`. `FLATTENED` is a separate flag, not a member (`:58-61`). Coord-carrying = `COORD` + `LANES_WITH_COORD` (`_COORD_ROUTING_TOPOLOGIES`, `:114-116`) — these never reach the warning path (they have `coordination_branch` → `_is_legacy_mission` False).

## F5 — Fix shape
New module-private helper in `transaction.py` near `_coordination_branch_from_meta` (`~:233`):
```python
def _warrants_legacy_warning(repo_root, mission_slug, mid8) -> bool:
    meta = <load primary meta.json, same as _is_legacy_mission :217-227>
    if not isinstance(meta, dict): return False
    if meta.get("coordination_branch"): return False   # defensive; legacy_mode already excludes
    if meta.get("flattened"): return False
    from specify_cli.missions._read_path_resolver import stored_topology_from_meta
    return stored_topology_from_meta(meta) is None
```
Re-point `:730`: `if _warrants_legacy_warning(repo_root, safe_mission_slug, safe_mid8): _emit_legacy_warning_once(...)`. `_is_legacy_mission`, `:719-729`, `:831`, `:909` untouched. **Malformed topology → warns** (stored_topology_from_meta → None), the correct conservative default. Optional DRY hoist: a shared `_load_mission_meta(...)` since three helpers read the same file (S1192/DRY).

## F6 — Coupled runbook (`docs/migrations/legacy-to-coordination.md`)
- Bullet `:61-65` ("such a mission sees the same once-only warning; equally safe to ignore") — now FALSE; rewrite: single_branch/lanes no longer warn (topology-aware).
- Flattened bullet `:66-69` — clarify no warning.
- Path A note `:125-127` ("warning behavior is unchanged") — now backfilling a genuine-legacy mission (stores `topology`) SUPPRESSES future warnings; update.
Run `pytest tests/architectural/test_no_legacy_terminology.py` after prose edits.

## F7 — Test seams
Extend `tests/integration/test_legacy_mission_fallback.py` — warning test `test_legacy_mission_warning_emitted_once` (`:183-219`); genuine-legacy fixture `_make_legacy_mission` (`:70-123`, writes meta with no coord_branch/topology/flattened). Parametrize the fixture with `topology=`/`flattened=`. Add direct unit tests of `_warrants_legacy_warning` (new file under `tests/specify_cli/coordination/`).

## Decision
Add `_warrants_legacy_warning` (reusing `stored_topology_from_meta`), re-point the emit, leave `_is_legacy_mission` + routing + write-contract untouched, update the runbook (3 spots). Malformed topology warns.

## Residual risks
1. **Reader-choice trap** (highest): wiring a deriving reader silences genuine-legacy → the genuine-legacy + single_branch tests together pin it (both mandatory).
2. Double meta read (harmless; optional `_load_mission_meta` hoist).
3. Import cycle — use a function-local import (module already does).
4. Doctrine terminology gate on the runbook prose.
5. Backfill-suppression is a documented-contract change (Path A note) — assert it with a test so it isn't "fixed" back.
