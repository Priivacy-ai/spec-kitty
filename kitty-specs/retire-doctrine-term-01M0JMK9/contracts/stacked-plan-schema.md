# Contract: Stacked Mission Plan Schema (IC-04)

**Governs**: `kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md`
**Requirements**: FR-009, FR-010, NFR-003, SC-003, SC-004.
**Consumed by**: program execution (mission-by-mission), SC-003/SC-004 verification.

## Shape (operator-approved — decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`)

**5 active missions + 1 deferred to the 4.0 milestone.** Granularity is fixed; do not re-litigate in execution.

| # | Slug (proposed — finalize here) | Purpose (one line) |
|---|----------------------------------|--------------------|
| M1 | `charter-authority-flip` | Glossary rewrite (FR-011) + charter-bundle update (`charter.yaml` + regeneration, incl. Terminology Canon line from the ADR) + guard arming (last WP) — one mission, one PR |
| M2 | `charter-cli-surface` | `spec-kitty doctrine` group (8 subcommands) + `doctor doctrine` → canonical names; hidden aliases + deprecation warnings; per-subcommand alias tests; same-wave CI consumer updates |
| M3 | `charter-packs-source` | User-facing strings/titles in `packs/built-in/` (canonical source of all agent copies) |
| M4 | `charter-skills-artifacts` | `spk-doctrine-*` → new names + legacy alias skills during the window (old→new map recorded in M4's artifacts; the alias skills are its executable form); agent dirs via migration/upgrade flow |
| M5 | `charter-docs-prose` | `docs/` prose + root-level operator docs (`AGENTS.md`, …); ADR titles stay legacy (C-003) |
| M6 *(deferred to 4.0)* | `charter-removal-audit` | Strip aliases; run the NFR-001 zero-doctrine audit (verifies the 4.0 hard rule) |

## Per-mission entry schema

Each mission gets one section with exactly these fields:

| Field | Rule |
|-------|------|
| `slug` | kebab slug (finalize the proposed slugs above or record a rename with reason) |
| `purpose` | one line, operator terms — what flips |
| `inputs` | list of artifacts from THIS mission (ADR / OC-## classes with counts + examples / methodology invariants) — the complete input set |
| `outputs` | list of flipped surfaces + verification evidence the next mission can rely on |
| `depends_on` | prior mission slugs (stack order M1→M5; M6 after the 4.0 milestone) — explicit, no implicit ordering |
| `retires` | list of OC-## IDs (union over M1..M6 = all in-scope classes) |
| `change_mode` | `bulk_edit` for M1–M5 (each with its own scoped `occurrence_map.yaml`, 8 standard categories); M1's map covers the glossary + bundle renames — its guard-arming WP is additive code, not a rename occurrence; M6 removal |
| `invariant_after` | I1..I6 (from `data-model.md` §5) — the state that must hold when this mission merges |
| `open_items` | any decision NOT fixed by this mission's artifacts — **M1 must have zero** (FR-010/SC-004); later missions may carry `OPEN` items only with a named owner |

## Assignment table (SC-003 pass condition)

A single table mapping **every** in-scope OC-## from `inventory.md` to exactly one mission slug (or `deferred:<milestone>` with rationale):

| OC-## | surface_category | assigned_mission | note (deferral rationale if deferred) |
|-------|------------------|------------------|----------------------------------------|

**Pass condition**: every in-scope OC-## appears exactly once; no class is assigned to two missions; deferrals carry a rationale.

## Invariants

- **SM-I1 (single assignment)**: as above — the assignment table is the check.
- **SM-I2 (spec-readiness of M1)**: from `stacked-plan.md` + the ADR + `inventory.md` (S2/S5 rows) + `methodology.md` (atomic-flip design, guard baseline spec), a planner can write M1's full spec with **0 new operator decisions**. SC-004 verifies this by dry run.
- **SM-I3 (same-wave consumers)**: any mission retiring an S1 or S8 class updates its scripted CI consumers in the same PR (catfooding conflict C5).
