# Quickstart: Verify the Integration/Core Boundary

**Mission**: `integration-boundary-01KW0PBE`
**Branch**: `feat/integration-boundary`

---

## 1. Run the enforcement test

```bash
pytest tests/architectural/test_integration_boundary.py -v
```

Expected output: all tests pass green. If any CORE-set module still carries a
non-exempted INTEGRATION import, the test fails with a message naming the
violating file, the offending import path, and the corrective action.

---

## 2. Verify zero CORE-to-INTEGRATION edges by grep

```bash
# Must return only the allowlisted line (readiness/coordinator.py → saas.rollout)
grep -rn \
  "specify_cli\.sync\|specify_cli\.tracker\|specify_cli\.saas\|specify_cli\.orchestrator_api\|specify_cli\.saas_client" \
  src/specify_cli/core/ \
  src/specify_cli/status/ \
  src/specify_cli/readiness/ \
  src/specify_cli/invocation/
```

Expected: exactly one match —
`src/specify_cli/readiness/coordinator.py:237: from specify_cli.saas.rollout import is_saas_sync_enabled`

Any other match is a regression.

---

## 3. Run the full architectural suite

```bash
pytest tests/architectural/ -v --timeout=30
```

Expected: all tests pass. The enforcement test must complete well within 30 s.

---

## 4. Verify no regressions in the full suite

```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
```

Expected: zero newly failing tests (NFR-003).

---

## 5. Verify invocation/adapters.py safe-degradation

```bash
# Unit test for the invocation adapter's no-registration fallback
pytest tests/invocation/test_adapters.py -v
```

Expected: the test that calls `resolve_sync_routing` and `get_saas_client` with
no registered implementations returns None without raising.

---

## 6. Verify mission creation still works end-to-end

```bash
# Functional smoke test: create a mission and confirm the lifecycle log is written
pytest tests/core/ -k "mission_creat" -v
```

Expected: `status.events.jsonl` contains exactly one `MissionCreated` event after
a mission creation call. No `OriginBinding` or `DossierSync` import errors.
