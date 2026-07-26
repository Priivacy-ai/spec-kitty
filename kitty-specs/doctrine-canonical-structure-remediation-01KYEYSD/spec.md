# Mission Specification: Doctrine Canonical Structure Remediation

**Mission Branch**: `fix/2934-demock-planning-closeout-test` (single_branch topology — see C-003)
**Created**: 2026-07-26
**Status**: Draft
**Input**: User description: "this scope is starting to feel like a same-branch unblock mission more than a series of ops... the systemic fix is the real structural remediation work that needs to happen now, even if it slows some other deliveries"

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

- **A legitimately mission-tier artefact trips the layout gate.** Happened on the gate's first run: 18 step contracts at `missions/built_in_step_contracts/`. Resolved as a documented carve-out, pinned *positively* so the exception cannot hide a real stray.
- **Deleting a stray removes a graph node.** Must not happen — the nine were dead. Proven by zero count movement (NFR-003).
- **Promoting a dormant artefact makes it live.** The PowerShell toolguide becomes reachable: a behavioural change inside a layout cleanup, disclosed rather than smuggled.
- **A duplicate is divergent, not identical.** Two files, one id, different content — the built-in twin wins; the stray must not be the one preserved.
- **The `refines` relation has never been exercised built-in.** A silent downgrade would be invisible without an explicit round-trip assertion.
- **Regenerating fragments by hand** desynchronizes the freshness test; regeneration must go through the CLI.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Layout gate | As a maintainer, I want a misplaced artefact to fail a test so it cannot silently never load. | High | Done (`f7ee9fb02`) |
| FR-002 | Clear the nine dead artefacts | As a maintainer, I want one artefact id to mean one file so I cannot edit a stale divergent copy. | High | Done (`f7ee9fb02`) |
| FR-003 | Promote the PowerShell toolguide | As an agent on Windows, I want the shipped PowerShell guidance to actually resolve. | Medium | Done (`f7ee9fb02`) |
| FR-004 | Freeze the reference-kind enums | As a contributor, I want the deprecated surface marked frozen so I do not "fix" it by widening it. | High | Open |
| FR-005 | Correct the unfollowable migration hint | As an operator, I want the rejection hint to name a file that exists. | High | Open |
| FR-006 | Remove the phantom `shipped/` layer | As an author, I want guidance to name the real pack directory. | Medium | Done (`f7ee9fb02`) |
| FR-007 | Author the test-quality doctrine series | As a reviewer, I want the over-mocking failure mode to be a citable rule. | High | Open |
| FR-008 | Split `DIRECTIVE_041` intent to the paradigm | As a reader, I want the mindset and the binding rule to live in the right artefact kinds. | Medium | Open |
| FR-009 | Augment styleguides/tactics; excise duplicated checklists to assets | As a curator, I want one copy of each checklist. | Medium | Open |
| FR-010 | Update `doctrine-daphne` with the canonical structure | As a curator agent, I want the pinned model at load time. | High | Open |
| FR-011 | Close the validator parity gap | As a contributor, I want local validation to predict CI. | Low | Open |
| FR-013 | Migrate all inline artefact relationships to edges | As a maintainer, I want one relationship authority in the tree, not a deprecated one still being derived. | High | Open |
| FR-014 | Retire the extractor's reference-extraction passes | As a maintainer, I want the mechanism that re-derives the legacy surface removed, so the class cannot regrow. | High | Open |
| FR-015 | Gate the relationship-free invariant | As a contributor, I want a structured reference entry to fail a test rather than pass review. | High | Open |
| FR-012 | Record both ADRs | As a future maintainer, I want the decisions citable, not re-derived. | High | Done (`c7df59e22`, `f7ee9fb02`) |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Gate non-vacuity | The layout gate rejects both real violation shapes in a self-mutation test, and its allowlist has exactly 0 entries. | Correctness | High | Done |
| NFR-002 | Regeneration is idempotent and CLI-driven | `spec-kitty doctrine regenerate-graph` run twice produces a zero diff; fragments are never hand-edited. | Reliability | High | Open |
| NFR-003 | Cleanup causes zero node loss | Deleting the nine strays moves node/edge/orphan counts by exactly 0. | Correctness | High | Done (verified: only +1 node, from the promotion) |
| NFR-004 | `refines` round-trips end-to-end | The `041 → paradigm` `refines` edge survives regeneration and the org→DRG bridge without downgrading to `applies`. Measured baseline: 0 `refines` edges exist built-in today. | Correctness | High | Open |
| NFR-005 | The legacy relationship surface reaches zero | Zero structured `{type, id}` reference entries remain under `src/doctrine/`, and zero remaining path-string entries resolve to a built-in artefact. Only raw non-artefact paths survive (14 entries). | Maintainability | High | Open |
| NFR-007 | Migration is proven by byte-identical regeneration | Regenerating the fragments after the migration yields a byte-identical fragment set to the pre-migration baseline, and again after the extraction passes are deleted. This single invariant covers all 414 migrated entries. | Correctness | High | Open |
| NFR-006 | Golden counts stay a contract | Every added node/edge extends the composition ledger in `test_extractor_projection.py`; counts are never bumped without a ledger entry. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Edges are the only relationship authority | Per ADR 2026-07-26-1: author relationships as DRG edges; never widen a `<kind>_reference.type` enum; never add an inline `references:` block. | Technical | High | Active |
| C-002 | Pack layout is mandatory | Per ADR 2026-07-26-2: `<type>/<pack>/[<category>/]<name>`; categories nest inside the pack. | Technical | High | Active |
| C-003 | Everything lands on one branch | All work stays on `fix/2934-demock-planning-closeout-test` and ships as one PR (#2936). Operator call; the P0 close is deliberately gated on the structural work. | Business | High | Active |
| C-004 | Structural work is not deferred while 3.2.6 is unreleasable | No known structural defect found by this mission is handed to a follow-up issue. Deferring is treated as the same failure mode as greenwashing: it converts a known defect into an invisible one. Supersedes this constraint's original "fence the migration out" form, withdrawn by the operator. | Business | High | Active |
| C-005 | Editing `DIRECTIVE_041` is its own reviewed change | It is live at `enforcement: required`; audit inbound edges before touching it. | Technical | High | Active |
| C-006 | Inherited base CI reds are not touched | The 6 `arch-adversarial` failures are byte-identical to `origin/main`; leave them honest (ADR 2026-07-17-1). `quality-gate` fails only as their cascade. | Technical | High | Active |
| C-007 | Do not run the full architectural suite | It leaks resources and blocks the working session; run targeted tests only. | Technical | High | Active |

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
- **SC-006**: `spec-kitty doctrine regenerate-graph` produces a zero diff on a second consecutive run, and golden counts match a ledger entry explaining every delta.
- **SC-007**: The `doctrine-daphne` profile states the layout convention, the edges-only rule, and the regeneration command.
- **SC-008**: #2934 closes with its durability proof intact — the status pair is asserted to reach the target branch's committed tree, not merely a spy's request set.
- **SC-009**: Zero structured `{type, id}` reference entries and zero artefact-resolving path entries remain under `src/doctrine/`; the 14 raw-material path entries survive and are recognised as non-relationships by the gate.
- **SC-010**: The fragment set regenerated after the migration is byte-identical to the pre-migration baseline — and still byte-identical after the extraction passes are deleted.
- **SC-011**: `extractor.py` contains no reference-extraction pass; a grep for the removed pass names returns nothing, and the fragments are authored rather than derived.
