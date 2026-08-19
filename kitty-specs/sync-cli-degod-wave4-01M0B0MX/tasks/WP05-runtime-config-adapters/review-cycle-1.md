---
affected_files: []
cycle_number: 1
mission_slug: sync-cli-degod-wave4-01M0B0MX
reproduction_command:
reviewed_at: '2026-08-18T21:51:35Z'
reviewer_agent: user
wp_id: WP05
---

# WP05 Review — REJECT (one blocking issue)

Reviewer: reviewer-renata. Mission: sync-cli-degod-wave4-01M0B0MX. Commit reviewed: `1d43d83f86`.

## Verdict summary
The pure-move fidelity is excellent — but the deliverable fails its own explicit
acceptance gate (`mypy --strict` clean on the changed files). One blocking issue,
trivial to fix, no suppression needed.

## What PASSED (verified, keep as-is)
- **Diff scope**: touches ONLY `cli/commands/sync.py` (-294) and NEW
  `sync/sync_runtime.py` (+353). No tests, no `_baselines.yaml`, no census baseline,
  golden test file byte-unchanged. Confirmed via `git show --name-status`.
- **Byte-identity of all 14 moved symbols**: AST/text-compared old (removed) bodies
  vs new module with the `sync_module.` prefix normalized out. 10 symbols
  byte-IDENTICAL; the 4 openers differ ONLY by the added function-local
  `import specify_cli.cli.commands.sync as sync_module` line. No logic reorder,
  no merged branch, no changed argument.
- **Authority split (THE load-bearing check)**: `_open_event_sync_runtime` (READ)
  and `_open_project_dispatch_runtime` (DISPATCH) relocated as TWO DISTINCT
  functions — not merged/de-duplicated. Dispatch opener's authority-call sequence
  is byte-identical: `sync_module._assert_event_sync_runtime_authority(...)` then
  `sync_module._assert_delivery_target_matches_context(...)`, same order, same args.
  Frozen-verbatim (C-007) held.
- **Late-bind (INV-4)**: every cross-module seam call
  (`_current_event_sync_scope`, `_assert_*`, and the wrapped `_open_event_sync_runtime`)
  uses `sync_module.<name>` attribute access. Zero
  `from ...cli.commands.sync import ...` early-bind. AST guard
  `test_sync_no_early_bind.py` walks the whole `src` tree (covers `sync_runtime.py`)
  and is GREEN.
- **TYPE_CHECKING trim** (`from ...delivery.config import EventSyncConfig, Mode`
  → drop `Mode`) is a correct consequence of the move: no remaining top-level type
  annotation in `sync.py` references `Mode`; `EventSyncConfig` is still used
  (lines 451/477) so it stays. Not a behavior change.
- **Secret discipline (DIR-008)**: `_event_sync_access_token` + `_write_event_sync_config`
  + `_load_event_sync_config` are byte-IDENTICAL. No token/secret newly logged or exposed.
- **Writer-census 1:1**: `test_sync_writer_census.py` GREEN, no net key change (N/A claim holds).
- **Tests**: 303 passed (golden + patch-tests + AST early-bind guard + writer-census).
- **INV-3/INV-5**: under `specify_cli.sync.*`; ZERO `runtime`-package import; LOC 353 (≤800).
- **ruff**: clean (exit 0) on both changed files — complexity within the 15 ceiling.

## BLOCKING ISSUE — mypy --strict is NOT clean (exit 1)

WP05 task file line 190 requires: "`ruff` and `mypy --strict` clean on both changed
files; ... no new `# noqa`/`# type: ignore`." The review bar restates it. It fails:

```
$ mypy src/specify_cli/sync/sync_runtime.py
src/specify_cli/sync/sync_runtime.py:181: error: Returning Any from function declared to return "_EventSyncRuntime"  [no-any-return]
src/specify_cli/sync/sync_runtime.py:189: error: Returning Any from function declared to return "_EventSyncRuntime"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)   # exit 1
```

**Root cause (a real move-induced regression, not a pre-existing red):**
The old host `specify_cli.cli.commands.sync` is in the transitional strict-quarantine
override list in `pyproject.toml` (`follow_imports = "skip"`), so it never faced these
errors. The NEW module `specify_cli.sync.sync_runtime` is NOT in that list — it faces
full `strict = true`. Two thin wrappers now `return` the result of a late-bound call
on the (Any-typed, quarantined) host module:

- L181 `_open_event_sync_runtime_readonly`: `return sync_module._open_event_sync_runtime()`
- L189 `_open_retention_runtime_or_exit`: `return sync_module._open_event_sync_runtime(include_target=False)`

In the OLD code these were direct local calls (`return _open_event_sync_runtime()`),
correctly typed. The mandated INV-4 late-bind through the quarantined host makes the
return `Any`. The merged sibling `sync_render.py` is mypy-clean, confirming this is
unique new debt, not an inherited baseline.

**Required fix (preserves the INV-4 late-bind, no suppression):** absorb the `Any`
into a typed local before returning — assigning `Any` to an annotated name is allowed
under strict and returning the typed name satisfies `no-any-return`:

```python
def _open_event_sync_runtime_readonly() -> _EventSyncRuntime:
    import specify_cli.cli.commands.sync as sync_module
    runtime: _EventSyncRuntime = sync_module._open_event_sync_runtime()
    return runtime
```
and analogously for `_open_retention_runtime_or_exit` (keep the `try/except` shape;
annotate the returned local inside the `try`). Do NOT add `# type: ignore` and do NOT
early-bind the call (that would break the monkeypatch seam / AST guard). Re-run
`mypy src/specify_cli/sync/sync_runtime.py` to confirm exit 0, then re-request review.

## Note for re-review
This is the ONLY blocker. Everything else (byte-identity, authority split, late-bind,
census, 303 green) is verified correct — the fix above is the sole delta needed.
