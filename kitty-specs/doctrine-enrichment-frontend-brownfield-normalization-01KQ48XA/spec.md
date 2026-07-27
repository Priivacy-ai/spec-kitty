# Doctrine Enrichment: Frontend, Brownfield, and Tactic Normalization

## Context

Spec Kitty's doctrine library encodes development practices as machine-readable artifacts that agents consume when planning, implementing, and reviewing work. As the set of supported practices grows, the library needs both new content and structural order.

This mission extends the library on four axes:

1. **New profiles** — a browser-side frontend specialist (Frontend Freddy) and a Node.js server-side specialist (Node Norris), both specializing from `implementer-ivan`
2. **New tactics** — brownfield analysis artifacts, new architecture tactics, and adapted content from existing practitioner-authored practice libraries
3. **Structural normalization** — grouping existing shipped tactics into category subdirectories (testing, analysis, communication, architecture) following the established `refactoring/` pattern
4. **Profile enrichment + test safety net** — adding operating procedures to existing profiles and a generic acceptance test for the profile-specialization tactic-inheritance contract

Source material for adapted tactics is drawn from the canonical pattern repository at `patterns.sddevelopment.be`. Provenance is recorded in `src/doctrine/_reference/` import files; shipped YAML artifacts contain only a brief attribution note in the `notes` field where applicable.

## Actors

| Actor | Description |
|-------|-------------|
| Doctrine author | Defines and curates doctrine artifacts |
| Agent consumer | Loads profiles, tactics, and approaches at mission time |
| Reviewer | Reviews work packages for conformance to profile-level constraints |
| Test suite | Validates doctrine schema and semantic contracts |

## Functional Requirements

### FR-001: Frontend Freddy Agent Profile

**Status**: In Scope

Create `src/doctrine/agent_profiles/shipped/frontend-freddy.agent.yaml` as a browser-side, UI-layer implementer profile.

**Scope boundary**: Frontend Freddy owns the browser rendering layer — DOM manipulation, CSS, component frameworks, accessibility, and paint performance. Server processes, HTTP handlers, and database concerns are explicitly out of scope (owned by Node Norris or other backend profiles).

| Sub-requirement | Description |
|----------------|-------------|
| FR-001.1 | Profile ID `frontend-freddy`; name `Frontend Freddy`; `schema-version: "1.0"` |
| FR-001.2 | `specializes-from: implementer-ivan` |
| FR-001.3 | `roles: [implementer]` |
| FR-001.4 | `applies_to_languages: [javascript, typescript, html, css]` |
| FR-001.5 | Capabilities: browser-component implementation, WCAG 2.1 accessibility compliance, responsive and mobile-first layout, frontend testing (unit, component, e2e), bundle optimization, design-system integration |
| FR-001.6 | `avoidance-boundary` explicitly names: server-side Node.js processes, HTTP handler authoring, database access, UX/UI design decisions (deferred to Designer Dagmar), architectural decisions, and managing other agents |
| FR-001.7 | `purpose` describes the role as translating UI specifications and component designs into tested, accessible, performant browser code |
| FR-001.8 | `initialization-declaration` is first-person, names Frontend Freddy, and states the browser-side scope boundary clearly |
| FR-001.9 | `specialization-context.frameworks`: react, vue, svelte, tailwind, vite, vitest, playwright. File patterns: `src/**/*.{tsx,jsx,vue,svelte,css,scss}`, `**/*.stories.{ts,tsx}` |
| FR-001.10 | `mode-defaults` covers at minimum: implementation (TDD-driven component development), accessibility audit (WCAG compliance review), and performance optimization (bundle analysis and critical-path review) |
| FR-001.11 | `self-review-protocol` steps: lint (eslint/biome), type-check (tsc --noEmit for TS projects), unit/component tests pass (vitest), e2e smoke pass (playwright), accessibility gate (axe-core / pa11y), no new bundle size regressions |
| FR-001.12 | `directive-references` includes at minimum: DIR-010 (Specification Fidelity), DIR-024 (Locality of Change), DIR-030 (Test and Typecheck Quality Gate), DIR-034 (Test-First Development) |

### FR-002: Node Norris Agent Profile

**Status**: In Scope

Create `src/doctrine/agent_profiles/shipped/node-norris.agent.yaml` as a Node.js server-side implementer profile.

**Scope boundary**: Node Norris owns the Node.js runtime layer — HTTP APIs, streaming, event-loop discipline, file I/O, npm ecosystem, and server-process lifecycle. Browser DOM, CSS, and component rendering are explicitly out of scope (owned by Frontend Freddy).

| Sub-requirement | Description |
|----------------|-------------|
| FR-002.1 | Profile ID `node-norris`; name `Node Norris`; `schema-version: "1.0"` |
| FR-002.2 | `specializes-from: implementer-ivan` |
| FR-002.3 | `roles: [implementer]` |
| FR-002.4 | `applies_to_languages: [javascript, typescript]` |
| FR-002.5 | Capabilities: Node.js HTTP API implementation (Express/Fastify/NestJS), async/await and Promise discipline, streaming and backpressure handling, npm package management, server-process lifecycle, integration testing with supertest or equivalent |
| FR-002.6 | `avoidance-boundary` explicitly names: browser DOM and CSS, React/Vue/Svelte rendering, mobile UI concerns, UX/UI design decisions, architectural decisions, and managing other agents |
| FR-002.7 | `purpose` describes the role as implementing reliable, non-blocking Node.js services with clear API contracts, disciplined event-loop use, and full test coverage before handoff |
| FR-002.8 | `initialization-declaration` is first-person, names Node Norris, and states the server-side scope boundary clearly |
| FR-002.9 | `specialization-context.frameworks`: express, fastify, nestjs, vitest, jest, supertest, prisma, typeorm. File patterns: `src/**/*.{ts,js}`, `**/*.spec.{ts,js}`, `**/package.json`, `**/tsconfig*.json` |
| FR-002.10 | `mode-defaults` covers at minimum: implementation (TDD-driven service development), debugging (event-loop profiling and async trace analysis), and integration testing (contract verification against external services) |
| FR-002.11 | `self-review-protocol` steps: lint (eslint), type-check (tsc --noEmit for TS), unit tests pass, integration tests pass, no unhandled promise rejections in test run, `npm audit` passes at configured severity threshold |
| FR-002.12 | `directive-references` includes at minimum: DIR-010 (Specification Fidelity), DIR-024 (Locality of Change), DIR-030 (Test and Typecheck Quality Gate), DIR-034 (Test-First Development) |

### FR-003: Brownfield Analysis Doctrine Artifacts

**Status**: In Scope

Create doctrine artifacts for brownfield code analysis — the practice of understanding existing codebases before modifying or extending them.

| Sub-requirement | Description |
|----------------|-------------|
| FR-003.1 | Adapt the `code-documentation-analysis` tactic into `src/doctrine/tactics/shipped/analysis/code-documentation-analysis.tactic.yaml` using the standard tactic YAML schema |
| FR-003.2 | Adapt the `terminology-extraction-mapping` tactic into `src/doctrine/tactics/shipped/analysis/terminology-extraction-mapping.tactic.yaml` |
| FR-003.3 | Both tactics retain their original purpose and procedure, expressed in YAML schema fields (`id`, `name`, `purpose`, `steps`, `preconditions`, `failure_modes`) |
| FR-003.4 | The `notes` field in each tactic contains a single attribution line: `Adapted from patterns.sddevelopment.be` |
| FR-003.5 | Provenance import files are created under `src/doctrine/_reference/quickstart-agent-augmented-development/candidates/` following the existing import file format |
| FR-003.6 | Both adapted tactics are discoverable by the existing `rglob("*.tactic.yaml")` loader without any code changes |

### FR-004: Tactic Directory Normalization

**Status**: In Scope

Create category subdirectories within `src/doctrine/tactics/shipped/` and move existing flat tactics into them.

| Sub-requirement | Description |
|----------------|-------------|
| FR-004.1 | Create `shipped/testing/` and move all testing-discipline tactics into it |
| FR-004.2 | Create `shipped/analysis/` and move all analysis and discovery tactics into it, including new brownfield tactics from FR-003 |
| FR-004.3 | Create `shipped/communication/` and move all documentation, decision, and stakeholder communication tactics into it |
| FR-004.4 | Create `shipped/architecture/` and move all structural and design tactics into it, including new tactics from FR-005 |
| FR-004.5 | Tactics that do not map clearly to any of the four categories remain in `shipped/` root |
| FR-004.6 | No loader code changes are needed; the existing `rglob` in `base.py` handles subdirectories |
| FR-004.7 | Tactic IDs and content are unchanged; only file paths change |

**Classification guide (non-exhaustive):**

*testing/*: `acceptance-test-first`, `atdd-adversarial-acceptance`, `black-box-integration-testing`, `formalized-constraint-testing`, `function-over-form-testing`, `mutation-testing-workflow`, `no-parallel-duplicate-test-runs`, `quality-gate-verification`, `tdd-red-green-refactor`, `test-boundaries-by-responsibility`, `testing-select-appropriate-level`, `test-minimisation`, `test-pyramid-progression`, `test-to-system-reconstruction`, `zombies-tdd`

*analysis/*: `ammerse-impact-analysis`, `analysis-extract-before-interpret`, `bounded-context-canvas-fill`, `bounded-context-identification`, `connascence-analysis`, `context-boundary-inference`, `context-mapping-classification`, `entity-value-object-classification`, `premortem-risk-identification`, `requirements-validation-workflow`, `reverse-speccing`, `safe-to-fail-experiment`, `strategic-domain-classification`

*communication/*: `adr-drafting-workflow`, `decision-marker-capture`, `documentation-curation-audit`, `glossary-curation-interview`, `stakeholder-alignment`, `traceable-decisions`, `usage-examples-sync`

*architecture/*: `aggregate-boundary-design`, `anti-corruption-layer`, `architecture-diagram-review-checklist`, `atomic-design-review-checklist`, `atomic-state-ownership`, `c4-zoom-in-architecture-documentation`, `compositional-stream-boundaries`, `cross-cutting-state-via-store`, `dependency-hygiene`, `domain-event-capture`, `language-driven-design`, `problem-decomposition`

**Classification heuristics for uncategorized tactics** (to guide implementer judgment on ambiguous cases): tactics primarily about *understanding* a system or domain → `analysis/`; tactics primarily about *expressing or informing* others → `communication/`; tactics about *system structure, boundaries, or design shape* → `architecture/`; tactics about *verifying correctness or behavior* → `testing/`. When a tactic straddles two categories, place it in the category where it is most often *invoked*. Tactics that apply equally across all categories remain in `shipped/` root.

### FR-005: New Architecture Tactics

**Status**: In Scope

Add tactics in `shipped/architecture/`:

| Sub-requirement | Description |
|----------------|-------------|
| FR-005.1 | Create `reference-architectural-patterns.tactic.yaml` — a tactic for identifying and applying named reference architecture patterns (layered, event-driven, CQRS, hexagonal, microservices, modular monolith) to a problem context. Steps: characterize the problem domain, enumerate candidate patterns, score against constraints (coupling, scalability, operational complexity), select and document rationale in an ADR |
| FR-005.2 | Adapt the `development-bdd` tactic into `shipped/architecture/development-bdd.tactic.yaml`. BDD is placed under architecture because behavioral contracts define system boundaries; the implementer may reclassify to `testing/` if project conventions favor that |
| FR-005.3 | The `notes` field in `development-bdd.tactic.yaml` contains: `Adapted from patterns.sddevelopment.be` |
| FR-005.4 | All new architecture tactics validate against the tactic schema |

### FR-006: Reviewer Renata — Test Readability Enrichment

**Status**: In Scope

| Sub-requirement | Description |
|----------------|-------------|
| FR-006.1 | Create `shipped/testing/test-readability-clarity-check.tactic.yaml` adapted from the test-readability-clarity-check approach, generalized to be framework-agnostic |
| FR-006.2 | The tactic encodes the dual-perspective reconstruction method: read only test code, reconstruct system understanding, compare against specification to identify gaps |
| FR-006.3 | Add a `tactic-references` entry in `reviewer-renata.agent.yaml` pointing to `test-readability-clarity-check` |
| FR-006.4 | The updated `reviewer-renata` profile passes schema validation |

### FR-007: Implementer Ivan — Bug Fixing Approach

**Status**: In Scope

| Sub-requirement | Description |
|----------------|-------------|
| FR-007.1 | Create `shipped/testing/bug-fixing-checklist.tactic.yaml` adapted from the quickstart project's `bug-fixing-checklist.md`, generalized to be language- and framework-agnostic |
| FR-007.2 | The tactic enforces test-first bug fixing: write a failing test to reproduce the defect before modifying production code |
| FR-007.3 | Add a `tactic-references` entry in `implementer-ivan.agent.yaml` pointing to `bug-fixing-checklist` |
| FR-007.4 | The updated `implementer-ivan` profile passes schema validation |
| FR-007.5 | Specialist profiles that `specializes-from: implementer-ivan` (java-jenny, python-pedro, frontend-freddy, node-norris) inherit the tactic reference automatically via `resolve_profile()` union-merge semantics (`tactic-references` is in `_LIST_FIELDS`). No explicit additions are required to specialist profiles that do not already declare their own `tactic-references`. Profiles that DO declare their own `tactic-references` (e.g., java-jenny after WP11 enrichment) get the base refs unioned in automatically. |

### FR-009: Behaviour-Driven Development Paradigm

**Status**: In Scope

Create `src/doctrine/paradigms/shipped/behaviour-driven-development.paradigm.yaml` encoding BDD as a first-class doctrine paradigm.

BDD is a distinct paradigm from `specification-by-example` (which covers the broader technique of using concrete examples as requirements). BDD specifies *how teams collaborate* to produce those examples — through the Discovery → Formulation → Automation cycle anchored by the Three Amigos practice — and mandates that executable tests are the canonical form of the specification.

| Sub-requirement | Description |
|----------------|-------------|
| FR-009.1 | `id: behaviour-driven-development`; `name: Behaviour-Driven Development`; `schema-version: "1.0"` |
| FR-009.2 | `summary` captures the three pillars: (a) shared understanding is built through structured Discovery conversations (Three Amigos), (b) behavior is expressed in plain-language Formulation (Gherkin Given/When/Then), (c) the formulated specification is the executable Automation — tests that fail when behavior diverges |
| FR-009.3 | `directive_refs` includes at minimum `DIRECTIVE_034` (Test-First Development) and `DIRECTIVE_037` (Living Documentation Sync) |
| FR-009.4 | The paradigm explicitly names that BDD does not replace the unit test pyramid — it sits above it; scenarios are reserved for behaviors with cross-functional business value |
| FR-009.5 | Attribution: the paradigm YAML schema has no `notes` field; attribution goes in the commit message only, referencing `patterns.sddevelopment.be/primers/toolchain-and-automation/bdd` as the content source. Do NOT add non-schema fields to the YAML. |

### FR-010: BDD Scenario Lifecycle Procedure

**Status**: In Scope

Create `src/doctrine/procedures/shipped/bdd-scenario-lifecycle.procedure.yaml` covering the Formulation → Automation → Maintenance phases of the BDD cycle.

The existing `example-mapping-workshop.procedure.yaml` covers the Discovery phase (collecting rules, examples, open questions with stakeholders). This procedure covers what happens *after* the examples are agreed on: translating them into Gherkin, wiring them to step definitions, and keeping them alive as the system evolves.

| Sub-requirement | Description |
|----------------|-------------|
| FR-010.1 | `entry_condition`: a canonical set of examples has been validated (output of `example-mapping-workshop`) |
| FR-010.2 | `exit_condition`: each agreed example exists as a passing executable scenario; no scenario is in a permanently pending or skipped state; the feature file is human-readable by a non-technical audience |
| FR-010.3 | Steps cover: (1) Express each example in Gherkin (`Feature`, `Scenario`, `Given/When/Then`); (2) Validate Gherkin readability with a non-technical reviewer; (3) Wire each step to a step definition; (4) Run the suite red, implement minimally until green; (5) Publish to the living documentation report |
| FR-010.4 | The `anti_patterns` section encodes at minimum: imperative Gherkin (describing UI clicks rather than business intent), rubber-stamp scenarios (written after code to pass), shared mutable state between scenarios, and orphaned step definitions |
| FR-010.5 | `references` links to: `example-mapping-workshop` procedure (predecessor), `behavior-driven-development` tactic, `acceptance-test-first` tactic, `DIRECTIVE_034`, `DIRECTIVE_037` |
| FR-010.6 | The procedure is toolchain-agnostic — it applies regardless of whether Cucumber-JVM, Cucumber-JS, Behave, SpecFlow, or a custom DSL is in use |

### FR-011: BDD Profile Enrichment

**Status**: In Scope

Enrich existing agent profiles with BDD-specific tactic and paradigm references. Each profile receives only the BDD references relevant to its role and toolchain.

| Profile | Enrichment |
|---------|-----------|
| `java-jenny` | Add `behaviour-driven-development` paradigm ref; add tactic references to `behavior-driven-development` and `bdd-scenario-lifecycle`; `self-review-protocol` gains a step: verify all Gherkin scenarios in scope have a passing step definition (Cucumber-JVM + Serenity BDD) |
| `frontend-freddy` | Add tactic references to `behavior-driven-development` and `bdd-scenario-lifecycle`; `self-review-protocol` gains a step: Cucumber-JS / Playwright e2e scenarios pass |
| `node-norris` | Add tactic reference to `behavior-driven-development`; `self-review-protocol` gains a step: Cucumber-JS scenarios (if present) pass with supertest or equivalent API driver |
| `reviewer-renata` | Add `behaviour-driven-development` paradigm ref; add tactic reference to `bdd-scenario-lifecycle`; her review checklist includes: every WP behavior has a corresponding passing Gherkin scenario or equivalent acceptance test |
| `architect-alphonso` | Add `behaviour-driven-development` paradigm ref; add procedural reference to `example-mapping-workshop` and `bdd-scenario-lifecycle`; behavioral contracts and observable outcomes are primary architectural artifacts in scoping decisions |

All updated profiles must pass schema validation.

### FR-012: Enrich Existing BDD Tactic

**Status**: In Scope

Extend `src/doctrine/tactics/shipped/behavior-driven-development.tactic.yaml` (currently categorized in the `testing/` subdirectory after FR-004 normalization) with content from the BDD primer.

| Sub-requirement | Description |
|----------------|-------------|
| FR-012.1 | Add a `notes` field (or extend existing one) covering: toolchain landscape summary (Cucumber-JVM, Cucumber-JS, Behave, SpecFlow, Playwright integration, Serenity BDD narrative reports, custom DSLs for highly domain-specific suites) |
| FR-012.2 | Extend `failure_modes` with at minimum: rubber-stamp scenarios (written after code), shared mutable state between scenarios, and orphaned step definitions |
| FR-012.3 | Add a reference to the new `bdd-scenario-lifecycle` procedure and `behaviour-driven-development` paradigm |
| FR-012.4 | The tactic remains toolchain-agnostic in its *steps* — toolchain content goes only in `notes`, not in step descriptions |
| FR-012.5 | Attribution note: a single line in `notes` references `patterns.sddevelopment.be/primers/toolchain-and-automation/bdd` as the source of the toolchain landscape section |

### FR-008: Profile Specialization Tactic Inheritance Test

**Status**: In Scope

| Sub-requirement | Description |
|----------------|-------------|
| FR-008.1 | Add a test in `tests/doctrine/test_profile_inheritance.py` (or a new sibling file) that asserts: for any profile P that `specializes-from` a base profile B, if B declares a `tactic-reference` with ID T, then `repo.resolve_profile(P)` also includes T. The test uses `resolve_profile()` — not `load_all()` raw profiles — because inheritance propagation occurs at resolution time via `_LIST_FIELDS` union-merge. |
| FR-008.2 | The test is **generic**: it does not hard-code specific tactic IDs or profile names. It iterates all loaded shipped profiles and verifies the invariant for every specialization pair found |
| FR-008.3 | The test must pass when zero specialization pairs exist (empty repo case) |
| FR-008.4 | The test uses only existing profile repository and tactic repository fixtures |
| FR-008.5 | The test carries `@pytest.mark.doctrine` (and `@pytest.mark.fast` if under 1 second) |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | All new and adapted tactic YAML files validate against the tactic schema | Zero errors on `pytest -m doctrine` |
| NFR-002 | All new and modified agent profile YAML files validate against `agent-profile.schema.yaml` | Zero errors |
| NFR-003 | The tactic repository loads all moved tactics after normalization | `len(repo.load_all()) >= pre-normalization count` |
| NFR-004 | FR-008 test must not require specific doctrine contents | Test green with zero profiles and with fixture specialization pairs |
| NFR-005 | Shipped YAML contains no local filesystem paths or project-specific identifiers | No occurrences of absolute paths or `quickstart_agent` in shipped YAML |
| NFR-006 | The `bdd-scenario-lifecycle` procedure and `behaviour-driven-development` paradigm load without schema errors | Zero validation failures on `pytest -m doctrine` |
| NFR-007 | BDD enrichment does not break any existing profile test | All pre-existing `pytest -m doctrine` tests remain green after profile enrichment |

## Constraints

| ID | Constraint |
|----|-----------|
| C-001 | Do not modify any doctrine loader Python code. The `rglob` pattern already handles subdirectories. |
| C-002 | Tactic IDs must remain unchanged when files are moved. The `id` field is the canonical identity; file path is incidental. |
| C-003 | Both Frontend Freddy and Node Norris must `specializes-from: implementer-ivan`. |
| C-004 | The bug-fixing-checklist tactic must be language-agnostic — no Java, Python, or JavaScript specifics. |
| C-005 | The development-bdd tactic may reference Gherkin/Given-When-Then as a format but must not mandate a specific BDD framework. |
| C-006 | Attribution to `patterns.sddevelopment.be` goes in: (a) the `notes` field of adapted tactic YAML files, and (b) provenance import files under `src/doctrine/_reference/`. Do not embed local filesystem paths in any shipped artifact. |
| C-007 | Frontend Freddy's `avoidance-boundary` must explicitly name Node Norris's domain (server-side Node.js, HTTP handlers) and vice versa. The two profiles must mutually exclude each other's scope. |

## User Scenarios

### Scenario A: Routing decision — browser component vs. API endpoint

An operator has two work packages: `WP-01` builds a login form (React component + CSS) and `WP-02` implements the authentication API (Express route + JWT issuance).

- `WP-01` is dispatched to Frontend Freddy: she implements the component with vitest unit tests and playwright e2e, runs axe for accessibility, and hands off
- `WP-02` is dispatched to Node Norris: he implements the Express route with supertest integration tests, runs `npm audit`, and hands off

**Success**: No work package crosses the browser/server boundary; each agent operates within its declared scope

### Scenario B: Tactic discovery after normalization

A project loads the tactic repository. All tactics from `shipped/testing/`, `shipped/analysis/`, `shipped/communication/`, `shipped/architecture/`, and `shipped/refactoring/` are discovered by `rglob`. Tactic IDs are identical to pre-normalization values. No "tactic not found" errors occur.

**Success**: `len(repo.load_all())` equals the pre-normalization count

### Scenario C: Reviewer Renata applies test readability check

Renata reviews a WP that includes a test suite. Her updated profile references `test-readability-clarity-check`. She reads only the tests, attempts to reconstruct system behavior from them, then compares her reconstruction against the specification. Tests that fail reconstruction produce a review finding.

**Success**: Test readability check is a documented, profile-driven step in Renata's review workflow

### Scenario E: BDD workflow from discovery to living documentation

A team completes an Example Mapping workshop (`example-mapping-workshop` procedure) and agrees on three canonical scenarios for a checkout feature. A Java Jenny work package begins:

1. She references the `bdd-scenario-lifecycle` procedure
2. She writes the three scenarios in Gherkin (`Feature: Checkout`, three `Scenario:` blocks)
3. She validates readability with the product owner (Gherkin passes the non-technical reader test)
4. She wires step definitions with Cucumber-JVM + Serenity BDD
5. She runs the suite red, implements minimally, runs it green
6. CI publishes the Serenity HTML report as living documentation
7. Reviewer Renata confirms all behaviors have passing scenarios before approving the WP

**Success**: Scenarios written before implementation; living documentation generated; no behavior without a failing-first test

### Scenario D: Profile specialization inheritance test on CI

CI runs `pytest -m doctrine`. The generic inheritance test finds that `implementer-ivan` declares a tactic reference to `bug-fixing-checklist`. It then verifies that `java-jenny`, `python-pedro`, `frontend-freddy`, and `node-norris` (all specializing from ivan) also resolve this reference. No profile name is hardcoded; any future specialists added to ivan's hierarchy are covered automatically.

**Success**: Test green; new specialist profiles are covered without test changes

## Success Criteria

1. All new YAML artifacts pass schema validation in the CI doctrine test suite
2. The tactic repository loads at least as many tactics as before normalization
3. Both `frontend-freddy` and `node-norris` are resolvable by the profile repository and pass schema validation
4. The generic profile specialization test (FR-008) passes on an empty fixture repo and on repos with specialization pairs
5. No loader code (Python) was modified in this mission
6. No shipped YAML contains local filesystem paths or project-specific identifiers
7. Attribution to `patterns.sddevelopment.be` is present in the `notes` field of artifacts adapted from that source
8. The paradigm repository resolves `behaviour-driven-development` and the procedure repository resolves `bdd-scenario-lifecycle`
9. All enriched agent profiles pass schema validation after BDD reference additions

## Assumptions

1. The `development-bdd` tactic is placed under `architecture/`; the implementer may reclassify to `testing/` without revisiting this spec
2. `terminology-extraction-mapping` is placed under `analysis/` because it supports domain model discovery
3. Tactics that do not fit the four categories remain in `shipped/` root — this is not a failure condition
4. The test-readability-clarity-check results in a single tactic YAML file rather than a multi-file approach package
5. The `notes` field in the tactic schema is the appropriate location for the `patterns.sddevelopment.be` attribution line; no schema changes are needed
6. The `behaviour-driven-development` paradigm does not replace `specification-by-example`; they coexist as complementary — SbE is the broader technique, BDD is a specific collaboration-and-toolchain expression of it
7. The `bdd-scenario-lifecycle` procedure is toolchain-agnostic; language-specific toolchain guidance (Cucumber-JVM, Playwright, Behave) appears only in the `behavior-driven-development.tactic.yaml` `notes` field and in individual profile `specialization-context` entries
