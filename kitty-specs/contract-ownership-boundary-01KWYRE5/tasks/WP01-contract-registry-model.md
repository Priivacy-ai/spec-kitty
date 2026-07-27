---
work_package_id: WP01
title: Contract Registry model + doctor validator + seeded records
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/contract-ownership-boundary
merge_target_branch: feat/contract-ownership-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/contract-ownership-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/contract-ownership-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: "reviewer-renata"
shell_pid: "3888123"
history:
- Created for mission contract-ownership-boundary-01KWYRE5
agent_profile: python-pedro
authoritative_surface: src/specify_cli/contracts/
create_intent:
- docs/contracts/contract-registry-schema.yaml
- docs/contracts/contract-registry.yaml
- src/specify_cli/contracts/__init__.py
- src/specify_cli/contracts/registry.py
- tests/specify_cli/contracts/test_registry.py
execution_mode: code_change
owned_files:
- docs/contracts/contract-registry-schema.yaml
- docs/contracts/contract-registry.yaml
- src/specify_cli/contracts/__init__.py
- src/specify_cli/contracts/registry.py
- src/specify_cli/cli/commands/doctor.py
- tests/architectural/_ratchet_keys.py
- tests/specify_cli/contracts/test_registry.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Model shared contracts + their declared consumer set + retirement as one owned artifact (#2441) — generalizing the proven shim-registry chain. **FR-001..004, NFR-003.** Additive — nothing enforced-new beyond structural validation, nothing deleted.

## Context (grounded — the near-precedent to generalize)
Shim chain: schema `kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml`; manifest `docs/migrations/shim-registry.yaml`; loader `src/specify_cli/compat/registry.py` (`ShimEntry`/`load_registry`/`validate_registry`); `spec-kitty doctor shim-registry` (`compat/doctor.py`, CLI `cli/commands/doctor.py`). Content-anchoring primitive: `tests/architectural/_ratchet_keys.py::composite_key`. See `kitty-specs/contract-ownership-boundary-01KWYRE5/design.md`.

## Guidance
**T001 — schema + manifest + loader (FR-001)**
- `docs/contracts/contract-registry-schema.yaml` + `docs/contracts/contract-registry.yaml` (docs-scoped sibling to `shim-registry.yaml`). Record fields: `id`, `kind`∈`{fallback_name, retired_literal}`, content-anchored `anchor` (`symbol:` dotted OR `literal:` fixed string — **never `file:line`**), `status`∈`{active, deprecated, retired}`, `owner`, `replaced_by`, `retirement`, `consumers`{`scan_roots`, `exemptions`, `test_shards?`, `call_sites?`}, `verification`{`enforcement: advisory`}.
- `src/specify_cli/contracts/registry.py` (`ContractRecord`, `load_registry`, `validate_registry`) — generalized from `compat/registry.py` (`ShimEntry` becomes the `kind=fallback_name` projection).
**T002 — `doctor contracts` + promote anchoring (FR-002, NFR-003)**
- `spec-kitty doctor contracts` (add to `cli/commands/doctor.py`, mirror `doctor shim-registry`) — **enforcing** well-formedness: schema-valid, anchors resolve, and it **rejects any positional `file:line` field** (NFR-003). Structural validation is the ONLY enforcing gate.
- Promote `composite_key` into a shared lib the loader can import (src can't import from `tests/`): create `src/specify_cli/contracts/anchoring.py` (or similar) holding it, and re-point `tests/architectural/_ratchet_keys.py` to re-export from there — **no behavior change** to existing `_ratchet_keys` callers (they keep importing `composite_key` from the same name).
**T003 — seed records (FR-003, FR-004)**
- Seed the manifest with the `retired_literal` records for `test_no_legacy_terminology.py` (the canonical terms) + the CLI-tree literal-grep half of `test_no_legacy_path_literals.py`, each with a **discovered-then-frozen** consumer set (scan_roots + exemptions mirroring the old tests' scope). `status: retired`, `enforcement: advisory`. (These feed WP02's driver + WP03's parity.)

## Definition of Done
- `doctor contracts` validates the seeded records; a malformed record AND a `file:line`-anchored record fail (red-first tests in `tests/specify_cli/contracts/test_registry.py`).
- `_ratchet_keys` callers unaffected (run `tests/architectural/` spot-check).
- `ruff`+`mypy --strict` clean; no suppression; no `file:line` anchoring anywhere.

## Reviewer guidance
Confirm the schema rejects `file:line`, the loader genuinely generalizes `compat/registry.py` (not a fork), the consumer sets are discovered (not hand-typed blind), and `_ratchet_keys` re-point is behavior-preserving.

## Activity Log

- 2026-07-07T18:44:06Z – python-pedro – shell_pid=3802124 – Assigned agent via action command
- 2026-07-07T18:45:09Z – python-pedro – shell_pid=3805261 – Assigned agent via action command
- 2026-07-07T19:19:18Z – python-pedro – shell_pid=3805261 – Scope note: two edits outside enumerated owned_files, both justified — (1) src/specify_cli/contracts/anchoring.py is within authoritative_surface src/specify_cli/contracts/ and is the FR-003 anchoring promotion the WP explicitly mandates; (2) tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py is a mechanical golden-snapshot update tracking the FR-002-mandated 'doctor contracts' subcommand (16->17). No behavior change to unrelated code.
- 2026-07-07T19:20:01Z – python-pedro – shell_pid=3805261 – Contract Registry model + doctor contracts validator + both seeded retired_literal records. ruff+mypy --strict clean; validator red-first proven (file:line rejection fails-closed); _ratchet_keys promotion behavior-preserving (ratchet+write_side+importer gates green); dead-module/symbol + terminology + path-literal gates green; doctor golden updated to 17. Lane commit f2c2c9267.
- 2026-07-07T19:21:26Z – reviewer-renata – shell_pid=3888123 – Started review via action command
- 2026-07-07T19:31:15Z – user – shell_pid=3888123 – Review passed: file:line rejection proven load-bearing by mutation; generalization 1:1; anchoring behavior-preserving (27 ratchet green); both records discovered-then-frozen
