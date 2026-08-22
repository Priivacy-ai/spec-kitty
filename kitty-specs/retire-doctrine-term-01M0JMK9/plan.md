# Implementation Plan: Retire the Doctrine Term

**Branch**: `feat/retire-doctrine-term` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/retire-doctrine-term-01M0JMK9/spec.md`

**Note**: Filled by `/spec-kitty.plan`. Execution workflow: `packs/built-in/missions/mission-steps/software-dev/plan/prompt.md`.

## Summary

This is a **research-and-planning mission**: it produces four program artifacts and executes no rename (C-001).

1. **ADR** in `docs/adr/3.x/` recording the retirement of "doctrine" from user-facing language in favor of "charter", with the three-way distinction (**charter bundle** / **active charter** / **inactive charter**), surviving kind vocabulary, scope boundary (internal identifiers out; operator-typed identifiers explicitly classified), and the 3.x-deprecate / 4.0-gone compatibility policy (FR-001..FR-005, FR-011 decisions). It amends the terminology portion of ADR `2026-07-15-1` (status → `Superseded` + pointer; body byte-for-byte untouched per C-003 carve-out) and reconciles with ADR `2026-07-18-1` (bundle authority).
2. **Occurrence inventory** (`inventory.md`) — a mechanical, case-insensitive audit over all tracked files with every hit classified into stable occurrence classes (OC-##): in-scope surface / internal identifier / legacy-marked historical artifact (FR-006, FR-007, NFR-001).
3. **Methodology analysis** (`methodology.md`) — surface ordering with per-choice rationale, the invariant that must hold at each stack level, the terminology-guard arming design (file-level frozen baseline, shrink-only ratchet, self-mutation test), per-surface verification mechanisms for classes outside the guard's scan roots, and catfooding conflict management (FR-008, C-004).
4. **Stacked mission plan** (`stacked-plan.md`) — the operator-approved shape (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`): **5 active missions + 1 deferred to 4.0**, each with slug, purpose, inputs/outputs, dependencies, and the occurrence classes it retires; every OC-## assigned to exactly one mission or explicitly deferred (FR-009, FR-010, NFR-003).

**Technical approach**: authority-first sequencing with an **atomic authority flip**. The sharpest planning hazard (found in the plan-phase catfooding analysis, C1 below) is that arming the terminology guard *before* the replacement vocabulary is canonical would trap concurrent spec-kitty missions between a forbidden old word and uncanonical new terms (DIRECTIVE_048). The fix: the glossary rewrite, the charter-bundle update, and the guard arming land in **one mission / one PR** (stack M1). Before that PR: status quo, zero friction. After: new vocabulary canonical *and* guard armed with a frozen baseline — no conflict window.

**Stacked shape (operator-approved 2026-08-21):**

| # | Mission (proposed slug) | Retires |
|---|---|---|
| M1 | `charter-authority-flip` — glossary rewrite (FR-011) + charter-bundle update via `charter.yaml` + regeneration (+ Terminology Canon line) + guard arming (last WP, single PR) | docs-glossary, charter-bundle classes; arms the ratchet for all later waves |
| M2 | `charter-cli-surface` — `spec-kitty doctrine` group (8 subcommands) + `doctor doctrine` → canonical names, hidden aliases + deprecation warnings, per-subcommand alias tests, **same-wave CI consumer updates** | CLI-executable + scripted-consumer classes |
| M3 | `charter-packs-source` — user-facing strings/titles in `packs/built-in/` (canonical source of all agent copies) | packs-source classes |
| M4 | `charter-skills-artifacts` — `spk-doctrine-*` → new names + legacy alias skills during the window (old→new map recorded in M4's artifacts); agent dirs via migration/upgrade flow | prompts-skills-agent-artifact classes (source: `src/doctrine/skills/`) |
| M5 | `charter-docs-prose` — `docs/` prose + root-level `AGENTS.md`; ADR titles stay legacy (C-003) | docs-prose + root-docs classes |
| M6 *(deferred to 4.0)* | `charter-removal-audit` — strip aliases, run the NFR-001 zero-doctrine audit | residual alias classes; verifies the 4.0 hard rule |

## Technical Context

**Language/Version**: Markdown (all four deliverables + planning artifacts); Python 3.11+ **only via existing tooling** — `git grep` for the mechanical audit and `python -m scripts.docs.freshen_adr_inventory` for ADR index registration. No new code is written by this mission (C-001).
**Primary Dependencies**: None. No dependency is added, upgraded, or removed — the supply-chain planning section of the plan step prompt is therefore N/A (documented, not silent).
**Storage**: N/A — tracked files only; no databases or state stores touched.
**Testing**: No new tests. Targeted verification surface: `tests/architectural/test_no_legacy_terminology.py` (must stay green — this mission adds no user-facing "doctrine" to `src/`, `tests/`, or scanned `docs/`; the new ADR lives under `docs/adr/3.x/`, which is guard-exempt as historical-snapshot path) plus the `docs-freshness` gate (ADR index + page-inventory lockfile, enforced by the freshen script).
**Target Platform**: N/A — repository documentation and decision records.
**Project Type**: single — docs-only deliverables; no source-structure change.
**Performance Goals**: N/A (planning artifacts only).
**Constraints**: C-001..C-005 from the spec, plus charter constraints: PRs only / operator merges; ADR conventions (C-002); no version numbers in scope — the 3.x/4.0 references are the *content* of the compatibility decision (FR-005), not implementation pins.
**Scale/Scope**: 4 deliverables + planning artifacts; the inventory covers ~9 surface classes across all tracked files (evidence: 429 `src/` files, 731 `tests/`, 430 `docs/`, 103 `packs/`, 51 `.kittify/` files contain the term case-insensitively at this base; `kitty-specs/` legacy missions are retain-as-legacy by definition).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — no new gaps.*

| Charter rule | Status | Note |
|---|---|---|
| Single canonical authority | PASS (by design) | The ADR is the one new vocabulary authority; it amends `2026-07-15-1` (terminology portion) and reconciles with `2026-07-18-1` (bundle authority). No second authority is introduced; the glossary rewrite (M1) derives from it. |
| Architectural alignment | PASS | No code changes; deliverables land in canonical homes (`docs/adr/3.x/`, mission directory). |
| DDD + tiered rigour | PASS | Occurrence class / stacked mission modeled as entities with invariants (`data-model.md`); rigour concentrated on the ADR content contract and the audit procedure, not on glue. |
| ATDD-first (adapted for docs) | PASS | Each FR maps to a verifiable acceptance procedure (`quickstart.md`). Red-first analog: the inventory WP runs the mechanical audit **before** classifying and records raw hits — evidence before conclusion. |
| Glossary & terminology adherence | PASS (with note) | This mission's own artifacts quote the retired term as *subject matter*; they live in `kitty-specs/` (guard-excluded) and become legacy-marked snapshots at merge (C-003). No new user-facing "doctrine" is introduced into `src/`, `tests/`, or scanned `docs/`. |
| Standing order #1 — adversarial squad cadence | SCHEDULED | Post-spec squad ran (`squad-findings-post-spec.md`, all findings folded). **Post-plan squad runs after this plan commits** (advisory, never a gate). |
| Standing order #5 — non-vacuous gates | PASS (by design) | The guard-arming design in `methodology.md` must carry a concrete floor + self-mutation test + shrink-only allowlist; the plan pins that requirement on IC-03. |
| Standing order #6 — canonical sources | PASS | ADR template (`docs/architecture/adr-template.md`), freshen script, guard test — all used canonically; no improvised substitutes. |
| No version numbers in scope (Specify/Plan) | PASS (with note) | 3.x/4.0 appear only as the recorded compatibility decision (FR-005), per the operator's resolved decision moment `specify.compatibility.alias-policy`. |
| Branch-intent terminology | PASS | "repository root checkout" used; branch names stated explicitly (`feat/retire-doctrine-term`). |

## Project Structure

### Documentation (this mission)

```
kitty-specs/retire-doctrine-term-01M0JMK9/
├── plan.md              # This file (/spec-kitty.plan output)
├── research.md          # Phase 0 output — resolved unknowns (Decision/Rationale/Alternatives)
├── data-model.md        # Phase 1 output — occurrence class, surface taxonomy, stacked mission entities
├── contracts/           # Phase 1 output — artifact schemas this mission commits to
│   ├── README.md        # Index + consumers of each contract
│   ├── adr-content-contract.md    # What the ADR must state (FR-001..FR-005, FR-011 decisions)
│   ├── inventory-schema.md        # Format of inventory.md (frontmatter + class table + audit procedure)
│   └── stacked-plan-schema.md     # Format of stacked-plan.md (per-mission fields + assignment table)
├── quickstart.md        # Phase 1 output — verification runbook (SC-001..SC-004 + guard green)
├── inventory.md         # DELIVERABLE — created at implementation (IC-02)
├── methodology.md       # DELIVERABLE — created at implementation (IC-03)
├── stacked-plan.md      # DELIVERABLE — created at implementation (IC-04)
└── squad-findings-post-plan.md  # Post-plan adversarial squad output (advisory)
```

### Repository surfaces touched by the deliverables (no `src/` changes — C-001)

```
docs/adr/3.x/
├── 2026-08-21-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md   # NEW ADR (IC-01; N = next free number, verify at creation — latest is 2026-08-20-1)
├── index.md                                                        # + table row via freshen script
└── 2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md  # status frontmatter ONLY → Superseded + pointer (C-003 carve-out)
docs/development/3-2-page-inventory.yaml                            # regenerated by freshen script (lockfile)
```

**Structure Decision**: docs-only, single stream. Deliverables live in the mission directory (planning-artifact convention; NFR-001's "named inventory artifact"); the ADR lives in `docs/adr/3.x/` per C-002. No source tree, test tree, or agent-directory changes in this mission.

## Complexity Tracking

No Charter Check violations — section not applicable.

## Implementation Concern Map

> Concerns are NOT work packages; `/spec-kitty.tasks` translates them into WPs.

### IC-01 — ADR authoring and registration

- **Purpose**: Record the terminology decision as the single canonical authority so no downstream mission re-litigates vocabulary.
- **Relevant requirements**: FR-001..FR-005, FR-011 (decisions the ADR must fix), NFR-002, C-002, C-003.
- **Affected surfaces**: `docs/adr/3.x/` (new ADR + index row), `docs/development/3-2-page-inventory.yaml` (lockfile via freshen script), `docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (status frontmatter only).
- **Sequencing/depends-on**: none — first concern; everything else cites the ADR.
- **Risks**: (a) Self-sufficiency (NFR-002/SC-001) — the ADR must let a reviewer with no other context state all six items (US1-AS3); the content contract (`contracts/adr-content-contract.md`) is the checklist. (b) The **operator-typed identifier classification** (profile IDs like `doctrine-daphne`, directive IDs, skill names) is recorded by the ADR as an explicit split (spec edge case: not left to downstream missions): **skill names in scope with aliases** — resolved decision moment `specify.compatibility.alias-policy` covers skill names (3.x hidden aliases + warnings; removed by 4.0) and the operator-approved shape gives M4 = skills/agent artifacts with legacy alias skills; **profile IDs and directive IDs out of scope as a named exception** (stable DRG node identifiers, analogous to `mission_id`; the prose around them is renamed). M3/M4 scope follows this classification. (c) The ADR must specify the **charter-bundle Terminology Canon line content** so M1 executes rather than re-decides. (d) Amending a `Proposed` ADR: status → `Superseded` + pointer, body byte-for-byte untouched (US1-AS2; C-003 carve-out).

### IC-02 — Occurrence inventory (mechanical audit)

- **Purpose**: Produce the evidence-based work list for the whole program, with stable class identifiers trackable from inventory → mission → completion.
- **Relevant requirements**: FR-006, FR-007, NFR-001, SC-002.
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md` (new artifact; schema in `contracts/inventory-schema.md`).
- **Sequencing/depends-on**: IC-01 (classification rules cite the ADR's scope decisions, especially operator-typed identifiers).
- **Risks**: (a) Completeness circularity — pinned by NFR-001's mechanical procedure: audit **first** (case-insensitive `git grep` over all tracked files excluding `.git`, worktrees, vendor dirs), classify **every** hit, record in the named artifact; 0 unclassified is the pass condition. (b) **String-level, not path-level, scope rule** for `src/`: user-facing strings (help text, errors, emitted output) are in scope; identifiers are out — including the nuance that user-facing *artifacts* live inside `src/doctrine/` (skills at `src/doctrine/skills/`, glossary-pack data at `src/doctrine/glossary_packs/built-in/` — the latter already guard-exempt as quoted data). (c) Canonical-source verification per artifact kind: `packs/built-in/` is the canonical YAML source (hatch build ships it to site-packages); `src/doctrine/<kind>/` is Python code (identifiers out of scope).

### IC-03 — Ordering and methodology analysis

- **Purpose**: State *in what order and why*, with the invariant that must hold at each stack level, so the program never breaks user-facing coherence mid-flight.
- **Relevant requirements**: FR-008, C-004, SC-003 (ordering half).
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md` (new artifact).
- **Sequencing/depends-on**: IC-02 (ordering rationale cites inventory evidence).
- **Risks / required content**: (a) **Guard arming design** — the guard today has no exemption mechanism for active surfaces (only path-fragment exclusions for legacy/vendor paths); wave design must add a **file-level frozen baseline** (shrink-only ratchet + self-mutation test, per Standing Order #5) and state the known blind spot (count growth inside baseline files is invisible to the guard; per-wave NFR-001 re-baselining catches it). (b) **Per-surface verification assignment** for classes outside the guard's scan roots (`packs/`, `.kittify/charter/`, root docs, `.github/`) — C-004 requires exactly one named mechanism per class (the NFR-001 audit procedure). (c) **Catfooding conflict management** — the C1–C6 analysis from plan-phase (see `research.md` R8): atomic authority flip, per-level invariants I0–I6, re-baselining per wave, same-wave CI consumer updates. (d) Alias introduction/removal verification: hidden + warning in 3.x, per-subcommand alias tests (string-fragment construction to avoid self-flagging the guard), 4.0 removal verified by audit not assumption.

### IC-04 — Stacked mission plan

- **Purpose**: Express the retirement as executable spec-kitty missions with explicit dependencies, so execution proceeds mission by mission without re-deciding anything.
- **Relevant requirements**: FR-009, FR-010, NFR-003, SC-003/SC-004.
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md` (new artifact; schema in `contracts/stacked-plan-schema.md`).
- **Sequencing/depends-on**: IC-03 (stack follows the methodology ordering).
- **Risks / required content**: (a) Shape is operator-approved (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`): 5 active + 1 deferred — do not re-litigate granularity. (b) **FR-010 is the sharp edge**: M1 (`charter-authority-flip`) must be spec-ready from this mission's artifacts alone — its inputs (ADR, glossary gap list FR-011, bundle topology, guard design) must all be fully determined here. (c) Every rename wave is a **`change_mode: bulk_edit` mission** with its own scoped `occurrence_map.yaml` (8 standard categories) — a methodology requirement recorded per mission. (d) Every OC-## assigned to exactly one mission or explicitly deferred with rationale (SC-003).

### IC-05 — Verification and closeout

- **Purpose**: Prove the four success criteria with live evidence before merge.
- **Relevant requirements**: SC-001..SC-004, NFR-001..NFR-003.
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/quickstart.md` (runbook) + review evidence in the PR.
- **Sequencing/depends-on**: IC-01..IC-04 (runs last).
- **Risks / required content**: ADR self-sufficiency pass with a **named independent reviewer** (SC-001: post-implement squad lens + operator at PR review); mechanical audit re-run against the merged base (SC-002); stacked-plan completeness check — every OC-## appears exactly once in the assignment table or as a deferral with rationale (SC-003); first-mission spec-readiness dry run — attempt to specify M1 from artifacts alone, 0 new decisions (SC-004); guard green (`pytest tests/architectural/test_no_legacy_terminology.py`).

## Parallel Work Analysis

Single stream — no parallel work. The deliverables are sequentially dependent (ADR → inventory → methodology → stacked plan), and this mission is docs-only; there are no independent file sets to split across agents.
