# Tasks: Common Docs Doctrine & Reconciliation (Mission A)

**Mission**: `common-docs-consolidation-01KW3Q6M` · **Branch**: `docs/2165-consolidation-research`

6 work packages mirror the 6 implementation concerns. **Lane shape:** WP01 (the ADR) is the serial spine that gates everything; WP02 (doctrine) and WP03/WP04 (two rulers) run in parallel after it; WP05 (ratchet) needs WP01 + WP02; WP06 (skills) needs WP01. **No doc-tree mutation** (C-006); **rulers ship report-only** (C-002). The Definition of Done for every ruler WP (WP03/04/05) is **its self-test demonstrably going RED on the seeded violation**.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Scaffold the reconciliation ADR (title/status/context) | WP01 | | [D] |
| T002 | Decide Candidate A + `doc_status` namespace + the 13-section structure | WP01 | | [D] |
| T003 | Decide the DocFX redirect mechanism (meta-refresh stubs) | WP01 | | [D] |
| T004 | Decide the glossary read-path mapping (seed read-path + extraction source) | WP01 | | [D] |
| T005 | Decide the era-less-ADR migration plan + the curation/lifecycle policy | WP01 | | [D] |
| T006 | Record acceptance + the merge-boundary note (C-001) | WP01 | | [D] |
| T007 | Author the Common Docs directive (bound to the ratchet) | WP02 | | [D] |
| T008 | Author the Common Docs styleguide (each rule → a live check) | WP02 | | [D] |
| T009 | Author the Common Docs tactic(s) | WP02 | | [D] |
| T010 | Wire the 3 nodes into `graph.yaml` (`regenerate-graph`) | WP02 | | [D] |
| T011 | Add the DRG freshness `--check` gate | WP02 | | [D] |
| T012 | Define the directive id + the binding contract for the ratchet | WP02 | | [D] |
| T013 | Build `related_validator.py` (resolvable-path check, report-only, `checked_count`) | WP03 | [D] |
| T014 | Self-test: dangling-edge fixture → RED + asserts `checked_count > 0` | WP03 | [D] |
| T015 | Report-only baseline run (emit count, exit 0) | WP03 | [D] |
| T016 | Build `inventory_lockfile.py` (frontmatter→inventory; drop `citation_refs`) | WP04 | [D] |
| T017 | Invert `check_docs_freshness.py` to generate-and-compare | WP04 | [D] |
| T018 | **Linchpin self-test**: frontmatter tamper → lockfile changes + gate RED; lockfile hand-edit → rejected | WP04 | [D] |
| T019 | Gate the `LEAK-FRONTMATTER-MISMATCH` retirement on the new gate being proven red (do NOT delete early) | WP04 | [D] |
| T020 | Report-only baseline run | WP04 | [D] |
| T021 | Build `anti_sprawl_ratchet.py` (4 detectors, report-only) | WP05 | |
| T022 | The content-anchored floor (enumerated 13 sections / exactly-one-root) | WP05 | |
| T023 | The violation message references the directive id (binding, C-003) | WP05 | |
| T024 | Self-test: 4 injection fixtures (one per condition) each detected | WP05 | |
| T025 | Report-only baseline run | WP05 | |
| T026 | Decide install-vs-out-of-scope for the Common Docs Agent Skills (per ADR) | WP06 | [D] |
| T027 | Install `common-docs-scaffold/write/find` into `.agents/skills/` + manifest, OR remove the dangling `common-docs-write` reference | WP06 | [D] |
| T028 | Verify no requirement/scenario references an absent skill | WP06 | [D] |

## Work Packages

### WP01 — Reconciliation ADR (serial spine) — `tasks/WP01-reconciliation-adr.md`
- **Goal**: One accepted ADR deciding all 7 mechanisms; gates every other WP. **Requirements**: FR-001, C-004. **Independent test**: the ADR records D1–D7; SC-001.
- **Subtasks**: T001–T006. **Deps**: none. **Risk**: the ADR is a merge boundary (C-001).

### WP02 — Doctrine artifacts + DRG — `tasks/WP02-doctrine-drg.md`
- **Goal**: directive + styleguide + tactic(s), DRG-wired + freshness-gated; the directive is bound to the ratchet. **Requirements**: FR-002/003/004, C-003/C-005, SC-002. **Independent test**: `regenerate-graph --check` green; the directive id is the contract WP05 references.
- **Subtasks**: T007–T012. **Deps**: WP01. **Risk**: #1755 DRG footgun; #2153 doc-policy bug (don't depend on it).

### WP03 — `related:` validator (ruler 1, report-only) — `tasks/WP03-related-validator.md`
- **Goal**: a resolvable-path validator + its self-test. **Requirements**: FR-005, NFR-001. **Independent test**: the dangling-edge fixture goes RED; `checked_count > 0`.
- **Subtasks**: T013–T015. **Deps**: WP01. **Parallel** with WP04.

### WP04 — Lockfile generator + freshness inversion (ruler 2, report-only) — `tasks/WP04-inventory-lockfile.md`
- **Goal**: frontmatter→inventory generator + the inverted freshness gate + the **linchpin tamper self-test**. **Requirements**: FR-006, NFR-004, SC-006. **Independent test**: T018 (tamper → RED; hand-edit → rejected).
- **Subtasks**: T016–T020. **Deps**: WP01. **Parallel** with WP03.

### WP05 — Anti-sprawl ratchet (ruler 3, report-only) — `tasks/WP05-anti-sprawl-ratchet.md`
- **Goal**: the 4-condition ratchet (report-only) + the content-anchored floor + the directive-binding + 4 injection self-tests. **Requirements**: FR-007, SC-003/004, C-002. **Independent test**: the 4 injection fixtures each detected; the floor is the enumerated 13 sections; the violation message carries the directive id.
- **Subtasks**: T021–T025. **Deps**: WP01, WP02 (the directive).

### WP06 — Agent Skills resolution — `tasks/WP06-agent-skills.md`
- **Goal**: install the three Common Docs skills or declare out-of-scope + remove the dangling reference. **Requirements**: FR-008. **Independent test**: no requirement references an absent skill.
- **Subtasks**: T026–T028. **Deps**: WP01. **Parallel** with WP02/03/04.
