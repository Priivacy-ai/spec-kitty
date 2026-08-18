# Tasks — Docling Graph for `kitty-specs`

This single closeout work package is a compatibility projection for the legacy
Spec Kitty acceptance surface. The research mission reached v2 runtime `done`
at commit `21bcce5a70b72e385fad77954a9f45d7806b7835`; adding this projection made the
current canonical WP lifecycle active again until acceptance closes it. The
research itself had no implementation work packages.

## Subtask index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Confirm terminal v2 research-runtime state | WP01 | No |
| T002 | Verify the original 40-artifact research seal at `48fd33167585c2757d7642297b663e074ed7c07e` | WP01 | No |
| T003 | Materialize pointer-only v0 research paths | WP01 | No |
| T004 | Prepare Spec Kitty acceptance-gate inputs | WP01 | No |

## Work Packages

### WP01 — Research closeout and acceptance proof

- **Goal**: bridge the completed v2 research runtime into the legacy acceptance
  reader without inventing implementation work or duplicating publication
  authority.
- **Priority**: P0
- **Dependencies**: none
- **Research trace (not canonical `requirement_refs`)**: DR-004, AR-002,
  QR-001, QR-002. The current task finalizer only recognizes
  `FR|NFR|C`; the approved compatibility exception is documented in WP01.
- **Independent test**: publication verification passes and `spec-kitty accept
  --diagnose` reports no blocking checks.
- [x] T001 Confirm terminal v2 research-runtime state (WP01)
- [x] T002 Verify the original 40-artifact research seal at `48fd33167585c2757d7642297b663e074ed7c07e` (WP01)
- [x] T003 Materialize pointer-only v0 research paths (WP01)
- [x] T004 Prepare Spec Kitty acceptance-gate inputs (WP01)
