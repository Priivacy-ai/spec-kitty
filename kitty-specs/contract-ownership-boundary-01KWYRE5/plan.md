# Implementation Plan: Contract-ownership boundary — MVP

**Branch**: `feat/contract-ownership-boundary` | **Mission**: `contract-ownership-boundary-01KWYRE5`
**Spec**: `kitty-specs/contract-ownership-boundary-01KWYRE5/spec.md` | **Design**: `kitty-specs/contract-ownership-boundary-01KWYRE5/design.md`

## Summary
Model shared contracts + their declared consumer set + retirement as one owned artifact — the conservative MVP. Generalize the proven shim-registry chain (schema→manifest→loader→doctor→scanner) into a Contract Registry; add the static-arm absence-sweep driver (advisory); adopt only the genuine retired-literal sweeps behind it (coverage proven first). No enforcement change, nothing force-folded.

## Technical Context
**Language/Version**: Python 3.11 (repo pinned)
**Primary Dependencies**: `ruamel.yaml`/`PyYAML` (manifest + schema); `src/specify_cli/compat/registry.py` (`ShimEntry`/`load_registry`/`validate_registry` — the generalization template); `tests/architectural/_ratchet_keys.py::composite_key` (content-anchoring, promoted to a shared lib); `src/specify_cli/compat/doctor.py` + `cli/commands/doctor.py` (the `doctor <sub>` pattern); `test_no_dead_symbols`'s import resolver (consumer-set discovery); `pytest` (`architectural` marker)
**Storage**: N/A — declarative YAML manifest `docs/contracts/contract-registry.yaml` + schema `…-schema.yaml`; no DB
**Testing**: unit tests for the loader/validator (well-formed vs malformed vs `file:line`-anchored → reject); the static-sweep driver with a mandatory anti-vacuity negative control; parity tests for each adopted literal sweep (driver catches exactly what the old sweep caught) BEFORE removal
**Target Platform**: local + CI (arch pole; `docs/contracts/` docs-scoped like `shim-registry.yaml`)
**Project Type**: single project — a governance/architecture boundary (registry + validator + one sweep driver + adoption)
**Performance Goals**: N/A — validation + a content-anchored static sweep
**Constraints**: **no `file:line` anchoring** (DIR-041 — the validator rejects it, NFR-003); the absence sweep is **advisory** in v1 (NFR-002); no coverage regression — parity proven before any removal (NFR-001); consumer sets **discovered-then-frozen**, never hand-typed blind (C-003); generalize the shim chain, don't reinvent (C-001); `ruff`+`mypy --strict` clean; no suppression
**Scale/Scope**: new `docs/contracts/` manifest+schema + `src/specify_cli/contracts/registry.py` + `spec-kitty doctor contracts` + a promoted anchoring lib + `tests/architectural/test_retired_contracts_absent.py` + adoption of `test_no_legacy_terminology.py` (+ the path-literal grep half)

## Charter Check
Canonical-source discipline (generalize the shim chain), DIR-041 one-source-of-truth (the mission's raison d'être), advisory-first / delete-the-assertion-not-the-test, no ratchet/suppression — charter-aligned.

## Implementation Concerns

### IC-01 — The Contract Registry model (FR-001..004) — WP1 (MVP, standalone)
- **Schema** `docs/contracts/contract-registry-schema.yaml` + **manifest** `docs/contracts/contract-registry.yaml` (docs-scoped sibling to `shim-registry.yaml`). Record: `id`, `kind`∈`{fallback_name, retired_literal}`, content-anchored `anchor` (dotted symbol OR fixed literal — never `file:line`), `status`, `owner`, `replaced_by`, `retirement`, `consumers`{`scan_roots`, `exemptions`, `test_shards`?, `call_sites`?}, `verification`{`enforcement: advisory`}.
- **Loader/validator** `src/specify_cli/contracts/registry.py` (`ContractRecord`, `load_registry`, `validate_registry`) — generalized from `compat/registry.py`; the validator **rejects** any positional `file:line` field (NFR-003).
- **`spec-kitty doctor contracts`** — enforcing well-formedness (schema, resolvable anchors, no `file:line`). Structural validation is the only enforcing gate in v1.
- **Promote** `_ratchet_keys.py::composite_key` to a shared lib the loader + driver depend on (no behavior change to existing callers).
- **Seed one record** (FR-004): a `retired_literal` from `test_no_legacy_terminology.py` **with its discovered-then-frozen consumer set** (scan_roots + exemptions), proving the model end-to-end.

### IC-02 — Static-arm absence-sweep driver (FR-005) — WP2 (advisory)
- `tests/architectural/test_retired_contracts_absent.py`: content-anchored sweep over `status=retired` records, using `composite_key`/literal anchoring across `scan_roots` minus `exemptions`. **Mandatory anti-vacuity negative control**: a planted reappearance of a retired anchor MUST be flagged (else the sweep is vacuously green). **Advisory/report-only** — never blocks.

### IC-03 — Model + parity-prove the literal sweeps, WITHOUT retiring the enforcing gates (FR-006) — WP3 (additive)
- Model the literal-sweep subset (`test_no_legacy_terminology.py` + the CLI-tree literal-grep half of `test_no_legacy_path_literals.py`) as `retired_literal` records with declared consumers + exemptions.
- **Prove parity**: the advisory driver flags exactly what `test_no_legacy_terminology.py` (`pytest.fail`, merge-blocking) + the path-literal grep (`assert`, blocking) flag — **but leave those enforcing gates in place** (removing them behind an advisory driver silently downgrades a blocking gate → report-only; NFR-004). The delete-the-assertion retirement awaits the enforcing-driver follow-up.
- **Carve out (do NOT fold)**: the `path_literals` behavioral nudge tests, `status_emit_callers`, `agent_profiles_path`.

## Project Structure (files touched)
```
docs/contracts/contract-registry-schema.yaml    # IC-01 NEW schema
docs/contracts/contract-registry.yaml           # IC-01 NEW manifest (seeded with 1 record)
src/specify_cli/contracts/registry.py           # IC-01 NEW loader/validator
src/specify_cli/contracts/__init__.py           # IC-01 NEW
src/specify_cli/cli/commands/doctor.py          # IC-01 add `doctor contracts` subcommand
tests/architectural/test_retired_contracts_absent.py     # IC-02 NEW sweep driver + anti-vacuity control
tests/architectural/test_no_legacy_terminology.py        # IC-03 parity-prove only — KEEP the enforcing gate in place (no retire in v1)
tests/audit/test_no_legacy_path_literals.py              # IC-03 parity-prove the literal-grep half; keep all its assertions
```

## Key Decisions
- **Generalize, don't reinvent** (C-001): new sibling registry under `docs/contracts/`, reusing the shim schema/loader shape; fold shim-registry in a later follow-up.
- **Advisory + anti-vacuity** (NFR-002): the sweep reports only; a planted-reappearance control proves it isn't vacuously green.
- **Discovered-then-frozen consumers** (C-003): seed from the import/call graph, freeze + review — never hand-type blind.
- **Carve-outs** (post-spec fold): only the literal sweeps fold; behavioral/AST/directory checks stay put or defer to the signature-kind follow-up.
