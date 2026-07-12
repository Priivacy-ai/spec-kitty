# Contracts — Dev-Assist Retirement + Path-Validation Hardening

This is a **test-suite hygiene + security-hardening** mission; it ships no new API/wire contracts.

The mission's "contracts" are the standing test guards it consolidates and the validator it hardens:
- `src/specify_cli/mission.py::validate_deliverables_path` — hardened to reject every malicious-path class (FR-001). Function-only; runtime wiring deferred to #2539/#2536.
- `tests/runtime/test_bridge_compat_surface.py` — the runtime-bridge family compat-surface guard (coverage authority for WP02's retirements).
- `tests/merge/test_merge_compat_surface.py` (new, WP04) — merge-family `{symbol→residual}` compat guard (54 symbols).
- `tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py` (new, WP05) — tasks-family compat guard (129 symbols, all 6 seams).

No `contracts/*.md` API specs apply.
