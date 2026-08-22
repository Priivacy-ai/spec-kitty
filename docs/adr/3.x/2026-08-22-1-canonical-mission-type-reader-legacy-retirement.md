---
title: 'ADR 2026-08-22-1: Canonical mission-type reader; legacy `mission`-field resolution retired'
description: 'One shared `read_mission_type(meta)` seam becomes the sole mission-type resolution authority; the legacy `{"mission": …}` field is no longer read and the silent `software-dev` default is removed. A deliberate behavior change, de-risked by the M0 `backfill-mission-type` migration that must run first.'
status: Accepted
date: '2026-08-22'
---

## Context

A single blessed canonical reader existed
(`specify_cli.mission._canonical_meta_mission_type`), yet ~10–12 **hand-rolled**
`meta.json` mission-type readers each re-derived their own field order and their
own default, and they **disagreed** (issue #3598, "second inconsistency"; epic
#3410 — charter/doctrine silent-drop, fail loud):

- The **charter path** read only `mission_type`, while the **CLI path** also
  honored the legacy `mission` field — so `{"mission": "software-dev"}` resolved
  **typeless** one way and **software-dev** the other.
- **Four readers silently defaulted `software-dev`** (`mission_metadata`,
  `retrospective/generator`, `charter/interview`, a migration step), masking
  typeless / typo'd missions.
- **A dashboard reader** (`dashboard/handlers/features.py`) read **only** the
  legacy `mission` field, ignoring the canonical field entirely.

This is the M5 half of the rc3 "fail-loud friction burndown" (epic #3410). The
per-type unknown-mission-type resolution fix (the primary half of #3598) is M3
and is out of scope here.

Two operator decisions (2026-08-20) frame this ADR:

1. **Legacy `{"mission": …}` resolution is retired entirely.** Every reader
   resolves the canonical `mission_type` field only, through one shared
   runtime-neutral helper; the silent `software-dev` defaults are removed.
2. Convergence is **downward** to canonical-only, **not** upward to legacy — the
   #3598 split closes because both paths stop reading legacy `mission`, not
   because the charter path gains it.

## Decision

### 1. One shared reader: `read_mission_type(meta: dict) -> str | None`

A single dict-in helper lands beside `canonical_mission_type_key` in
`src/charter/mission_type_key.py` — the `charter` layer, below `specify_cli` and
importable by both (dissolving #2480's import blocker). It reads **only** the
canonical `mission_type` field → `canonical_mission_type_key` → `None`; **no
legacy fallback, no default.** `_canonical_meta_mission_type` collapses to a thin
delegate, and M3's charter read path (`_read_meta_mission_type` /
`resolve_mission_type_key`) delegates its field-extraction to the same seam — the
**M3↔M5 reconciliation** that keeps the two readers from re-diverging (the exact
defect M5 exists to kill). File I/O stays per-reader; the seam is pure.

### 2. Legacy `mission` read and silent `software-dev` default retired

Every in-scope runtime **reader** is routed through the seam, dropping the legacy
field and the silent default. Create-time / inference **writers**
(`build_mission_identity`, `feature_meta.infer_mission`) and the template
selection boundary in `get_mission_for_feature` (C-006) legitimately retain a
`software-dev` value; these are encoded, rationale-bearing exemptions in
`tests/architectural/mission_type_reader_allowlist.yaml`. The field-aware
census/audit tool (`_mission_type_audit`) keeps reading both fields by design.

### 3. Structural gate (FR-010)

`tests/architectural/test_mission_type_reader_invariants.py` asserts (a) every
in-scope reader returns exactly `read_mission_type(meta)` for the same dict
(parity registry) and (b) no in-scope module carries a legacy `mission` read or a
`software-dev` fallback (AST source-scan, allow-list for encoded exemptions). A
newly-added reader that reintroduces either pattern trips the build.

### 4. FR-009 inline reads unchanged

The frozen-migration and charter-layer inline `meta.json` reads (#2477–#2480) are
already exempted in the pre-existing `inline_meta_read_allowlist.yaml` (mission
#883). That gate governs a **different** invariant (raw `json.loads` bypassing
`load_meta`); this ADR does not duplicate it. The charter reader now delegates
its *field extraction* to the shared seam while its inline *file read* stays
exempt (the charter package cannot import `specify_cli.load_meta`).

## Consequences

### Deliberate behavior change, with blast radius

A legacy mission carrying only `{"mission": …}` (no `mission_type`) **stops
resolving** — it becomes typeless. It **compounds with M3**: once M3's #3598
per-type hard-fail lands, an unmigrated legacy mission moves *silently-resolving*
→ *typeless* (M5) → *hard-fail* (M3).

### The M0 backfill is the safety net — and must run first

`spec-kitty migrate backfill-mission-type` (M0, #3614) mints a profile-resolving
`mission_type` into every legacy `meta.json` whose only type signal is the
deprecated `mission` field (idempotent; a value that resolves no governance
profile is reported `needs_manual_resolution`, never written — so the backfill
never manufactures an M3-breaker). **This migration must land and be run against
a project before the M3 and M5 changes reach it.** `migrate backfill-identity`
mints `mission_id` only — it does **not** backfill `mission_type`.

### User-visible surfaces now show the true type

The dashboard, retrospective records, and identity resolution now show a
mission's true `mission_type` (or a neutral typeless / `Unknown`) instead of a
masked `software-dev`. See the `[Unreleased]` changelog for the per-surface note.

## References

- Issue #3598 (second inconsistency), epic #3410 (fail-loud friction burndown).
- Folded: #2901 (WP-frontmatter tolerant reader — verified landed), #2477–#2480
  (inline meta reads — exempt in `inline_meta_read_allowlist.yaml`).
- M0 backfill: #3614. M3 per-type hard-fail: #3596/#3598.
- Mission: `kitty-specs/rc3-canonical-mission-type-reader-01M0GGWM/`.
