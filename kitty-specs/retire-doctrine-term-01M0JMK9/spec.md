# Mission Specification: Retire the Doctrine Term

**Mission Branch**: `feat/retire-doctrine-term`
**Created**: 2026-08-21
**Status**: Draft
**Input**: User description: "this is a research and planning mission. We've decided to retire the word Doctrine from Spec Kitty, and this mission is meant to 1) identify all of the work to be done 2) reason about the order and methodology in which to do it 3) Make a plan in terms of stacked spec-kitty missions to get the job done. First we should create an ADR, though, in proper spec-kitty style, with the decision that Doctrine is not the word we use. Instead we'll be calling everything Charter, and specifying between the charter.md file, active charter (formerly doctrine that is wired in) and inactive charter."

Discovery decisions (resolved via decision moments, all `resolved`):
- **Scope** (`specify.scope.internal-identifiers`): user/operator-facing language only; non-public internal code identifiers are out of scope, while supported public Python APIs are user-facing and in scope.
- **Vocabulary** (`specify.vocabulary.kind-vocabulary`): "charter" is the umbrella for the layer and its activation state (three-way distinction); the kind vocabulary survives.
- **Compatibility** (`specify.compatibility.alias-policy`): deprecate in 3.x (hidden aliases + warnings); by 4.0, zero user-visible "doctrine" — hard rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The decision is recorded as an ADR (Priority: P1)

The operator wants the terminology decision captured in a proper spec-kitty-style ADR under `docs/adr/3.x/`, so that every downstream mission and reviewer has a single canonical authority for the new vocabulary instead of relying on chat history or memory.

**Why this priority**: Without a decision record, every downstream mission re-litigates the vocabulary and drift is guaranteed. The ADR is the root of the stack — nothing else in this mission's output is authoritative without it.

**Independent Test**: Can be fully tested before merge by reading the new, registered ADR on the mission branch and asking a reviewer who has seen nothing else to state: what "charter" names, the three-way distinction, which terms survive, what is out of scope, the compatibility policy, and how "charter" the term differs from `src/charter/` the code package. If all six are stated correctly from the ADR alone, the story is merge-ready.

**Acceptance Scenarios**:

1. **Given** the confirmed decision (retire "doctrine" in user-facing language; "charter" is the umbrella with a three-way distinction; kinds survive; non-public internals out of scope but supported public APIs in scope; 3.x deprecation / gone by 4.0), **When** the ADR is authored, **Then** it follows the shared ADR template, uses its actual creation date in metadata and filename, records deciders/reviewers with `status: Accepted`, makes product-vocabulary effectiveness conditional on M1/I1, and is registered via `python -m scripts.docs.freshen_adr_inventory`.
2. **Given** the existing ADR `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`, **When** the new ADR is reviewed, **Then** it explicitly amends or supersedes the terminology portion of that ADR while leaving its resolution mechanics intact, and the old ADR's frontmatter `status:` is updated to `Superseded` with a pointer to the new ADR. (The 3.x index carries no status column — `Date | Title` only; the repo convention is frontmatter status, per the five existing `Superseded` ADRs. The old ADR is currently `status: Proposed`; status frontmatter is exempt from C-003 immutability — its wording stays byte-for-byte untouched.)
3. **Given** the new ADR, **When** a reviewer reads it without other context, **Then** they can state unambiguously: (a) what "charter" names, (b) the three-way distinction (charter bundle / active charter / inactive charter), (c) which terms survive, (d) the scope boundary (non-public internals untouched; supported public APIs and operator identifiers migrate), (e) the compatibility policy, and (f) that "charter" the term is disambiguated from `src/charter/` the pre-existing code package (the term names the governance layer, not that package).

---

### User Story 2 - Complete inventory of user-facing occurrences (Priority: P1)

The operator wants a complete, surface-by-surface inventory of every user-visible occurrence of "doctrine", so that downstream missions are scoped from evidence rather than guesswork, and completion can be verified by audit.

**Why this priority**: The inventory is the work list for the entire program. An incomplete inventory means un-retired occurrences survive to 4.0, violating the hard rule. It is as load-bearing as the ADR.

**Independent Test**: Can be fully tested by running the pinned, case-insensitive content-and-path audit, joining every hit to `inventory-hits.tsv`, and confirming zero unclassified hits (non-public internal identifiers, immutable history, and intentional non-user-facing quoted test/data are classified out by explicit rule; supported public APIs are OC hits).

**Acceptance Scenarios**:

1. **Given** the repository at this mission's pinned base, **When** the inventory is produced, **Then** every user-facing surface category — CLI help text/errors/command names/flags; active human prose regardless directory and all glossary authorities; prompts/skills/profiles/directives/agent artifacts and overrides; the charter bundle; pack and project-overlay paths; serialized operator configuration; workflows; and generated output — has an occurrence count and representative examples.
2. **Given** the inventory, **When** a downstream mission is scoped from it, **Then** each occurrence class has a stable identifier that can be tracked from inventory to mission to completion, and no surface category is missing.
3. **Given** non-public internal code identifiers (`src/doctrine/` implementation package/module paths), immutable historical artifacts, and intentional quoted/non-user-facing test or matcher data, **When** the inventory is reviewed, **Then** each occurrence is explicitly classified X1, X2, or X3 — not silently dropped from the audit; public exports/imports remain OC.

---

### User Story 3 - Ordering and methodology analysis (Priority: P2)

The operator wants a reasoned ordering and methodology for the retirement, so that stacked missions can be executed without breaking user-facing coherence mid-program (e.g. docs referencing terms the glossary has not yet defined, or a terminology guard that fails between waves).

**Why this priority**: The inventory says *what*; the methodology says *in what order and why*. Without it, the stack is a bag of missions that can be executed in an order that breaks invariants.

**Independent Test**: Can be fully tested by having a reviewer challenge each ordering choice and confirming every one has a stated rationale tied to a concrete risk (glossary authority, terminology guard, upgrade migrations, agent skill routing), plus an explicit statement of the invariant that must hold at each stack level.

**Acceptance Scenarios**:

1. **Given** the inventory, **When** the methodology is written, **Then** it explains why surfaces are ordered as they are (e.g. ADR + glossary first as canonical authority, then executable CLI surfaces with aliases, then prose/docs/prompts) and states the invariant that must hold at each stack level.
2. **Given** the 3.x deprecation policy, **When** the methodology is reviewed, **Then** it specifies how aliases are introduced (hidden + warning), what verifies they work, and exactly when/how removal at 4.0 is verified (zero user-visible "doctrine" audit).
3. **Given** the terminology guard (`tests/architectural/test_no_legacy_terminology.py`), **When** a wave lands, **Then** the methodology states how it stays green and non-vacuous at every stack level — M1 records the complete pre-edit fingerprint preimage, removes its own ordinary hits, and lands the final guard/compatibility reservations in one PR; later waves shrink ordinary fingerprints and introduce only reserved compatibility overlays. New hits, equal-count substitutions, missing baseline shrink, new files, or reservation evasion must fail.

---

### User Story 4 - Stacked mission plan (Priority: P2)

The operator wants the retirement expressed as a stack of spec-kitty missions with explicit dependencies, so that each can be specified, planned, and implemented independently in order without re-deciding anything this mission decided.

**Why this priority**: The stack is the executable form of the plan — it is what the operator actually runs. It depends on Stories 1–3 (ADR authority, inventory work list, ordering rationale), hence P2.

**Independent Test**: Can be fully tested by taking the first mission in the stack and attempting to specify it using only this mission's artifacts as input — if no new decision is required, the story is delivered.

**Acceptance Scenarios**:

1. **Given** the methodology, **When** the stacked plan is written, **Then** it names each downstream mission (slug + purpose), its inputs and outputs, its dependencies on prior missions in the stack, and which inventory occurrence classes it retires.
2. **Given** the stacked plan, **When** every inventory occurrence class and compatibility reservation is checked against it, **Then** each OC is assigned exactly once to its M1–M5 primary-use owner (or explicit external deferral), each CR has its declared M1–M4 introduction wave plus M6 removal, and every funded source hit's OC owner equals that introduction wave, without duplicate ownership/funding.
3. **Given** the first mission in the stack, **When** its specification is started from this mission's artifacts alone, **Then** no further decision from the operator is required.

---

### Edge Cases

- **`src/charter/` already exists as a package.** The ADR must disambiguate the term from the code surface. Non-public internals are X1, but names/imports in `__all__`, package re-exports, public docs/skills, or supported external contracts are public API and M2-map OC hits; a canonical charter facade can coexist with internal implementation under `src/doctrine/`.
- **Historical artifacts are immutable.** Every merged ADR body/title — including this new Accepted terminology ADR after this planning PR merges — and merged `kitty-specs/` mission snapshot retains legacy wording whether or not later archived; the inventory classifies it X2, never a rename target. ADR status/pointer metadata is the narrow mutable carve-out. The current unmerged mission remains active and cannot use X2.
- **The glossary page is both target and authority.** `docs/context/doctrine.md` is the canonical terminology authority *and* a rename target; its rewrite must precede any prose wave that depends on the new terms, or waves will cite undefined vocabulary.
- **The glossary authority pathname has consumers and history.** M1 renames `docs/context/doctrine.md` to `docs/context/charter.md` and owns every active docs/source/test referrer in the same PR. Immutable ADR/archive inline/path references remain byte-identical X2 historical text with no current-HEAD link promise; a named audit proves zero dangling active link/referrer. A registered 3.x redirect/loader alias warns only until M6; later prose waves never carry the rename dependency.
- **The charter bundle is terminology-laden and load-bearing.** The project-local bundle under `.kittify/charter/` has mixed ownership: `charter.yaml` contains human-authored governance plus generated catalog/metadata; `charter.md` is a human-curated companion and is never generated; `graph.yml`, interview answers, and synthesis/runtime sections retain their owning workflows. M1 directly edits the human-owned sections, uses `charter generate` only to refresh catalog/metadata, and never relies on `charter sync` to write either file. It must preserve context resolution and the compiled reference set (Charter Resolution Hints block).
- **Terminology guard between waves.** `tests/architectural/test_no_legacy_terminology.py` enforces the canon; if a wave retires a term before its replacement is canonical in the glossary, the guard or the docs go red. The methodology must sequence so the guard is updated shrink-only at each wave boundary and stays green throughout.
- **Deprecation aliases must actually work.** Old executable names — the top-level `spec-kitty doctrine` command group (8 subcommands: fetch, regenerate-graph, new, validate, pack, org, mission-type, asset) and `spec-kitty doctor doctrine` — must keep functioning with a deprecation warning during the 3.x window; the plan must define how alias behavior is tested (per subcommand) and how removal at 4.0 is verified (audit, not assumption).
- **Agent skill routing.** Renaming `spk-doctrine-*` skills changes agent-facing identifiers; harnesses that route on skill names need the old→new map, and legacy alias skills (repo precedent: `ad-hoc-profile-load`) may be required during the window.
- **Operator-typed identifiers are in scope.** Profile/directive/skill IDs are user-facing language, not internal identifiers. The complete fixed map is in the ADR contract: seven `spk-doctrine-*` IDs map to their named `spk-charter-*` replacements; both `spk-doctrine-charter` and its legacy alias `spec-kitty-charter-doctrine` route to `spk-charter-lifecycle`; `doctrine-daphne` maps to `charter-daphne`; `018-doctrine-versioning-requirement` maps to `018-charter-versioning-requirement`. Old IDs remain 3.x warning aliases and are removed in M6.
- **Serialized uses have different meanings.** M1 maps charter selection `governance.doctrine` → `governance.charter`. M2 maps org-pack config `doctrine.org.packs` → `charter_packs.org.packs`, while tracker ownership policy maps its `doctrine` block / `--doctrine-mode` / `doctrine_mode` output to `ownership` / `--ownership-mode` / `ownership_mode`. Each old reader/flag is a 3.x warning alias removed by M6; tracker `field_owners` survives. Out-of-repo SaaS consumers require owner + tracking reference/process + milestone.
- **Serialized/API topology is an operator surface.** M2 freezes authoritative `canonical-operator-surface-map.md`, joined exhaustively to all M2-scope inventory hits, plus set-equal CLI projection `canonical-cli-route-map.md` before editing. It owns every mapped consumer regardless directory; M3–M5 exclude those hits. ADR-fixed M1/M3/M4 seams retain their named owners. Fixed M2 rows include target URN plus target-kind/category/policy/hash/tool-enum/JSON-alias mappings. Canonical writers emit only new values; old active reads warn through 3.x; immutable X2 records remain byte-identical but render canonically; M6 removes active aliases.
- **Public package metadata is an operator surface.** Legacy-bearing public metadata/content inside `src/doctrine/pyproject.toml`, the `spec-kitty-doctrine` project/distribution/wheel name, and the `doctrine.api` facade are S7/M2 OC, never X1; exact `doctrine.api.__all__` membership and wheel-closure tests are supporting evidence without invented hit rows for legacy-free members. A physical tracked implementation pathname such as `src/doctrine/pyproject.toml` or `src/doctrine/api.py` is a separate X1 pathname hit unless itself installed/user-visible. M2 selects the collision-free charter distribution/facade names in its sole map question, records publication evidence and the resulting compatibility treatment, and owns build/install/export consumers through M6 removal.
- **Charter Pack and Charter Bundle are different things.** A *Charter Pack* is a versioned, distributable catalogue of governance artefacts — the offer side (`packs/built-in/`, org packs, and project overlays currently stored under `.kittify/doctrine/`). A *Charter Bundle* is the per-project materialized file set under `.kittify/charter/` — the consume side. The glossary rewrite must replace “Doctrine Pack” with “Charter Pack”, add “Charter Bundle”, and disambiguate both from unrelated code senses of “bundle”.
- **The project overlay root has a fixed destination.** M3 migrates offer-side `.kittify/doctrine/` to `.kittify/charter-packs/`, never `.kittify/charter/`. Canonical writers use only the new root; 3.x readers accept either with warning. Disjoint entries merge with new-root precedence, identical duplicates deduplicate, and conflicting duplicate paths/URNs hard-fail with recovery guidance. M3 updates readers/writers/staging/migrations/consumers together; M6 removes old-root support.
- **Human prose is audience-classified.** Active source-tree READMEs and Markdown are S3/M5 even when they live under `src/`; root operator docs are exclusively S9; generated/render templates are S7, while only non-public internal symbols remain X1.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | ADR records the terminology decision | As an operator, I want a spec-kitty-style ADR in `docs/adr/3.x/` recording the retirement of "doctrine" in favor of "charter", so that downstream work has a single canonical authority. | High | Open |
| FR-002 | Three-way distinction defined | As an operator, I want the ADR to define *charter bundle* (the per-project file set under `.kittify/charter/`), *active charter* (a governance artefact activated/wired in for the project), and *inactive charter* (an artefact available in a Charter Pack but not activated) as distinct canonical concepts, so that vocabulary does not confuse file-set state with artefact activation. | High | Open |
| FR-003 | Kind vocabulary preserved | As an operator, I want the ADR to state that the existing kind terms — including `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, agent profile, glossary pack, and mission step contract — remain canonical labels in their existing roles, so that cascade and DRG vocabulary are undisturbed without falsely making every kind activatable. | High | Open |
| FR-004 | Scope boundary recorded | As an operator, I want non-public internals and the `src/doctrine/` implementation tree out of scope, while operator IDs, serialized/API tokens, supported public Python exports/imports, exact `doctrine.api.__all__`, and public distribution/wheel metadata are in scope with canonical charter surfaces, evidence-driven 3.x compatibility, and M6 supported-surface removal, so implementation location is not confused with public API. | High | Open |
| FR-005 | Compatibility policy recorded | As an operator, I want the ADR to record 3.x deprecation (hidden aliases + warnings) and the hard rule that zero user-visible "doctrine" remains by 4.0, so that the upgrade path is explicit and verifiable. | High | Open |
| FR-006 | Complete user-facing occurrence inventory | As an operator, I want a surface-by-surface inventory and a one-row-per-hit manifest covering content and tracked pathnames across CLI, active human prose regardless directory, glossary authorities, prompts/skills/profiles/directives/overrides, agent artifacts, charter bundle, pack/overlay paths, operator config, workflows, generated output, supported public APIs, and distribution/wheel metadata, so downstream missions are scoped from evidence. | High | Open |
| FR-007 | Classified-out occurrences | As an operator, I want every non-public internal identifier (X1), immutable historical occurrence (X2), and intentional non-user-facing quoted/test/data occurrence (X3) explicitly classified, while supported public APIs remain OC, so completion audits are complete without inflating user-facing work. | Medium | Open |
| FR-008 | Ordering and methodology analysis | As an operator, I want a reasoned ordering and methodology (why this surface order; the invariant that must hold at each stack level), so that the program does not break user-facing coherence mid-flight. | High | Open |
| FR-009 | Stacked mission plan | As an operator, I want the retirement expressed as a stack of spec-kitty missions with dependencies, inputs/outputs, the ordinary occurrence classes each retires, and the compatibility reservations each introduces/removes, so that execution proceeds mission by mission without duplicate ownership. | High | Open |
| FR-010 | First stack mission is spec-ready | As an operator, I want the first downstream mission in the stack to be fully determined by this mission's outputs (no further decisions needed), so that execution can start immediately. | Medium | Open |
| FR-011 | Glossary gap closure for the new vocabulary | As an operator, I want the glossary rewrite to replace “Doctrine Pack” with canonical “Charter Pack”, add canonical “Charter Bundle”, distinguish offer-side packs from the project-local bundle and unrelated code senses, and define what replaces the existing “Doctrine Domain” glossary sense, so downstream waves cite complete vocabulary. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Inventory completeness | After fetching the target, the branch must incorporate the exact `origin/main` tip; that target tip is the pinned `base_commit` (a stale branch-point merge base fails). 100% of its content occurrences and tracked pathnames are enumerated. `inventory-hits.tsv` records one row per hit (`hit_id`, kind, path, line, column, classification ID, surface category, nullable `compatibility_registry_id`); `inventory.md` is mechanically derived from it. The CR ID is allowed only on introduced OC product-compatibility hits, never X; it does not change arithmetic. Every hit is in-scope or X1/X2/X3, and 0 are unclassified. | Completeness | High | Open |
| NFR-002 | ADR self-sufficiency | 1 reviewer with no other context can state the new vocabulary, scope boundary, and compatibility policy from the ADR alone (verified by an independent review pass). | Quality | High | Open |
| NFR-003 | Plan determinism | 100% of downstream missions have named dependencies and inputs/outputs; 0 unresolved cross-wave inputs. One local question is allowed only when bounded/owned. M2 owns every command route, otherwise-unfixed M2-scope serialized/API occurrence, supported public Python facade with aggregate exact `doctrine.api.__all__` evidence, legacy-bearing public member, public distribution/wheel surface and publication-evidence treatment, plus every mapped consumer regardless directory; it freezes exhaustive `canonical-operator-surface-map.md` plus set-equal `canonical-cli-route-map.md`. M3–M5 exclude mapped hits, while ADR-fixed seams retain named owners. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No rename execution in this mission | This mission produces planning/lifecycle artifacts only (ADR, inventory + hit manifest, methodology, stacked plan, squad evidence, durable `implementation-baseline.json`, and required docs-contract CI metadata); it does not rename any product surface. Before any WP01 edit, WP01 persists `git rev-parse HEAD` plus capture metadata in that owned artifact. Verification distinguishes the PR planning base from the persisted implementation base and checks committed plus working-tree changes. | Scope | High | Open |
| C-002 | ADR conventions | The ADR follows the shared template (`docs/architecture/adr-template.md`), dated naming `YYYY-MM-DD-N-<slug>.md` under `docs/adr/3.x/`, and is registered via `python -m scripts.docs.freshen_adr_inventory`. | Process | High | Open |
| C-003 | Historical artifacts immutable | Every merged ADR body/title, including this new Accepted terminology ADR after this PR merges, and every merged mission snapshot retains legacy wording whether or not later archived; merge is the mission X2 threshold, so a current/unmerged mission is never X2. They are not rename targets. Status/pointer frontmatter is exempt: an ADR whose decision is amended may have its status updated (e.g. to `Superseded` with a pointer) without that counting as a wording change. | Scope | High | Open |
| C-004 | Terminology guard integrity | M1 fingerprints every classified pre-M1 guard-root hit, including owner=M1, materializes the complete pre-edit baseline, and records the scoped same-PR M1 source/baseline shrink before the final guard lands; every OC keeps one M1–M5 primary-use owner. WP02 first records non-owning semantic `CR-##` candidates with disjoint planning-base coordinates/counts, fixed target or fail-closed `owner:M2; source_oc:<OC-##>`, planned introduction, M6 removal, fixed control path, and named tests. At its actual pre-M1 base, M1 reruns the audit, fail-closed reconciles drift, materializes disjoint source coordinates/frozen product maxima, and creates one exact X3 control record per CR at `tests/architectural/legacy_terminology_compatibility_registry.yaml`; controls do not consume product budget. Resolving an M2 target does not change CR identity. Only the declared introduction wave may atomically remove ordinary fingerprints, set `reserved` to `active` (or M2 distribution-only `closed-no-channel`), and create at most the CR budget of exact OC product fingerprints; every funded source hit's OC owner equals that wave, no source funds two CRs, and no product fingerprint joins two CRs. An unpublished distribution creates no product alias and retains its no-channel control/evidence tombstone until M6. The guard enforces its roots; pinned registry audit plus named verifiers enforce other roots. Product compatibility may not evade audit via fragments. M6 deletes every CR control/product/tombstone and runtime/file/key compatibility; I6 permits only justified X fingerprints and an empty CR inventory. Four ordinary plus six CR mutation cases and a fail-closed pre-edit check make this non-vacuous. | Technical | High | Open |
| C-005 | Internal identifiers untouched | Non-public internals and the `src/doctrine/` implementation tree/module paths need not be renamed. This does not exempt supported public APIs: exported/documented access receives a canonical charter facade in M2, old public aliases warn in 3.x, and M6 removes them from supported exports/docs; underlying implementation may remain internal. | Scope | High | Open |

### Key Entities *(include if feature involves data)*

- **Charter (term)**: The umbrella term for the governance artefact layer and its activation state; replaces "doctrine" in user-facing language. One of three canonical senses (see below).
- **Charter bundle**: The per-project materialized file set under `.kittify/charter/` — `charter.yaml`, curated `charter.md`, `graph.yml`, and synthesis sidecars. Human-authored and generated sections retain documented owners; it is distinct from the offer-side Charter Pack.
- **Charter pack**: A versioned distributable catalogue of governance artefacts; the offer side. It replaces “Doctrine Pack” in user-facing language.
- **Active charter**: A governance artefact wired in (activated) for the project; the second canonical sense.
- **Inactive charter**: A governance artefact available in a Charter Pack but not activated for the project; the third canonical sense.
- **Charter kind**: Existing labels such as `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, agent profile, glossary pack, and mission step contract survive in their current roles; this illustrative list does not redefine or claim exhaustiveness of the runtime activatable-kind registry.
- **Occurrence class**: A stable identifier for a group of user-facing "doctrine" occurrences sharing a surface and rename treatment; the tracking unit from inventory → mission → completion.
- **Stacked mission**: A downstream spec-kitty mission in the retirement program with explicit dependencies on prior missions in the stack.

## Domain Language *(optional — included: terminology is the subject of this mission)*

| Term | Canonical meaning | Do NOT use (synonyms to avoid) |
|------|-------------------|-------------------------------|
| **Charter** (umbrella) | The governance artefact layer and its activation state, in user-facing language. | "doctrine" (retired from user-facing language by this program) |
| **Charter pack** | A versioned, distributable catalogue of governance artefacts: the offer side. | “charter bundle” when project-local materialized files are meant |
| **Charter bundle** | The per-project file set under `.kittify/charter/`; human-owned and generated sections retain their documented owners. | "the charter" when activation is meant; "constitution" (legacy, pre-063); “charter pack” when project files are meant |
| **Charter (CLI/directory senses)** | The `spec-kitty charter` command group and the `.kittify/charter/` directory — pre-existing senses covered by the umbrella, not additional canonical concepts. | Treating them as separate terms in new prose |
| **Active charter** | A wired-in (activated) governance artefact. | "activated doctrine", "wired-in doctrine" |
| **Inactive charter** | An un-activated governance artefact available in a pack. | "inactive doctrine", "dormant doctrine" |
| **Charter kind** | `directive` / `tactic` / `styleguide` / `toolguide` / `paradigm` / `procedure` / agent profile / glossary pack / mission step contract — canonical, unchanged. | Collapsing kinds into bare "charter" (loses the precision cascade syntax depends on) |
| **Doctrine** (legacy) | Deprecated/non-canonical after ADR acceptance, not instantly absent: pre-I1 current authorities remain operational; inventoried primary-use debt shrinks in its M1–M5 owner wave; registered 3.x compatibility identifiers/routes/keys/paths/redirects may remain or relocate until M6; X history/internal/test evidence survives. | Any unregistered new primary use, baseline growth, or survival past its owner wave/M6 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Before merge, the new ADR is present on the mission branch, registered in the 3.x index, and merge-ready; an independent reviewer (a squad lens or the operator — named in the plan) states the three-way distinction, surviving kinds, scope boundary, and compatibility policy correctly from the ADR alone (1/1 review pass).
- **SC-002**: The inventory covers 100% of textual occurrences and tracked pathnames with stable per-hit and class identifiers; manifest arithmetic and the NFR-001 audit find 0 unclassified hits.
- **SC-003**: The stacked plan names every downstream mission with dependencies and inputs/outputs; 100% of OCs have one M1–M5 primary-use owner or explicit external deferral, 100% of CRs have one introduction wave plus M6 removal, and 100% of funded source hits have OC owner = introduction wave, with 0 duplicate hit ownership, double-funded source coordinates, or overlapping product fingerprints.
- **SC-004**: The first mission in the stack can be specified from this mission's artifacts alone, with 0 new operator decisions required.

## Assumptions

1. **4.0 is a real, planned milestone** at which the hard-removal rule takes effect — consistent with the existing burn-down policy that targets pure shims at 0 by 4.0.
2. **Downstream stacked missions run under the same workflow** — the operator executes them via the standard spec-kitty flow (specify → plan → tasks → implement → review → merge), PRs to `main`, operator merges.
3. **The user-facing surface boundary is the complete FR-006 list.** New locations discovered by the audit default to unclassified and fail until explicitly added or classified X1/X2/X3; omission never implies out of scope.
4. **The existing `src/charter/` package is not the terminology target** — non-public implementation identifiers are out of scope (C-005), but supported public APIs migrate through an M2 charter facade; no code-package merge is implied.
5. **Cross-repo surfaces are out of scope.** The inventory covers this repository only; user-facing surfaces in sibling repos (e.g. the spec-kitty-saas dashboard) are deferred with rationale, not silently dropped.
6. **ADR state is explicit.** The prior ADR is currently `Proposed`; WP01 changes it to `Superseded` with a pointer. The new ADR is `Accepted` on merge, while its product-vocabulary effectuation remains explicitly conditional on M1/I1.
