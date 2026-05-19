# WP-Prompt Governance Payload Completeness

> Mission ID: `01KRR8HS66A7NFV64HHPXG2JJE`
> Mission slug: `wp-prompt-governance-payload-01KRR8HS`
> Target branch: `feat/org-doctrine-layer`
> Mission type: software-dev
> Created: 2026-05-16

---

## Overview

Spec Kitty's per-WP `implement` and `review` prompts invoke the charter / doctrine pipeline at the right boundary but the pipeline returns a degenerate payload: section anchors only, the wrong directive namespace, zero tactics, zero glossary or ADR pointers. The runtime implement template then explicitly forbids the executing agent from looking elsewhere, closing the trap.

This was empirically verified during the post-merge review of mission `layered-doctrine-org-layer-01KRNPEE` (see `docs/development/org-doctrine-layer-architecture-review.md`, sections "Process architecture", "Root cause", and "Empirical addendum"). A failing-first ATDD test suite was written to pin the contract (see `tests/specify_cli/next/test_wp_prompt_governance_contract.py`); 9 of its 23 acceptance tests currently fail. The per-test failure-to-FR mapping is documented in `docs/development/wp-prompt-governance-atdd-findings.md`.

This mission closes the substantive gaps so the next mission run on spec-kitty itself (or on any consumer project) receives a WP prompt that is self-sufficient: every directive, tactic, term, and ADR the executing agent needs is either embedded verbatim or cited via a fetch command paired with a "when doing X, run …" conditional.

---

## User Journeys

### Journey 1 — Implementer agent receives actionable governance, not a table of contents

> "I am `python-pedro` implementing WP01. The implement prompt I receive lists the project's governance section anchors but not the bodies, and points at no glossary or ADRs. I have no way to satisfy DIRECTIVE_032 (Conceptual Alignment) — I don't even know it applies to me."

**Actors:** Implementing agent (any of the 13 supported agents), per-WP implement prompt
**Preconditions:** A mission is in `implement` phase; the WP frontmatter selects an agent profile that declares `directive-references` and `tactic-references`.

After this mission:
1. The implementer runs `spec-kitty agent action implement WP01 --agent <name>`.
2. The generated prompt's Governance block cites every `DIRECTIVE_NNN` and tactic ID the loaded profile references — either with the body inline, or with a `spec-kitty charter context --include <id>` fetch command paired with a "When you implement <X>, run this command and apply the returned rule" conditional.
3. The prompt includes a `Project authority paths:` block naming `glossary/contexts/`, `architecture/2.x/adr/`, and any additional authority directories the project charter declares.
4. The implementer can satisfy every governance check by reading only what the prompt cites.

### Journey 2 — Reviewer agent receives DIRECTIVE_032 explicitly in the review prompt

> "I am `reviewer-renata` reviewing a terminology rename. My profile loads DIRECTIVE_032 (Conceptual Alignment) — the directive that says terminology must align with the project glossary. But the review prompt I read does not surface it. I review the diff without ever consulting the glossary, and a `shipped → built-in` rename ships with `shipped/` references still in the spec."

**Actors:** Reviewer agent, per-WP review prompt
**Preconditions:** A WP is in `for_review`; the WP frontmatter selects `reviewer-renata`.

After this mission:
1. The reviewer runs `spec-kitty agent action review WP02 --agent <name>`.
2. The review prompt explicitly cites DIRECTIVE_032 with either the directive body or a fetch command + "When you assess a WP that renames identifiers or terms, run this and apply" conditional.
3. The prompt explicitly names `glossary/contexts/` as the authority for canonical terminology with a "When you encounter a domain term in the diff, grep this directory" rule.
4. A WP that renames `shipped → built-in` without updating `glossary/contexts/doctrine.md` is caught at review time, not at post-merge mission review.

### Journey 3 — Project charter maintainer declares resolver inputs once and they take effect

> "I maintain `.kittify/charter/charter.md`. Today the resolver emits a 'fallback applied' diagnostic on every WP prompt because the charter does not declare a `template_set` or `available_tools` block. I have no way to make the diagnostic go away without writing those declarations in a place the resolver actually reads."

**Actors:** Project charter maintainer
**Preconditions:** A project charter exists at `.kittify/charter/charter.md`.

After this mission:
1. The maintainer adds a fenced YAML block to `charter.md` declaring `template_set:` and `available_tools:`.
2. `spec-kitty charter sync` reads the block and persists the values into the bundle.
3. `spec-kitty charter context --action implement` emits no `Template set not selected in charter; fallback ... applied` diagnostic.
4. The resolved governance context surfaces the declared template-set's directives and tools, not a generic `software-dev-default` fallback.

### Journey 4 — Charter directive cross-links to doctrine catalog ID

> "My `.kittify/charter/charter.md` Code Review Checklist mentions `DIRECTIVE_032 — Conceptual Alignment`. After `charter sync`, the auto-generated `.kittify/charter/directives.yaml` entry for that checklist item shows just a `DIR-NNN` ID with the description text. The citation of DIRECTIVE_032 is lost in extraction; the resolver cannot surface the catalog body when an action asks for the charter-side checklist."

**Actors:** Charter sync extractor, governance resolver
**Preconditions:** Charter body cites a catalog ID by reference.

After this mission:
1. `charter sync` detects `DIRECTIVE_NNN` and `<tactic-id>` citations inside extracted directive bodies.
2. The generated `directives.yaml` entry carries a structured `references:` field listing the catalog IDs.
3. When `charter context --action <X>` resolves a `DIR-NNN` that carries `references: [DIRECTIVE_032]`, the resolver also surfaces DIRECTIVE_032 (body inline or fetch command + when-doing rule).

### Journey 5 — Operator runs a self-sufficient prompt without "rummaging"

> "The runtime implement template tells me not to call `spec-kitty charter context` myself because the prompt is authoritative. I trust it. The prompt is hollow. I implement code, miss the project's terminology rules, and the drift surfaces in post-merge review."

**Actors:** Implementing agent reading the runtime template
**Preconditions:** A WP is being implemented under the software-dev mission template.

After this mission, either:
- (a) The forbid clause is removed, OR
- (b) The forbid clause remains but is paired with a "Governance Payload Contract" section in the template that explicitly enumerates the bodies and pointers the prompt is contractually guaranteed to carry.

The implementer can therefore trust the prompt's completeness or knows exactly what to fetch themselves.

---

## Domain Language

| Term | Canonical meaning |
|---|---|
| **Governance payload** | The substantive content (rule bodies, profile-cited directives and tactics, authority pointers) the WP prompt's Governance block carries — not the section anchors. |
| **Section anchor** | A heading title that appears in the resolved context without its body content. Anchors alone are insufficient to govern execution. |
| **Profile-cited directive** | A `DIRECTIVE_NNN` ID listed in an agent profile's `directive-references`. The mission contract is that the WP prompt surfaces these for the loaded profile. |
| **Authority path** | A repository-relative directory the prompt explicitly names as the canonical source for some governance concern (e.g. `glossary/contexts/` for terminology, `architecture/2.x/adr/` for architectural intent). |
| **Fetch command + when-doing rule** | The alternative to verbatim embedding: a CLI command the agent can run paired with an explicit conditional sentence ("When you encounter a domain term, run …"). Both halves are required. |
| **Governance Payload Contract** | A section in the runtime command template that enumerates the bodies, pointers, and fetch commands the prompt is guaranteed to carry. |
| **Charter-extracted directive namespace** | The `DIR-NNN` IDs auto-emitted by `spec-kitty charter sync` into `.kittify/charter/directives.yaml`. |
| **Doctrine-catalog directive namespace** | The `DIRECTIVE_NNN` IDs hand-authored under `src/doctrine/directives/built-in/*.directive.yaml`. |
| **Catalog cross-link** | A structured `references:` field on a `DIR-NNN` entry pointing at one or more `DIRECTIVE_NNN` IDs, preserved by `charter sync` when the source body cites a catalog ID. |
| **Resolver-input declaration** | A machine-readable `template_set:` / `available_tools:` block in the charter that the resolver reads, eliminating the "fallback applied" diagnostic. |

Avoid: "governance context" (overloaded — use "governance payload"), "shipped directive" (use "doctrine-catalog directive"), "default directive" (use "fallback").

---

## Functional Requirements

| ID | Statement | Status |
|---|---|---|
| FR-001 | When `build_charter_context(action="implement"\|"review")` is called against a project whose charter body contains a section the action depends on (Terminology Canon, Code Review Checklist, Regression Vigilance, plus any section the resolver identifies as action-critical), the returned `text` MUST include the body of that section verbatim, not just the anchor. The set of "action-critical" sections is configurable per mission type; for software-dev it includes at minimum the four named above. | Proposed |
| FR-002 | When `build_charter_context(profile="<profile-id>")` is called with a known agent profile, the resolver MUST resolve the profile's `directive-references` and `tactic-references` against the doctrine catalog and include each — either as `DIRECTIVE_NNN: <full body>` or as `DIRECTIVE_NNN: <one-line summary>` + a `spec-kitty charter context --include directive:<id>` fetch command + an explicit "When you <action>, run …" conditional sentence. The `profile=` parameter is currently discarded (`_ = profile` at `src/charter/context.py:92`); this FR makes it load-bearing. | Proposed |
| FR-003 | The resolved governance payload for any action in `BOOTSTRAP_ACTIONS` MUST include a `Project authority paths:` block naming at minimum `glossary/contexts/` (when present in the repository) and `architecture/2.x/adr/` (when present). Additional authority paths declared in the project charter's `authority_paths:` block (new — see FR-007) MUST also appear. | Proposed |
| FR-004 | When the runtime `_governance_context(repo_root, action=<X>)` in `src/specify_cli/next/prompt_builder.py` builds the WP prompt's Governance block, it MUST pass the loaded agent profile ID (resolved from the WP frontmatter's `agent_profile:` field) to `build_charter_context` as the `profile=` argument. | Proposed |
| FR-005 | The runtime implement template at `src/specify_cli/missions/software-dev/command-templates/implement.md` MUST contain either (a) no forbid clause that prevents the agent from calling `spec-kitty charter context` directly, or (b) a "Governance Payload Contract" section explicitly enumerating: the action-critical section bodies, the profile-cited directive IDs (with whether each is inlined or fetch-deferred), the glossary pointer, the ADR pointer, and the set of fetch commands + when-doing rules the prompt carries. The same MUST apply to the review template (`review.md`). | Proposed |
| FR-006 | `spec-kitty charter sync` MUST detect catalog citations of the form `DIRECTIVE_\d{3}` or a tactic-id slug appearing inside the body of an extracted charter directive. The generated `.kittify/charter/directives.yaml` entry MUST include a structured `references:` list field naming each catalog ID detected. | Proposed |
| FR-007 | The project charter MUST be allowed to declare a fenced YAML block of the form `template_set: <name>` and `available_tools: [<tool>, …]`. `spec-kitty charter sync` MUST read these declarations and persist them into the bundle so `spec-kitty charter context --action implement` does NOT emit a `Template set not selected in charter; fallback ... applied` or `No available_tools selection provided; using runtime tool registry fallback` diagnostic. | Proposed |
| FR-008 | The project charter MUST be allowed to declare an optional fenced YAML block of the form `authority_paths: [<path>, …]` to extend the default set surfaced by FR-003. | Proposed |
| FR-009 | Spec-kitty's OWN `.kittify/charter/charter.md` MUST declare a `template_set` and an `available_tools` block per FR-007 before this mission is merged. (Dogfood enforcement — the same project that built the resolver must consume it without fallback diagnostics.) | Proposed |
| FR-010 | The aggregate self-sufficiency contract: a WP prompt built for any software-dev action MUST satisfy FR-001 through FR-008 simultaneously. Concretely: the existing ATDD test `tests/specify_cli/next/test_wp_prompt_governance_contract.py::TestPromptSelfSufficiency::test_implement_prompt_self_sufficiency` MUST pass. | Proposed |

## Non-Functional Requirements

| ID | Statement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The augmented WP prompt MUST stay under a token budget that leaves room for the agent's WP-specific working context. Measure the prompt's character count (proxy for tokens) and emit a warning if it exceeds the threshold; auto-substitute fetch commands for the longest sections when the threshold is exceeded. | WP prompt ≤ 32 000 characters total (proxy for ~8 000 tokens). | Proposed |
| NFR-002 | The augmented `build_charter_context` MUST not regress the perceived latency of the WP-prompt build. | `_build_wp_prompt` end-to-end runtime stays within 1.5× of the baseline measured before this mission. | Proposed |
| NFR-003 | All ATDD tests in `tests/specify_cli/next/test_wp_prompt_governance_contract.py` MUST pass after this mission. The 9 currently-failing tests are the acceptance gate. The 14 currently-passing tests MUST remain green (no regression). | 23/23 tests pass; 0 unintended changes to assertion semantics. | Proposed |
| NFR-004 | No new architectural-layer violation. `kernel ← doctrine ← charter ← specify_cli` invariants enforced by `tests/architectural/test_layer_rules.py` MUST continue to pass. In particular, any new content embedded in `charter.context` must not require importing from `specify_cli`. | All 8 layer-rule tests pass. | Proposed |
| NFR-005 | The charter sync extension for resolver-input declarations and catalog cross-links MUST be backwards compatible with charters that lack the new YAML blocks. A charter without `template_set:` should produce the same fallback diagnostic the system emits today (no regression), and a charter without `references:` cross-links should not error during sync. | Run `spec-kitty charter sync` against pre-mission state of `.kittify/charter/charter.md` (a copy preserved in test fixtures) — sync MUST succeed. | Proposed |

## Constraints

| ID | Statement | Status |
|---|---|---|
| C-001 | The dependency direction `kernel ← doctrine ← charter ← specify_cli` (ADR `2026-03-27-1`) is non-negotiable. Any new resolver code that needs `specify_cli`-layer data (e.g. agent profile resolution) MUST live in the `specify_cli` layer and pass data into the charter layer; the charter layer MUST NOT gain a new `specify_cli` import. | Proposed |
| C-002 | The ATDD test suite is the canonical spec. Implementation work MUST satisfy the existing test assertions verbatim. If a test's assertion is unrealistic, the test is revised in a *separate, prior* commit with explicit justification; otherwise the test stands. | Proposed |
| C-003 | The runtime implement template's forbid clause is a design choice with historical context. The mission MUST either preserve it and add the Governance Payload Contract section, or remove it and ensure the prompt carries the rule bodies. No middle ground (a forbid clause with no payload guarantee is the failure mode this mission exists to fix). | Proposed |
| C-004 | The token-budget enforcement (NFR-001) MUST be measured against real WP prompts from at least one existing mission (e.g. `layered-doctrine-org-layer-01KRNPEE` WP01–WP10), not against synthetic fixtures. | Proposed |
| C-005 | The dogfood enforcement (FR-009) is non-optional. Spec-kitty's own charter MUST be updated as part of this mission; the test `TestProjectCharterDeclaresResolverInputs` exists specifically to enforce this. | Proposed |

## Goals

- Close the structural payload gap at the WP-prompt boundary so the executing agent receives all the governance content it needs to do its job without consulting any uncited source.
- Eliminate the resolver-fallback diagnostics on spec-kitty's own missions (dogfood the fix).
- Make the runtime implement / review templates honest about what they guarantee.
- Cross-link the two directive namespaces so charter and doctrine catalog references can be navigated from either side.

## Non-Goals

- Adding new doctrine directives or tactics. The catalog content is out of scope; only the *plumbing* that surfaces it is in scope.
- Changing the agent profile YAML schema. Profiles already declare `directive-references` and `tactic-references` correctly; this mission makes the resolver read them.
- Rewriting `spec-kitty charter context` as a new subsystem. The existing API surface is augmented; signatures may add optional parameters but no public symbol is removed.
- Re-running the org-doctrine-layer ATDD tests. Those tests pin a different contract (artifact rendering); they remain green throughout this mission as a regression gate.
- Mission-review skill updates. Those land in a separate, follow-on mission per the architecture review recommendations.

## Out-of-scope (defer to follow-ups)

- Glossary alignment auto-detection in `/spec-kitty.analyze` (separate mission).
- Making `/spec-kitty.analyze` a hard gate before `/spec-kitty.implement` (separate mission).
- Refactoring `DoctrineLayerCollisionWarning` to carry structured attributes (already documented as a follow-up in the org-doctrine-layer architecture review).
- Wiring `apply_org_charter_to_interview` into the second `default_interview` call site (already documented in the prior review).

---

## Acceptance Criteria

The mission is accepted when all of the following are true on the target branch:

1. The full ATDD suite `tests/specify_cli/next/test_wp_prompt_governance_contract.py` reports **23 passed, 0 failed**.
2. The architectural layer-rule suite `tests/architectural/test_layer_rules.py` reports **8 passed**.
3. `ruff check` and `mypy` are clean on all modules touched by this mission.
4. Spec-kitty's own `.kittify/charter/charter.md` declares `template_set:` and `available_tools:` (FR-009) and `spec-kitty charter context --action implement` against this repo emits no fallback diagnostic.
5. A fresh integration check (run after this mission lands) shows: `spec-kitty agent action implement <any-WP-of-any-future-mission> --agent <profile>` produces a prompt whose Governance block contains the loaded profile's directive bodies (or fetch + when-doing pairs), a glossary pointer, and an ADR pointer.
6. The runtime implement and review templates either (a) drop the forbid clause OR (b) carry a `## Governance Payload Contract` section enumerating the guaranteed bodies and fetch commands.
7. Post-merge mission review (run via the `spec-kitty-mission-review` skill) confirms the FR coverage matrix is closed.

---

## References

- `docs/development/org-doctrine-layer-architecture-review.md` — root-cause analysis that produced this mission.
- `docs/development/wp-prompt-governance-atdd-findings.md` — per-test failure-to-FR mapping.
- `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — executable spec (23 ATDD tests).
- `architecture/2.x/adr/2026-03-27-1-pytestarch-architectural-dependency-testing.md` — layer rule.
- `src/specify_cli/next/prompt_builder.py:147` — WP-prompt governance injection call site.
- `src/charter/context.py:70-92` — `build_charter_context` (note: `profile=` parameter currently unused).
- `src/specify_cli/missions/software-dev/command-templates/implement.md:68-71` — current forbid clause.
- `.kittify/charter/charter.md` — project charter requiring the FR-009 update.
