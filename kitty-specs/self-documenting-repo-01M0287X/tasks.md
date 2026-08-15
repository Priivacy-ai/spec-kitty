# Work Packages: Self-documenting repo — migrate agent-memory gap-fillers

**Mission**: self-documenting-repo-01M0287X | **Branch**: `kitty/mission-self-doc-gapclose`
**Spec**: `spec.md` | **Plan**: `plan.md`

Decomposition per the post-plan squad (implementer-ivan + paula-patterns). Parallel: WP01, WP02, WP03. WP04 after WP03 (shared generated yaml). WP05 terminal.

---

## Work Package WP01: Gate-remedy enrichment (G1) (Priority: P1)

**Goal**: Add content-anchored remedies to the gates that genuinely lack them, derived from current gate code and validated by tripping the gate; a meta-test pins remedy presence.
**Independent Test**: A meta-test asserts each registered gate's assertion carries a remedy substring; each remedy is validated by tripping its gate in a scratch tree.
**Prompt**: `/tasks/WP01-gate-remedy-enrichment.md`
**Dependencies**: None
**Requirement Refs**: FR-001, NFR-003, C-005, SC-001

### Included Subtasks
- [ ] T001 Locate each enumerated gate in code; classify remedy-extensible vs not-applicable (shard→auto-covered/#2671 retired; analysis-report-staleness→narrow correctness test; docs-move→`test_relative_link_fixer.py`+`test_related_validator.py`; mission-gate→locate/drop). Record the classification (feeds the manifest).
- [ ] T002 Add a content-anchored remedy line to each confirmed remedy-extensible gate (`test_no_write_side_rederivation.py`, `test_no_inert_schema_slots.py`, the docs-link gates), derived from the gate's own logic — never transcribed from memory.
- [ ] T003 Add `tests/architectural/test_gate_remedy_presence.py` meta-test asserting each registered gate's assertion contains its remedy substring.
- [ ] T004 Validate each remedy by tripping the gate in a scratch tree; confirm golden-count remains the model (already complete).

---

## Work Package WP02: CLAUDE.md source-location sweep (G2) (Priority: P1)

**Goal**: Correct every stale `src/doctrine/missions/…` reference in CLAUDE.md to `packs/built-in/missions/…`; a grep-guard test prevents regression.
**Independent Test**: A test asserts zero `src/doctrine/missions/` occurrences in CLAUDE.md; terminology guard passes.
**Prompt**: `/tasks/WP02-claudemd-source-sweep.md`
**Dependencies**: None
**Requirement Refs**: FR-002, SC-003

### Included Subtasks
- [x] T005 Sweep all `src/doctrine/missions/…` refs in CLAUDE.md (Template-Source table, flow diagram, Use-Canonical-Sources section) → `packs/built-in/…`.
- [x] T006 Add `tests/architectural/test_claudemd_template_source.py` grep-guard (0 stale refs).

---

## Work Package WP03: Coord/lane recovery entries in operations (G3) (Priority: P1)

**Goal**: Publish six coord/lane split-brain recovery entries in `docs/operations/`, each leading with a shipped `doctor … --fix` where one exists (audit first), cross-linked to `docs/guides/how-to/recovery/` and the root-cause note; registered so docs-freshness stays green.
**Independent Test**: Each split-brain reproduces to recovery via the entry; `check_docs_freshness --ci` errors=0.
**Prompt**: `/tasks/WP03-operations-recovery-entries.md`
**Dependencies**: None
**Requirement Refs**: FR-003, FR-004, C-001, C-002, NFR-001, SC-002

### Included Subtasks
- [ ] T007 Audit `spec-kitty doctor` subcommands + `--fix` semantics per split-brain class (present/partial/absent); verify names (`workspaces`→`_workspace_husk_doctor.py`).
- [ ] T008 Author the six recovery entries (`divio_type: none`), leading with the shipped command, manual fallback + operator-grant caveat where no `--fix`; cite `docs/plans/engineering-notes/coord-splitbrain-rootcause.md`.
- [ ] T009 Register in `recovery-index.md` + `toc.yml`; add bidirectional cross-links with `docs/guides/how-to/recovery/` + a one-line IA rationale.
- [ ] T010 Regenerate `docs/development/3-2-page-inventory.yaml` + `3-2-docs-retrieval-index.yaml` via `inventory_lockfile.py --write`; `check_docs_freshness --ci` errors=0.

---

## Work Package WP04: Discoverable commands + env/tracker docs (G4, G6) (Priority: P2)

**Goal**: Make repo-owned workflow commands discoverable (docs-inventory freshen, mission wrap-up; regen is a pointer to #3447) and document env/tracker conventions.
**Independent Test**: A fresh reader finds the freshen/wrap-up commands + the env/tracker conventions in `docs/development/**`; `check_docs_freshness --ci` errors=0.
**Prompt**: `/tasks/WP04-discoverable-commands-and-conventions.md`
**Dependencies**: WP03
**Requirement Refs**: FR-005, FR-007, C-003, NFR-001

### Included Subtasks
- [ ] T011 Document the docs-inventory freshen + mission wrap-up commands; reference #3447 for regen (do not duplicate).
- [ ] T012 Document env gotchas (pyenv-editable-shadows-pipx, pre-commit interpreter pin) + tracker conventions (retired `bug` label → native type; tension/opposed_by edges).
- [ ] T013 Regenerate the two docs yaml (serialized after WP03); `check_docs_freshness --ci` errors=0.

---

## Work Package WP05: File bugs + migration manifest (G5, FR-008) (Priority: P2)

**Goal**: File the three behavior-quirk bugs (fixes deferred), and write the committed migration manifest mapping every G1–G6 gap-filler to its repo home / tracking issue / "behavior retired".
**Independent Test**: A manifest-completeness test asserts every G1–G6 gap-filler maps to a repo home, an issue ref, or an explicit "retired" outcome.
**Prompt**: `/tasks/WP05-file-bugs-and-manifest.md`
**Dependencies**: WP01, WP02, WP03, WP04
**Requirement Refs**: FR-006, FR-008, C-004, SC-004, SC-005

### Included Subtasks
- [ ] T014 File the three behavior-quirk bugs (finalize-clobbers-matrix, review-cycle double-increment, status-daemon stale-commit); record issue refs.
- [ ] T015 Author `docs/development/agent-memory-migration-manifest.md` mapping each audited gap-filler → repo home / issue / "behavior retired" (e.g. shard-registration is retired by #2671 auto-cover).
- [ ] T016 Add a manifest-completeness test (derives the set from the audit headers; asserts home paths exist).
- [ ] T017 Regenerate rollups + `check_docs_freshness --ci` errors=0 (the manifest is an inventoried docs/development page).
