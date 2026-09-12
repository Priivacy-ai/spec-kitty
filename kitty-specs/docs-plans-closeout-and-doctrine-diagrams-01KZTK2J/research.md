# Research: docs/plans Tier 3 Closeout (Scope A)

Consolidates the pre-spec docs-Tier-3 investigation with the post-plan squad's Scope-A findings.
Scope-B research (PlantUML integration, artefact schemas, drift guard) moves to Mission B.

## D1 — `doc_status: durable` vocabulary and its propagation sites (FR-002, NFR-001, C-004/C-005)

- **Decision**: `durable` is a **reserved, never-retire** value added to the vocabulary. The
  AUTHORITY is **directive `042-common-docs`** (the closed vocabulary is declared there and
  restated); the `DocStatus` StrEnum **mirrors** it. Editing the enum alone leaves directive
  (authority) and code inconsistent — that is doctrine/code drift.
- **Full enumeration of validation/enumeration sites** (post-plan squad, independently grepped):
  1. `packs/built-in/directives/042-common-docs.directive.yaml` — **authoritative vocabulary** (edit first).
  2. `scripts/docs/frontmatter_backfill.py:DocStatus` (StrEnum) — the mirror.
  3. `packs/built-in/styleguides/common-docs.styleguide.yaml` — `structural_lint_config` (`point_in_time_markers`, `frontmatter_required_fields`) + vocabulary prose. Assert `durable ∉ point_in_time`.
  4. `packs/built-in/styleguides/docs-freshness-sla.styleguide.yaml` — the freshness/retire gate (never-stale for durable).
  5. `packs/built-in/assets/docs_structural_lint.py` — `point_in_time_markers` consumer.
  6. `src/doctrine/styleguides/models.py` + the generated schema — if durable is encoded structurally.
  7. Tests: `tests/docs/{test_docs_structural_lint,test_frontmatter_backfill,test_audience_resolves,test_description_length_gate}.py` **and** `tests/doctrine/test_schema_generation_integrity.py`.
  8. (Awareness) `scripts/docs/bulk_ref_rewrite.py`, `frontmatter_backfill_sections.yaml`, `publication-authority.styleguide.yaml`, `divio-type-discipline.styleguide.yaml` — verify none reject an unlisted value.
- **Correction**: `closeout` is **not** a `DocStatus` value (enum = draft/active/deprecated/superseded);
  it is a point-in-time-marker / archive-directory convention → `deprecated`. FR-001's mechanism uses
  `deprecated` (or move-to-archive), never a `closeout` enum value.
- **Risk**: a missed site rejects `durable`. Mitigation: a directive-042-led enumeration + one test
  asserting `durable` passes every site (red-first).

## D2 — Retire/archive sweep evidence and mechanism (FR-001, NFR-002, C-001)

- **Decision**: per-document, evidence-gated. Mechanism: `doc_status: deprecated` in place (RECORD-tier)
  or move-to-archive (dead clusters). Content is never deleted. **There is no automated sweep tool** —
  this is manual curation.
- **Candidate ledger (11 clusters)**: 3 auto-retireable (`runtime_and_state_overhaul/`,
  `naming-identity-ssot-strangler/`, `3-2-x-goal-corroboration/` — evidenced in the open-core plan);
  8 evidence-gated (per-doc `gh issue view` before flip; do NOT sweep the #3324-relocated
  `charter-sole-door-deferred-issues.md`); 1 deferred (`3-2-x-milestone-roadmap.md`, C-001).
- **Decomposition**: fan out at tasks time (auto batch + per-evidence-source WPs).

## D3 — Two new domain plans + boundary seams (FR-003, FR-004)

- **Decision**: `packs-extraction-domain-plan.md` (physical extraction/modularization lineage:
  standalone `spec-kitty-doctrine` module boundary, the charter↔doctrine import-cycle blocker,
  in-place strangler cutover, repo-split transparency) and `api-dashboard-domain-plan.md`
  (application/mission-data API #645 + dashboard/UX #650). Each declares an explicit non-goal against
  doctrine-charter §3.2 (pack ecosystem) and §3.6 (doctrine public API).
- **Source material**: open-core plan §2.2–2.3 + the standalone `src/doctrine/pyproject.toml`; epics
  #2466/#2539/#2216 (packs), #645/#650 (api-dashboard).

## D4 — domains/ migration (FR-005, C-002)

- **Decision**: move all four plans into `docs/plans/domains/` with a `domains/index.md`; update every
  reference (index, `3-2-x-*` release docs, §6 cross-refs); regenerate the docs lockfiles.
  `change_mode: bulk_edit` + a schema-conformant `occurrence_map.yaml` (per
  `src/doctrine/schemas/occurrence-map.schema.yaml`) so the gate fires. Verified by the
  relative-link-fixer test (zero dead links).

## Open questions

None blocking. The 8 evidence-gated retire candidates are resolved per-document during implementation.
