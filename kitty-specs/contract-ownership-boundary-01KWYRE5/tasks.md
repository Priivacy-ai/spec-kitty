# Tasks: Contract-ownership boundary — MVP

**Mission**: `contract-ownership-boundary-01KWYRE5` | **Branch**: `feat/contract-ownership-boundary`

3 WPs. WP01 (model) is a standalone MVP; WP02 (driver) depends on WP01; WP03 (parity-prove) depends on both. **Additive** — nothing is retired.

## Subtask Index
| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Schema + manifest + typed loader (generalize `compat/registry.py`) | WP01 | |
| T002 | `doctor contracts` validator (rejects `file:line`) + promote `_ratchet_keys` | WP01 | |
| T003 | Seed the `retired_literal` records (terminology + path-literal) with discovered-then-frozen consumer sets | WP01 | |
| T004 | Static-arm absence-sweep driver (advisory) + anti-vacuity negative control | WP02 | |
| T005 | Parity-prove the literal sweeps vs the driver — KEEP the enforcing gates | WP03 | |

## WP01 — Contract Registry model (FR-001..004) — P1 (MVP, standalone)
Goal: the owned artifact + validator + one seeded contract. Advisory; nothing enforced-new, nothing deleted.
- [x] T001 `docs/contracts/contract-registry-schema.yaml` + `contract-registry.yaml`; `src/specify_cli/contracts/registry.py` (`ContractRecord`, `load_registry`, `validate_registry`) generalized from `compat/registry.py` (WP01)
- [x] T002 `spec-kitty doctor contracts` (enforcing well-formedness: schema, resolvable anchors, **rejects `file:line`** — NFR-003); promote `_ratchet_keys.py::composite_key` to a shared lib (no behavior change to existing callers) (WP01)
- [x] T003 Seed the `retired_literal` records for BOTH adopted sweeps (terminology terms + the CLI-tree path-literal), each with its **discovered-then-frozen** consumer set — WP01 solely owns the manifest; WP03's parity needs both (WP01)
**Independent test**: `doctor contracts` validates the seeded record; a malformed one AND a `file:line`-anchored one fail (red-first).

## WP02 — Static-arm absence-sweep driver (FR-005) — P1 (advisory) — depends on WP01
Goal: the content-anchored sweep over `status=retired` records, report-only, with an anti-vacuity guarantee.
- [x] T004 `tests/architectural/test_retired_contracts_absent.py`: sweep `status=retired` records via `composite_key`/literal anchoring over `scan_roots` minus `exemptions`; **advisory/report-only** (never blocks); **mandatory anti-vacuity negative control** — a planted reappearance of a retired anchor MUST be flagged (WP02)
**Independent test**: the planted reappearance is flagged; a clean tree reports clean; the sweep never fails CI.

## WP03 — Parity-prove the literal sweeps, WITHOUT retiring the enforcing gates (FR-006, NFR-004) — P1 — depends on WP01+WP02
Goal: demonstrate the driver subsumes the literal sweeps' detection — but leave the merge-blocking gates in place (no enforcement downgrade).
- [ ] T005 Model the literal-sweep subset (`test_no_legacy_terminology.py` + the CLI-tree literal-grep half of `test_no_legacy_path_literals.py`) as `retired_literal` records; a parity test shows the advisory driver flags exactly what those (still-in-place, merge-BLOCKING) gates flag. **Do NOT remove/neuter the enforcing assertions** (NFR-004 — retiring behind an advisory driver downgrades enforcement). Carve out the behavioral/AST/directory checks entirely. (WP03)
**Independent test**: parity holds; `test_no_legacy_terminology.py` (`pytest.fail`) + the path-literal assert still BLOCK; carved-out checks unchanged.

**MVP**: WP01. **Dependencies**: WP02 → WP01; WP03 → WP01, WP02.
