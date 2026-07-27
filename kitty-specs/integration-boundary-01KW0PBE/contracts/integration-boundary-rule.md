# Contract: Integration/Core Boundary Rule

**Contract ID**: integration-boundary-rule
**Version**: 1.0.0
**Mission**: `integration-boundary-01KW0PBE`
**Status**: Active

---

## One-Directional Rule

```
CORE must NOT import INTEGRATION.
INTEGRATION may import CORE facades.
```

### CORE set (src/specify_cli/)
- `core/`
- `status/`
- `readiness/`
- `invocation/`

### INTEGRATION set (src/specify_cli/)
- `orchestrator_api/`
- `sync/`
- `tracker/`
- `saas/`
- `saas_client/`

---

## Enforcement

`tests/architectural/test_integration_boundary.py` enforces this contract on
every CI run. The test:
1. Uses stdlib `ast.walk` to scan ALL import forms (module-level,
   `if TYPE_CHECKING:` blocks, lazy function-body imports).
2. Scans every `.py` file in all four CORE-set directories recursively.
3. Fails with a message identifying: the violating source file, the offending
   import path, and the corrective action (NFR-002: ≥ 3 diagnostic fields).
4. Carries `pytest.mark.architectural`.
5. Includes a path-existence sanity check for every CORE-set directory so that
   a directory rename causes a loud failure rather than a vacuous pass (C-008).
6. Includes a sanity sub-test that proves the allowlist cannot be bypassed silently.

---

## Allowlist

Controlled exceptions. Each entry must include source module, imported module,
and written rationale. Changes require editing `test_integration_boundary.py`
directly.

| Source | Imported | Rationale | Planned resolution |
|--------|----------|-----------|-------------------|
| `readiness/coordinator.py` | `specify_cli.saas.rollout` | `is_saas_sync_enabled` is a shared-config v1 pure feature-flag read; relocation to a core/kernel config module is planned. Exempted until relocation lands. | Follow-up mission (no issue number yet) |

---

## Corrective Action for Violations

When the test fails:
1. Do NOT add an allowlist entry unless the crossing is a deliberate, time-bounded
   exception with a written follow-up plan.
2. Route the dependency through the adapter/observer registry instead:
   - Core → Sync/Tracker/SaaS fan-out: register an observer with
     `status/adapters.py` or `core/adapters.py`; call the fire function.
   - Invocation → Sync: register via `invocation/adapters.py`.
3. If physical extraction is the right long-term fix, file a follow-up mission
   targeting `src/orchestrator/` per ADR
   `architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md`.

---

## Out-of-Scope (Deferred)

- Bidirectional enforcement (INTEGRATION importing CORE) — C-003.
- `coordination/`, `lanes/`, `runtime/` — C-004.
- Physical extraction to `src/orchestrator/` — C-001, ADR 2026-05-11-1.
