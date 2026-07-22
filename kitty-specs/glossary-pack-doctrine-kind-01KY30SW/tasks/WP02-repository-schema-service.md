---
work_package_id: WP02
title: Pack repository + schema + service accessor + boundary guard
dependencies:
- WP01
requirement_refs:
- C-002
- C-004
- FR-004
- FR-005
planning_base_branch: research/glossary-doctrine-artefact
merge_target_branch: research/glossary-doctrine-artefact
branch_strategy: Planning artifacts for this mission were generated on research/glossary-doctrine-artefact. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/glossary-doctrine-artefact unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/glossary_packs/
create_intent:
- src/doctrine/glossary_packs/__init__.py
- src/doctrine/glossary_packs/models.py
- src/doctrine/glossary_packs/repository.py
- tests/doctrine/glossary_packs/test_models.py
- tests/doctrine/glossary_packs/test_repository.py
- tests/architectural/test_glossary_pack_boundary.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/doctrine/glossary_packs/__init__.py
- src/doctrine/glossary_packs/models.py
- src/doctrine/glossary_packs/repository.py
- src/doctrine/service.py
- tests/doctrine/glossary_packs/test_models.py
- tests/doctrine/glossary_packs/test_repository.py
- tests/architectural/test_glossary_pack_boundary.py
role: implementer
tags: []
tracker_refs: []
shell_pid: "1550469"
shell_pid_created_at: "1784667810.92"
---

# WP02 — Pack repository + schema + service accessor + boundary guard

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and adopt it fully (type-safe Python, TDD, full gate before
handoff). **Boundary**: the schema and repository shape are ratified in `data-model.md` and
`contracts/pack-schema.md`. Implement faithfully; escalate genuine ambiguity, don't invent.

## Objective

Create the greenfield `src/doctrine/glossary_packs/` package: a `GlossaryPack` aggregate and a
`GlossaryTerm` entity that carries **every field the seed carries** (so migration is provably
zero-loss), a `GlossaryPackRepository` that inherits `BaseDoctrineRepository` and globs
`*.glossary-pack.yaml`, and a `DoctrineService.glossary_packs` accessor. Also ship the C-002
import-boundary guard proving the package never couples to the retiring runtime `src/glossary/`.
No pack content and no activation wiring here (WP03/WP04).

## Context

- **Design of record**: `data-model.md` (GlossaryPack/GlossaryTerm tables), `contracts/pack-schema.md`
  (§1, §3), `plan.md` IC-02.
- **Requirements owned**: FR-004 (repository), FR-005 (schema), C-004 (enforcement fields present,
  unwired), C-002 (no runtime coupling — the import-boundary guard).
- **Squad-verified facts** (do not relitigate): the seed at `.kittify/glossaries/spec_kitty_core.yaml`
  has **104 terms**; `confidence` is a **float** (0.6/0.75/0.9/0.95/1.0), NOT enum/str; the seed also
  carries `see_also`, `introduced_in_mission`, and populated `synonyms_to_avoid` — the schema MUST
  carry all of them. `BaseDoctrineRepository` (`src/doctrine/…/base.py`) provides glob loading +
  provenance; a `GlossaryPackRepository(BaseDoctrineRepository[GlossaryPack])` with `_schema` +
  `_glob="*.glossary-pack.yaml"` is the correct "copy directive" for the repo half.
- **Naming**: package dir/accessor/plural = `glossary_packs`; `DoctrineService.glossary_packs`;
  `_built_in_dir("glossary_packs")` (which resolves `<root>/glossary_packs/built-in`).

## Subtasks

### T006 — Model round-trip test (RED-FIRST) · FR-005, C-004

- File: `tests/doctrine/glossary_packs/test_models.py` (create the package + `__init__` for tests dir).
- Author a fixture pack (in-test YAML or a tmp file) with a term that populates EVERY field:
  `surface`, `definition`, `confidence` (a float like `0.9`), `status`, `see_also`,
  `introduced_in_mission`, `synonyms_to_avoid`, `aliases`, `banned_synonyms`.
- Assert the loaded `GlossaryTerm` exposes every field unchanged; `confidence` is a `float`; a term
  omitting the optional fields loads with `None` defaults (decided default is `None`, matching the
  runtime `TermSense`). RED first (models don't exist yet).

### T007 — Implement `GlossaryPack` / `GlossaryTerm` models · FR-005

- File: `src/doctrine/glossary_packs/models.py`.
- `GlossaryTerm`: `surface: str`, `definition: str`, `confidence: float`, `status: str`, and optional
  `see_also: list[str] | None = None`, `introduced_in_mission: str | None = None`,
  `synonyms_to_avoid: list[str] | None = None`, `aliases: list[str] | None = None`,
  `banned_synonyms: list[str] | None = None`.
- `GlossaryPack`: `id: str`, `provenance: str` (`built-in`/`org`/`project`), `terms: list[GlossaryTerm]`
  (non-empty), `description: str | None = None`.
- Use the project's standard model idiom (pydantic/dataclass — match `directive`'s model style).

### T008 — Implement `GlossaryPackRepository` + `__all__` · FR-004

- File: `src/doctrine/glossary_packs/repository.py`; `GlossaryPackRepository(BaseDoctrineRepository[GlossaryPack])`
  with `_glob = "*.glossary-pack.yaml"` and the `GlossaryPack` schema. Mirror the `directive` repository.
- `src/doctrine/glossary_packs/__init__.py` declares `__all__` exporting the public models + repository.

### T009 — `DoctrineService.glossary_packs` accessor · FR-004

- Edit `src/doctrine/service.py`: add a `glossary_packs` accessor that wires
  `_built_in_dir("glossary_packs")` into a `GlossaryPackRepository`, mirroring the existing
  `directives`/`tactics` accessors (see `service.py:68-142`).

### T010 — Duplicate-surface validation + enforcement round-trip · FR-005, C-004

- Duplicate `surface` within a pack → load/validation error. The real seed has no dups, so add a
  **synthetic** fixture with two identical surfaces and assert the error.
- Assert `aliases`/`banned_synonyms` round-trip unchanged (forward-compat for Mission B). Confirm NO
  gate consumes them yet (they are inert in Mission A).

### T011 — C-002 import-boundary architectural test · C-002

- File: `tests/architectural/test_glossary_pack_boundary.py`.
- Statically assert **no module under `src/doctrine/glossary_packs/` imports the runtime `glossary`
  package**. Walk the package sources via **AST** (`ast.Import`/`ast.ImportFrom`) and match the
  module name `glossary` at a **module boundary** — i.e. reject `import glossary`,
  `import glossary.<x>`, `from glossary import …`, `from glossary.<x> import …` — while explicitly
  **NOT** matching the sibling package `glossary_packs` (a naive substring/regex on `"glossary"`
  would collide with the package's own name). This is the non-vacuous guard that keeps the #1418
  `pack_seed_loader` ACL from being reintroduced.
- **Prove it fails**: the test itself (or a co-located self-test) must demonstrate that an injected
  `from glossary import X` in a fixture source would be flagged, and that a `from glossary_packs …`
  import is NOT flagged — otherwise the guard is vacuous.

## Branch Strategy

Planning base `research/glossary-doctrine-artefact`; execution worktree per `lanes.json` lane; merge
back to `research/glossary-doctrine-artefact` unless redirected.

## Definition of Done

- [ ] T006 model round-trip RED-first → GREEN, covering all fields + float confidence + None defaults.
- [ ] Models, repository, `__init__` (`__all__`) implemented; `DoctrineService.glossary_packs` wired.
- [ ] Duplicate-surface rejected; enforcement fields round-trip.
- [ ] C-002 import-boundary test present and passing (and provably fails if a `glossary` import is added).
- [ ] `ruff` + `mypy --strict` clean; complexity ≤ 15; new code ≥ 90% covered.
- [ ] `pytest tests/doctrine/glossary_packs/ tests/architectural/test_glossary_pack_boundary.py -q` green.

## Risks & Reviewer Guidance

- **Risk**: dropping a seed field (the exact vacuous-migration trap the squad caught) — reviewer
  checks the model carries `see_also`/`introduced_in_mission`/`synonyms_to_avoid` and `confidence: float`.
- **Risk**: the import-boundary test asserting a tautology — reviewer confirms it actually parses the
  package sources and would fail on an injected `from glossary import ...`.
- **Reviewer**: confirm the repository truly inherits `BaseDoctrineRepository` (no re-implemented glob).

## Activity Log

- 2026-07-21T20:51:35Z – claude:sonnet:python-pedro:implementer – shell_pid=1537018 – Assigned agent via action command
- 2026-07-21T21:00:36Z – claude:sonnet:python-pedro:implementer – shell_pid=1537018 – WP02 complete; models(all seed fields,float confidence,None defaults), repository, service accessor, non-vacuous import-boundary guard — targeted tests+ruff+mypy green
- 2026-07-21T21:04:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=1550469 – Started review via action command
- 2026-07-21T21:07:41Z – user – shell_pid=1550469 – Review passed: schema carries all 9 seed fields (confidence:float, optional->None); repository inherits BaseDoctrineRepository (no re-implemented glob/merge); DoctrineService.glossary_packs wired via _built_in_dir and proven live through a through-service load test; T011 boundary guard is AST-based, module-boundary, non-vacuous (self-tests prove 'from glossary import X' flagged, 'glossary_packs' NOT); dup-surface rejected at model+load; 30/30 tests green, ruff+mypy --strict clean; commit touches only owned files + test scaffolding.
