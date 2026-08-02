# Contract: Charter Read/Path Authority

**Owning FRs:** FR-001, FR-002, FR-003, FR-004, FR-006, FR-016
**Landed by:** WP01, WP02, WP03, WP04, WP11

## The contract

There is exactly **one** door for a "does a charter exist / where is it" decision:
`charter/bundle.py`'s `CHARTER_YAML` / `CHARTER_MD` constants, read through
`charter/charter_yaml_io.load_charter_yaml`.

- **`charter.yaml`** (`.kittify/charter/charter.yaml`) is the deterministic,
  schema-guarded resolution **authority**. Every *authority-presence* surface —
  dashboard (`resolve_project_charter_presence`), analysis-report staleness,
  retrospective policy resolution — keys on this file and survives `charter.md`
  deletion.
- **`charter.md`** (`.kittify/charter/charter.md`) is a **secondary**,
  readable, free-form prose/rationale companion. It is never a resolving
  override. One legitimate exception class survives by design (C-003): the
  `charter/context.py:249` gate, which renders prose if *either* file exists
  (an operator-facing "is there anything to show" gate, not an
  authority-presence check) — pinned, not retired, by WP01.
- One legitimate migration-compat exception (FR-006): `_status_collectors.py`'s
  pre-consolidation `charter.md`-only shape, explicitly scoped and regression-pinned.

## Non-vacuous durability guard

`tests/architectural/test_charter_path_literal_authority.py` (WP11) AST-walks
for inline `.kittify/charter/charter.{yaml,md}` path-literal construction
outside `charter/bundle.py`, and for new `charter.md`-keyed `.exists()`
presence gates. A frozen, shrink-only, per-site-justified allowlist (38
entries at mission close) captures the sanctioned residue — migration
historical-determinism sites, the C-003 prose class, and the layering-forced
`src/doctrine/**` sites that cannot import `charter.bundle` at all.

## Evidence

- `tests/charter/test_context_prose_presence_pin.py` (WP01)
- `tests/specify_cli/dashboard/test_charter_path_presence_probe.py` (WP02)
- `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py` (WP03)
- `tests/specify_cli/cli/commands/charter/test_status_collectors_legacy_md_shape.py` (WP04)
- `tests/architectural/test_charter_path_literal_authority.py` + `charter_path_literal_allowlist.yaml` (WP11)
