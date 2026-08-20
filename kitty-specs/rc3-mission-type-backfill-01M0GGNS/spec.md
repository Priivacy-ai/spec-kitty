# Mission Spec (LIGHT — not finalized): mission_type backfill migration (program gate)

> **Program gate for rc3.** This mission must land AND be run against real projects
> **before M3 and M5 reach them.** M5 drops legacy `{"mission":…}` resolution and M3
> makes a typeless/typo'd `mission_type` hard-fail; together, an unmigrated legacy
> mission carrying only `{"mission":…}` goes from silently-resolving → typeless (M5) →
> hard-fail (M3). Backfilling `mission_type` first is what makes that combined change
> safe. Hoisted out of M5 (was M5/FR-007) into its own mission-0 gate per the
> integration check.

## Problem & impact (BLUF)

Legacy missions store their type in the deprecated `mission` field of `meta.json`;
newer missions use `mission_type`. Several readers still fall back to `mission`.
Missions **M3** (charter gate predicate-inversion — typo/typeless `mission_type` now
hard-fails) and **M5** (canonical reader — legacy `mission` resolution dropped
entirely) remove that fallback. Without a backfill, any project whose `kitty-specs/`
carries `mission`-only `meta.json` files breaks on upgrade: those missions stop
resolving and then hard-fail. This mission mints `mission_type` for every legacy
mission so the M3+M5 behavior change is non-breaking.

## In scope

- A deterministic, idempotent backfill that, for every mission under `kitty-specs/`
  whose `meta.json` has a legacy `mission` value but no (or empty) `mission_type`,
  writes `mission_type = canonical_mission_type_key(mission)`.
- An audit/dry-run mode (report what would change; `--json`).
- A doctor check surfacing any remaining `mission`-only missions (a fail-on gate CI
  can use before shipping M3/M5).
- Coordination with the existing identity backfill: `migrate backfill-identity` mints
  only `mission_id` today — this mission adds the `mission_type` dimension (either a
  new `migrate backfill-mission-type` command or a `mission_type` step folded into the
  same migration surface — decide in plan).

## Out of scope (deferred / owned elsewhere)

- The resolution/reader changes themselves (M3 owns the gate/hard-fail; M5 owns the
  reader convergence and the legacy-resolution drop).
- Retiring the `mission` field from `meta.json` schema (a separate later migration).

## Functional requirements

- **FR-001** — Detect legacy missions: `meta.json` with a non-empty `mission` and a
  missing/empty `mission_type`.
- **FR-002** — Backfill `mission_type = canonical_mission_type_key(mission)`; leave a
  mission that already has `mission_type` untouched.
- **FR-003** — Idempotent: a second run is a no-op (added=0).
- **FR-004** — Dry-run/audit mode with `--json` machine output (added/skipped counts,
  per-mission before→after).
- **FR-005** — A `doctor` check (or `--fail-on`) that exits non-zero while any
  `mission`-only mission remains, so CI can gate the M3/M5 release on a clean census.

## Acceptance criteria

- **AC-1** — After backfill, every mission under `kitty-specs/` resolves a
  `mission_type` via the canonical reader; no mission is `mission`-only.
- **AC-2** — A mission with only `{"mission":"software-dev"}` gets
  `mission_type: software-dev`; a mission already carrying `mission_type` is unchanged
  (byte-identical apart from the intended field).
- **AC-3** — Re-running the backfill reports `added=0` (idempotent).
- **AC-4** — The doctor/fail-on gate reds while a `mission`-only mission exists and
  greens once the census is clean.

## Key design decisions

- Derive the canonical value through the **same** `canonical_mission_type_key` used by
  the M5 shared `read_mission_type()` helper, so the backfill and the readers agree by
  construction.
- Ship the gate (FR-005) so the rc3 release pipeline can refuse to ship M3+M5 into a
  project that hasn't been backfilled.

## Open decisions (plan-phase, non-blocking)

- **New command vs fold into `backfill-identity`:** a dedicated `migrate
  backfill-mission-type` (clear, separately runnable) vs a `mission_type` step in the
  existing identity migration (one migration surface). *Lean: dedicated command, since
  it must be independently runnable as a release gate.*

## Risks / blast-radius

- Consumer projects must run this before upgrading to the rc that carries M3+M5 —
  document the ordering in the release notes and enforce it via FR-005's gate.
- Must not alter a mission that already has a correct `mission_type`.

## Issues

- **Program gate for:** M3 (#3596/#3598) and M5 (#3598 dec#2, reader convergence).
- **Related:** `migrate backfill-identity` (mission_id only, today).

## See also

- rc3 program overview / approach (this mission is the M0 gate).
