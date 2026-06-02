# Quickstart — Verifying the Close-Out

Per-FR verification recipes (run from repo root on `mission/org-doctrine-profile-integrity-activation-closure`).

| FR | Verify |
|----|--------|
| FR-001/002 (I-1) | New test in `tests/specify_cli/test_doctor_doctrine.py` driving an org `tactic_refs` profile → `healthy:false` + profile surfaced. RED on current code, GREEN after fix. `PWHEADLESS=1 pytest tests/specify_cli/test_doctor_doctrine.py -q` |
| FR-003 (I-9) | `diagnostics.py` docstring and `repository.py` inline-ref comment agree (inspection). |
| FR-004 (I-2) | `pytest tests/architectural/test_pytest_marker_convention.py -q` passes; `grep -c '^pytestmark'` = 1 for each of the 5 named files. |
| FR-005 (I-3) | `mypy --strict src/doctrine/drg/merge.py` → 0 errors. |
| FR-006/007 (I-4) | `pytest tests/architectural/test_runtime_charter_doctrine_boundary.py tests/architectural/test_ratchet_baselines.py -q` green; `_baselines.yaml` boundary baseline == 0; `grep -rn 'from doctrine' src/specify_cli/cli/commands/charter/{activate,list_cmd}.py` shows none (routed via `charter.*`). |
| FR-008 (I-5) | Cascade test asserts no "not yet implemented"/"deferred" string in `charter activate/deactivate --cascade` output. |
| FR-009 (I-6) | `pytest tests/architectural/test_no_dead_symbols.py -q` green; `events.py.__all__` no longer lists the two payloads; allowlist shrunk. |
| FR-010 (I-7) | `acceptance-matrix.json` has 0 `pending`/`null` for implemented FRs; `overall_verdict` set. |
| FR-011 (I-8) | `grep -i 'cascade\|kind_vocabulary\|specializes_from\|OperationalContext' CLAUDE.md` returns the new section. |
| FR-012/013 (I-10/11) | doctor render helpers relocated OR tracker filed; provenance typed OR tracker filed. |
| FR-014 (I-12) | Tracker issue exists for `ceremony` + `git_repo` marker pre-existing failures, referenced from `_baselines.yaml`/spec. |

## Whole-mission regression gate (NFR-001/002)
```
PWHEADLESS=1 pytest tests/charter/ tests/doctrine/ tests/specify_cli/cli/commands/charter/ tests/architectural/ -q
```
Must stay green (modulo the pre-existing-on-main failures tracked by FR-014); no new dead symbols, no allowlist growth.
