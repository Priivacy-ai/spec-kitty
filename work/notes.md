# Work Notes

## Pending doctrine artifacts

- **Contextive toolguide** — no toolguide or styleguide exists yet for Contextive
  (the VS Code extension that surfaces domain terminology definitions inline from a
  `.contextive/definitions.yml` file). Natural implementation companion to the
  language-cluster directives and tactics below. Related doctrine:
  - `DIRECTIVE_031` (Context-Aware Design) — Contextive enforces ubiquitous language at the IDE level
  - `DIRECTIVE_032` (Conceptual Alignment) — Contextive provides the shared definition source agents and humans can reference
  - `glossary-curation-interview` tactic — Contextive definitions file is a natural output of the curation interview
  - `kitty-glossary-writing` styleguide — style rules should extend to Contextive definition format
  - `stakeholder-alignment` tactic — Contextive makes agreed terminology durable and discoverable
  - Language-First Architecture approach (pending, see below)

- **Language-First Architecture approach** — no doctrine artifact yet for
  "language as first-class architectural concern" / ubiquitous language as design
  driver. Referenced from DIRECTIVE_032 (Conceptual Alignment) but not yet a
  shipped tactic or approach. Draw from QAAD language-first-architecture.md and
  the PPP connascence article. Companion to `glossary-curation-interview` tactic.

- **Stakeholder Interview tactic/approach** — create a structured tactic for
  conducting a stakeholder interview: preparation, question framework, capturing
  motivations/desiderata/frustrations, and recording outputs. Complements the
  existing `stakeholder-alignment` tactic (which maps the stakeholder landscape)
  by providing the *how* for actually interviewing individuals.
  Natural companion to `stakeholder-persona-template.md`.

## Candidate: Test Behavior Over Structure

Tests should verify what code *does* (observable behavior, outcomes, contracts), not how
it is built (which CLI command is called, whether names appear as substrings in a file,
internal wiring). Implementation-detail tests create false confidence and break on
harmless refactors.

**Closest existing doctrine:**
- `acceptance-test-first` tactic — "keep acceptance checks black-box" / "exercise real workflows through public interfaces"
- `tdd-red-green-refactor` tactic — behavior increments, but doesn't explicitly address the behavior-vs-structure line
- `DIRECTIVE_030` — quality gates, not testing philosophy

**Gap:** No directive or tactic explicitly states the principle. Consider authoring as a
directive (e.g., "Test Behavioral Contracts") or extending `DIRECTIVE_004` (Test-Driven
Implementation Standard, currently unwritten — see table below) to include this guidance.

**Origin:** Corrective feedback during profile-context template development — tests were
written that checked for CLI command names in markdown and substring presence of profile
IDs, rather than verifying profiles were actually loadable and usable.

---

## Directives referenced by profiles but not yet authored

The following directive codes appear in shipped agent profiles but have no corresponding
directive file. References were removed from profiles to keep the codebase consistent.
Each code is a placeholder for a directive to author and interview through the HIC process.

| Code | Name | Profile(s) |
|------|------|------------|
| 002  | Accessibility First Principle | designer |
| 004  | Test-Driven Implementation Standard | implementer, reviewer |
| 005  | Design System Consistency Standard | designer |
| 006  | Coding Standards Adherence | implementer, reviewer |
| 008  | Security Review Protocol | reviewer |
| 009  | User-Centered Validation Requirement | designer |
| 011  | Feedback Clarity Standard | reviewer |
| 012  | Work Package Granularity Standard | planner |
| 013  | Dependency Validation Requirement | planner |
| 014  | Acceptance Criteria Completeness | planner |
| 015  | Research Time-boxing Requirement | researcher |
| 016  | Finding Documentation Standard | researcher |

These were **not** created as placeholder artifacts — directives should be authored
through proper HIC curation, not auto-generated to satisfy test constraints.

## Proposed directives awaiting HIC review

| Code | Name | Location |
|------|------|----------|
| 007  | Trade-off Assessment Protocol | `directives/_proposed/` |
| 017  | Glossary Integrity Standard | `directives/_proposed/` |
| 019  | Documentation Gap Prioritization | `directives/_proposed/` |

Note: 017 and 019 were drafted to resolve a pre-existing test failure in `curator.agent.yaml`
(which referenced these codes without backing files). They require a proper curation interview
before promotion to `shipped/`.
