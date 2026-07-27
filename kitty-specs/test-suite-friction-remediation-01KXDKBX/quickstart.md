# Quickstart — running the affected guards

All commands from the mission clone root (`spec-kitty-gate-doctrine`), using the clone's venv (`uv run` or `.venv/bin/…`) so imports resolve to *this* checkout, not the primary.

## Per-concern guard runs

```bash
# IC-01/02/03 — dead-code gate (dynamic-access awareness + deshim safety net)
.venv/bin/python -m pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py -q

# IC-04 — positional-anchor ban (seed-tuple hole) + the non-fakeable grep
.venv/bin/python -m pytest tests/architectural/test_ratchet_positional_anchor_ban.py -q
git grep -nE '\.py", *[0-9]{3}\)' tests/architectural/ ; echo "expect: no matches"

# IC-05 — lane enum content assertion
.venv/bin/python -m pytest tests/status/test_models.py -q

# IC-06 — emit/wiring observable contracts
.venv/bin/python -m pytest tests/status/test_agent_status_emit_aggregate_wiring.py -q

# IC-07 — mission factory parity
.venv/bin/python -m pytest tests/_factories -q   # (after the factory + parity test land)

# IC-10 — shard-registry completeness (must NOT raise bare KeyError)
.venv/bin/python -m pytest tests/architectural/test_arch_shard_marker_completeness.py -q

# IC-11 — quality-gate.needs containment guard
.venv/bin/python -m pytest tests/architectural/test_workflow_coherence.py -q   # + the new sibling guard
```

## Full suite (parallel + serial daemon pass)

```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_orphan_sweep.py -n0 -q   # real-port/daemon serial
```

## Lint / type / terminology gates (pre-push)

```bash
.venv/bin/ruff check .
.venv/bin/mypy   # zero issues on the diff
.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q   # CI-only gate; run locally when touching prose/doctrine
```

## UI-e2e (IC-12 context)

```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/ui/ -q   # dashboard e2e; see docs/development/ui-e2e.md
```

## Ordering reminder (NFR-001)
IC-01 (#2559) MUST be merged before IC-02 (#2561) / IC-03 (#2293). In `lanes` topology this is a lane dependency, not a suggestion.
