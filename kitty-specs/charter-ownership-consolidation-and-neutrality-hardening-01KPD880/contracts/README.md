# Contracts — Charter Ownership Consolidation and Neutrality Hardening

This mission is an internal refactor with a small new lint module. It does **not** introduce new CLI commands or new public HTTP/RPC APIs. The "contracts" below describe the surfaces that this mission either preserves (must not break) or introduces (must be stable going forward).

Each contract is a testable specification of behavior, not a prose description.

---

## Index

| # | Contract | Kind | File |
|---|----------|------|------|
| C-1 | Charter public import surface — baseline preservation | Import API | [charter-public-import-surface.md](./charter-public-import-surface.md) |
| C-2 | Shim deprecation warning — emission contract | Runtime | [shim-deprecation-contract.md](./shim-deprecation-contract.md) |
| C-3 | Neutrality lint pytest — discovery & failure-output contract | Test harness | [neutrality-lint-contract.md](./neutrality-lint-contract.md) |
| C-4 | Banned-terms YAML — v1 schema | Config file | [banned-terms-schema.yaml](./banned-terms-schema.yaml) |
| C-5 | Language-scoped allowlist YAML — v1 schema | Config file | [language-scoped-allowlist-schema.yaml](./language-scoped-allowlist-schema.yaml) |
| C-6 | Charter ownership invariant — enforced at CI | Test harness | [charter-ownership-invariant-contract.md](./charter-ownership-invariant-contract.md) |

---

## How these map to spec requirements

| Contract | Covers |
|---|---|
| C-1 | FR-007 (CLI behavioral invariance via stable import API), NFR-005 (no startup regression) |
| C-2 | FR-005 (DeprecationWarning catchable), NFR-004 (standard warnings category) |
| C-3 | FR-010, FR-011 (regression test mechanics + error messages) |
| C-4 | FR-008, FR-014 (banned-term enforcement, single-file maintenance) |
| C-5 | FR-009, FR-013 (allowlist existence, Python guidance scope) |
| C-6 | FR-001, FR-002, SC-001 (canonical ownership invariant) |
