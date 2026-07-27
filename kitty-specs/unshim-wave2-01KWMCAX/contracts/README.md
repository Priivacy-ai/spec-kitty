# Contracts — unshim-wave2-01KWMCAX

Declared **N/A by design** in [plan.md](../plan.md) (Project Structure): this mission has no
data entities or API surfaces. Recorded here so downstream gates don't read absence as omission.

The mission's executable contracts live as tests and ledgers instead:

| Contract | Executable surface |
|---|---|
| Registry stays drained (FR-003/FR-004) | `tests/architectural/test_shim_registry_schema.py` absence pins (flip-verified) |
| No unregistered shims reappear | `tests/architectural/test_unregistered_shim_scanner.py` |
| Every patch-string re-point intercepts (FR-002) | `occurrence_map.yaml` interception-proof ledger (197 rows, 100% populated) |
| mission_runtime outbound boundary (FR-009) | `tests/architectural/test_layer_rules.py::TestMissionRuntimeBoundary` incl. committed negative test |
| Legacy charter paths stay gone (FR-006) | `tests/architectural/test_charter_runtime_canonical_paths.py::test_legacy_charter_paths_are_gone` |
| No-import invariant (NFR-002) | pinned grep in `acceptance-matrix.json` NI-001 |
