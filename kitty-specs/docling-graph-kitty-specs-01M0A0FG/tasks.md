# Tasks — Docling Graph for `kitty-specs`

This single closeout work package is a compatibility projection for the legacy
Spec Kitty acceptance surface. The research mission itself executed through the
v2 research runtime (`scoping` → `methodology` → `gathering` → `synthesis` →
`output` → `done`) and has no implementation work packages.

## Subtask index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Confirm terminal v2 research-runtime state | WP01 | No |
| T002 | Verify the hash-bound publication seal | WP01 | No |
| T003 | Materialize pointer-only v0 research paths | WP01 | No |
| T004 | Prepare Spec Kitty acceptance-gate inputs | WP01 | No |

## Work Packages

### WP01 — Research closeout and acceptance proof

- **Goal**: bridge the completed v2 research runtime into the legacy acceptance
  reader without inventing implementation work or duplicating publication
  authority.
- **Priority**: P0
- **Dependencies**: none
- **Requirements**: DR-004, AR-002, QR-001, QR-002
- **Independent test**: publication verification passes and `spec-kitty accept
  --diagnose` reports no blocking checks.
- [x] T001 Confirm terminal v2 research-runtime state (WP01)
- [x] T002 Verify the hash-bound publication seal (WP01)
- [x] T003 Materialize pointer-only v0 research paths (WP01)
- [x] T004 Prepare Spec Kitty acceptance-gate inputs (WP01)
