# Phase 0 — Research (pre-plan grounding squad)

Three read-only agents grounded the mission against main (`db4e39806`). Findings are the authority
for the plan; re-verify with `git grep` if the tree moves.

## §1 — #2534 consumer-repo calm-degrade (VERDICT: M — manual reconcile, land the branch)

- Fix = commit **`0153934f9`** (branch `fix/2534-pre-review-gate-consumer-repo`), **4 files, +142/−3**:
  - `src/charter`... no — `src/specify_cli/review/pre_review_gate.py` (+31): gives `GateAuthoritiesUnavailable`
    a real `__init__(self, message, *, is_consumer_repo)`; adds `_is_spec_kitty_source_repo(repo_root)` =
    `(repo_root/"tests"/"architectural"/"_gate_coverage.py").is_file()` (the single robust discriminator —
    it *is* the module being imported); passes `is_consumer_repo=` to both raise sites.
  - `src/specify_cli/cli/commands/agent/tasks_move_task.py` (+28/−3): adds `_PRE_REVIEW_CONSUMER_REPO_REASON`
    (calm text, never names the internal module); the `except GateAuthoritiesUnavailable` branch picks it when
    `exc.is_consumer_repo`, still routing through `_mt_empty_scope_verdict` (non-blocking `no_coverage`).
  - `tests/review/test_pre_review_gate_engine.py` (+43, 3 fast unit tests), `tests/review/test_pre_review_gate_integration.py`
    (+43, 1 integration e2e through the real `move-task` path).
- **Bug still reproduces on main**: `GateAuthoritiesUnavailable` is a plain RuntimeError (no `is_consumer_repo`);
  `pre_review_gate.py:156-160` embeds `_GATE_COVERAGE_MODULE_NAME = "tests.architectural._gate_coverage"`
  (`:106`) in the message. `git grep` finds zero `is_consumer_repo`/`_is_spec_kitty_source_repo`/`_PRE_REVIEW_CONSUMER_REPO_REASON` on main.
- **Rebase**: 3 of 4 files `git apply --check` **clean** (pre_review_gate.py + both tests). Only
  `tasks_move_task.py` conflicts — **positional drift only** (its two hunks target byte-identical text that
  moved ~110 lines, partly from #2573's own `_PRE_REVIEW_GATE_DISABLE_ENV_VARS` insertion at `:758-771`).
  `git apply --3way` resolves it. Port-the-intent fallback documented: the guard belongs in
  `_mt_pre_review_gate_verdict`'s `except` branch (HEAD `:1025-1029`).

## §2 — #2573b daemon-disable-env + #2809 strict-json isolation (both S)

- **#2573b fix site**: `_daemon_start_skip_reason` at **`src/specify_cli/sync/daemon.py:1038-1051`** — it checks
  `rollout_disabled`/`intent_local_only`/`policy_manual` then returns `None` (proceed to spawn); it never
  consults the disable envs. Add an early check (~3-6 lines) reusing `is_truthy` from `specify_cli.core.env`,
  mirroring the pre-review-gate's `_PRE_REVIEW_GATE_DISABLE_ENV_VARS = ("SPEC_KITTY_SYNC_DISABLE",
  "SPEC_KITTY_SYNC_MINIMAL_IMPORT")` grammar (`tasks_move_task.py:768-771,825-828`). Returning a non-None
  reason short-circuits before the spawn. **Blast radius: none** on the non-disabled path; all daemon callers
  (dashboard, events, restart) route through this helper and uniformly gain the honor-disable behavior (the
  intended FR-006 semantics). Repro `tests/sync/test_daemon_sync_disable_env.py` confirmed **RED**
  (`started=True, skipped_reason=None` despite the env).
- **#2809 root cause**: `test_strict_json_stdout::test_mission_create_json_strict_when_sync_skips_ingress`
  (`tests/sync/test_strict_json_stdout.py:744`) is a subprocess test that `os.environ.copy()`s WITHOUT resetting
  `SPEC_KITTY_SYNC_*`; a leaked toggle (the #2794 parallel-suite leak class) disables sync in the child, so the
  `direct ingress skipped` diagnostic never fires → red.
- **The env-reset fixture already exists** — `_isolate_pre_review_gate_sync_toggles` (autouse, from #2794 commit
  `922935a4d`) at `tests/specify_cli/cli/commands/agent/conftest.py:51-70` (two `monkeypatch.delenv`). But it is
  **agent-package-scoped** and does not reach `tests/sync/`. **WP03 = copy that fixture into
  `tests/sync/conftest.py`** (minimal blast-radius; root `tests/conftest.py` is the wider alternative).

## §3 — CI-red depth (all S; nothing needs splitting) — debugger-debbie

- **KEY CONVERGENCE**: the `'str' object has no attribute 'get'` red AND `test_charter_epic_golden_path` (e2e)
  are the **same bug** at `src/charter/evidence/orchestrator.py:95-96`: `config.get("charter")` returns a
  **path string** post-#2773 (config `charter:` key was repurposed to a pointer), then `.get("synthesis_inputs")`
  → AttributeError. `synthesis_inputs`/`url_list` has no live config home post-#2773. **FIX**: `if not
  isinstance(charter_cfg, dict): charter_cfg = {}` (2 lines) + fix the stale docstring (`:82`). Clears the
  phase3 dry-run, the orchestrator dry-run, AND the e2e golden-path. **Defer** (separate issue, NOT this
  mission): re-wiring `url_list` to read from `charter.yaml` — scope expansion, not CI-red work.
- **`test_bundle_contract` charter.yaml-missing**: test-fixture staleness — `_init_fixture`
  (`tests/charter/test_bundle_contract.py:43-68`) seeds only `charter.md`, but the v2 manifest tracks BOTH
  `charter.md` + `charter.yaml` (authored, neither derived). **FIX (test-only)**: seed + commit a minimal
  `charter.yaml` in the fixture.
- **`test_upgrade_updates_templates`** (`tests/adversarial/test_distribution.py:237`): CLAUDE.md category-2 auth
  artifact (`logged_out_on_connected_teamspace`). **Env-guard/skip-when-logged-out** (preferred, mirrors the
  charter-mission auth-skip) or xfail-with-ref.
- **`test_resolve_by_urn` warnings flake** (`tests/runtime/test_resolve_by_urn.py:178-195`): a
  `DeprecationWarning` at fixed loc `resolver.py:181`; a prior same-worker emission populates
  `resolver.__warningregistry__` and `catch_warnings` filter-restore leaves a later same-location `warn()`
  deduped → 0 captured → red. Passes in isolation. **FIX (test-side)**: clear
  `resolver.__warningregistry__` inside the block (or autouse fixture); `simplefilter("always")` alone is
  insufficient.
- **mission-loader-coverage skip anomaly**: guard/filter mismatch in `.github/workflows/ci-quality.yml` —
  the job gates on `next || core_misc` (`:1290-1293`) but `src/specify_cli/mission_loader/**` maps to the
  `platform` filter group (`:353`), so a mission_loader-only change skips the gate protecting it. **FIX**:
  add `|| needs.changes.outputs.platform == 'true'` to the job `if:`. Do NOT split — clearly rooted.
