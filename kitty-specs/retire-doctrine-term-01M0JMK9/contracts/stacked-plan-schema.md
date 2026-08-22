# Contract: Stacked Mission Plan Schema (IC-04)

**Governs**: `kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md`
**Requirements**: FR-009, FR-010, NFR-003, SC-003, SC-004.
**Consumed by**: program execution (mission-by-mission), SC-003/SC-004 verification.

## Shape (operator-approved — decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`)

**5 active missions + 1 deferred to the 4.0 milestone.** Granularity is fixed; do not re-litigate in execution.

| # | Slug (proposed — finalize here) | Purpose (one line) |
|---|----------------------------------|--------------------|
| M1 | `charter-authority-flip` | Atomically rewrite three glossary authorities; move active referrers to `docs/context/charter.md`; retain immutable X2 refs as history and prove no dangling active refs; migrate `governance.doctrine` → `governance.charter`; edit human-owned bundle sections; refresh metadata; arm guard/registry last |
| M2 | `charter-cli-surface` | Freeze exhaustive `canonical-operator-surface-map.md` plus set-equal `canonical-cli-route-map.md`; update canonical CLI, serialized/API values including target URNs, supported public Python facades and distribution/wheel metadata, hidden warning/read aliases, semantic config seams, and every mapped producer/consumer regardless directory in the same PR |
| M3 | `charter-packs-source` | Built-in/org/project pack and overlay surfaces; fixed `.kittify/doctrine/` → `.kittify/charter-packs/` migration under the canonical-write/dual-read/collision contract; canonical `018-charter-versioning-requirement` directive ID + alias |
| M4 | `charter-skills-artifacts` | Execute the ADR contract's full skill/profile map: both `spk-doctrine-charter` and `spec-kitty-charter-doctrine` → `spk-charter-lifecycle`, six other named skill mappings, and `doctrine-daphne` → `charter-daphne`; retain 3.x warning aliases; migrate non-route prompts, overrides, and generated agent dirs through owning flow; route references were retired by M2 |
| M5 | `charter-docs-prose` | Remaining current human-facing prose regardless directory; glossary referrers were retired by M1 and route references by M2; ADR titles stay legacy (C-003) |
| M6 *(deferred to 4.0)* | `charter-removal-audit` | Remove every active or closed-no-channel CR/control record, aliases, and migrated legacy keys/paths; run the pinned content-and-path audit |

## Per-mission entry schema

Each mission gets one section with exactly these fields:

| Field | Rule |
|-------|------|
| `slug` | kebab slug (finalize the proposed slugs above or record a rename with reason) |
| `purpose` | one line, operator terms — what flips |
| `inputs` | list of artifacts from THIS mission (ADR / OC-## classes + CR candidates/evidence / methodology invariants) — the complete input set |
| `outputs` | list of flipped surfaces + verification evidence the next mission can rely on |
| `depends_on` | prior mission slugs (stack order M1→M5; M6 after the 4.0 milestone) — explicit, no implicit ordering |
| `retires_oc` | ordinary OC IDs; union over M1–M5 = all in-scope OCs; M6 empty; one primary-use owner only |
| `introduces_compatibility` | CR IDs whose declared introduction wave is this M1–M4 mission; empty M5/M6 |
| `removes_compatibility` | empty M1–M5; M6 lists every CR ID, including `closed-no-channel` tombstones |
| `change_mode` | `bulk_edit` for every M1–M6; each owns a scoped occurrence map because alias removal is occurrence-sensitive too |
| `invariant_after` | I1..I6 (from `data-model.md` §6) — the state that must hold when this mission merges |
| `local_design_questions` | **M1 must have zero**. M2's operator-surface map is the only later question: M2 owns every affected command, otherwise-unfixed M2-scope serialized/API occurrence/consumer, supported public Python facade, and distribution/project/wheel surface regardless category, then freezes authoritative map + set-equal CLI projection before edits. M3–M5 exclude mapped hits; ADR-fixed seams retain named owners. |
| `rollback` | Before dependents land, the wave may be reverted alone. Afterward, reverse the landed suffix M(n)..M1 or forward-fix. M6 may restore 3.x aliases only while 3.x compatibility remains supported; after 4.0 it follows whole-release rollback policy. |

## Assignment table (SC-003 pass condition)

One table maps **every** in-scope OC-## from `inventory.md` to exactly one M1–M5 mission slug (or `deferred:<milestone>` with rationale):

| OC-## | surface_category | assigned_mission | note (deferral rationale if deferred) |
|-------|------------------|------------------|----------------------------------------|

A second table maps every compatibility reservation:

| CR-## | semantic_seam | source_oc_ids | introduction_wave | removal_mission | note |
|-------|---------------|---------------|-------------------|-----------------|------|

**Pass condition**: every in-scope OC appears exactly once across M1–M5; every CR appears once at
its declared M1–M4 introduction and once at M6 removal; every funded source hit's OC primary owner
equals that introduction wave (split mixed-owner OCs/CRs); no hit/coordinate is double-owned or
double-funded. Out-of-repo deferrals name surface, repo, owner, milestone, tracking reference/downstream
process, and rationale; no `TBD` remains.

## Invariants

- **SM-I1 (single assignment)**: the OC and CR tables are the check: one primary OC owner; one CR
  introduction plus M6 removal; each funded source OC owner equals that introduction; pairwise-disjoint
  source/product coordinates and product budgets. Mixed-owner OCs/CRs are split before the plan passes.
- **SM-I2 (spec-readiness of M1)**: from `stacked-plan.md` + the ADR + `inventory.md` (S2/S5 rows and CR candidates) + `methodology.md` (atomic-flip design, guard baseline spec), a planner can write M1's full spec with **0 new operator decisions**. Fixed CRs carry literal targets; M2-owned CRs carry fail-closed owner/OC references and cannot introduce compatibility before M2 freezes the target. M1 materializes actual-base coordinates/maxima and X3 control records by deterministic drift reconciliation. SC-004 verifies this by dry run.
- **SM-I3 (same-wave consumers)**: any mission retiring an S1 or S8 class updates its scripted CI consumers in the same PR (catfooding conflict C5).
- **SM-I4 (fixed overlay cutover)**: M3 writes only `.kittify/charter-packs/`; 3.x reads either root with an old-root warning. Disjoint entries merge with canonical-root precedence, identical duplicates deduplicate, differing duplicate relative paths/URNs hard-fail, and upgrade uses atomic rename or recoverable checked merge. M3 owns readers, writers, staging, migration, docs/config/tests; M6 removes legacy root support.
- **SM-I5 (operator-map exhaustiveness)**: every command, serialized/API, supported-public-Python-API, and public-distribution/wheel OC joins exactly one complete M2 map row and every producer/consumer is M2-owned or externally coordinated. The map enumerates exact `doctrine.api.__all__` membership and the `spec-kitty-doctrine` packaging/wheel contract. `canonical-cli-route-map.md` is set-equal to the authoritative map's command rows and records its hash. M3–M5 contain zero mapped hits. Immutable X2 data stays byte-identical and renders canonically.
