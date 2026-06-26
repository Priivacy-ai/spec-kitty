---
affected_files: []
cycle_number: 2
mission_slug: spec-kitty-home-isolation-01KW1JXX
reproduction_command:
reviewed_at: '2026-06-26T12:22:47Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-06-26T12:33:58Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "Cycle-1 fix verified: focused test 18/18 in isolation, single shim test passes alone, POSIX-flat + lazy shim intact, sync suite green (1738 passed), ruff+mypy clean. Arbiter override of stale review-cycle-2 artifact; --force for known coord/primary subtask-gate lag."
---

# WP02 Review — Cycle 1 (reviewer-renata)

**Verdict: CHANGES REQUESTED**

The production reroute is correct and clean (config/queue/daemon/clock all resolve
under `get_runtime_root().base`; POSIX flat layout preserved byte-identical; lazy
`SPEC_KITTY_DIR` shim via module `__getattr__`; no `Path.home()`/`.spec-kitty`
literals in `src/specify_cli/sync/`; ruff + mypy clean; no new suppressions). One
blocker in the test file must be fixed before approval.

---

## Issue 1 (BLOCKER) — `test_spec_kitty_dir_shim_is_lazy` fails the focused review command

`tests/sync/test_spec_kitty_home_paths.py:172`

```python
monkeypatch.delattr(daemon, "SPEC_KITTY_DIR", raising=False)
```

This line raises `AttributeError: 'module' object has no attribute 'SPEC_KITTY_DIR'`
whenever the module is in its clean state (no real `SPEC_KITTY_DIR` attribute in
`daemon.__dict__`) — which is exactly production state and exactly the state the
WP's own required focused command exercises:

```
.venv/bin/pytest tests/sync/test_spec_kitty_home_paths.py -q
=> 1 failed, 17 passed
FAILED ...::test_spec_kitty_dir_shim_is_lazy[False]
```

Reproduced deterministically in isolation too:

```
.venv/bin/pytest "tests/sync/test_spec_kitty_home_paths.py::test_spec_kitty_dir_shim_is_lazy" -q
=> F.   (1 failed, 1 passed)
```

### Root cause
`monkeypatch.delattr(target, name, raising=False)` first checks `hasattr(target, name)`.
For a module with `__getattr__`, `hasattr` returns `True` even when no *real*
attribute exists (the shim synthesizes a `Path`). So `raising=False` does NOT
short-circuit; monkeypatch proceeds to call the builtin `delattr(daemon, "SPEC_KITTY_DIR")`,
which fails because the name lives only on `__getattr__`, not in `daemon.__dict__`.

Worse, monkeypatch appends `(daemon, "SPEC_KITTY_DIR", <Path>)` to its undo list
*before* the failing `delattr`. On teardown it runs `setattr(daemon, "SPEC_KITTY_DIR", <Path>)`,
leaking a **real** module attribute. That is why:
- the `[False]` param (runs first) always fails, then leaks a real attribute;
- the `[True]` param then "passes" because the leaked real attribute makes `delattr` succeed;
- the **full** `tests/sync/` suite is green only because an earlier daemon test
  (`tests/sync/test_daemon.py`, `test_daemon_intent_gate.py`, `test_issue_598_hang_fixes.py`)
  leaks a real `SPEC_KITTY_DIR` via its own `monkeypatch.setattr` teardown before
  this file runs. The test passes by cross-test global-state pollution, not by the
  production code path — a false-green (WP anti-pattern checklist item 2).

### Fix
Only delete a **real** attribute, gated on its presence in `daemon.__dict__`
(not `hasattr`, which the shim defeats):

```python
# Remove any real attribute leaked by a prior test's monkeypatch teardown so the
# module __getattr__ shim — not a frozen real attribute — is what we exercise.
if "SPEC_KITTY_DIR" in daemon.__dict__:
    monkeypatch.delattr(daemon, "SPEC_KITTY_DIR")
base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
assert base == daemon.SPEC_KITTY_DIR
```

(Equivalently `daemon.__dict__.pop("SPEC_KITTY_DIR", None)`, which also avoids the
teardown re-leak. Either is fine — production never reads the name, and the daemon
tests set it themselves.)

### Acceptance after fix
`.venv/bin/pytest tests/sync/test_spec_kitty_home_paths.py -q` must be fully green
(18 passed) **in isolation**, and the file must pass when run alone, not only after
a daemon test has polluted the module. Please re-run the focused command and paste
the result.

---

## Everything else: PASS

- **FR-001/004/005/006/007** (env-set): config (`config_dir = base`, `config_file = base/config.toml`),
  queue feeders (`credentials`, `auth`, `queue.db`, `queues/`, `active_queue_scope`, `config.toml`),
  active scope, daemon `_sync_root`/`_daemon_root`, Lamport clock all resolve under
  `get_runtime_root().base`. Verified in source and by the (otherwise-passing) parametrized tests.
- **NFR-001 / POSIX flat (research.md D3)**: `_daemon_root()` POSIX = `base` (NOT `base/daemon`);
  `_sync_root()` POSIX = `base/sync`; clock = `base/clock.json`; queue suffixes unchanged.
  No POSIX path was switched to `RuntimeRoot.daemon_dir`/`tracker_dir`. Windows branches
  correctly delegate to `get_runtime_root().sync_dir`/`.daemon_dir` (now env-aware via WP01).
  `test_unset_base_is_byte_identical_to_legacy` asserts `base == Path.home()/".spec-kitty"`.
- **Lazy `SPEC_KITTY_DIR` (research.md D5)**: import-time constant removed; resolved per-access
  via module `__getattr__` → `_spec_kitty_dir()` → `get_runtime_root().base`; raises
  `AttributeError` for unknown names (verified by `test_spec_kitty_dir_shim_rejects_unknown_attr`).
  No production importer of `SPEC_KITTY_DIR` outside `daemon.py` (grep `src/` clean;
  `auth/token_manager.py` has its own independent `_SPEC_KITTY_DIRNAME`, out of scope).
- **FR-010**: no `Path.home() / ".spec-kitty"` and no `.spec-kitty` literals in
  `src/specify_cli/sync/` (only doc-comment references in `preflight.py`, not owned by WP02).
- **Anti-pattern checklist**: dead code N/A; silent-empty-return N/A; frozen surface PASS;
  locked decision PASS (POSIX flat respected); production fragility PASS (no new bare raises in
  prod paths — the `__getattr__` `AttributeError` is the correct Python contract for a missing attr).
- **Quality gates**: `ruff check src/specify_cli/sync tests/sync` → all checks passed;
  `mypy src/specify_cli/sync` → success, 32 files; no new `# noqa`/`# type: ignore`; the
  `base: Path = get_runtime_root().base` narrowings are genuine typed-boundary coercions
  (mypy `follow_imports=skip` makes the symbol `Any`), with inline rationale — not suppressions.

Fix Issue 1, re-run the focused command, and this is an approve.
