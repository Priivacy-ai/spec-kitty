# Contract: Contract-ownership boundary (MVP)

The observable contracts this mission upholds (verified by the tests + reviews cited in `acceptance-matrix.json`).

## C1 — A shared contract is a modeled, owned artifact (#2441, FR-001..004)
- A **Contract Record** lives in `docs/contracts/contract-registry.yaml` (schema `…-schema.yaml`): `id`, `kind∈{fallback_name,retired_literal}`, a **content-anchored** `anchor` (`symbol:` OR `literals:` — never `file:line`), `status`, `owner`, `replaced_by`, `retirement`, and the missing piece — a **declared consumer set** (`scan_roots`/`exemptions`/`test_shards`/`call_sites`), `verification{enforcement: advisory}`.
- **Invariant (NFR-003, DIR-041)**: the loader/validator (`src/specify_cli/contracts/registry.py`, `spec-kitty doctor contracts`) **rejects any `file:line` anchor** — both a positional field and a fragment-join reconstruction. The registry must not become the rot it replaces. Generalizes the proven shim-registry chain (not a fork).

## C2 — Retirement is verified against the declared consumers, advisory-first (FR-005)
- `tests/architectural/test_retired_contracts_absent.py` sweeps each `status=retired` record's anchor across `scan_roots` minus `exemptions`. **Advisory/report-only** — never blocks CI on a live find (proven structural under `-W error`); a mandatory anti-vacuity control proves it bites.

## C3 — Adoption proves the driver SUBSUMES the gates WITHOUT downgrading enforcement (#2441, FR-006, NFR-004)
- The literal sweeps (`test_no_legacy_terminology.py` + the CLI-tree path-literal) are modeled as records + a **superset parity proof** (`test_contract_registry_parity.py`): the advisory driver's detection is a **superset** of what the (still merge-**BLOCKING**) gates detect — it preserves all the gate's coverage (NFR-001) AND additionally over-flags comment-line / non-`.py` mentions the CLI-path gate carves out (an advisory-safe over-flag; `driver ⊋ gate`, pinned by a comment-line control). Set-equality holds **only over the curated divergence-free envelope** (non-comment lines in in-scope `.py` files), not globally — proven via the gates' own logic against a fabricated repo.
- **Invariant (NFR-004)**: the enforcing gates are **byte-for-byte unchanged** and still block; nothing is retired (the actual delete-the-assertion + enforcing-driver mode are deferred #2441 follow-ups). No enforcing→advisory downgrade. The gate's comment-skip + `.py`-scoping must be modeled in the driver **before** any enforcing flip, to avoid false friction.
