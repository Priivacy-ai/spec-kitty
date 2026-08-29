# Post-Plan IMPLEMENTABILITY lens — sync-deactivate-by-default-01M16M1P

## 1. Predicate ingredients
- `first_set_sync_disable_env()` — `core/env.py:73`, returns None when neither
  SPEC_KITTY_SYNC_DISABLE nor SPEC_KITTY_SYNC_MINIMAL_IMPORT truthy. `SYNC_DISABLE_ENV_VARS`
  = those two (`env.py:24`). CONFIRMED.
- `is_saas_sync_enabled()` — canonical def in `core/saas_sync_config.py:37`, reads ONLY
  `SPEC_KITTY_ENABLE_SAAS_SYNC` via `is_truthy`. CONFIRMED. Re-exported through
  `saas/rollout.py:14` → `sync/feature_flags.py:5`. daemon uses rollout; events uses
  feature_flags; both root at saas_sync_config. Composition correct.

## 2. Gated sites (all CONFIRMED, minor line drift)
- daemon: `first_set_sync_disable_env()` at :1131, `is_saas_sync_enabled()` at :1154
  (imported :1141). Matches "disable-first + saas". OK.
- events.py:109 and :182 both `if repo_root is None or not is_saas_sync_enabled():`.
  CONFIRMED. Egress: replacing with sync_active() does NOT bypass consent — events.py
  docstring :166-176 states this is machine-global ARMING; true egress refusal lives in
  `SyncRuntime.publish_event`. sync_active() is strictly STRICTER (adds disable-var), so it
  can only arm-less, never bypass egress. INV-2 safe.
- emitter `_route_event` at **:2633** (plan says 2648); unconditional
  `return self._queue_event_locally(event)` at ~2645, `_queue_event_locally` at :2651.
  This IS the local-capture path (#1072, deliberately ungated). "2648" ±right. CONFIRMED.
- dossier_pipeline.py:471 = `def trigger_feature_dossier_sync_if_enabled`. CONFIRMED.
- tasks_move_task.py: `_mt_pre_review_gate_env_disable_reason()` :987, reads
  `first_set_sync_disable_env()` :993 (import :120, sole use → clean removal OK). CONFIRMED.

## 3. IMPORT CYCLE — REAL. sync_active() must NOT live in core/env.py as written.
`saas_sync_config.py:18` does `from specify_cli.core.env import is_truthy`. A top-level
`from ...saas_sync_config import is_saas_sync_enabled` in env.py creates env→saas_sync_config
→env, and `is_truthy` (env.py:30) is not yet bound when env imports first → ImportError.
**Fix: put `sync_active()` in `core/saas_sync_config.py`** (already depends on env, one
direction; can import `first_set_sync_disable_env`). Consumers already reach is_saas_sync_enabled
via that module's re-export chain. Alternative: keep in env.py but with a function-LOCAL
deferred import — uglier, still one predicate. Contract's "Location: core/env.py" is WRONG;
correct it to saas_sync_config.py. INV-4 (single predicate) preserved either way.

## 4. Registration is IMPORT-TIME (late-bind hazard)
sync/__init__.py:455/458 gate on `SPEC_KITTY_SYNC_MINIMAL_IMPORT` at MODULE level →
decision frozen at first import. Comment :453-455 says tests re-call
`register_default_handlers()` after toggling env. So the seam must sit INSIDE
`register_default_handlers()` (call-time, live re-eval), NOT only at the import-time call
site — otherwise C-006 late-bind breaks. WP02 must gate the function body, keep the function
unconditionally callable. (Note _dossier_sync_handler :248 already gates at call-time.)

## 5. WP ordering
- WP01 unblocker: YES — seam + #2801 are the shared prerequisite.
- WP02 (src) vs WP04 (tests/conftest): no file collision (sync/* vs tests/conftest.py).
  conftest mask confirmed: :223 setdefault + :427 autouse `_enable_saas_sync_feature_flag`.
- MIS-ORDER: graph hangs WP05 (skipif) and WP07 (arch guards → no-op contract) under WP04
  only. Both VALIDATE the gated behavior introduced by WP02. Add edges WP05→WP02 and
  WP07→WP02, else they assert default-off before registration/emit are actually gated.
- WP02/WP04 parallel is otherwise fine; WP02→WP03 serialize (both sync/, OK).
