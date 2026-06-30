# Contracts: Safe Sync Daemon Orphan Cleanup

These are the normative interface contracts for the mission. They are CLI/process
contracts (not REST) — the product surface is the `spec-kitty auth doctor` command
and the loopback `/api/health` endpoint.

| Contract | File | Requirements |
|----------|------|--------------|
| Cleanup classification engine (pure) | [cleanup-classification.md](cleanup-classification.md) | FR-001, FR-002, FR-003, FR-008 |
| `auth doctor --json` / `--reset --json` output | [auth-doctor-json.md](auth-doctor-json.md) | FR-004, FR-005, FR-009 |
| `/api/health` payload (extended) | [health-payload.md](health-payload.md) | FR-001, FR-003 |

Behavioral contracts enforced by tests rather than schema:
- Startup auto-clean acts on `safe_auto` only (FR-006, FR-007).
- `--reset` guards `operator_required` behind `--force`/confirmation (D-02, FR-009).
- Self-retirement transitions (FR-010, FR-011) — see `../data-model.md`.
- Port-range and cross-family boundaries (NFR-001, NFR-002, NFR-003, C-002).
