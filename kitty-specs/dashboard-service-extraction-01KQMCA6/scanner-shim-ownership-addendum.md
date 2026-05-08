# Governance Addendum — `src/specify_cli/scanner.py` Shim Ownership

**Filed by**: Follow-up mission `dashboard-extraction-followup-01KQMNTW` (DRIFT-1).
**Parent mission**: `dashboard-service-extraction-01KQMCA6` (mission #111).
**Date**: 2026-05-02.

## Why this addendum exists

The post-merge mission review of `dashboard-service-extraction-01KQMCA6`
identified `src/specify_cli/scanner.py` (17 lines) as a file that was added
during the extraction without being declared in any work package's
`owned_files` list. The file is functionally necessary but the parent
mission's governance record was silent on it. This addendum closes that
silence.

## What `src/specify_cli/scanner.py` is

A re-export shim. Its only purpose is to give the new `src/dashboard/`
package an import path that is **not** under `specify_cli.dashboard.*` so
that FR-010 of the parent mission can be enforced (the architectural
boundary test asserts that no module inside `src/dashboard/` imports from
`specify_cli.dashboard.*`).

Canonical implementations live in `specify_cli.dashboard.scanner` for the
duration of this transitional period. The shim re-exports five names:

- `format_path_for_display`
- `resolve_active_feature`
- `resolve_feature_dir`
- `scan_all_features`
- `scan_feature_kanban`

The file carries `# ruff: noqa: F401` because the names are imported
purely for re-export, and a docstring naming the FastAPI transport
migration milestone as the removal trigger.

## Ownership and removal trigger

- **Owning mission for the shim's lifetime**: parent
  `dashboard-service-extraction-01KQMCA6`.
- **Audit declaration ownership** (this addendum): follow-up
  `dashboard-extraction-followup-01KQMNTW`.
- **Canonical authority for the underlying scanner module**:
  `specify_cli.dashboard.scanner` (until the scanner extraction mission
  #613 relocates it to its own canonical package).
- **Removal release / trigger**: scanner extraction mission #613
  completion. When that mission lands, the shim updates to point at the
  new canonical location and is then retired the moment `dashboard.*`
  imports the new canonical path directly.
- **Scope of the shim**: scanner names only — no other `specify_cli.*`
  surface is re-exported through `src/specify_cli/scanner.py`. Future
  authors must not extend this shim to bridge unrelated symbols; if a
  new symbol needs a `dashboard.*`-friendly import, file a new shim or
  expand the parent mission's ownership map.

## Cross-references

- Ownership map: `architecture/2.x/05_ownership_map.md` § Dashboard
  → `shims:` entry adds this shim alongside the existing
  `api_types.py` shim and links back to this addendum.
- Manifest: `architecture/2.x/05_ownership_manifest.yaml` →
  `dashboard.shims[1]` mirrors the map entry in machine-readable form.
- ADR: `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md`
  → "Consequences" section names the shim and links to this addendum.

## Reviewer audit trail

A reviewer auditing the parent mission's compliance with DIRECTIVE_024
(Locality of Change) can find this file via three independent paths:

1. The ownership map (entry point for governance reviews).
2. The ADR (entry point for architectural design reviews).
3. The parent mission directory (entry point for mission-level audits).

All three paths converge on this addendum. The addendum names the
removal trigger explicitly so future readers do not need to re-derive
when the shim should retire.
