# Programme Plan: Doctrine Canonical Structure Remediation

> **This is a programme plan, not an implementation plan.** This mission was specced and then
> broken into five child missions (see [`spec.md`](spec.md)). Nothing is implemented here. Each
> child mission carries its own `plan.md` scoped to the concerns it owns; this document holds what
> only makes sense once — the Phase 0 findings, the ordering rationale, the concern map, and the cost.

**Branch**: `feat/doctrine-canonical-structure-01KYEYSD` (off `upstream/main` @ `1a15bcf6c`) — programme scaffolding only
**Date**: 2026-07-26
**Spec**: [`spec.md`](spec.md) — 33 FR / 13 NFR / 11 C / 24 SC
**Governing ADRs**: [2026-07-26-1](../../docs/adr/3.x/2026-07-26-1-drg-edges-are-the-canonical-relationship-authority.md) (relationship authority, **read the Amendment**) · [-2](../../docs/adr/3.x/2026-07-26-2-doctrine-artefact-pack-layout-convention.md) (pack layout) · [-3](../../docs/adr/3.x/2026-07-26-3-impacts-edge-subsumes-in-tension-with.md) (`impacts` / `is_symmetric`)
**Sequencing authority**: [`manifesto-program-delivery-sequence.md`](../../docs/plans/doctrine/manifesto-program-delivery-sequence.md)
**Design authority**: [`foundational-values-and-creed.md`](../../docs/plans/doctrine/foundational-values-and-creed.md)

## Summary

One root cause, four symptoms: **the doctrine layer predates its own canonical model, and nothing
enforces the model that replaced it.** Every failure mode in the spec is *silence* — a misplaced
artefact that never loads, a migration hint naming a file that does not exist, a relationship
surface that is derived rather than authored, a schema slot with no producer.

The plan closes that class in four movements, in this order and no other:

1. **Make silence impossible** before adding anything that could ship silently (IC-01…IC-05).
2. **Fix the leaking seams** the new vocabulary would otherwise flow through (IC-06…IC-07).
3. **Evolve the relation vocabulary and migrate all 774 edges to authored form**, retiring the
   extractor's edge production entirely (IC-08…IC-13).
4. **Author the doctrine content** that surfaced the defect in the first place (IC-14).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic v2, ruamel.yaml, typer, pytest
**Storage**: YAML artefacts under `src/doctrine/`; generated `*.graph.yaml` cache
**Testing**: pytest, targeted single-file runs only (C-007). ATDD red-first per WP (charter C-011)
**Project Type**: single project
**Scale/Scope**: 311 DRG nodes · 774 edges · 171 files carrying 761 inline entries · ~560–645 file touches

**Measured ground truth** (re-derived on this branch, 2026-07-26 — never hand-counted):

```
nodes 311 · edges 774
suggests 332 · requires 259 · scope 157 · rejects 8 · instantiates 8
specializes_from 4 · reconciles_tension 3 · in_tension_with 2 · applies 1 · refines 0

inline surfaces: 559 MIGRATE / 188 GOVERNANCE / 14 RAW_MATERIAL
MIGRATE files: 169  (references 137 · context-sources.directives 17 ·
                     directive_refs 12 · tactic-references 10 · steps[].references 7)
```

Reproduce with `PYTHONPATH=src python scripts/doctrine/inline_reference_inventory.py`.

## Charter Check

*GATE: passed. Re-check after Phase 2.*

| Charter rule | How this plan satisfies it |
|---|---|
| Single canonical authority | The whole point: one relationship authority (edges), one profile→directive field, one AMMERSE definition, one relationship vocabulary. Two Python edge registries are **deleted**, not shadowed. |
| Architectural alignment | The localized-source + generated-cache split (IC-10) is the existing three-tier repository pattern, not a new seam. |
| ATDD-first (C-011) | Every WP lands a failing-first test as its first commit. For IC-12 the RED *is* the deliverable (NFR-009 ablation). |
| Campsite cleaning (SO-2) | Ranks 1–7 of the sequencing authority are campsite work, scheduled **before** functional change — six of the top eight, deliberately. |
| Architectural gate discipline (SO-5) | Every gate added carries a self-mutation test and a zero-entry allowlist (NFR-001, NFR-011, SC-021). A gate-unmask cannot self-validate. |
| Red-main discipline (SO-9) | The 6 inherited `arch-adversarial` reds stay red (C-006). No greenwashing, no retry-to-green. |
| Git/workflow discipline (SO-7) | Three draft PRs to `main`, operator merges. Never `git push origin main`. |
| Canonical sources (SO-6) | Templates resolved from `src/doctrine/missions/software-dev/templates/`; scope derived from the inventory script, never restated as a literal. |

## Phase 0 results — completed 2026-07-26

Phase 0 was decisions plus two cheap probes. It cost ~2 hours and deleted the largest line item in
the programme before anything was spent on it.

### G5 — the `#2538` rig does not exist ❌

Searched exhaustively: every in-repo hit for `2538` is a **document** (the superseded ADR, four
plan files, four squad reports, the docs retrieval index). The two `test_no_dead_symbols.py` hits
are content-hash substrings. No brief, no fork fixtures, no pre-registration, no judge harness under
`tests/`, `scripts/`, `src/`, `.local/`. No branch, local or upstream. `git log --all -S` over the
rig's distinctive phrases returns only the commits that added the design documents — nothing was
ever committed, and nothing was deleted.

The issue says "Rig is standing", but it is P2, milestone 3.3.x, self-described as "a validation
spike, not release-critical", and its two most recent comments are about the parent ADR.

**Cascade** (reverses if the rig turns out to exist off-repo):

| Item | Disposition |
|---|---|
| **I14** value fields — 14–18 code files + **~1,372–1,596 authored cells** | **Closed.** G3 unreachable. This was the programme's entire unquantified authoring tail. |
| **I17** interview instrument | **Closed.** G3 + D-4. |
| **I4-WP03** render grouping | Loses its only stated purpose (produce arm B). Follow-on mission, on independent merit only. |
| **I16** advisory-homonym unification | **Kept** (operator ruling) — removes a `primary`/`merge`-class footgun on independent merit. Follow-on mission; needs its own occurrence map (C2). |
| **I4-WP01/02** `ResolvedContext` partition + un-vacuum `walker.py:507-509` | **Kept.** WP02's red is a real defect closure regardless of G3. Follow-on mission. |

### I5 — the second AMMERSE copy, found ✅

`src/doctrine/templates/architecture/ammerse-analysis-template.md`. The earlier "only one definition
exists under `src/doctrine/`" reading was scoped to YAML; the second copy is Markdown.

All seven definitions differ (template = compressed glosses, tactic = full text), and the failure is
sharper than drift:

> **Tactic:** "Use the canonical definitions **exactly as stated** — do not substitute personal
> interpretations… use these **verbatim** as the scoring lens." …then: "Use the AMMERSE Analysis
> template to structure the record."

`tactic:ammerse-impact-analysis --suggests--> template:ammerse-analysis-template` is a **live DRG
edge**, so an agent following the tactic is told to quote verbatim and then routed by the graph to
seven different definitions. This is the accreditation hazard §12 names ("accrediting a misquoted
definition is worse than not accrediting") sitting on a shipped path. I5 does **not** collapse to a
parity test; it stays a 2-file unification + parity test. Follow-on mission.

### Operator rulings taken

| Ruling | Decision | Consequence |
|---|---|---|
| occurrence_map granularity | **Honest map now + schema fix as a Phase 1 WP** | `occurrence_map.yaml` authored at file granularity (gate verified green); WP02 adds field-path granularity; the map is re-authored against it before Phase 2. |
| pedro/034 | **Evidence-determined: accept as ledgered deviation** | Not a judgement call. Both blocks were created in the same commit (`fa80fa0f9`) and were already out of sync at birth; every later addition (041, 043/044/045) landed in **both**; four other profiles carry 034 in both, including all three sibling language implementers. It is an omission at birth, corrected. |
| I16 scope | **Keep** — footgun removal stands alone | Moves to the follow-on mission with its own occurrence map. |
| D-3 (creed → arithmetic or prose?) | **Arithmetic** | I10 unparks (3 files, ~4h) into the follow-on mission. See Complexity Tracking for the measured risk this carries. |

### Rulings still open — do not start the dependent work without them

| # | Decision | Status |
|---|---|---|
| **D-1** | Is `toolguide` value-bearing? Is `agent_profile` `value_bias` or out? | **Settled in full (2026-07-26).** `toolguide` **OUT** — complimentary, not behavioural, so no Δ-from-not-adopting; `_VALUE_IMPACT_KINDS` stays `{DIRECTIVE, TACTIC, STYLEGUIDE, PROCEDURE}`. `agent_profile` **IN on the bias side**, carrying *two* fields (more than §7.4 anticipated): a structured **creed/bias matrix** (`{value, bias, rationale}` list) and a free-text multiline **creed description**. Adds ~126 bias cells + 18 descriptions across the 18 built-in profiles — real, but not a reopening of I14: that was the *impact* side and gated on G3; the bias side never was. Both are new `AgentProfile` slots, so C-009 binds them and mission A must precede. |
| **D-5** | Mandatory `rationale` — advisory or hard? | **Settled (2026-07-26): HARD**, on value descriptions and deltas only. The number is a warning signal; the rationale is the tie-breaker and the real value-add. **Not** hard on `DRGEdge` relationships unless trivially inferable. Consequence: the calibration corpus fails this (≥3 of 38), so I9's import must supply or reject those rationales rather than quietly weakening the rule. |
| **D-4** | Interview instrument: authored question bank, or model-chosen questions? | **SETTLED 2026-07-26 — the framing was a false binary.** It bundled two independent failures with different fixes. *Flatness* is caused by the **response format**, not authorship: the ruling is a **constant-sum budget** for the N weights, which prevents a flat creed whoever asks. *Provenance laundering* is fixed by recording **per-weight provenance** (`operator` / `model-suggested-operator-confirmed` / `default`) — needed anyway for §9's deviation ledger. And an authored question bank was rejected on a third ground the original framing missed: it is **basis-specific and breaks ADR-D10's N-genericity**, since a bank of 21 AMMERSE pairs cannot serve a consumer's 5-value basis. **Elicitation questions therefore live on the value-set artefact**, authored by whoever authors the basis. **I8 runs before the instrument is built** — it tells us how much elicitation precision is worth buying. |
| **ADR-D8** | The asymmetric matrix pair | **SETTLED 2026-07-26.** The operator — author of the **AMMERSE analysis procedure** (§3, the Pragmatic Penguin Patterns library) — confirms the asymmetry is an error, and repairs it by **symmetrising to `+0.75` in both directions**. The adopted claim: **maintainability and extensibility reinforce each other.** The published `−0.75` is the errant cell. **Headline residual moves 4.70% → 4.37%; per-step gain 0.3892 → 0.3766.** Unblocks D's matrix validator. See the provenance note below — this is *not* upstream confirmation. |

### Provenance note on ADR-D8 — settled, not pending

The operator authored the **analysis procedure** this repository implements; **J.B. Crossland
authored the AMMERSE value system** (§3), which is its **ideological root**.

**Operator statement, 2026-07-26:** he holds **prior written consent** from Crossland to use the
AMMERSE idea and to publish his own procedure under his own intellectual property. Accreditation and
mention discharge the obligation in full.

So the adjudication is **the operator's, taken on his own authority over his own procedure**. It is
not provisional and is not waiting on anyone.

**Withdrawn as a consequence** — an earlier revision of this plan and of ADR `2026-07-26-3` treated
the upstream report as an outstanding operator-only obligation and put a "should not front-run that
conversation" caveat on D8. **Both are superseded.** There is no owed report, no pending response,
and no precondition on shipping the matrix.

**What survives, reframed from obligation to provenance hygiene:** the in-repo divergence record. Our
matrix differs from the published one at exactly one cell; a future reader needs to know which and
why, and a `source_digest` detects a later upstream change. That is useful engineering, not a debt —
and it is *not* a gate.

The distinction between the two authorships still holds and should not be collapsed: the judgement is
the operator's, and Crossland's system remains the acknowledged root. The required non-empty
`attribution` and the root `NOTICE` matter **more** under this framing, not less — accreditation is
precisely what discharges it.

### Ruling not to lose: the operative frame behind D-5

D-5's answer states the design's centre of gravity, so it is recorded here rather than only in
mission D: **the numeric layer is a warning signal, and the rationale is the tie-breaker.** That is
the same principle as §8's floor — *"never render a number without its rationale, and treat the
rationale as authoritative where they disagree"* — now enforced by schema on the surface that
carries the numbers, rather than left as prose guidance.

## Corrections to the spec, folded here

The spec is the plan of record, but four of its statements did not survive re-derivation on this
branch. Recorded here rather than silently worked around:

1. **C-003 is void.** It pins "all work stays on `fix/2934-demock-planning-closeout-test` and ships
   as one PR (#2936)". Both are merged (`1a15bcf6c`). **Replaced** by the programme shape below.
2. **The migration is 169 files, not 139.** ADR 2026-07-26-1's Consequences prose says 139;
   NFR-013's "169-file" is correct. Derived, not counted.
3. **FR-027 is not behaviour-neutral and collides with NFR-010/SC-012.** Resolved as a ledgered
   deviation (above). NFR-010's before-snapshot carries exactly one enumerated entry.
4. **The `shipped/` count is 22 across 9 files, not 21 across 8** — and at least one hit
   (`model-to-task_type.yaml`: "shipped/packaged") is prose, not a path. SC-015's gate needs a
   path-shaped discriminator or it false-reds, the same trap SC-003's `graph.yaml` gate must dodge.

## Programme shape — five missions, replacing C-003

One PR of ~600 file touches is not reviewable, and the sequencing authority's **C2** forbids two
all-surface sweeps sharing one occurrence map. This scope contains at least three. So the work is
five missions, each its own draft PR to `main`, each independently green.

| # | Mission | Working branch | Concerns | Occurrence map | Days | Files |
|---|---|---|---|---|---|---|
| **A** | `doctrine-silence-guards-01KYFV7Q` | `remediation/doctrine-silence-guards` | IC-01…IC-07 | n/a | 4–6 | ~55–70 |
| **B1** | `drg-relation-impacts-vocabulary-01KYFV87` | `feat/drg-relation-impacts-vocabulary` | IC-08 | n/a | 3–5 | ~45–60 |
| **B2** | `drg-edge-migration-extractor-retirement-01KYFV8C` | `remediation/drg-edge-migration` | IC-09…IC-13 | **yes** — re-authored against A's field-path schema | 11–14 | ~365–390 |
| **C** | `test-quality-doctrine-series-01KYFV8H` | `feat/test-quality-doctrine-series` | IC-14 | n/a | 3–5 | ~30–45 |
| **D** | `foundational-values-creed-band-01KYFV8N` | `feat/foundational-values-creed-band` | creed band (I5, I9, I6, I13, I8, I1a, I16, I4-WP01/02/03, I10) | **yes** — its own, for I16 | 7–13 | ~60–100 |

Each mission's `meta.json` `target_branch` names its **own working branch**, which is where its
planning artefacts and lane work land. The pull request from that branch targets `main`; the operator
merges. `target_branch` is never `main` — the safe-commit guard refuses planning commits to a
protected branch, correctly.

### The order is load-bearing, not a preference

```
A ──► B1 ──► B2 ──► C
└──► D  (independent of B1/B2; gates on A only)
```

- **A before B1** is **C-010**, non-negotiable. `extractor.py:133-145` (`_KIND_MAP`) and `:1210-1229`
  (the field-by-field writers) would silently delete a new edge field at extraction and
  regeneration. Land B1 first and `impacts` / `is_symmetric` ship inert behind green tests — this
  mission's own defect class, reproduced by its remediation.
- **A before everything** is **C-009**. The zero-producer lint (IC-01) is the only thing that
  mechanically prevents a fourth inert register; the precedent is 3-for-3, one green for 162 days.
- **B1 before B2** because the two shipped tension claims would otherwise be migrated twice — once
  as `in_tension_with`, again as `impacts`.
- **A before B1** also covers the bridge: ADR 2026-07-26-3 states the org→DRG bridge fix "must land
  before or with the `Relation.IMPACTS` migration, or the new relation inherits a silent-drop path".
- **C after B2** because C-001/C-002 require the new series to be authored edge-native with zero
  inline references, against a tree where the authored-edge tier already exists.
- **D gates on A only** — its increments need the guards, not the migration.

### Missions are specced just-in-time — operator guidance, 2026-07-26

> Do not over-specify or plan any mission after phase A. Run them one at a time, refreshing the spec
> and planning after each previous phase is finalized.

Only **mission A carries a full specification**. B1, B2, C and D carry a **scope sketch**: what the
mission is for, why it sits where it does, the measured surface to re-derive, and the carried
constraints that must not be lost — but no requirement tables, no success criteria, no plan.

This is not under-planning. Each mission changes the ground the next one stands on: A closes the
silent-drop sites and extends the occurrence-map schema, B1 changes the relation vocabulary the
migration writes, B2 creates the authored-edge tier that C must author against. A requirement set
written now would pin assumptions the previous phase is about to invalidate — the programme's own
defect class, reproduced in the programme's planning.

Nothing is lost by waiting, because **this document and [`spec.md`](spec.md) hold the findings**: the
measurements, the concern map, the traps, and the ordering rationale. Each mission is specced from
here, refreshed against the tree the previous phase actually produced.

### Why B split into B1 and B2

B1 is ADR 2026-07-26-3's delivery: self-contained, ~45–60 files, its own proof, no bulk edit. B2 is
one indivisible proof chain — committed baseline → author → structured diff → ablation → completion
gate — which must not be cut across missions. Keeping them together would have put ~450 files and
two unrelated concerns in the mission we split the programme to avoid.

## Project Structure

### Documentation (programme + children)

```
kitty-specs/
├── doctrine-canonical-structure-remediation-01KYEYSD/   # PROGRAMME RECORD — does not implement
│   ├── spec.md              # requirements + the split banner and routing table
│   ├── plan.md              # this file
│   ├── tasks.md             # no WPs — delegation record
│   └── research/inline-reference-inventory.md
├── doctrine-silence-guards-01KYFV7Q/                    # A
├── drg-relation-impacts-vocabulary-01KYFV87/            # B1
├── drg-edge-migration-extractor-retirement-01KYFV8C/    # B2
│   └── occurrence_map.yaml  # DIRECTIVE_035 guardrail (gate: green)
├── test-quality-doctrine-series-01KYFV8H/               # C
└── foundational-values-creed-band-01KYFV8N/             # D
```

`occurrence_map.yaml` lives with **B2**, the only mission that performs a bulk edit. Leaving it on
this mission would have been a guardrail with nothing to guard — inert by construction, which is the
failure mode NFR-013 exists to catch.

### Source Code (repository root)

```
src/doctrine/
├── <kind>s/built-in/[<category>/]*.yaml   # 169 artefact files carrying MIGRATE entries
├── <kind>.edges.yaml                      # NEW — authored source of truth (IC-10)
├── <kind>.graph.yaml                      # generated cache, 14 fragments, never hand-edited
├── drg/
│   ├── models.py                          # Relation, DRGNode, DRGEdge — gains IMPACTS,
│   │                                      #   is_symmetric, aliases, extra="forbid"
│   ├── merge.py · loader.py · query.py    # silent-drop sites; org→DRG bridge
│   └── migration/
│       ├── extractor.py                   # 1229 lines → node minter + validator
│       ├── hand_authored_overlay.py       # 17 edges / 6 nodes → DELETED
│       └── calibrator.py                  # synthesised scope edges → DELETED
├── schemas/                               # 7 stale; generator drops structural_lint_config
└── agent_profiles/built-in/*.agent.yaml   # 18 profiles; duplicated directive field

scripts/
├── doctrine/inline_reference_inventory.py # scope authority — gates import it
└── generate_schemas.py                    # --check exits 1 today

tests/architectural/                       # gates. NEVER run the full directory (C-007)
```

**Structure Decision**: single project, existing layout. The only new artefact class is the
`<kind>.edges.yaml` authored tier, co-located with the fragments it generates.

## Implementation Concern Map

> Concerns are **not** work packages, and this programme mission has none. Each child mission's
> `tasks.md` translates the concerns it owns into WPs.
>
> **Ownership:** IC-01…IC-07 → **A** · IC-08 → **B1** · IC-09…IC-13 → **B2** · IC-14 → **C**.
> Mission **D**'s concerns are specced in its own mission; the Phase 0 section above records which
> of its increments survived and which are closed.

### IC-01 — Inert-slot prevention

- **Purpose**: Make it structurally impossible for a schema slot to ship with no producer. Precedent is 3-for-3 inert in this repo, one green for 162 days.
- **Relevant requirements**: FR-029, C-009, SC-021
- **Affected surfaces**: new `tests/architectural/` lint module
- **Sequencing/depends-on**: none — **must be first**
- **Risks**: A lint that cannot see a producer in a fixture false-reds. Prove non-vacuity by planting a producerless slot and asserting RED, and by asserting GREEN on the shipped tree.

### IC-02 — Bulk-edit guardrail granularity

- **Purpose**: `occurrence-map.schema.yaml` classifies by path glob; this mission's exemptions are field-scoped, and all 17 GOVERNANCE files also carry MIGRATE entries. The guardrail cannot express its own mission.
- **Relevant requirements**: NFR-013, C-004
- **Affected surfaces**: `src/doctrine/schemas/occurrence-map.schema.yaml`, `src/specify_cli/bulk_edit/{occurrence_map,diff_check}.py`, template
- **Sequencing/depends-on**: none
- **Risks**: Backward compatibility — legacy single-term maps must keep validating (C-OMAP-1).

### IC-03 — Silent-drop closure across the kind and field boundaries

- **Purpose**: Four sites drop an unknown *kind* silently; the DRG models have no `model_config`, so they drop an unknown *field* silently, and the writers are field-by-field. Both must close **before** any new edge field exists, or `impacts` / `is_symmetric` / `aliases` ship inert and the tests stay green.
- **Relevant requirements**: FR-030, FR-031, SC-022, SC-023, C-010
- **Affected surfaces**: `query.py:230-242`, `charter/context.py:672-683` (missing `else`), `extractor.py:133-145` (`_KIND_MAP`), `extractor.py:1210-1229` (writers); `drg/models.py`; `agent_profiles/profile.py`
- **Sequencing/depends-on**: IC-01. **Blocks IC-08 and IC-11.**
- **Risks**: Collides with `#2532` (decompose `charter/context.py`) — pin the missing `else` **behaviourally**, not by code shape, so the decomposition cannot drop it. Model + writer + round-trip must land in **one commit** each.

### IC-04 — Schema generation integrity

- **Purpose**: `generate_schemas --check` exists, exits 1 today with 7 stale schemas, and is wired into nothing. Wiring it as-is puts a red gate on the branch and invites someone to "fix" it by accepting a regeneration that deletes valid schema.
- **Relevant requirements**: sequencing I3a (spec §"I3a is not a one-file campsite")
- **Affected surfaces**: `scripts/generate_schemas.py`, 7 `src/doctrine/schemas/*.yaml`, one workflow file
- **Sequencing/depends-on**: none
- **Risks**: Three divergence classes, only one safe. `structural_lint_config` is a **real model field the generator drops** — accepting its deletion invalidates a shipped artefact. `point_in_time_marker` is used by a shipped artefact and declared in no model — adjudicate, do not regenerate blindly.

### IC-05 — Structural ratchets

- **Purpose**: The layout gate validates 1 of 2 mandatory path segments, so a right-pack/wrong-type file passes. The reference-kind enum freeze is a comment, not a gate.
- **Relevant requirements**: FR-004, SC-016, SC-018, NFR-001
- **Affected surfaces**: `tests/architectural/test_doctrine_artefact_layout.py`, four `<kind>_reference.type` enums
- **Sequencing/depends-on**: none
- **Risks**: Allowlist must stay at exactly 0 entries.

### IC-06 — Followable guidance

- **Purpose**: The one hint pointing from the legacy surface to the canonical one names a file sharded out of existence; a `shipped/` pack layer documented in operator-facing guidance has never existed on disk.
- **Relevant requirements**: FR-005, FR-006, FR-020, SC-003, SC-015
- **Affected surfaces**: `InlineReferenceRejectedError` + ~10 sites; 22 `shipped/` hits across 9 files incl. two `SKILL.md` and a glossary term body
- **Sequencing/depends-on**: none
- **Risks**: **Both gates need discriminators.** The `graph.yaml` gate must not sweep `.kittify/doctrine/graph.yaml` (live project-tier) or the deliberate mentions that name the dead path in order to forbid it. The `shipped/` gate must not match the prose "shipped/packaged".

### IC-07 — org→DRG bridge integrity and relation hygiene

- **Purpose**: The bridge drops a built-in-source → pack-target edge with no warning and no conflict record, blindly re-kinds bare targets, and raises raw pydantic on URN-shaped ones. **Adding vocabulary to a leaking bridge is how a new relation inherits a silent-drop path.**
- **Relevant requirements**: FR-021, FR-022, FR-023, NFR-012
- **Affected surfaces**: `drg/merge.py`, `drg/org_pack_loader.py`, the `CLAUDE.md` `specializes_from` snippet, daphne's `applies` edge
- **Sequencing/depends-on**: IC-03. **Must precede IC-08** (ADR 2026-07-26-3, Negative consequences).
- **Risks**: `applies` is **not** a dead sink — the comment at `drg/merge.py:97-98` is wrong. `orphan.py` reads it and `project_drg.py` produces it. Do not build an "`applies` is dead" gate on that comment.

### IC-08 — Relation vocabulary evolution

- **Purpose**: `Relation.IMPACTS` (directed, signed, authored-only) replaces the `in_tension_with` boolean; `is_symmetric` is shorthand for the un-written inverse, **expanded by the generator, never in traversal**.
- **Relevant requirements**: FR-032, SC-024, ADR-D1…D6, ADR-D11
- **Affected surfaces**: 21 files reference `in_tension_with` (9 src + 12 test); **50 files touch the `Relation` vocabulary**; `consistency_check.py:917-1050` (1 dataclass + 5 functions); `RELATION_DESCRIPTIONS`
- **Sequencing/depends-on**: IC-03, IC-07. **The long pole.**
- **Risks**: Cache counts move 2 → 4 via expansion while the authored count stays 2 — every golden baseline needs a ledger entry on the **cache side only**. Expansion must be idempotent and `edges_from`/`edges_to` must stay purely structural, both asserted. `reconciles_tension` survives re-pointed.

### IC-09 — Migration proof infrastructure

- **Purpose**: Without a **committed** pre-migration baseline, "regenerate and compare" degenerates into `regenerate(tree) == regenerate(tree)` — a tautology of determinism, blind to content loss. Without in-process ablation, pass deletion cannot be proven at all.
- **Relevant requirements**: NFR-007, NFR-008, NFR-009, NFR-010, SC-010
- **Affected surfaces**: new SHA-256 per-fragment manifest; new ablation harness; NFR-010 governance before-snapshot
- **Sequencing/depends-on**: **must land before any artefact YAML is edited**
- **Risks**: NFR-002 needs the extractor alive as the migration oracle while NFR-009 needs it deleted — irreconcilable as a git sequence, hence **in-process** ablation over a tree copy. NFR-010 must assert at the **production** seams (`charter/context.py` closure + the two inline render paths), *not* at `resolve_governance_for_profile`, which has no production caller.

### IC-10 — Authored-edge tier: localized source, generated cache

- **Purpose**: `<kind>.edges.yaml` is the authored source of truth; the aggregate `*.graph.yaml` is a **generated cache** that declares itself in-band and whose freshness is enforced in CI. This inverts a vacuity trap: the five current canaries compare `extractor(tree) + overlay` against the fragments, which degenerates to `overlay == overlay` once 559 edges move into the overlay. Under cache semantics the check becomes `merge(authored) == cache` — a real coherence assertion that gets *stronger* as more edges become authored.
- **Relevant requirements**: FR-016, NFR-002, SC-006
- **Affected surfaces**: loader/merge, new authored tier, CI freshness job
- **Sequencing/depends-on**: IC-03
- **Risks**: Open question the operator flagged — whether the cache is committed at all. A committed cache means every rebase re-touches exactly the files whose state is the correctness proof.

### IC-11 — Inline surface excision

- **Purpose**: Move all 559 MIGRATE entries to authored edges across 169 files, leaving the 188 GOVERNANCE and 14 RAW entries untouched. Collapse the duplicated profile→directive field first; lift the 219 reference labels onto 102 artefacts as `aliases`.
- **Relevant requirements**: FR-013, FR-027, FR-028, FR-015, NFR-005, NFR-011, SC-009, SC-013
- **Affected surfaces**: 169 artefact files; 18 agent profiles; 102 artefacts gaining `aliases`
- **Sequencing/depends-on**: IC-03, IC-09, IC-10. FR-027 is a **prerequisite** to FR-013.
- **Risks**: **Relation inference keys on SOURCE kind, not ref type** — keying on ref type mis-types 118 of 372 structured entries. The overlay merge keys on `(source, target, relation)` and *overwrites*, so a half-done migration passes a diff invariant — completion must be asserted by the inventory gate, never by the diff alone. **Never sweep `directive-references`**: it produces zero edges but seeds the entire charter governance closure.

### IC-12 — Derived-edge absorption and extractor retirement

- **Purpose**: Author the remaining 215 structural edges, absorb and **delete** both Python edge registries, delete the calibrator, and retire every edge-producing pass. Node discovery stays derived; the extractor becomes a node minter plus validator.
- **Relevant requirements**: FR-014, FR-024, FR-025, FR-026, SC-011, NFR-006
- **Affected surfaces**: `extractor.py` (1229 lines), `hand_authored_overlay.py` (17 edges / 6 nodes), `_CURATED_ARTIFACT_EDGES` (13 edges, all four `specializes_from`), `calibrator.py`
- **Sequencing/depends-on**: IC-11
- **Risks**: Without registry deletion the surface count holds flat at 11 while the PR claims consolidation. `scope` (157) is the **seed of every context resolution** — leaving it derived leaves the load-bearing relation outside the authority. The calibrator's 21 synthesised edges are invented from a policy inequality and must be promoted with a ledger line each, not migrated anonymously.

### IC-13 — Authored-content preservation and human adjudication

- **Purpose**: 68 procedure rationales are already dropped by the extractor and 219 labels were never read. Preserving them breaks byte-identity **by design** — which is why the proof is a structured diff. 55 relations are inference artifacts that must not be laundered into declared intent.
- **Relevant requirements**: FR-017, FR-018, SC-013, SC-014
- **Affected surfaces**: deviation ledger; the 55 `tactic --suggests--> directive` relations
- **Sequencing/depends-on**: IC-11
- **Risks**: **The 55 need a human verdict, not an agent's.** A byte-identity proof would actively pressure the migrator into deleting authored content to pass.

### IC-14 — Doctrine content and curator capability

- **Purpose**: Author the test-quality series that surfaced this mission (the #2934 over-mocking failure becomes a citable rule), split `DIRECTIVE_041`'s intent to a paradigm, de-duplicate excised checklists into assets, pin the canonical structure into the curator profile, and close the CLI/CI validator parity gap.
- **Relevant requirements**: FR-003, FR-007, FR-008, FR-009, FR-010, FR-011, NFR-004, SC-004, SC-005, SC-007, SC-017, SC-019, SC-020
- **Affected surfaces**: new paradigm + `DIRECTIVE_047` + procedure + 2 anti-patterns + 4 assets; `doctrine-daphne.agent.yaml`; `spec-kitty doctrine validate`
- **Sequencing/depends-on**: IC-11 (C-001/C-002 constrain how it is authored — edge-native from birth, zero inline references)
- **Risks**: The `041 → paradigm` link is the **first `refines` edge in any built-in fragment** (histogram: 0). #2079 fixed a silent `refines`→`applies` downgrade that nothing shipped has ever exercised, so NFR-004's round-trip assertion is a real risk item, not a formality. Editing `041` is its own reviewed change (C-005) — do its migration *with* the intent split, not as an anonymous line in the bulk pass.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| C-003 replaced (3 PRs, not 1) | ~600 file touches; C2 forbids two all-surface sweeps sharing one occurrence map, and this scope has three | One PR is unreviewable — and C-003's named branch and PR are both already merged, so it had to be rewritten regardless |
| Guardrail schema change inside the mission (IC-02) | The guardrail cannot express its own mission's exemptions | Deferring it is what C-004 forbids: it converts a known defect into an invisible one |
| `Relation.IMPACTS` at ~45–60 files rather than option B's ~5–10 | Operator chose the clean end state knowingly (ADR-D2) | A relation named `in_tension_with` cannot honestly carry `impacts: +0.5` — half the range becomes unauthorable and the name lies about its contents |
| **D-3 answered "arithmetic"** | Operator ruling; unparks I10 | **Recorded risk, not an objection:** the design authority measured creed-weighted ranking collapsing to row-sum at r ≈ 0.98, and vector-derived precedence at **0 reproductions of 6** — worse than chance. I10 must not rebuild either mechanism. I8's perturbation probe (follow-on mission, ~20 lines) is the cheapest instrument that can falsify the arithmetic reading before it is built on. |

## Cost

| Mission | Agent-days | Files |
|---|---|---|
| A — doctrine silence guards | 4–6 | ~55–70 |
| B1 — relation `impacts` vocabulary | 3–5 | ~45–60 |
| B2 — edge migration & extractor retirement | 11–14 | ~365–390 |
| C — test-quality doctrine series | 3–5 | ~30–45 |
| D — creed band | 7–13 | ~60–100 |
| **Programme** | **28–43** | **~555–665** |

**Operator time: 18–28 hours**, down from 25–40 — D-1, D-5 and ADR-D8 are all settled, and the
upstream AMMERSE report is withdrawn rather than deferred. What remains: the charter deprioritisation
statement, the D-4 interview design, FR-018's 55 relations, the two occurrence-map category
contracts, and five draft-PR reviews.

The inherited 15-WP / 6–9 agent-day / 12–18h figure was priced for 559 edges and none of the
programme. This replaces it. Most of PR 2's file count is mechanical — the migration is
script-assisted with the extractor as oracle, which is why 185 files is ~4 days and not ~20.

## Session constraints (binding on every WP and every dispatched agent)

- **Never run the full `tests/architectural/` suite** (C-007) — known harness issue kills the
  session. Targeted single-file runs only.
- The 6 inherited `arch-adversarial` reds stay red (C-006). `quality-gate` fails only as their
  cascade. Do not greenwash; do not "fix" them.
- `unset GITHUB_TOKEN` before every `gh` call.
- **Run the whole docs gate set, not the one you remember** — two sibling generated lockfiles have
  separate generators, and fixing the description-length gate *caused* the retrieval-index gate to
  fail last session:

  ```bash
  PYTHONPATH=. python scripts/docs/description_length_check.py --strict --repo-root .
  PYTHONPATH=. python scripts/docs/freshen_adr_inventory.py --all
  PYTHONPATH=. python scripts/docs/docs_index.py --write
  PYTHONPATH=. python scripts/docs/check_docs_freshness.py
  npx --no-install markdownlint-cli2 "<changed .md files>"     # exit 1 = job FAILS
  PYTHONPATH=src python -m pytest tests/docs/ -q -p no:cacheprovider
  ```

  markdownlint is **not** advisory and CI lints changed files only — touching a file inherits its
  pre-existing lint debt. `check_docs_freshness` link-health findings are WARNINGS.
- `pytest tests/architectural/test_no_legacy_terminology.py` before pushing any `src/doctrine/` or
  prose change — it is a CI-only gate that local doctrine runs do not cover.
- **Derive, never hand-count.** Two hand-counted inventories were wrong. Use the inventory script.
