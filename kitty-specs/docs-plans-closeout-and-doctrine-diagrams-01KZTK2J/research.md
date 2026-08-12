# Research: docs/plans Closeout and Doctrine Schema Diagrams

Consolidates the pre-spec investigations (SaaS-plan, docs-Tier-3, doctrine-docs-map,
artefact-schemas, PlantUML-integration) with the `doc_status` enumeration grep. Each
decision below resolves a Technical Context unknown or a spec requirement.

## D1 — `doc_status: durable` marker and its propagation sites (FR-002, C-005)

- **Decision**: Add `DURABLE = "durable"` to the canonical `DocStatus(StrEnum)` and teach every
  validation site to accept it; the retire tooling and freshness/structural gates treat `durable`
  as never-retire.
- **Enumeration sites (verified via `git grep doc_status`)**:
  - `scripts/docs/frontmatter_backfill.py` — `class DocStatus(StrEnum)` (line ~109): the canonical enum. Add `DURABLE`.
  - `packs/built-in/styleguides/common-docs.styleguide.yaml` — the frontmatter contract / allowed `doc_status` set consumed by the structural lint (verify the allowlist and extend).
  - `tests/docs/test_docs_structural_lint.py`, `test_frontmatter_backfill.py`, `test_audience_resolves.py`, `test_description_length_gate.py`, `test_adr_converter.py` — tests that assert on doc_status values; extend fixtures/expectations.
  - The structural-lint asset (`common-docs-structural-lint`) frontmatter-contract check.
- **Rationale**: A dedicated enum value is machine-distinguishable (chosen over `throughline: true` field per operator decision); the retire sweep keys on it directly.
- **Alternatives considered**: new frontmatter field `throughline: true` (rejected by operator — prefers a first-class `doc_status`); "active + banner convention" (rejected — not machine-distinguishable).
- **Risk**: a missed validation site rejects `durable`. Mitigation: a test that asserts `durable` passes every gate over a fixture domain plan (ATDD red-first).

## D2 — Retire/archive sweep evidence and mechanism (FR-001, NFR-005, C-001)

- **Decision**: Per-document retirement, evidence-gated. Mechanism: **in-place `superseded`/`closeout`
  marker** for RECORD-tier docs; **move-to-archive** for whole dead clusters. Never delete content.
- **Candidate ledger (from docs-Tier-3 investigation)** — 11 clusters:
  - **Auto-retireable (3, evidenced in open-core plan §1.2/§1.4)**: `engineering-notes/runtime_and_state_overhaul/`, `naming-identity-ssot-strangler/`, `3-2-x-goal-corroboration/`.
  - **Evidence-gated (8, need a per-doc `gh issue view` before flip)**: the `3-2-0-training-bugs-2007/` + surface/symmetry clusters; `doctrine/` architecture-review drafts (RECORD-tier, selective — do NOT sweep the #3324-relocated `charter-sole-door-deferred-issues.md`); `reviews/` PR305 cluster; `refactor/` #1111 debriefs; `3-2-doc-publication/` checklist; stale `investigations/` drafts; `next-mission-mappings/` compat surface.
  - **Deferred (blocked, C-001)**: `3-2-x-milestone-roadmap.md` — retire only when open-core item R lands.
- **Rationale**: retirement must be reversible and honest; a blanket sweep would hide un-shipped work.
- **Risk**: partial-shipping. Mitigation: a doc stays live if its backing design is not fully shipped.

## D3 — Two new domain plans + boundary seams (FR-003, FR-004)

- **Decision**: Author `packs-extraction-domain-plan.md` (physical extraction/modularization lineage:
  standalone `spec-kitty-doctrine` module boundary, the charter↔doctrine import-cycle blocker, in-place
  strangler cutover, repo-split transparency) and `api-dashboard-domain-plan.md` (application/mission-data
  API #645 + dashboard/UX #650). Each states an explicit non-goal against doctrine-charter §3.2 (pack
  ecosystem) and §3.6 (doctrine public API).
- **Source material**: open-core plan §2.2–2.3 + the verified standalone `src/doctrine/pyproject.toml`
  (`spec-kitty-doctrine` v1.0.0); epics #2466/#2539/#2216 (packs), #645/#650 (api-dashboard).
- **Rationale**: complete the four-domain throughline set with no overlap.

## D4 — PlantUML docsite rendering approach (FR-006, NFR-002/003/004, C-004/006)

- **Decision**: Local **build-time `plantuml.jar` pre-render**, wired as a **post-DocFX HTML
  post-processor** (`scripts/docs/plantuml_render.py`, mirroring `glossary_linker.py`) that replaces
  `@startjson`/`@startyaml` fences with SVGs in `docs/_site`. Both `docs-pages.yml` and
  `docs-build-pr.yml` gain: `actions/setup-java` (Temurin 17) → fetch a **pinned** `plantuml.jar`
  (version + sha256) → run the render with `-DPLANTUML_SECURITY_PROFILE=SANDBOX`. SVGs CI-generated,
  not committed. No `docfx.json` change; native Mermaid undisturbed.
- **Rationale**: keeps doctrine content **local** (zero egress), reproducible, extends a proven seam.
- **Alternatives considered**: client-side plantuml-server encoder (**rejected** — egresses doctrine
  content to plantuml.com unless self-hosted; C-006); custom .NET DocFX plugin (**rejected** — highest
  effort, still needs the jar, fragile against `dotnet tool install -g docfx@latest`).
- **Accepted limitation (C-004)**: SVGs render only on the built docsite, not github.com source view.

## D5 — Doctrine artefact schemas (source of truth for diagrams) (FR-008, FR-010, NFR-001)

- **Decision**: Generate `@startyaml` typed-placeholder diagrams from the **frozen** code models
  (`frozen=True, extra="forbid"` → closed field sets, safe to depict completely). A drift guard
  (FR-010) compares each diagram's fields against its model and fails on mismatch.
- **Model source of truth (verified)**:
  - agent-profile → `src/doctrine/agent_profiles/schema_models.py:AgentProfileSchema` (6-section, kebab-case)
  - mission-type/step/action-index → `src/doctrine/missions/models.py` (`MissionType`, `MissionStep`), `step_contracts.py:MissionStepContract`, `action_index.py:ActionIndex`
  - DRG → `src/doctrine/drg/models.py` (`NodeKind`×15, `Relation`×15, `DRGNode/Edge/Graph`, `RELATION_DESCRIPTIONS`)
  - artefact-kind vocab → `src/doctrine/artifact_kinds.py:ArtifactKind` (12 members)
  - other kinds → `src/doctrine/<plural>/models.py` (directive/tactic/paradigm/styleguide/toolguide/procedure/glossary_pack/asset)
- **Trap**: `styleguides/models.py:AntiPattern` (inline example type) ≠ the DRG `anti_pattern` node — do not conflate (FR-009).
- **Placement (doctrine-docs-map)**: cross-kind overview in `doctrine-kinds.md`; DRG in `doctrine-relationships.md`; mission-type/step in `mission-type-resolution.md`.

## D6 — Diagram/code drift guard mechanism (FR-010, NFR-001)

- **Decision**: A pytest guard that parses each schema diagram's field set and asserts it equals the
  field set introspected from the source model (Pydantic `model_fields` / dataclass fields). Fails on
  any add/remove/rename. Runs in `tests/docs/` (or `tests/architectural/`).
- **Rationale**: makes NFR-001 (zero drift) enforceable rather than aspirational; ATDD red-first.

## Open questions

None blocking. The 8 evidence-gated retire candidates are resolved per-doc **during implementation**
(each WP carries its `gh issue view` evidence line), not pre-committed here.
