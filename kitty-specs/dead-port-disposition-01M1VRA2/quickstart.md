# Quickstart: Dead-Port Disposition

## Verify the defect exists (before implementing)

```bash
# Both greps should hit today; the mission removes both.
grep -n "flush(ctx.sync_emitter)\|sync_emitter=ctx.sync_emitter" src/runtime/next/runtime_bridge.py
# Two classes, one name:
grep -rn "^class RuntimeEventEmitter" src/runtime/next/
```

## Implement in dependency order

1. **Seam (Concern A)** — edit `src/runtime/next/_internal_runtime/events.py`: add `NullEmitter.for_mission`, `NullEmitter.seed_from_snapshot`, `runtime_emitter_for_mission`, `register_runtime_emitter_factory`, `reset_runtime_emitter_factory`; extend `__all__`; mirror in `_internal_runtime/emitter.py`.
2. **Red-first tests (Concern D)** — create `tests/runtime/test_bridge_decision_log_flush.py`; run it and confirm tests F1 and F2 are **red**:
   ```bash
   .venv/bin/pytest tests/runtime/test_bridge_decision_log_flush.py -q -p no:cacheprovider
   ```
3. **Flush fixes (Concern C)** — `runtime_bridge.py:2187` and `:1976` → `ctx.emitter_for_engine`; add `DecisionGitLog.seed_from_snapshot`. Re-run step 2: all green.
4. **Bridge rewiring + delete (Concern B)** — swap the import at `runtime_bridge.py:195`; replace `RuntimeEventEmitter.for_feature(` at `:1552` and `:2739` with `runtime_emitter_for_mission(`; fix `runtime_bridge_engine.py:80`; `git rm src/runtime/next/event_emitter.py`; update `tests/specify_cli/events/test_decision_log_coord.py:17`.
5. **Rewrites + guard (Concern E)** — patch the factory name at the 14 sites listed in `plan.md`; add factory/registry tests to `tests/next/test_internal_runtime_coverage.py`; add `tests/architectural/test_runtime_emitter_seam.py`.
6. **Docs + CHANGELOG (Concern F)** — docstring, two conformance comments, one `### Fixed` line.

## Verify

```bash
make test-fast
.venv/bin/pytest tests/runtime/ tests/next/ tests/specify_cli/next/ tests/specify_cli/events/ -q -p no:cacheprovider
.venv/bin/pytest tests/status/test_producer_conformance.py tests/contract/test_identity_contract_matrix.py -q -p no:cacheprovider
.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_runtime_emitter_seam.py -q -p no:cacheprovider
.venv/bin/ruff check . && .venv/bin/mypy src/runtime/next/_internal_runtime/events.py src/specify_cli/events/decision_log.py
```

Expected after completion: both greps in "Verify the defect" return nothing; exactly one `class RuntimeEventEmitter`; all suites green; ruff and mypy clean.

## Record in the PR

Commands and passed/failed counts for every line above; the added-lines terminology grep (`feature` identifiers: 0); retired-surface scan: 0 hits.
