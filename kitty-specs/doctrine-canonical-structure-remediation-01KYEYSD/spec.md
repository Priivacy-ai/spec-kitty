# Mission Specification: Doctrine Canonical Structure Remediation

**Created**: 2026-07-26
**Status**: ⛔ **SPECCED, THEN SPLIT — this mission does not implement.** See below.
**Input**: User description: "this scope is starting to feel like a same-branch unblock mission more than a series of ops... the systemic fix is the real structural remediation work that needs to happen now, even if it slows some other deliveries"

---

## ⛔ This mission was specced and then broken into five missions

**Operator ruling, 2026-07-26.** This specification is complete and remains the **programme record** —
the design authority for the whole remediation, the home of the three governing ADRs, the inventory
research, and the Phase 0 findings. It is **not implemented directly**. Every requirement below is
delivered by one of five child missions.

Why: the delivery is ~28–43 agent-days and ~555–665 file touches. One pull request of that size is
not reviewable, and the sequencing authority's **C2** forbids two all-surface sweeps sharing a single
occurrence map — this scope contains three.

| Mission | Slug | Delivers |
|---|---|---|
| **A** | `doctrine-silence-guards-01KYFV7Q` | Guards and campsite. Every mechanism that makes silence impossible, landed **before** anything new can ship inert. |
| **B1** | `drg-relation-impacts-vocabulary-01KYFV87` | `Relation.IMPACTS` + `is_symmetric`; retires `in_tension_with`. Delivers ADR 2026-07-26-3. |
| **B2** | `drg-edge-migration-extractor-retirement-01KYFV8C` | All 774 edges become authored; both Python edge registries and the calibrator are deleted; extractor edge production retires. **Carries `change_mode: bulk_edit` and the occurrence map.** |
| **C** | `test-quality-doctrine-series-01KYFV8H` | The original #2935 deliverable: the over-mocking failure becomes a citable rule. |
| **D** | `foundational-values-creed-band-01KYFV8N` | The reachable band of the FoundationalValues/creed programme. |

**Mandatory order: A → B1 → B2 → C. D is independent of B2 but gates on A.**
The order is not a preference — see C-009, C-010, and the ordering rationale in
[`plan.md`](plan.md). A landing after B1 means `impacts`, `is_symmetric`, and `aliases` ship inert
behind green tests, which is this mission's own defect class reproduced by its remediation.

### Requirement routing — no requirement falls between the missions

| Requirement | Owner |
|---|---|
| FR-000, FR-001, FR-002, FR-012 | **Done** (PR #2936) — closed here, not routed |
| FR-004, FR-005, FR-006, FR-020, FR-021, FR-022, FR-023, FR-029, FR-030, FR-031 | **A** |
| FR-032 | **B1** |
| FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-024, FR-025, FR-026, FR-027, FR-028 | **B2** |
| FR-003, FR-007, FR-008, FR-009, FR-010, FR-011 | **C** |
| NFR-001, NFR-003 | **Done** (PR #2936) |
| NFR-012 | **A** |
| NFR-006 | **B1** and **B2** (each ledgers its own count deltas) |
| NFR-002, NFR-005, NFR-007, NFR-008, NFR-009, NFR-010, NFR-011, NFR-013 | **B2** |
| NFR-004 | **C** |
| C-001, C-002, C-004, C-006, C-007, C-011 | **All five** — standing constraints |
| C-009 | Mechanism in **A**; binds **B1** and **B2** |
| C-010 | Ordering constraint: **A before B1** |
| C-005 | **C** |
| SC-001, SC-002, SC-008 | **Done** (PR #2936) |
| SC-003, SC-015, SC-016, SC-018, SC-021, SC-022, SC-023 | **A** |
| SC-024 | **B1** |
| SC-006, SC-009, SC-010, SC-011, SC-012, SC-013, SC-014 | **B2** |
| SC-004, SC-005, SC-007, SC-017, SC-019, SC-020 | **C** |

### What changed in this document at the split

- **C-003 is superseded** (see the Constraints table). It named a branch and a PR that are both
  merged, so it had to be rewritten regardless of the split.
- **C-008 is closed.** ADR 2026-07-26-3 decided ADR-D2: a new `Relation.IMPACTS` carries `impacts`.
  The gate it guarded is cleared.
- **`change_mode: bulk_edit` moved off this mission's `meta.json` to B2's**, along with
  `occurrence_map.yaml`. This mission edits nothing, so a bulk-edit guardrail on it was inert by
  construction — the same failure mode NFR-013 exists to catch.
- Four measured corrections are recorded in [`plan.md`](plan.md) under *Corrections to the spec*:
  the migration is **169 files, not 139**; FR-027 is **not** behaviour-neutral and its resolution is
  a ledgered deviation; the `shipped/` count is **22 across 9 files, not 21 across 8**, and one hit
  is prose rather than a path.

---

## Context

This mission was not planned. It was **discovered** while fixing P0 [#2934](https://github.com/Priivacy-ai/spec-kitty/issues/2934) and researching the test-quality doctrine series [#2935](https://github.com/Priivacy-ai/spec-kitty/issues/2935). Four unrelated-looking symptoms turned out to be one root cause:

> **The doctrine layer predates its own canonical model, and nothing enforces the model that replaced it.**

The symptoms, each found by inspection rather than by a failing test:

1. A "`type: asset` is schema-rejected" bug that was the **deprecated relationship surface correctly refusing to grow**.
2. A migration hint instructing operators to edit `src/doctrine/graph.yaml` — sharded out of existence by #2680, still named at ~10 source sites.
3. Nine doctrine artefacts in the wrong directory, **all silently dead**, including two *divergent* copies of live artefacts (an edit-the-wrong-file trap).
4. A `shipped/` pack layer documented in authoring guidance and cross-links that has **never existed on disk**.

In every case the failure mode is **silence**, not an error. That is the defect class this mission closes.

The operator's rationale for landing this as structural remediation rather than unblocking the P0 alone:

> There is no point unblocking a P0 if we are just going to recreate one right after.

Governing decisions: [ADR 2026-07-26-1](../../docs/adr/3.x/2026-07-26-1-drg-edges-are-the-canonical-relationship-authority.md) (relationship authority) and [ADR 2026-07-26-2](../../docs/adr/3.x/2026-07-26-2-doctrine-artefact-pack-layout-convention.md) (pack layout).

### The extractor is scaffolding (operator framing, 2026-07-26)

> The extractor is to be considered as mostly a migration/curation enabler, not a stable,
> repeatable system. The published DRG, edges, and doctrine relationship model is the
> envisioned/desired way of working.

This settles the mission's central design question, which a post-spec squad flagged as a
blocker across three independent lenses. The question was "where do migrated relationships
live, given `regenerate-graph` overwrites the fragments?" — and it was the wrong question. It
assumed the extractor is permanent infrastructure that the migration must accommodate. It is
not: it is a **transitional tool whose job ends when the migration it enables is complete.**

Consequences that shape every requirement below:

- The **published DRG — authored edges over the `Relation` vocabulary — is the target model.**
  Not a build output of a legacy surface.
- The authored-edge YAML tier (FR-016) is therefore the *destination*, not a workaround for an
  overwrite bug.

#### Localized source + generated cache (operator framing, 2026-07-26)

> Why not a + b? `a` as the localized source of truth, with `b` an aggregate composed out of
> those localized edge files for efficiency reasons? (think: file-based generated cache)

This replaces an earlier false dichotomy in this spec, which treated "the loader reads the
`*.graph.yaml` fragments" as evidence that the fragments are an *authority*. Under cache
semantics that is a non-problem — being read is what a cache is for. The model:

- **(a) `<kind>.edges.yaml` — localized source of truth.** Authored, co-located with the
  artefacts whose relationships they declare (locality of change: a curator edits a
  relationship next to the thing it relates).
- **(b) the aggregate `*.graph.yaml` — a generated cache**, read at runtime for efficiency.

Three properties this buys that neither "fragments are the authority" nor "Python registry is
the authority" did:

1. **"Derived" becomes falsifiable rather than aspirational.** A cache has exactly one correct
   value, `f(sources)`. That is a checkable equation. "This YAML is authored and that YAML is
   generated" is a convention a reader must remember; "this is a cache" is a semantic that
   carries its own rule — the name does the enforcement work.
2. **It inverts a vacuity trap.** The five freshness canaries currently compare
   `extractor(tree) + overlay` against the committed fragments. With 559 of 774 edges moved
   into the overlay that degenerates to `overlay == overlay` — vacuous for 72% of the edge set,
   and no requirement noticed. Under (a)+(b) the check becomes `merge(authored) == cache`, a
   real coherence assertion that gets **stronger** as more edges become authored.
3. **It survives pack extraction** — the cache need not ship; rebuild on install.

Conditions that make it safe, and these are requirements rather than preferences: the cache
declares itself in-band (a header naming it generated plus a content hash of its inputs, so
staleness is self-evident rather than inferred — the fragments already carry
`generated_by: drg-migration-v1`, so there is precedent); the freshness check is **enforced in
CI, not advisory**; and nothing hand-edits it. **Open:** whether the cache must be committed at
all, or can be a build artefact — the 14 fragments are the highest-churn shared output in this
mission, so a committed cache means every rebase re-touches exactly the files whose state is
the correctness proof.
- The extractor remains legitimate and useful *as a migration oracle*: it is precisely the
  thing that tells us what edge each of the 559 entries should become. Using it that way is
  its intended purpose. Depending on it afterwards is not.
- After FR-014, **nothing in the end state requires the extractor to run.** Any requirement
  that would be falsified by deleting it entirely is a requirement mis-specified.

This mission is therefore **completing deferred work, not inventing a direction.** The pattern
is visible in the repo's own history: #2680 sharded the `graph.yaml` monolith but left ~18
sites naming the old path; the inline-reference excision mission banned the scalar `*_refs`
fields but left the structured blocks and missed `directive_refs`; the extractor was always
meant to retire and never did. Each step deferred the last mile, which is how a build tool
ended up masquerading as an authority — and why C-004 forbids adding another deferral to the
pile.

## Programme integration — the FoundationalValues/creed design (folded 2026-07-26)

The FoundationalValues/creed design session finalized on `docs/manifesto-tier-analysis` and is
merged onto this branch (`091f1c7ae`). **Operator ruling: this entire design and implementation
lands before any other work unblocks** — not doing so "would cause a lot of issues down the
line." So this mission is no longer only the relationship/layout remediation; it is the
remediation *plus* the programme that depends on it, sequenced as one delivery.

**Authority tiers** (per `docs/plans/doctrine/index.md` — only these two are citable):

- `docs/plans/doctrine/foundational-values-and-creed.md` — design authority (§6 maths,
  §11 contradiction register, §13 open decisions D-1..D-6).
- `docs/plans/doctrine/manifesto-program-delivery-sequence.md` — **sequencing authority**
  (critical path, 22 ranked increments, ADR-D1..D10 scope, park register).
- `docs/plans/doctrine/squad-reports/review-round-2026-07-26.md` — the 26-item fix ledger the
  authorities are post-fix against. Findings are checkable, not asserted:
  `_reproduce_matrix_findings.py` is stdlib-only and the *rejected* second-order matrix is
  committed as `_ammerse-second-order.json` so the false-derivation claim can be verified.

### Why this reorders our own requirements

Three increments from that programme are **hard prerequisites to work already in this spec**,
and one of them would otherwise silently destroy it:

| Increment | Rank | Why it gates us |
| --- | --- | --- |
| **I19 zero-producer lint** | 1 | "The only thing preventing a fourth inert register." Directly guards FR-028 (`aliases`) from shipping as a field nothing produces. |
| **I2 silent-kind-drop closure** (4 sites) | 5 | `query.py:230-242`, `charter/context.py:672-683` (no `else`), `extractor.py:133-145` (`_KIND_MAP`), `extractor.py:1210-1229` (the writers). **Cannot be sequenced after any new edge field** — sites 3 and 4 would silently delete it at extraction and regeneration. Collides with `#2532`; pin the fix **behaviourally**. |
| **I3b DRG model + writers + round-trip** | 6 | `DRGNode`/`DRGEdge` carry **no `model_config`**, so extra fields are silently ignored, and the writers are field-by-field (`_node_to_dict` enumerates `urn`/`kind`/`label`/`tags`). Verified. Converts two silent-drop hazards into load errors. **Non-negotiably one commit.** |

Governing precedent from the sequencing authority: **a schema slot without a producer *and* a
coverage gate in the same commit goes silently inert — 3 for 3 in this repo, one of them for 162
days behind green tests.** That is the same failure mode as everything else this mission exists
to close, so it binds our own new fields.

### The programme-shape gate sits between us and `extractor.py`

**G2 / ADR-D2 must be answered inside the superseding ADR before anyone opens `extractor.py`.**
It decides which relation carries `impacts` once `in_tension_with` retires — and the answer moves
the blast radius by an order of magnitude: a new `Relation.IMPACTS` is ~45–60 files, whereas
"keep the name, retire only the lifecycle" collapses to **~5–10**. FR-014 *is* "open
`extractor.py`", so it is gated on G2. Operator-only sign-off.

### Consequences for the authored-edge tier

`in_tension_with` **retires**; `impacts` (a signed numeric annotation on the edge) subsumes it,
with `impacts < 0` *being* a tension claim on strict sign. `reconciles_tension` survives,
re-pointed at negative-`impacts` pairs. So our authored tier must carry an `impacts` annotation,
and the two existing authored tension edges (`directive.graph.yaml:90-93`, `:103-106`) migrate to
`{relation: impacts, impacts: <negative>}` **preserving each `reason`**. This aligns with our own
architecture rather than fighting it: **ADR-D3 makes `impacts` authored-only, never derived** —
the same principle as the authored-edge tier.

### Correction to the sequencing authority: I3a is not a one-file campsite

The sequencing authority ranks **I3a** third — *"wire `generate_schemas --check` into CI, 1
workflow file, closes a verified gap."* The gap is real (`--check` exists; zero references in
`.github/`), but the cost estimate is wrong, and wiring the gate as-is would immediately go red.

Measured: `--check` **exits 1 today** with **7 stale schemas**. Regenerating produces three
distinct divergence classes, only one of which is safe to accept:

| Divergence | Direction | Disposition |
| --- | --- | --- |
| `enhances` / `overrides` removed from tactic/styleguide schemas | Models retired them (`_RETIRED_RELATIONSHIP_FIELDS`, `tactics/models.py:14`); the schemas still bless them | **Safe** — regeneration finishes a half-done excision. Same residue class as `directive_refs`. |
| `structural_lint_config` removed from the styleguide schema | It is a **real declared model field** (`styleguides/models.py:92`) that the generator **fails to emit** | **Generator bug.** Accepting the deletion would invalidate `common-docs.styleguide.yaml`, which uses it. Fix the generator. |
| `point_in_time_marker` removed | Declared in **no model**, yet **used by a shipped artefact** (`common-docs.styleguide.yaml`) | Silently ignored today, because the models lack `extra="forbid"`. Either add it to the model or remove it from the artefact — decide, don't regenerate blindly. |

Also a definition rename (`reference` → `paradigm_reference`) whose `$ref` targets must be
verified, and `mission_step_template_ref` newly emitted.

So I3a's real shape is: **fix the generator, adjudicate two fields, regenerate, then wire the
gate** — not one workflow file. Note the third row is itself an argument for I3c: a field in a
shipped artefact that no model declares is exactly what `extra="forbid"` would have caught.

**Status: not wired.** Wiring `--check` before this reconciliation would put a red gate on the
branch and invite someone to "fix" it by accepting a regeneration that deletes valid schema.

### I5's "two drifted AMMERSE copies" — target not yet pinned

Searched for the second definition and did not find it where the estimate implies. Under
`src/doctrine/` exactly **one** artefact defines the AMMERSE axes
(`tactics/built-in/analysis/ammerse-impact-analysis.tactic.yaml`, 13 axis-name hits). The only
other hits repo-wide are `.kittify/charter/charter.yaml` and `.kittify/charter/references.yaml`
— the **compiled charter bundle**, which is generated, so divergence there is a staleness
symptom rather than a second authored copy.

So before I5 is actionable someone must name the second copy. Likely candidates: the tactic's
prose definitions vs the axis ids in `docs/plans/doctrine/_ammerse-corpus-36-practices.json`, or
the design authority's own §2 table. **Do not "unify" the compiled charter** — that is a
regeneration target, not a source.

### Both corrections above discharge a limitation the design authority states about itself

The reviewer-facing companion is explicit: *"nothing was executed — every claim about how the
existing codebase behaves is a careful static read, labelled as such."* These two findings are
the first *executed* checks against that band, and both moved: I3a is not one workflow file, and
I5's target is unconfirmed. That is the static-read caveat being discharged as intended, not a
defect in the design work — but it does mean the ~9–12 file / 2–3 day campsite estimate should be
re-priced before it is committed to.

### Ship-first set (gates on nothing)

Ranks 1–4, ~9–12 files, ~2–3 days: I19 zero-producer lint · I1a sign-vs-rationale polarity lint
(validation set of 12 known corpus rows exists **today**) · wire the existing
`generate_schemas --check` into CI · unify the two drifted AMMERSE definition copies. Six of the
top eight ranked increments are campsite work — deliberately, debt before functional work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A misplaced artefact fails loudly instead of vanishing (Priority: P1)

A maintainer adds a doctrine artefact and puts the directory in a reasonable-but-wrong place — for example grouping by category above the pack layer (`assets/audiences/built-in/`) instead of inside it. Today nothing complains: the file is never loaded, never becomes a graph node, and never resolves. It looks authored and does nothing. After this story, the mistake is a red test naming the correct shape.

**Why this priority**: This is the generator of the other symptoms. Until misplacement is loud, every other fix is a one-off cleanup that drifts again. It is also the cheapest to verify.

**Independent Test**: Plant an artefact at each wrong shape in a temporary tree and assert the checker rejects it; plant the two legal shapes and assert it accepts. Fully testable without any other story.

**Acceptance Scenarios**:

1. **Given** an artefact at `tactics/x.tactic.yaml` (no pack layer), **When** the layout gate runs, **Then** it fails and names `<type>/<pack>/[<category>/]<name>`.
2. **Given** an artefact at `assets/audiences/built-in/x.asset.yaml` (category above pack), **When** the gate runs, **Then** it fails.
3. **Given** artefacts at `directives/built-in/x.directive.yaml` and `tactics/built-in/testing/x.tactic.yaml`, **When** the gate runs, **Then** it passes.
4. **Given** the shipped tree, **When** the gate runs, **Then** it passes with an **empty** allowlist.

---

### User Story 2 - An operator can follow the migration instruction they are given (Priority: P1)

An operator hits `InlineReferenceRejectedError` and is told to add an edge to `src/doctrine/graph.yaml`. That file does not exist. The single piece of guidance pointing from the legacy surface to the canonical one points at nothing, so the operator either guesses or gives up and re-adds an inline reference.

**Why this priority**: Authoring new doctrine (US4) while the system's own migration hint is unfollowable propagates the confusion this mission exists to reduce. It is a prerequisite, not a nicety.

**Independent Test**: Grep for the stale path across `src/`; assert zero occurrences in operator-facing strings, and assert the rejection-hint regex and its contract fixture name the per-kind fragment path.

**Acceptance Scenarios**:

1. **Given** a YAML carrying a forbidden inline ref field, **When** the validator rejects it, **Then** the hint names an existing per-kind `<kind>.graph.yaml` fragment.
2. **Given** the four `<kind>_reference.type` schema enums, **When** a reader inspects them, **Then** each carries a frozen-legacy comment pointing at ADR 2026-07-26-1.
3. **Given** a contributor tries to add `asset` to a reference enum, **Then** the ADR and comment tell them not to, and why.

---

### User Story 3 - A curator starts from the pinned model, not from rediscovery (Priority: P2)

An agent loads the `doctrine-daphne` curator profile to author or maintain doctrine. Today the profile does not carry the layout convention or the edges-not-inline-refs rule, so each invocation rediscovers them — or doesn't. #2918's layout mistake and this session's abandoned enum-widening are both that gap.

**Why this priority**: It converts this mission's findings from a one-time cleanup into standing capability. Lower than P1 only because the gate (US1) already blocks the worst outcome.

**Independent Test**: Assert the profile content carries both rules and points at both ADRs.

**Acceptance Scenarios**:

1. **Given** the `doctrine-daphne` profile, **When** it is loaded, **Then** it states artefacts live at `<type>/<pack>/[<category>/]<name>`.
2. **Given** the same profile, **Then** it states relationships are DRG edges and inline `references:` blocks are frozen.
3. **Given** the same profile, **Then** it names the regeneration command rather than implying hand-editing fragments.

---

### User Story 4 - The #2934 test-quality failure becomes a citable rule (Priority: P2)

A reviewer sees a test that mocks a function internal to the system under test in order to pin a call contract — the exact shape that made #2934 look like P0 data loss. Today they can argue it is bad; after this story they can cite a rule, an anti-pattern node, and a remediation procedure.

**Why this priority**: This is the original #2935 deliverable and the reason the structural problems surfaced. It depends on US1/US2 landing first (C-001/C-002 constrain how it is authored).

**Independent Test**: The series loads, resolves, validates to zero pack errors, and its anti-pattern nodes are reachable only via `rejects` edges.

**Acceptance Scenarios**:

1. **Given** the authored series, **When** doctrine validation runs, **Then** it reports zero errors.
2. **Given** `DIRECTIVE_041`, **When** its intent is split to the new paradigm, **Then** the link is a `refines` **edge** and 041's existing inline `references:` block is untouched.
3. **Given** the new paradigm, **When** the graph is regenerated, **Then** the `refines` edge survives the org→DRG round-trip (it is the first such edge — see NFR-004).
4. **Given** every new resolved-only node (asset / anti-pattern), **Then** each has at least one inbound edge from an activatable artefact.

---

### User Story 5 - The CLI validator rejects what the canonical tests reject (Priority: P3)

A contributor runs `spec-kitty doctrine validate`, sees green, pushes, and CI's strict canonical tests reject the artefact anyway.

**Why this priority**: Real but narrow, and part of the originally-reported gap is likely the frozen inline surface behaving correctly. Characterize before fixing.

**Independent Test**: A parity test feeding the same invalid artefacts to both surfaces and asserting matching verdicts.

**Acceptance Scenarios**:

1. **Given** an artefact the canonical tests reject, **When** the CLI validator runs, **Then** it also rejects it.
2. **Given** a divergence that is the frozen surface working as designed, **Then** it is documented as intended, not "fixed".

---

### Edge Cases

- **A legitimately mission-tier artefact trips the layout gate.** Happened on the gate's first run: 17 step contracts at `missions/built_in_step_contracts/`. Resolved as a documented carve-out, pinned *positively* so the exception cannot hide a real stray.
- **Deleting a stray removes a graph node.** Must not happen — the nine were dead. Proven by zero count movement (NFR-003).
- **Promoting a dormant artefact makes it live.** The PowerShell toolguide becomes reachable: a behavioural change inside a layout cleanup, disclosed rather than smuggled.
- **A duplicate is divergent, not identical.** Two files, one id, different content — the built-in twin wins; the stray must not be the one preserved.
- **The `refines` relation has never been exercised built-in.** A silent downgrade would be invisible without an explicit round-trip assertion.
- **Regenerating fragments by hand** desynchronizes the freshness test; regeneration must go through the CLI.
- **An entry is added to the authored tier but not removed from the YAML.** The overlay merge keys on `(source, target, relation)` and *overwrites*, so the duplicate produces identical output and a byte-style proof passes on a half-done migration. Completion must be asserted by the inventory gate (NFR-005), never by the diff invariant alone.
- **A relationship is disguised as raw material** to dodge the gate — by pointing at an artefact's markdown payload (`POWERSHELL_SYNTAX.md` is a toolguide's content) or at a mission-tier template (empty glob, so a resolver-based predicate calls it raw material). Both shapes already exist in the tree, which is why the exemption is an enumerated allowlist rather than a computed predicate.
- **A migration keyed on reference `type` instead of source kind** mis-types 118 of 372 structured entries. The mapping table in `research/inline-reference-inventory.md` is the contract.
- **The org→DRG bridge silently drops a cross-layer edge** (built-in source → pack target) with no warning and no conflict record. NFR-004 must assert the *built-in fragment* round-trip, which is the path this mission's `refines` edge actually takes; the bridge defect is a separate finding.
- **A grep gate for `graph.yaml` sweeps in `.kittify/doctrine/graph.yaml`**, which is a live project-tier path, and the deliberate mentions that name the dead path in order to forbid it. The gate needs both discriminators or it false-reds on correct code.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-000 | Close P0 #2934 with a durability proof | As a maintainer, I want the planning-only closeout test to exercise the real pipeline and prove the status pair reaches the target branch's committed tree. | High | Done (`ca5e91c8f`, `775323199`) — owns SC-008, which previously had no requirement row |
| FR-001 | Layout gate | As a maintainer, I want a misplaced artefact to fail a test so it cannot silently never load. | High | Done (`f7ee9fb02`) — **but see SC-016**: validates only 1 of 2 mandatory path segments |
| FR-002 | Clear the nine dead artefacts | As a maintainer, I want one artefact id to mean one file so I cannot edit a stale divergent copy. | High | Done (`f7ee9fb02`) |
| FR-003 | Promote the PowerShell toolguide | As an agent on Windows, I want the shipped PowerShell guidance to actually resolve. | Medium | **Partial** — loads from the pack layer, but is a **graph orphan** with zero inbound edges, so no agent is handed it. "Resolves" was operationalized as id-lookup, not reachability. Needs an inbound edge (precedent: `DIRECTIVE_042 --requires--> asset:common-docs-structural-lint`, hand-authored for this exact shape). |
| FR-004 | Freeze the reference-kind enums | As a contributor, I want the deprecated surface marked frozen so I do not "fix" it by widening it. | High | Open |
| FR-005 | Correct the unfollowable migration hint | As an operator, I want the rejection hint to name a file that exists. | High | Open |
| FR-006 | Remove the phantom `shipped/` layer | As an author, I want guidance to name the real pack directory. | Medium | **Open — earlier "Done" was false.** `f7ee9fb02` fixed 6 cross-links + 2 READMEs; **21 references survive in 8 files**, including two operator-facing `SKILL.md` files that instruct readers to read `src/doctrine/<kind>/shipped/`, and a canonical glossary term body. Superseded by FR-020. |
| FR-007 | Author the test-quality doctrine series | As a reviewer, I want the over-mocking failure mode to be a citable rule. | High | Open |
| FR-008 | Split `DIRECTIVE_041` intent to the paradigm | As a reader, I want the mindset and the binding rule to live in the right artefact kinds. | Medium | Open |
| FR-009 | Augment styleguides/tactics; excise duplicated checklists to assets | As a curator, I want one copy of each checklist. | Medium | Open |
| FR-010 | Update `doctrine-daphne` with the canonical structure | As a curator agent, I want the pinned model at load time. | High | Open |
| FR-011 | Close the validator parity gap | As a contributor, I want local validation to predict CI. | Low | Open |
| FR-013 | Migrate the 559 MIGRATE-class entries to authored edges | As a maintainer, I want one relationship authority in the tree, not a deprecated one still being derived. Scope and relation-mapping are defined by `research/inline-reference-inventory.md`, not by shape. | High | Open |
| FR-014 | Retire **all** edge production from the extractor | As a maintainer, I want the mechanism that re-derives relationships removed entirely, so the class cannot regrow. Operator decision 2026-07-26: **full retirement**, not reference passes only. Covers the reference passes (559), the action/`scope` pass (157), mission-type projection (21), template instantiation (8), `_CURATED_ARTIFACT_EDGES` (13), and the calibrator's synthesised `scope` edges (21). Node discovery stays derived. Also deletes the two dead `tactic_refs` passes and the vestigial `_SKIP_REF_TYPES`. | High | Open |
| FR-024 | Author the 215 structural edges | As a maintainer, I want `scope`, mission-type, template-instantiation, curated, and calibrated edges authored rather than computed, since they are the edges the closure actually traverses. `scope` is the **seed** of every context resolution, so leaving it derived would leave the load-bearing relation outside the authority. | High | Open |
| FR-025 | Promote the calibrator's 21 synthesised `scope` edges | As a reviewer, I do not want edges invented from a policy inequality (`\|review\| >= 0.80 * \|implement\|`) sitting in the graph indistinguishable from authored intent. Promote each to an authored edge with a ledger line, then delete `calibrate_surfaces`. This is the same laundering as FR-018's 55, at larger scale and on the seed relation. | High | Open |
| FR-026 | Absorb both Python edge registries into the authored tier | As a maintainer, I want one authoring surface, measurably. `hand_authored_overlay.py` (17 edges, 6 nodes — every `rejects`, every `reconciles_tension`, both `in_tension_with`) and `_CURATED_ARTIFACT_EDGES` (13 edges, all four `specializes_from`) both move to YAML and **both modules are deleted**. Without this the surface count holds flat at 11 while the PR claims consolidation. | High | Open |
| FR-027 | Collapse the duplicated profile→directive field | As a curator, I want one field to own "which directives does this profile cite". `context-sources.directives` (67) and `directive-references` (68) are the **same set on all 18 profiles** and have already drifted (`python-pedro` carries `034` in one only). **Prerequisite to FR-013** per operator decision: reconcile the drift, keep `directive-references` (it carries rationale and seeds the charter closure), delete `context-sources.directives`. | High | Open |
| FR-028 | Add `aliases: list[str]` to doctrine **artefacts** (supersedes the `DRGEdge.label` plan) | As a curator, I want the 219 reference labels to live on the artefact they name, not on every pointer to it — enabling grep now and semantic search later. **Measured:** the 219 label occurrences collapse to **102 distinct artefacts**, and the 8 targets carrying more than one label are genuine synonym sets (`tdd-red-green-refactor` → "Red-Green-Refactor" / "TDD Red-Green-Refactor" / "Test Driven Development (TDD)"). So these were never edge metadata; they are artefact names repeated at each pointer. Storing them as `DRGEdge.label` would have scattered one name across up to a dozen edges and preserved 8 silent disagreements that `aliases` merges into legitimate alias lists. Also removes the `DRGEdge` schema change and its six-consumer ripple. | High | Open |
| FR-029 | I19 — zero-producer lint | As a maintainer, I want a schema slot with no producer to fail a test, because the precedent is 3-for-3 inert (one for 162 days behind green tests). **Rank 1, gates nothing, guards FR-028.** | High | Open |
| FR-030 | I2 — close the four-site silent-kind-drop | As a maintainer, I want an unknown kind to fail loudly at all four sites rather than be dropped. **Must precede FR-028 and FR-013/014**: sites 3 and 4 would silently delete a new field at extraction and regeneration. Collides with `#2532` — pin behaviourally. Unblocks `#2468`/`#2847`/`#2862`/`#2829`. | High | Open |
| FR-031 | I3b/I3c — `extra="forbid"` on `DRGNode`/`DRGEdge`/`AgentProfile` + writers + round-trip | As a maintainer, I want an unknown field to be a load error, not silence. Verified: the DRG models carry **no `model_config`** and the writers are field-by-field. **Model + writer + round-trip test in ONE commit** — this is the mechanism that makes FR-028 real rather than inert. | High | Open |
| FR-032 | Carry `impacts` in the authored tier; migrate the two authored tension edges | As a curator, I want `impacts` (signed, authored-only, never derived) on the edge, with `impacts < 0` being the tension claim. Migrate `directive.graph.yaml:90-93` and `:103-106` to `{relation: impacts, impacts: <negative>}` **preserving each `reason`**; `reconciles_tension` survives re-pointed. Gated on G2/ADR-D2. | High | Open |
| FR-015 | Gate the relationship-free invariant | As a contributor, I want any MIGRATE-class entry to fail a test rather than pass review. Gate walks `steps[]` and all five MIGRATE fields, deriving scope from the inventory module. | High | Open |
| FR-016 | Add an authored-edge YAML tier the generator merges | As a doctrine author, I want to declare relationships in YAML that regeneration preserves instead of overwriting. | High | Open |
| FR-017 | Preserve authored rationale and labels through migration | As a curator, I want the 68 procedure rationales and 219 reference labels to survive rather than be deleted to make a proof pass. | High | Open |
| FR-018 | Human review of the 55 hardcoded-`suggests` relations | As a maintainer, I do not want an inference artifact laundered into declared intent. | Medium | Open |
| FR-019 | Preserve governance seeding untouched | As an agent, I want profile-routed prompts to keep rendering directives and tactics after the migration. | High | Open |
| FR-020 | Correct the surviving `shipped/` references | As a reader, I want authoring guidance and glossary bodies to name paths that exist. | High | Open |
| FR-021 | Fix the org→DRG bridge's silent cross-layer drop | As a pack author, I want an unresolvable edge to fail loudly instead of vanishing. Today a built-in-source→pack-target edge returns `None` with no warning and no conflict record; a bare built-in target id is blindly re-kinded to a node that may not exist; and a URN-shaped target dies with a raw pydantic error instead of a typed pack error. | High | Open |
| FR-022 | Fix the documented `specializes_from` org-pack example | As a reader following `CLAUDE.md`, I want the documented lineage snippet to actually produce an edge. The `urn:profile:` shape in the docs is silently dropped by the bridge — documentation that yields an inert declaration. | Medium | Open |
| FR-023 | Retype daphne's `applies` edge and gate the relation | As a curator, I want `procedure:onboard-external-agent-to-pack` reachable, and no future artefact to author a no-op `applies` edge. | Medium | Open |
| FR-012 | Record both ADRs | As a future maintainer, I want the decisions citable, not re-derived. | High | Done (`c7df59e22`, `f7ee9fb02`) |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Gate non-vacuity | The layout gate rejects both real violation shapes in a self-mutation test, and its allowlist has exactly 0 entries. | Correctness | High | Done |
| NFR-002 | The extractor is used as a migration oracle, not a durable producer | During migration, `spec-kitty doctrine regenerate-graph` is the oracle that says what each entry's edge *should* be (idempotency verified: three consecutive runs, zero diff). After FR-014, the **authored edge tier is the source** and no generated `*.graph.yaml` is ever hand-edited. The end state must not depend on the extractor still running — see "The extractor is scaffolding" below. | Reliability | High | Open |
| NFR-003 | Cleanup causes zero node loss | The **eight deletions** move node/edge/orphan counts by exactly 0. The separate **one promotion** is an expected +1 node / +0 edges / +1 orphan. (Earlier wording said "nine deletions … exactly 0", which its own Done evidence falsified — git shows 8 deletions + 3 renames.) | Correctness | High | Done |
| NFR-004 | `refines` round-trips through the built-in fragment load | The `041 → paradigm` `refines` edge survives the **built-in fragment** load path (`load_graph_or_dir`) without downgrading to `applies` — verified as the path this edge actually takes. Measured baseline: 0 `refines` edges exist built-in today, so #2079's downgrade fix has never been exercised by anything shipped. The org→DRG **bridge** is explicitly *not* this edge's path and is covered by FR-021 instead. | Correctness | High | Open |
| NFR-012 | No `applies` edge is authored | `applies` is a documented dead sink — no traversal reads it, so aliasing a real relation onto it silently makes the edge a no-op (the #2079 defect class). Exactly one exists in the built-in graph today, and it is `agent_profile:doctrine-daphne --applies--> procedure:onboard-external-agent-to-pack` — the only inbound edge that procedure has, making daphne's own operating procedure unreachable. | Correctness | Medium | Open |
| NFR-005 | The legacy relationship surface reaches zero | Zero MIGRATE-class entries remain across **all five** fields (`references`, `steps[].references`, `directive_refs`, `tactic_refs`, `tactic-references`, `context-sources.directives`). Measured by `scripts/doctrine/inline_reference_inventory.py`, which the gate imports — **not** by a hardcoded count and **not** by entry shape. The 14 RAW_MATERIAL entries survive as an enumerated `(file, path)` allowlist with a reason each; the 188 GOVERNANCE entries are untouched. | Maintainability | High | Open |
| NFR-007 | Migration is proven by a structured diff invariant | The regenerated graph differs from the committed **pre-migration baseline manifest** only by the enumerated, ledgered deviations: added `reason`/label content (FR-017) and any relation changed by review (FR-018). Every other node, edge, relation, `when`, and `reason` is unchanged. Byte-identity is **not** the invariant — FR-017 and FR-018 break it by design, and a byte proof would pressure the migrator into deleting authored content to pass. | Correctness | High | Open |
| NFR-008 | The baseline is a committed artefact, not a local snapshot | A per-fragment SHA-256 manifest of the pre-migration graph is committed **before** any artefact YAML is edited. Without it, "regenerate and compare" degenerates into `regenerate(tree) == regenerate(tree)` — a tautology of determinism that is blind to content loss. | Correctness | High | Open |
| NFR-009 | Pass deletion is proven by an observed RED — as an **in-process ablation**, not a git state | For each edge-producing pass, an ablation harness deletes it over a *tree copy* and asserts the graph loses exactly the expected N edges. It must be in-process: as a git sequence it is unachievable, because NFR-002 needs the extractor alive as the migration oracle while NFR-009 needs it deleted, and once the authored tier carries the edges the deletion is a no-op again — the same vacuity one layer up. This method is already proven: two review lenses independently reproduced the 559 count by exactly this ablation. | Correctness | High | Open |
| NFR-013 | The occurrence-classification guardrail is active | `meta.json` carries `change_mode: bulk_edit` and an admissible `occurrence_map.yaml` exists, so DIRECTIVE_035 (`enforcement: required`) actually gates implement/review/finalize-tasks. It was **inert by omission** until 2026-07-26: a 559-occurrence, 169-file, same-surface migration was escaping the repo's own required bulk-edit guardrail because a metadata field was never set — this mission's defect class in this mission's own metadata. The map's `do_not_change` entries turn the GOVERNANCE and RAW_MATERIAL exemptions from a hope into a gate, and `check_diff_compliance` makes the reviewer review *exceptions* rather than a 169-file sweep. | Correctness | High | In progress |
| NFR-010 | Governance resolution is unchanged — asserted at the **production** seams | For every built-in agent profile and all 24 actions, the resolved context and the **rendered** governance text are byte-equal before and after. Asserted at `charter/context.py` closure resolution and at the two inline profile-field render paths — **not** at `resolve_governance_for_profile`, which has no production caller (only re-exports and tests), so pinning it would have left this mission's anti-silence guard silently green while the rendered prompt changed. Requires a **committed** before-snapshot for the same reason NFR-008 does. | Correctness | High | Open |
| NFR-011 | The FR-015 gate is non-vacuous | Mirrors NFR-001. The gate plants and rejects: a structured `{type, id}` entry, a step-level entry, a `directive_refs` bare-id entry, and a relationship disguised as raw material (a path to an artefact's markdown payload, and a path to a mission-tier template). | Correctness | High | Open |
| NFR-006 | Golden counts stay a contract | Every added node/edge extends the composition ledger in `test_extractor_projection.py`; counts are never bumped without a ledger entry. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Edges are the only relationship authority | Per ADR 2026-07-26-1: author relationships as DRG edges; never widen a `<kind>_reference.type` enum; never add an inline `references:` block. | Technical | High | Active |
| C-002 | Pack layout is mandatory | Per ADR 2026-07-26-2: `<type>/<pack>/[<category>/]<name>`; categories nest inside the pack. | Technical | High | Active |
| C-003 | ~~Everything lands on one branch~~ **SUPERSEDED 2026-07-26** | Original form: "All work stays on `fix/2934-demock-planning-closeout-test` and ships as one PR (#2936)." Both the branch and the PR are **merged** (`1a15bcf6c`), so the constraint named surfaces that no longer exist. **Replaced by:** the work ships as five sequenced missions (A → B1 → B2 → C; D independent of B2), each its own draft PR to `main`, each independently green. The operator merges. Rationale: ~600 file touches is not reviewable in one PR, and C2 of the sequencing authority forbids two all-surface sweeps sharing one occurrence map — this scope has three. | Business | High | **Superseded** |
| C-004 | Structural work is not deferred while 3.2.6 is unreleasable | No known structural defect found by this mission is handed to a follow-up issue. Deferring is treated as the same failure mode as greenwashing: it converts a known defect into an invisible one. Supersedes this constraint's original "fence the migration out" form, withdrawn by the operator. | Business | High | Active |
| C-005 | Editing `DIRECTIVE_041` is its own reviewed change | It is live at `enforcement: required`; audit inbound edges before touching it. | Technical | High | Active |
| C-006 | Inherited base CI reds are not touched | The 6 `arch-adversarial` failures are byte-identical to `origin/main`; leave them honest (ADR 2026-07-17-1). `quality-gate` fails only as their cascade. | Technical | High | Active |
| C-007 | Do not run the full architectural suite | It leaks resources and blocks the working session; run targeted tests only. | Technical | High | Active |
| C-008 | G2/ADR-D2 is answered before anyone opens `extractor.py` | The superseding ADR must decide which relation carries `impacts` after `in_tension_with` retires. The answer moves FR-014's blast radius from ~45–60 files to ~5–10, so building first risks doing an order of magnitude more work than needed. **Operator-only sign-off.** | Technical | High | **Closed 2026-07-26** — ADR 2026-07-26-3 decided ADR-D2: a new `Relation.IMPACTS`. The operator chose the clean end state over the cheap one, overruling the reviewing analysis's evidence-per-cost recommendation of option B, and accepted the ~45–60 file cost knowingly. |
| C-009 | No new schema slot without a producer and a coverage gate in the same commit | Governing precedent: 3-for-3 inert in this repo, one for 162 days behind green tests. Binds FR-028 (`aliases`) and FR-032 (`impacts`). | Technical | High | Active |
| C-010 | `I2` cannot be sequenced after any new edge field | `extractor.py:133-145` and `:1210-1229` would silently delete the field at extraction and regeneration, so the field would ship inert and the tests would stay green. | Technical | High | Active |
| C-011 | Operator-only, never agent-drafted | **Remaining:** the charter deprioritisation statement. **D-4 settled 2026-07-26** — constant-sum budget for the weights, per-weight provenance, elicitation questions carried on the value-set artefact, I8 first (see `plan.md`). **Discharged 2026-07-26:** G2/ADR-D2 (decided in ADR `2026-07-26-3`) · ADR-D8 (the asymmetric pair, symmetrised to `+0.75`) · the upstream report to the AMMERSE author — **withdrawn, not deferred**: the operator holds prior written consent from J.B. Crossland to use the AMMERSE idea and publish his own procedure under his own IP, so accreditation and mention discharge the obligation in full. No report is owed and nothing gates on one. | Business | High | Active |

### Key Entities

- **Doctrine artefact**: a kind-typed YAML at `<type>/<pack>/[<category>/]<name>`. Loadable only from inside a pack layer.
- **Pack layer**: the provenance segment (`built-in` today). Becomes the outermost segment after pack extraction (`<pack id>/<type>/...`).
- **DRG edge**: a typed relationship over the `Relation` vocabulary; the sole authority for artefact→artefact relationships.
- **Inline `references:` block**: the pre-DRG relationship surface. Frozen: readable, closed to growth, slated for migration.
- **Graph fragment**: per-kind `<kind>.graph.yaml`, generated by the extractor; regenerated only via the CLI.
- **Golden-count baseline**: pinned node/edge/orphan cardinality with a composition ledger; a contract, not an incidental.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A doctrine artefact placed outside `<type>/<pack>/` fails a test that names the correct shape — verified for both real-world violation shapes, with an allowlist of 0 entries.
- **SC-002**: Zero doctrine artefacts sit outside the pack layer, and zero `<type>/shipped/` directories are referenced in guidance or cross-links. All previously-broken cross-links resolve on disk.
- **SC-003**: Zero source sites instruct an operator to edit `src/doctrine/graph.yaml`; the rejection hint and its contract fixture name an existing per-kind fragment.
- **SC-004**: The test-quality series (paradigm + `DIRECTIVE_047` + procedure + 2 anti-patterns + 4 assets, plus the augments) resolves with **zero** pack-validation errors, and every resolved-only node has ≥1 inbound edge.
- **SC-005**: The `041 → paradigm` `refines` edge is present after regeneration and has not been downgraded to `applies`.
- **SC-006**: The regenerated graph matches the **committed** fragments (freshness), and golden counts match a ledger entry explaining every delta. *Not* "a second consecutive run is identical" — regeneration is a pure function of the tree, so that is a tautology of determinism and cannot detect content loss.
- **SC-007**: The `doctrine-daphne` profile states the layout convention, the edges-only rule, and the regeneration command.
- **SC-008**: #2934 closes with its durability proof intact — the status pair is asserted to reach the target branch's committed tree, not merely a spy's request set.
- **SC-009**: `scripts/doctrine/inline_reference_inventory.py` reports **0** MIGRATE-class entries across all five fields (including `steps[]`); the 14 RAW_MATERIAL entries survive and match the enumerated allowlist exactly; the 188 GOVERNANCE entries are unchanged.
- **SC-010**: The regenerated graph differs from the committed pre-migration SHA manifest only by the ledgered deviations (FR-017 additions, FR-018 relation changes) — every other node, edge, relation, `when`, and `reason` identical.
- **SC-011**: `extractor.py` produces **no edges at all** — no reference pass, no action/`scope` pass, no mission-type projection, no template-instantiation pass, no curated registry, no calibrator. All 774 edges load from the authored tier, and **deleting every edge-producing function does not change the resolved graph**. What survives is node discovery plus validation. This is now a falsifiable claim: an earlier revision asserted it while the graph still derived 215 edges, which made it vacuously true at load time and self-contradictory as a scope statement.
- **SC-012**: Governance resolution for every built-in agent profile returns an identical `(directives, tactics, styleguides, toolguides, procedures)` tuple before and after the migration.
- **SC-013**: All 68 procedure rationales survive on their edges, and the 219 reference labels survive as `aliases` on the 102 artefacts they name — each accounted for by a ledger entry, with the 8 multi-label artefacts carrying alias lists rather than a single arbitrary winner.
- **SC-021**: The zero-producer lint (FR-029) fails on a planted schema slot that nothing produces, and passes on the shipped tree — so `aliases` and `impacts` cannot ship inert.
- **SC-022**: An unknown field on `DRGNode`/`DRGEdge`/`AgentProfile` is a **load error**, not silence; and a round-trip test proves `aliases` survives write→read (the writers are field-by-field, so this is the assertion that matters).
- **SC-023**: An unknown kind fails loudly at all four silent-drop sites, proven by a planted unknown kind at each.
- **SC-024**: `in_tension_with` has zero members after retirement; the two authored tension edges carry `{relation: impacts, impacts: <negative>}` with their original `reason` text intact; `reconciles_tension` still resolves against the negative-`impacts` pairs.
- **SC-014**: The 55 hardcoded-`suggests` relations have a recorded human verdict; any retyped relation is a ledgered deviation.
- **SC-015**: Zero `<kind>/shipped/` references remain under `src/doctrine/` (currently 21 across 8 files), and every relative cross-link in built-in markdown resolves on disk. Enforced by a gate, since the earlier fix-by-inspection missed 21 of 27.
- **SC-016**: The layout gate validates **both** mandatory path segments — `parts[0] == kind.plural` and `parts[1] == built-in` — so a right-pack/wrong-type file (e.g. a tactic under `assets/built-in/`) is rejected.
- **SC-017**: `toolguide:powershell-syntax` has ≥1 inbound edge from an activatable artefact, or FR-003 is restated as "loadable, not yet referenced" — no Done row whose user story is unmet.
- **SC-018**: FR-004's enum freeze is enforced by a ratchet on the four enums' member sets, not only by a comment; adding a member fails a test.
- **SC-019**: The excised checklist content (FR-009) appears exactly once under `src/doctrine/` — de-duplication is measured, not assumed.
- **SC-020**: `spec-kitty doctrine validate` and the strict canonical tests return matching verdicts on a shared corpus of invalid artefacts (FR-011).
