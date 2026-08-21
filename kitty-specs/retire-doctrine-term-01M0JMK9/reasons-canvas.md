# REASONS Canvas — Retire the Doctrine Term

> Mission: retire-doctrine-term-01M0JMK9
> Generated: 2026-08-21
> Charter activation: structured-prompt-driven-development (paradigm)

## Requirements
- Problem statement: Spec Kitty's user-facing vocabulary splits "doctrine" (the artefact layer) from "charter" (the compiled file and activation surface); the operator has decided "doctrine" is retired and everything user-facing becomes "charter", with a three-way distinction — this mission plans that retirement (ADR + inventory + methodology + stacked plan) without executing it.
- Acceptance criteria:
  - ADR in `docs/adr/3.x/` (template + dated naming + index registration) records: the decision, the three-way distinction (charter bundle / active charter / inactive charter), surviving kind vocabulary, scope boundary (internal identifiers out), and compatibility policy (3.x deprecation; zero user-visible "doctrine" by 4.0).
  - Inventory covers 100% of user-facing surface categories with occurrence counts and stable class identifiers; internal identifiers and legacy-marked historical artifacts explicitly classified out.
  - Methodology states the surface ordering with per-choice rationale and the invariant that must hold at each stack level, including terminology-guard handling (shrink-only) and alias introduction/removal verification.
  - Stacked plan assigns every occurrence class to exactly one downstream mission (or defers with rationale); the first stack mission is spec-ready from these artifacts alone.
- Definition of done:
  - `spec.md` committed and substantive; quality checklist passes.
  - ADR authored, registered via `python -m scripts.docs.freshen_adr_inventory`, and amends/supersedes the terminology portion of ADR `2026-07-15-1`.
  - Inventory, methodology, and stacked plan committed as mission artifacts.
  - `tests/architectural/test_no_legacy_terminology.py` still green (this mission adds no user-facing "doctrine" usage).

## Entities
- Domain concepts and relationships: Charter (umbrella term) → three senses {charter bundle, active charter, inactive charter}; Charter kind (directive/tactic/styleguide/toolguide/paradigm/procedure) is orthogonal to the senses; Occurrence class links inventory → stacked mission → completion audit.
- Glossary terms (canonical):
  - **Charter** — umbrella for the governance artefact layer and its activation state (replaces "doctrine" in user-facing language).
  - **Charter bundle** — the per-project file set under `.kittify/charter/` (`charter.yaml` authoritative structured source per ADR 2026-07-18-1, `charter.md` curated companion).
  - **Active charter** — a wired-in (activated) governance artefact.
  - **Inactive charter** — an un-activated governance artefact present in a pack.
  - **Charter kind** — the surviving kind vocabulary; unchanged by this decision.
  - **Doctrine (legacy)** — retired in user-facing language; permitted only in legacy-marked historical artifacts and internal code identifiers.

## Approach
- Selected strategy: Plan-first, authority-first sequencing with an **atomic authority flip** — this mission produces ADR (decision record) + inventory + methodology + stacked plan; the stack is 5 active missions + 1 deferred to 4.0 (operator-approved, decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`): M1 `charter-authority-flip` (glossary rewrite + charter-bundle update via `charter.yaml`/regeneration incl. the ADR's Terminology Canon line + guard arming as last WP — one mission, one PR) → M2 `charter-cli-surface` (hidden aliases + warnings, per-subcommand alias tests, same-wave CI consumer updates) → M3 `charter-packs-source` (`packs/built-in/`) → M4 `charter-skills-artifacts` (`src/doctrine/skills/` + generated agent dirs via migration) → M5 `charter-docs-prose` (`docs/` + root docs; ADR titles stay legacy) → M6 `charter-removal-audit` (deferred to 4.0: strip aliases, run the NFR-001 zero-doctrine audit). The atomic flip closes catfooding hazard C1 (research.md R8): arming the guard before replacement terms are canonical would trap concurrent missions between a forbidden old word and uncanonical new terms (DIRECTIVE_048).
- Tradeoffs considered:
  - Scope A (user-facing only) vs full internal rename — chose A per operator decision; keeps the program bounded and avoids the `src/charter/` package collision.
  - Hard break vs deprecation window — chose 3.x deprecation with a binding 4.0 end state (repo shim burn-down precedent).
  - Kinds retire vs survive — chose survive; cascade syntax and DRG edge vocabulary depend on kind precision.
  - Separate guard-wave-0 mission vs guard arming inside M1 — chose inside M1 (last WP); a separate wave-0 creates the C1 conflict window.
  - Coarser ~3-mission grouping vs per-wave — operator chose per-wave (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`); each wave keeps one surface class, one invariant to verify, one reviewable PR.

## Structure
- Code surfaces affected (this mission): `docs/adr/3.x/` (new ADR + index row + page-inventory lockfile via freshen script; `2026-07-15-1` status frontmatter only — C-003 carve-out), mission artifacts under `kitty-specs/retire-doctrine-term-01M0JMK9/` (inventory, methodology, stacked plan; schemas in `contracts/`). No `src/` or test changes.
- Components and dependencies: IC-01 ADR authoring/registration → IC-02 occurrence inventory (mechanical audit, string-level scope rule) → IC-03 methodology analysis (ordering + invariants I0–I6 + guard design) → IC-04 stacked mission plan (5+1, every OC-## assigned once) → IC-05 verification (SC-001..SC-004 + guard green). Single stream — no parallel work. The ADR amends `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (terminology portion; resolution mechanics intact).
- Ownership boundaries: This mission owns the decision record and the plan; downstream stacked missions own execution of each surface wave. Canonical sources verified at plan phase: `packs/built-in/` = artifact YAML source (hatch-shipped to site-packages); `src/doctrine/skills/` = skill source; `.kittify/charter/charter.yaml` = bundle authority (ADR 2026-07-18-1).

## Operations
- Ordered implementation steps: (1) ADR + index registration, (2) occurrence inventory by surface with class identifiers, (3) ordering/methodology analysis, (4) stacked mission plan with dependencies and per-mission inputs/outputs.
- Test strategy: ADR self-sufficiency review pass; case-insensitive audit of user-facing surfaces against the inventory (0 unclassified hits); guard test `tests/architectural/test_no_legacy_terminology.py` green; stacked-plan completeness check (every class assigned or deferred).

## Norms
- Coding/style conventions: ADR follows `docs/architecture/adr-template.md`; dated naming `YYYY-MM-DD-N-<slug>.md`; index updated via the freshen script (module form `python -m scripts.docs.freshen_adr_inventory`).
- Observability, testing, and team rules: Terminology Canon discipline (name the sense of overloaded terms); historical artifacts stay immutable snapshots marked legacy; no user-facing "doctrine" introduced by this mission's own artifacts.

## Safeguards
- Hard constraints and invariants: C-001 (no rename execution here), C-003 (historical artifacts immutable), C-004 (guard green at every stack level, shrink-only updates), C-005 (internal identifiers untouched).
- Security rules: none specific to this mission.
- Performance limits: none specific to this mission (planning artifacts only).
- Things not to break: `spec-kitty charter sync` / context resolution (charter file is load-bearing); agent skill routing during the alias window; the terminology guard between waves.

## Deviations (append-only)
- 2026-08-21 — specify — Decision Moment Protocol requires a mission handle, but discovery precedes `mission create`; the three resolved decisions were recorded via open+resolve immediately after creation (audit trail preserved). — CLI cannot mint pre-create decisions (`FEATURE_CONTEXT_UNRESOLVED`).
