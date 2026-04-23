# Spec: Glossary DRG Surfaces and Charter Lint

**Mission ID**: 01KPTY5YAVPZKFDFTG197XZAHG  
**Mission slug**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Mission type**: software-dev  
**Target branch**: main  
**Source**: [Phase 5] Glossary as DRG-resident doctrine + chokepoint — https://github.com/Priivacy-ai/spec-kitty/issues/467  
**Related issues**: #532 (WP5.5), #533 (WP5.6)

---

## Design Reference

**Mockup**: `src/specify_cli/dashboard/templates/glossary.html`  
**Design notes**: `designs/README.md`

The approved visual design for the `/glossary` dashboard route is the static HTML mockup at `src/specify_cli/dashboard/templates/glossary.html`. It establishes the CSS design system (dashboard-inherited color palette, dark/light mode), the card layout, the filter UX (search + status tabs + alpha nav), and the confidence bar. WP02 adapts this static mockup into a dynamic page by replacing the hardcoded `TERMS` array with a live fetch from `/api/glossary-terms`.

---

## Overview

This mission implements four user-facing surfaces that sit on top of the DRG-resident glossary and chokepoint middleware built in Phase 5 WP5.1–WP5.2 (out of scope here, treated as pre-existing dependencies):

- **WP5.3** — Inline-in-agent-output observation surface: compact high-severity drift notice injected into agent output by the chokepoint, never blocking.
- **WP5.4** — Dashboard glossary tile: persistent health summary tile for the spec-kitty dashboard.
- **WP5.5** — Glossary entity pages with two-way backlinks: every DRG-resident term becomes a regenerable Markdown page that accumulates every artifact touching it, reverse-walked from the merged DRG.
- **WP5.6** — `spec-kitty charter lint`: graph-native decay detection (orphans, contradictions, staleness, reference integrity) across the merged DRG, with structured JSON output for the FR4 retrospective profile and a dashboard "decay watch" tile.

Nothing in this mission blocks agent output or introduces LLM calls to the hot path.

---

## Actors

- **Developer / operator**: runs `spec-kitty` CLI commands, reads dashboard, reads entity pages
- **Automated agent** (Claude, Codex, etc.): receives inline drift notices in output; calls `spec-kitty charter lint --json` as a tool
- **FR4 retrospective profile**: consumes `spec-kitty charter lint --json` output as structured input to its findings proposals
- **spec-kitty chokepoint middleware** (WP5.2, external dependency): the source of drift observations that feed WP5.3 and WP5.4

---

## Assumptions

- WP5.1 (glossary moved into DRG addressing scheme with `glossary:<id>` URN nodes and `vocabulary` edges) is complete before this mission's WPs execute.
- WP5.2 (`ProfileInvocationExecutor` chokepoint middleware) is complete and emits `glossary.conflict` events with severity levels (`high`, `medium`, `low`) before this mission's WPs execute.
- The merged DRG provides a queryable graph with `vocabulary` edges from actions/profiles to glossary term nodes, and back-reference edges from WPs, ADRs, mission steps, retrospective findings, and charter sections to term nodes.
- Entity pages are gitignored build artifacts regenerated on demand, never manually maintained.
- `ensure_charter_bundle_fresh()` (Phase 2 chokepoint) exists as the hook point for triggering entity page regeneration.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | When the chokepoint detects a **high-severity** glossary drift event during any `spec-kitty ask`, `do`, or `advise` invocation, it appends a compact inline notice to the agent output before returning | Proposed |
| FR-002 | The inline notice (FR-001) identifies the offending term, the conflicting senses observed, and a suggested resolution action; it fits within 5 lines of terminal output | Proposed |
| FR-003 | The inline notice is **never** shown for low- or medium-severity drift; those are logged only | Proposed |
| FR-004 | The inline surface (FR-001) never blocks or delays agent output beyond the p95 overhead target defined in ADR-5 (proposed: 50ms) | Proposed |
| FR-005 | The spec-kitty dashboard displays a **glossary tile** showing: count of active high-severity drift events, total term count, count of terms with no `vocabulary` edge (orphaned terms), and a link to the `/glossary` full-page browser | Proposed |
| FR-006 | The dashboard glossary tile (FR-005) refreshes at the same cadence as other dashboard tiles | Proposed |
| FR-025 | The dashboard serves a full-page glossary browser at `/glossary` with: real-time search across term surface and definition, status filter tabs (All / Active / Draft / Deprecated), alphabetical jump navigation, and term cards arranged in an auto-fill responsive grid — matching the design in `designs/README.md` and `src/specify_cli/dashboard/templates/glossary.html` | Proposed |
| FR-026 | Term cards in the `/glossary` page render: the canonical surface name in monospace bold, a status badge (green = active, lavender = draft, peach = deprecated), a definition excerpt, and a confidence bar; deprecated terms render with strikethrough surface name and italic definition | Proposed |
| FR-027 | The `/glossary` page populates term data by fetching from `/api/glossary-terms` at load time; the API returns an array of `{surface, definition, status, confidence}` objects drawn live from the glossary store | Proposed |
| FR-007 | For every glossary term node in the merged DRG, a regenerable entity page exists at `.kittify/charter/compiled/glossary/<term-id>.md` | Proposed |
| FR-008 | Each entity page (FR-007) renders: canonical sense, scope, status, and current definition; inbound references grouped by source type (WPs, ADRs, mission steps, retrospective findings, charter sections); provenance (which synthesizer run first introduced the term and when); full conflict history (every `glossary.conflict` event for this term, with severity, resolution, and resolving actor); and cross-term relationships (siblings and generalizations reachable via DRG edges) | Proposed |
| FR-009 | Backlinks are bidirectional: the entity page links to each reference artifact, and artifact rendering (ADRs, WPs, mission step contracts) includes a backlink anchor pointing back to the entity page | Proposed |
| FR-010 | Entity pages are regenerated by `ensure_charter_bundle_fresh()` — never stale and never manually maintained | Proposed |
| FR-011 | `spec-kitty glossary show <term>` renders the entity page for the named term in the terminal | Proposed |
| FR-012 | `spec-kitty charter lint` runs all four decay-check categories (orphan, contradiction, staleness, reference integrity) against the merged DRG for all features | Proposed |
| FR-013 | `spec-kitty charter lint --feature <id>` scopes the lint run to a single feature | Proposed |
| FR-014 | `spec-kitty charter lint --orphans` runs only orphan-detection checks | Proposed |
| FR-015 | `spec-kitty charter lint --contradictions` runs only contradiction-detection checks | Proposed |
| FR-016 | `spec-kitty charter lint --stale` runs only staleness-detection checks | Proposed |
| FR-017 | `spec-kitty charter lint --json` emits a machine-readable findings array consumable by the FR4 retrospective profile | Proposed |
| FR-018 | `spec-kitty charter lint --severity high` filters findings to a specified minimum severity | Proposed |
| FR-019 | Orphan detection uses the DRG's symmetric incoming-edge property: WPs with no mission-step reference, ADRs referenced by nothing, glossary terms with no `vocabulary` edge, synthesized artifacts unreachable from any profile or action scope edge, and procedures never delegated from a step contract | Proposed |
| FR-020 | Contradiction detection identifies: ADRs with conflicting decisions on the same topic URN, directives whose severity and scope overlap with a contradicting directive, glossary terms with multiple active senses in the same scope, and charter selections activating mutually-exclusive paradigms | Proposed |
| FR-021 | Staleness detection identifies: synthesized artifacts whose source corpus snapshot is older than a configurable threshold, WPs referencing artifacts edited after the WP started, and profile `context-sources` referencing removed or renamed doctrine artifacts | Proposed |
| FR-022 | Reference integrity checks identify: WPs referencing superseded ADRs (via `replaces:` DRG edges) and DRG edges pointing to nodes that no longer exist | Proposed |
| FR-023 | The spec-kitty dashboard displays a **decay watch tile** rendering a summary of the most recent `spec-kitty charter lint` run (finding counts by category and severity) | Proposed |
| FR-024 | The FR4 retrospective profile can call `spec-kitty charter lint --json` as a tool and receive a structured list of decay findings with enough context to generate specific remediation proposals | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Chokepoint inline surface overhead (WP5.3) does not increase p95 latency of `spec-kitty ask/do/advise` beyond the ADR-5 target | p95 ≤ 50ms additional overhead | Proposed |
| NFR-002 | `spec-kitty charter lint` completes a full scan on a large fixture project | ≤ 5 seconds wall time | Proposed |
| NFR-003 | No LLM calls are made in the chokepoint hot path or in the `charter lint` command | 0 LLM calls | Proposed |
| NFR-004 | Entity page generation for an entire glossary completes within a reasonable time | ≤ 10 seconds for up to 500 terms | Proposed |
| NFR-005 | `spec-kitty charter lint --json` output is valid JSON parseable by standard tooling with no extra text | 100% valid JSON | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Nothing in this mission blocks agent output or shows modal dialogs | Proposed |
| C-002 | Entity pages are gitignored build artifacts — never committed to the repository | Proposed |
| C-003 | `charter lint` must not introduce LLM calls; all checks are graph traversals, regex, or heuristic comparisons | Proposed |
| C-004 | The inline surface (WP5.3) is only triggered by the existing chokepoint middleware (WP5.2); this mission does not re-implement chokepoint logic | Proposed |
| C-005 | Backlink anchors in artifact rendering (FR-009) must not break existing artifact rendering for consumers that do not have entity pages generated | Proposed |

---

## User Scenarios and Testing

### Scenario 1: High-severity drift surfaces inline (WP5.3)

**Actor**: Developer running `spec-kitty do "implement the caching layer"`  
**Trigger**: Chokepoint detects that the term "cache" is being used with two conflicting senses (infrastructure-level vs. application-level) at high severity  
**Happy path**: The agent's response is returned with a compact inline notice appended: the term name, conflicting senses, and a suggested resolution action (5 lines max). The response is not delayed beyond the ADR-5 p95 budget.  
**Exception**: If the chokepoint yields only medium/low severity, no notice appears — the response returns cleanly.

### Scenario 2: Dashboard glossary tile visible (WP5.4)

**Actor**: Developer opening the spec-kitty dashboard  
**Trigger**: Dashboard renders  
**Happy path**: A "Glossary" tile appears showing high-severity drift count, total term count, orphaned term count, and a navigable link to the entity pages directory.  
**Exception**: If the glossary has no terms yet, the tile shows zero counts without erroring.

### Scenario 3: Entity page accumulates references (WP5.5)

**Actor**: Developer running `spec-kitty glossary show "deployment-target"`  
**Trigger**: CLI command  
**Happy path**: The entity page for "deployment-target" prints to terminal with canonical definition, a list of WPs and ADRs that cite it (linked), conflict history, and cross-term relationships.  
**Exception**: If the term ID is not found in the DRG, a clear "term not found" error is shown.

### Scenario 4: Charter lint catches orphan ADR (WP5.6)

**Actor**: FR4 retrospective profile calling `spec-kitty charter lint --feature 042 --json`  
**Trigger**: Retrospective profile tool call  
**Happy path**: JSON output includes a finding: `{"category": "orphan", "type": "adr", "id": "ADR-7", "severity": "medium", "message": "ADR-7 is not referenced by any WP, charter section, or other ADR in feature 042"}`. Profile uses this to generate a specific remediation proposal.  
**Exception**: If the feature has no decay, the JSON output is `{"findings": [], "scanned_at": "..."}`.

### Scenario 5: Charter lint decay watch tile on dashboard (WP5.6)

**Actor**: Developer opening dashboard after a charter lint run  
**Trigger**: Dashboard renders  
**Happy path**: "Decay Watch" tile shows findings summary from last lint run: e.g., "3 orphans · 1 contradiction · 0 stale · 2 broken refs". Links to the full lint report.  
**Exception**: If lint has never been run, tile shows "No lint data — run `spec-kitty charter lint`".

---

## Success Criteria

1. A developer running `spec-kitty do` with a high-severity drift scenario receives the inline notice within the ADR-5 p95 budget — measured against the fixture test suite.
2. The dashboard glossary tile and decay watch tile render correctly with accurate counts for a project with at least 20 terms and one manufactured decay condition.
3. Every term in a 20-term fixture glossary has a regenerated entity page with at least one inbound reference correctly reverse-walked from the DRG.
4. `spec-kitty charter lint` correctly identifies all four decay categories (one each) in a purpose-built fixture project with manufactured decay in under 5 seconds.
5. The FR4 retrospective profile can call `spec-kitty charter lint --json` and parse the result without modification.
6. No existing `spec-kitty ask/do/advise` invocation returns an error or is blocked by WP5.3's inline surface — only appended output.

---

## Domain Language

| Canonical term | Synonyms to avoid | Notes |
|----------------|-------------------|-------|
| entity page | "term page", "glossary page" | The regenerable `.md` artifact at `.kittify/charter/compiled/glossary/<term-id>.md` |
| decay detection | "rot detection", "drift detection" (for charter lint) | `charter lint` specifically; "drift" is reserved for glossary semantic drift |
| `vocabulary` edge | "reference edge" (in DRG context) | The DRG edge type connecting an action/profile to a glossary term node |
| chokepoint | "middleware" (acceptable in code), "interceptor" | The deterministic inline check in `ProfileInvocationExecutor`; no LLM calls |
| merged DRG | "compiled DRG", "built graph" | The DRG as assembled by `ensure_charter_bundle_fresh()` |
| observation surface | "display surface", "output surface" | The output channel where drift notices appear (inline in WP5.3, tile in WP5.4) |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `GlossaryTermNode` | DRG node with `glossary:<id>` URN; carries canonical sense, scope, status, definition, and provenance metadata |
| `VocabularyEdge` | DRG edge from an action/profile node to a `GlossaryTermNode`; establishes that the action uses that term |
| `InlineNotice` | Compact drift-notice object appended to agent output by WP5.3; has term, conflicting senses, severity, and suggested action |
| `EntityPage` | Regenerable Markdown artifact at `.kittify/charter/compiled/glossary/<term-id>.md`; rendered from a DRG reverse-walk |
| `LintFinding` | Structured decay-detection result with fields: `category`, `type`, `id`, `severity`, `message`, `feature_id` (optional) |
| `DecayReport` | Aggregated output of a `charter lint` run; contains `findings[]` and run metadata (`scanned_at`, `feature_scope`) |

---

## Out of Scope

- WP5.1 (moving existing glossary into DRG addressing scheme) — external dependency
- WP5.2 (chokepoint middleware in `ProfileInvocationExecutor`) — external dependency
- Phase 6 WP6.6 (retrospective profile tool integration beyond the JSON contract) — future work
- Auto-remediation of lint findings (lint is read-only; resolution is a human or profile action)
- Backlink injection into pre-existing committed artifact files (backlinks are added to rendering, not to stored artifacts)
