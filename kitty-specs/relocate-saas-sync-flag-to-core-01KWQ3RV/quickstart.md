# Quickstart / Verification: Relocate SaaS-Sync Flag to Core

## 1. Boundary enforced at zero exemptions (SC-1)
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_integration_boundary.py -p no:cacheprovider -q
# expect green; ALLOWLIST is empty; test_allowlist_count_ratchet asserts == 0
grep -n "ALLOWLIST" tests/architectural/test_integration_boundary.py   # frozenset() ; ratchet == 0
grep -rn "specify_cli.saas.rollout" src/specify_cli/{core,status,readiness,invocation}/  # → nothing
```

## 2. Single canonical definition (SC-3 / NFR-002)
```bash
grep -rn "^def is_saas_sync_enabled\|^def saas_sync_disabled_message" src/  # exactly one each, in core/saas_sync_config.py
```

## 3. Behavior identical + shims preserved (SC-2 / NFR-001)
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/saas/ -p no:cacheprovider -q          # incl. test_rollout.py identity tests, UNCHANGED
python -c "from specify_cli.saas.rollout import is_saas_sync_enabled as a; from specify_cli.sync.feature_flags import is_saas_sync_enabled as b; assert a is b, 'identity preserved'"
```

## 4. Docs recorded (SC-4)
```bash
grep -n "2252\|resolved\|saas_sync_config" docs/adr/3.x/2026-06-26-1-core-integration-boundary.md
PWHEADLESS=1 .venv/bin/python -m pytest tests/contract/test_example_round_trip.py -p no:cacheprovider -q   # contract still parses
```

## 5. Quality gates
```bash
.venv/bin/python -m ruff check src/specify_cli/core/saas_sync_config.py src/specify_cli/saas/rollout.py src/specify_cli/readiness/coordinator.py
.venv/bin/python -m mypy --strict src/specify_cli/core/saas_sync_config.py
```
