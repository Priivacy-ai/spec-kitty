# Mission Specification: Retire the Doctrine Term

**Mission Branch**: `feat/retire-doctrine-term` (coordination branch: `kitty/mission-retire-doctrine-term-01M0JMK9`)
**Created**: 2026-08-21
**Status**: Draft
**Input**: User description: "this is a research and planning mission. We've decided to retire the word Doctrine from Spec Kitty, and this mission is meant to 1) identify all of the work to be done 2) reason about the order and methodology in which to do it 3) Make a plan in terms of stacked spec-kitty missions to get the job done. First we should create an ADR, though, in proper spec-kitty style, with the decision that Doctrine is not the word we use. Instead we'll be calling everything Charter, and specifying between the charter.md file, active charter (formerly doctrine that is wired in) and inactive charter."

Discovery decisions (resolved via decision moments, all `resolved`):
- **Scope** (`specify.scope.internal-identifiers`): user/operator-facing language only; internal code identifiers are out of scope.
- **Vocabulary** (`specify.vocabulary.kind-vocabulary`): "charter" is the umbrella for the layer and its activation state (three-way distinction); the kind vocabulary survives.
- **Compatibility** (`specify.compatibility.alias-policy`): deprecate in 3.x (hidden aliases + warnings); by 4.0, zero user-visible "doctrine" — hard rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The decision is recorded as an ADR (Priority: P1)

The operator wants the terminology decision captured in a proper spec-kitty-style ADR under `docs/adr/3.x/`, so that every downstream mission and reviewer has a single canonical authority for the new vocabulary instead of relying on chat history or memory.

**Why this priority**: Without a decision record, every downstream mission re-litigates the vocabulary and drift is guaranteed. The ADR is the root of the stack — nothing else in this mission's output is authoritative without it.

**Independent Test**: Can be fully tested by reading the merged ADR and asking a reviewer who has seen nothing else to state: what "charter" names, the three-way distinction, which terms survive, what is out of scope, and the compatibility policy. If all five are stated correctly from the ADR alone, the story is delivered.

**Acceptance Scenarios**:

1. **Given** the confirmed decision (retire "doctrine" in user-facing language; "charter" is the umbrella with a three-way distinction; kinds survive; internal identifiers out of scope; 3.x deprecation / gone by 4.0), **When** the ADR is authored, **Then** it follows the shared ADR template (`docs/architecture/adr-template.md`), uses dated naming `YYYY-MM-DD-N-descriptive-title-with-dashes.md`, and is registered in the 3.x index via `python -m scripts.docs.freshen_adr_inventory`.
2. **Given** the existing ADR `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`, **When** the new ADR is reviewed, **Then** it explicitly amends or supersedes the terminology portion of that ADR while leaving its resolution mechanics intact, and the old ADR's frontmatter `status:` is updated to `Superseded` with a pointer to the new ADR. (The 3.x index carries no status column — `Date | Title` only; the repo convention is frontmatter status, per the five existing `Superseded` ADRs. The old ADR is currently `status: Proposed`; status frontmatter is exempt from C-003 immutability — its wording stays byte-for-byte untouched.)
3. **Given** the new ADR, **When** a reviewer reads it without other context, **Then** they can state unambiguously: (a) what "charter" names, (b) the three-way distinction (charter bundle / active charter / inactive charter), (c) which terms survive, (d) the scope boundary (internal identifiers untouched), and (e) the compatibility policy.

---

### User Story 2 - Complete inventory of user-facing occurrences (Priority: P1)

The operator wants a complete, surface-by-surface inventory of every user-visible occurrence of "doctrine", so that downstream missions are scoped from evidence rather than guesswork, and completion can be verified by audit.

**Why this priority**: The inventory is the work list for the entire program. An incomplete inventory means un-retired occurrences survive to 4.0, violating the hard rule. It is as load-bearing as the ADR.

**Independent Test**: Can be fully tested by running a case-insensitive search for "doctrine" across the user-facing surface categories, classifying every hit against the inventory, and confirming zero unclassified hits in in-scope surfaces (internal identifiers and legacy-marked historical artifacts are excluded by definition).

**Acceptance Scenarios**:

1. **Given** the repository at this mission's base, **When** the inventory is produced, **Then** every user-facing surface category — CLI help text/errors/command names/flags, documentation (including the glossary page `docs/context/doctrine.md`), prompts/skills/agent artifacts, the charter file itself, and generated output (e.g. `charter context` output) — has an occurrence count and representative examples.
2. **Given** the inventory, **When** a downstream mission is scoped from it, **Then** each occurrence class has a stable identifier that can be tracked from inventory to mission to completion, and no surface category is missing.
3. **Given** internal code identifiers (`src/doctrine/` package, module names, import paths) and historical artifacts (old ADRs, archived missions), **When** the inventory is reviewed, **Then** they are explicitly classified as out-of-scope or retain-as-legacy — not counted as work.

---

### User Story 3 - Ordering and methodology analysis (Priority: P2)

The operator wants a reasoned ordering and methodology for the retirement, so that stacked missions can be executed without breaking user-facing coherence mid-program (e.g. docs referencing terms the glossary has not yet defined, or a terminology guard that fails between waves).

**Why this priority**: The inventory says *what*; the methodology says *in what order and why*. Without it, the stack is a bag of missions that can be executed in an order that breaks invariants.

**Independent Test**: Can be fully tested by having a reviewer challenge each ordering choice and confirming every one has a stated rationale tied to a concrete risk (glossary authority, terminology guard, upgrade migrations, agent skill routing), plus an explicit statement of the invariant that must hold at each stack level.

**Acceptance Scenarios**:

1. **Given** the inventory, **When** the methodology is written, **Then** it explains why surfaces are ordered as they are (e.g. ADR + glossary first as canonical authority, then executable CLI surfaces with aliases, then prose/docs/prompts) and states the invariant that must hold at each stack level.
2. **Given** the 3.x deprecation policy, **When** the methodology is reviewed, **Then** it specifies how aliases are introduced (hidden + warning), what verifies they work, and exactly when/how removal at 4.0 is verified (zero user-visible "doctrine" audit).
3. **Given** the terminology guard (`tests/architectural/test_no_legacy_terminology.py`), **When** a wave lands, **Then** the methodology states how the guard is updated so it stays green at every stack level — including wave 0, which adds "doctrine" to the guard's forbidden terms with all in-scope surfaces exempted (the guard currently forbids only "ceremony" and "status-writing"), followed by shrink-only removal of exemptions as each wave lands.

---

### User Story 4 - Stacked mission plan (Priority: P2)

The operator wants the retirement expressed as a stack of spec-kitty missions with explicit dependencies, so that each can be specified, planned, and implemented independently in order without re-deciding anything this mission decided.

**Why this priority**: The stack is the executable form of the plan — it is what the operator actually runs. It depends on Stories 1–3 (ADR authority, inventory work list, ordering rationale), hence P2.

**Independent Test**: Can be fully tested by taking the first mission in the stack and attempting to specify it using only this mission's artifacts as input — if no new decision is required, the story is delivered.

**Acceptance Scenarios**:

1. **Given** the methodology, **When** the stacked plan is written, **Then** it names each downstream mission (slug + purpose), its inputs and outputs, its dependencies on prior missions in the stack, and which inventory occurrence classes it retires.
2. **Given** the stacked plan, **When** every inventory occurrence class is checked against it, **Then** each class is assigned to exactly one mission in the stack or explicitly deferred with a rationale.
3. **Given** the first mission in the stack, **When** its specification is started from this mission's artifacts alone, **Then** no further decision from the operator is required.

---

### Edge Cases

- **`src/charter/` already exists as a package.** The ADR must disambiguate "charter" the term from `src/charter/` the code surface, and the inventory must not conflate occurrences of the word in that package's user-facing strings with the doctrine layer.
- **Historical artifacts are immutable.** Old ADRs and archived `kitty-specs/` missions retain legacy wording as immutable snapshots, explicitly marked legacy — the inventory classifies them as retain-as-legacy, never rename targets.
- **The glossary page is both target and authority.** `docs/context/doctrine.md` is the canonical terminology authority *and* a rename target; its rewrite must precede any prose wave that depends on the new terms, or waves will cite undefined vocabulary.
- **The charter bundle is doctrine-laden and load-bearing.** The project's charter is a *bundle* of files under `.kittify/charter/` — `charter.yaml` (the authoritative structured source per ADR 2026-07-18-1; ~53 doctrine occurrences) plus `charter.md` (curated companion; ~13), `graph.yml`, and synthesis sidecars. Updates must target `charter.yaml` (the source) and regenerate — hand-editing `charter.md` breaks on the next sync. Updating the bundle must not break context resolution or the compiled reference set (Charter Resolution Hints block).
- **Terminology guard between waves.** `tests/architectural/test_no_legacy_terminology.py` enforces the canon; if a wave retires a term before its replacement is canonical in the glossary, the guard or the docs go red. The methodology must sequence so the guard is updated shrink-only at each wave boundary and stays green throughout.
- **Deprecation aliases must actually work.** Old executable names — the top-level `spec-kitty doctrine` command group (9 subcommands: fetch, regenerate-graph, new, validate, pack, org, mission-type, asset) and `spec-kitty doctor doctrine` — must keep functioning with a deprecation warning during the 3.x window; the plan must define how alias behavior is tested (per subcommand) and how removal at 4.0 is verified (audit, not assumption).
- **Agent skill routing.** Renaming `spk-doctrine-*` skills changes agent-facing identifiers; harnesses that route on skill names need the old→new map, and legacy alias skills (repo precedent: `ad-hoc-profile-load`) may be required during the window.
- **Operator-typed identifiers are a distinct class.** DRG node IDs that operators type or agents route on — profile IDs (`doctrine-daphne`), directive IDs (`018-doctrine-versioning-requirement`), skill names (`spk-doctrine-*`) — are user-facing language, not internal code identifiers. The ADR must classify this class explicitly (in scope with aliases, or out of scope as a named exception); the inventory must not leave it to downstream missions.
- **"Pack" and "bundle" are different things, and the glossary only defines one of them.** A *pack* (Doctrine Pack) is a versioned, distributable catalogue of governance artefacts — the offer side (what pack-composer composes; `packs/built-in/`, org packs, `.kittify/doctrine/`). A *bundle* (charter bundle) is the per-project, sync-materialized file set under `.kittify/charter/` — the consume side (`CharterBundleManifest v2.0.0`, `spec-kitty charter bundle validate`). The glossary defines "Doctrine Pack" but has no term entry for "Charter Bundle", and the pack definition itself uses "bundle" as a generic word. The glossary rewrite must add a canonical "Charter Bundle" entry and disambiguate it from packs and the other code senses of "bundle" (action-doctrine bundle, prompt bundles, tool-surface bundles).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | ADR records the terminology decision | As an operator, I want a spec-kitty-style ADR in `docs/adr/3.x/` recording the retirement of "doctrine" in favor of "charter", so that downstream work has a single canonical authority. | High | Open |
| FR-002 | Three-way distinction defined | As an operator, I want the ADR to define *charter bundle* (the per-project file set under `.kittify/charter/`, with `charter.yaml` as authoritative source per ADR 2026-07-18-1), *active charter* (wired in), and *inactive charter* as distinct canonical concepts, so that the vocabulary is unambiguous. | High | Open |
| FR-003 | Kind vocabulary preserved | As an operator, I want the ADR to state that `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, and `procedure` remain canonical kind terms, so that CLI cascade syntax and DRG edge vocabulary are undisturbed. | High | Open |
| FR-004 | Scope boundary recorded | As an operator, I want the ADR to record that internal code identifiers (`src/doctrine/` package, module names, import paths) are out of scope for the retirement — and to classify operator-typed identifiers (DRG node IDs: profile/directive/skill names) explicitly, since they are user-facing language — so that downstream missions do not expand or split scope. | High | Open |
| FR-005 | Compatibility policy recorded | As an operator, I want the ADR to record 3.x deprecation (hidden aliases + warnings) and the hard rule that zero user-visible "doctrine" remains by 4.0, so that the upgrade path is explicit and verifiable. | High | Open |
| FR-006 | Complete user-facing occurrence inventory | As an operator, I want a surface-by-surface inventory of every user-visible "doctrine" occurrence (CLI surfaces, docs/glossary, prompts/skills/agent artifacts, charter file, generated output), so that downstream missions are scoped from evidence. | High | Open |
| FR-007 | Out-of-scope classification in inventory | As an operator, I want the inventory to explicitly classify internal identifiers and historical artifacts as out-of-scope or retain-as-legacy, so that the work list is not inflated and completion audits are well-defined. | Medium | Open |
| FR-008 | Ordering and methodology analysis | As an operator, I want a reasoned ordering and methodology (why this surface order; the invariant that must hold at each stack level), so that the program does not break user-facing coherence mid-flight. | High | Open |
| FR-009 | Stacked mission plan | As an operator, I want the retirement expressed as a stack of spec-kitty missions with dependencies, inputs/outputs, and the inventory occurrence classes each retires, so that execution proceeds mission by mission. | High | Open |
| FR-010 | First stack mission is spec-ready | As an operator, I want the first downstream mission in the stack to be fully determined by this mission's outputs (no further decisions needed), so that execution can start immediately. | Medium | Open |
| FR-011 | Glossary gap closure for the new vocabulary | As an operator, I want the glossary rewrite to add a canonical "Charter Bundle" term entry (currently undefined in `docs/context/`), disambiguate it from "Doctrine Pack" and the other code senses of "bundle", fix the "Doctrine Pack" definition's use of "bundle" as a generic word, and define what replaces the existing "Doctrine Domain" glossary sense — so that downstream waves cite defined vocabulary. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Inventory completeness | 100% of user-facing surface categories are enumerated with occurrence counts; a mechanical audit — case-insensitive search over all tracked files (excluding `.git`, worktrees, vendor dirs) with every hit classified as in-scope surface / internal identifier / legacy-marked historical artifact, recorded in a named inventory artifact — finds 0 unclassified "doctrine" occurrences. | Completeness | High | Open |
| NFR-002 | ADR self-sufficiency | 1 reviewer with no other context can state the new vocabulary, scope boundary, and compatibility policy from the ADR alone (verified by an independent review pass). | Quality | High | Open |
| NFR-003 | Plan determinism | 100% of downstream missions in the stack have named dependencies and inputs/outputs; 0 missions depend on an undecided item. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No rename execution in this mission | This mission produces planning artifacts only (ADR, inventory, methodology, stacked plan); it does not rename any user-facing surface. | Scope | High | Open |
| C-002 | ADR conventions | The ADR follows the shared template (`docs/architecture/adr-template.md`), dated naming `YYYY-MM-DD-N-<slug>.md` under `docs/adr/3.x/`, and is registered via `python -m scripts.docs.freshen_adr_inventory`. | Process | High | Open |
| C-003 | Historical artifacts immutable | Old ADRs and archived missions retain legacy wording as immutable snapshots, explicitly marked legacy; they are not rename targets. Status frontmatter (`status:`) is exempt: an ADR whose decision is amended may have its status updated (e.g. to `Superseded` with a pointer) without that counting as a wording change. | Scope | High | Open |
| C-004 | Terminology guard integrity | Downstream waves keep `tests/architectural/test_no_legacy_terminology.py` green at every stack level. Wave 0 adds "doctrine" to the guard's forbidden terms with all in-scope surfaces exempted (the guard currently forbids only "ceremony" and "status-writing"); each subsequent wave removes exemptions shrink-only. Because the guard's scan roots (`src`, `tests`, `docs`) do not cover all in-scope surfaces, the methodology assigns each surface class outside those roots (`packs/`, `.kittify/charter/`, root-level docs) to exactly one named verification mechanism. | Technical | High | Open |
| C-005 | Internal identifiers untouched | The `src/doctrine/` package, module names, and import paths are not modified by any mission in the stack (scope decision A). | Scope | High | Open |

### Key Entities *(include if feature involves data)*

- **Charter (term)**: The umbrella term for the governance artefact layer and its activation state; replaces "doctrine" in user-facing language. One of three canonical senses (see below).
- **Charter bundle**: The per-project, sync-materialized file set under `.kittify/charter/` — `charter.yaml` (authoritative structured source per ADR 2026-07-18-1) plus `charter.md` (curated companion), `graph.yml`, and synthesis sidecars; the first canonical sense of "charter". Distinct from a *pack* (a distributable artefact catalogue — the offer side); see Edge Cases.
- **Active charter**: A governance artefact wired in (activated) for the project — formerly "activated doctrine"; the second canonical sense.
- **Inactive charter**: A governance artefact present in a pack but not activated for the project; the third canonical sense.
- **Charter kind**: The surviving artefact-kind vocabulary (`directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`); orthogonal to the three senses.
- **Occurrence class**: A stable identifier for a group of user-facing "doctrine" occurrences sharing a surface and rename treatment; the tracking unit from inventory → mission → completion.
- **Stacked mission**: A downstream spec-kitty mission in the retirement program with explicit dependencies on prior missions in the stack.

## Domain Language *(optional — included: terminology is the subject of this mission)*

| Term | Canonical meaning | Do NOT use (synonyms to avoid) |
|------|-------------------|-------------------------------|
| **Charter** (umbrella) | The governance artefact layer and its activation state, in user-facing language. | "doctrine" (retired from user-facing language by this program) |
| **Charter bundle** | The per-project file set under `.kittify/charter/` (`charter.yaml` authoritative + `charter.md` companion). | "the charter" when the activation state is meant; "constitution" (legacy, pre-063); "charter pack" (collides with the canonical *Doctrine Pack* term — a distributable catalogue, not project files) |
| **Charter (CLI/directory senses)** | The `spec-kitty charter` command group and the `.kittify/charter/` directory — pre-existing senses covered by the umbrella, not additional canonical concepts. | Treating them as separate terms in new prose |
| **Active charter** | A wired-in (activated) governance artefact. | "activated doctrine", "wired-in doctrine" |
| **Inactive charter** | An un-activated governance artefact available in a pack. | "inactive doctrine", "dormant doctrine" |
| **Charter kind** | `directive` / `tactic` / `styleguide` / `toolguide` / `paradigm` / `procedure` — canonical, unchanged. | Collapsing kinds into bare "charter" (loses the precision cascade syntax depends on) |
| **Doctrine** (legacy) | Retired in user-facing language; permitted only in legacy-marked historical artifacts and internal code identifiers (out of scope for this program). | Using it in any new user-facing surface after the ADR lands |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The ADR is merged and registered in the 3.x index; an independent reviewer (a squad lens or the operator — named in the plan) states the three-way distinction, surviving kinds, scope boundary, and compatibility policy correctly from the ADR alone (1/1 review pass).
- **SC-002**: The inventory covers 100% of user-facing surface categories with occurrence counts and stable class identifiers; the mechanical audit defined in NFR-001 finds 0 unclassified user-facing occurrences.
- **SC-003**: The stacked plan names every downstream mission with dependencies and inputs/outputs; 100% of inventory occurrence classes are assigned to exactly one mission in the stack or explicitly deferred with a rationale.
- **SC-004**: The first mission in the stack can be specified from this mission's artifacts alone, with 0 new operator decisions required.

## Assumptions

1. **4.0 is a real, planned milestone** at which the hard-removal rule takes effect — consistent with the existing burn-down policy that targets pure shims at 0 by 4.0.
2. **Downstream stacked missions run under the same workflow** — the operator executes them via the standard spec-kitty flow (specify → plan → tasks → implement → review → merge), PRs to `main`, operator merges.
3. **The user-facing surface boundary is as enumerated in FR-006** (CLI surfaces, docs/glossary, prompts/skills/agent artifacts, charter file, generated output); a surface not enumerated is treated as out of scope until the inventory proves otherwise.
4. **The existing `src/charter/` package is unrelated to this rename** — internal identifiers are out of scope (C-005); no code-package merge is implied by the terminology decision.
5. **Cross-repo surfaces are out of scope.** The inventory covers this repository only; user-facing surfaces in sibling repos (e.g. the spec-kitty-saas dashboard) are deferred with rationale, not silently dropped.
6. **The amended ADR is still Proposed.** `2026-07-15-1` carries `status: Proposed`; amending its terminology portion leaves its resolution mechanics intact and changes only what US1-AS2 specifies.
