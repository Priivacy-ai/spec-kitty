# REASONS Canvas — Retire the Doctrine Term

> Mission: retire-doctrine-term-01M0JMK9
> Generated: 2026-08-21
> Charter activation: structured-prompt-driven-development (paradigm)

## Requirements
- Problem statement: Spec Kitty's user-facing vocabulary splits "doctrine" (the artefact layer) from "charter" (the compiled file and activation surface); the operator has decided "doctrine" is retired and everything user-facing becomes "charter", with a three-way distinction — this mission plans that retirement (ADR + inventory + methodology + stacked plan) without executing it.
- Acceptance criteria:
  - ADR in `docs/adr/3.x/` (template + actual-date naming + index registration) records: the decision, the three-way distinction (charter bundle / active charter / inactive charter), surviving kind vocabulary, scope boundary (non-public internals out; operator identifiers and supported public APIs in), and compatibility policy (3.x deprecation; zero user-visible "doctrine" by 4.0).
  - Inventory covers all content occurrences and matching tracked pathnames with one-row-per-hit evidence, stable class identifiers, and explicit X1/X2/X3 classification.
  - Methodology states ordering/rationale and I0–I6, including exact occurrence-fingerprint guard mutations, per-surface verification, compatibility proof, and rollback.
  - Stacked plan assigns every occurrence class to exactly one downstream mission (or defers with rationale); the first stack mission is spec-ready from these artifacts alone.
- Definition of done:
  - `spec.md` committed and substantive; quality checklist passes.
  - ADR authored, registered via `python -m scripts.docs.freshen_adr_inventory`, and amends/supersedes the terminology portion of ADR `2026-07-15-1`.
  - Inventory + `inventory-hits.tsv`, methodology, and stacked plan committed as mission artifacts.
  - `tests/architectural/test_no_legacy_terminology.py` still green (this mission adds no user-facing "doctrine" usage).

## Entities
- Domain concepts and relationships: Charter (umbrella term) → Charter Pack (offer), Charter Bundle (project-local consume surface), Active/Inactive Charter (individual artefact activation); surviving kind labels remain orthogonal; manifest hits roll up to occurrence classes and stacked missions.
- Glossary terms (canonical):
  - **Charter** — umbrella for the governance artefact layer and its activation state (replaces "doctrine" in user-facing language).
  - **Charter Pack** — a versioned distributable governance catalogue, the offer side.
  - **Charter bundle** — the per-project file set under `.kittify/charter/`; human-owned and generated sections retain documented owners.
  - **Active charter** — a wired-in (activated) governance artefact.
  - **Inactive charter** — an unactivated governance artefact available in a Charter Pack.
  - **Charter kind** — the surviving kind vocabulary; unchanged by this decision.
  - **Doctrine (legacy)** — deprecated/non-canonical after ADR acceptance. Pre-I1 authorities remain transitional; inventoried primary-use debt shrinks in its M1–M5 owner wave; registered 3.x compatibility surfaces remain only until M6; X history/internal/test evidence survives.

## Approach
- Selected strategy: ADR acceptance fixes the future decision while existing authorities remain operational through pre-I1 transition. Authority-first atomic M1 (`docs/context/charter.md` plus active referrers, X2 refs retained as history, both YAML authorities, owner-correct charter/config edits, CR materialization, guard last) → M2 exhaustive command/serialized/API map + CLI projection + semantic config → M3 packs/overlays to `.kittify/charter-packs/` + directive ID → M4 skills/profile/prompts/agents → M5 remaining active prose regardless directory → M6 CR compatibility removal + terminal audit. Each wave is bulk edit, maps M1→I1 through M6→I6, and follows prefix-safe rollback.
- Tradeoffs considered:
  - Scope A (user-facing only) vs full internal rename — chose A per operator decision; keeps the program bounded and avoids the `src/charter/` package collision.
  - Hard break vs deprecation window — chose 3.x deprecation with a binding 4.0 end state (repo shim burn-down precedent).
  - Kinds retire vs survive — chose survive; cascade syntax and DRG edge vocabulary depend on kind precision.
  - Separate guard-wave-0 mission vs guard arming inside M1 — chose inside M1 (last WP); a separate wave-0 creates the C1 conflict window.
  - Coarser ~3-mission grouping vs per-wave — operator chose per-wave (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`); each wave keeps one surface class, one invariant to verify, one reviewable PR.

## Structure
- Surfaces affected (this mission): ADR + registration files, mission planning/lifecycle/review artifacts, and required docs-contract example/ratchet metadata. No product source rename.
- Components and dependencies: IC-01 ADR authoring/registration → IC-02 occurrence inventory (current-target audit, string-level scope rule, CR candidates) → IC-03 methodology analysis (ordering + invariants I0–I6 + guard/CR design) → IC-04 stacked mission plan (5+1, every OC-## one M1–M5 owner, every CR one introduction + M6 removal, funded OC owner = introduction) → IC-05 verification (SC-001..SC-004 + guard green). Single stream — no parallel work. The ADR amends `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (terminology portion; resolution mechanics intact).
- Ownership boundaries: This mission owns decision and plan. M1 respects three glossary authorities/parity; `charter.yaml` has human + generated sections, `charter.md` is curated, `charter generate` owns catalog/metadata, and sync writes nothing. Downstream missions own product execution.

## Operations
- Ordered implementation steps: (1) ADR + index registration, (2) occurrence inventory by surface with class identifiers, (3) ordering/methodology analysis, (4) stacked mission plan with dependencies and per-mission inputs/outputs.
- Test strategy: exact six-question ADR review by one independent reviewer; pinned content+pathname audit joined to manifest (0 unclassified); docs-contract/ratchet + guard tests; exactly-once assignments and M1 dry run.

## Norms
- Coding/style conventions: ADR follows `docs/architecture/adr-template.md`; dated naming `YYYY-MM-DD-N-<slug>.md`; index updated via the freshen script (module form `python -m scripts.docs.freshen_adr_inventory`).
- Observability, testing, and team rules: Terminology Canon discipline (name the sense of overloaded terms); historical artifacts stay immutable snapshots marked legacy; after ADR acceptance, unregistered new primary use is forbidden while existing inventoried debt and registered 3.x compatibility follow their owner-wave contracts.

## Safeguards
- Hard constraints and invariants: C-001 planning-only; C-003 every merged ADR body/title plus immutable event/merged-mission history (archive optional; ADR status/pointer carve-out); C-004 ordinary fingerprints plus non-owning CR reservation/control overlay with four ordinary + six CR mutations and fail-closed M2 pre-edit blocking; C-005 non-public internals untouched while supported public APIs migrate; pre-I1 current authority remains coherent; M1→I1 … M6→I6; reverse-suffix/forward-fix rollback.
- Security rules: none specific to this mission.
- Performance limits: none specific to this mission (planning artifacts only).
- Things not to break: charter context/resolution, glossary parity, config/path migrations, workflow consumers, agent routing during alias window, and fingerprint guard between waves. `charter sync` is not a writer.

## Deviations (append-only)
- 2026-08-21 — specify — Decision Moment Protocol requires a mission handle, but discovery precedes `mission create`; the three resolved decisions were recorded via open+resolve immediately after creation (audit trail preserved). — CLI cannot mint pre-create decisions (`FEATURE_CONTEXT_UNRESOLVED`).
