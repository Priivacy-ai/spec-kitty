# Work Packages: Bootstrap Playwright for dashboard UI regression coverage

**Mission**: `playwright-ui-e2e-bootstrap-01KWX72W` | **Issues**: Closes #1008 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. Two WPs: WP01 = the framework bootstrap + synthetic fixture + the ONE e2e test; WP02 = CI wiring + CLAUDE.md/docs. WP02 depends on WP01 (needs the runnable test).

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Add `pytest-playwright` dev dep + minimal config; Chromium via install/cache (not committed); respect `test_pyproject_shape.py` + version-bump/CHANGELOG if `__init__.py` changes | WP01 | FR-001 |
| T002 | Synthetic-mission fixture (`tests/ui/conftest.py`): temp project root with WP(s) using dict `agent:{tool,model}` + `agent_profile` + `role` frontmatter; boot in-thread via `start_dashboard(background_process=False)` on `find_free_port()`, headless | WP01 | FR-003 |
| T003 | The ONE e2e (`tests/ui/test_dashboard_wp_modal.py`): load page → click WP card → assert modal renders `agent`/`model`/`agent_profile`/`role` + `prompt_markdown` (populated) | WP01 | FR-002 |
| T004 | Non-vacuity: simulate the #970 regression (modal drops agent identity) → the test fails cleanly; green with it intact | WP01 | FR-006 |
| T005 | CI job: scoped headless Playwright (browser cached) wired into the merge gate; bounded (one test, not a full-suite dep) | WP02 | FR-004, FR-005, NFR-001 |
| T006 | Point `CLAUDE.md`'s "Playwright proof" rule at the real test path; add `docs/development/ui-e2e.md` (page-inventory registered + `description` frontmatter) on how to extend | WP02 | FR-005 |

---

## Work Package WP01: Framework bootstrap + synthetic fixture + the kanban→modal e2e (Priority: P1)
**Prompt**: `/tasks/WP01-bootstrap-and-e2e.md`
**Goal**: `pytest-playwright` installed + a hermetic synthetic-mission fixture (dict-form frontmatter, in-thread `start_dashboard`) + the ONE e2e asserting the modal renders the canonical agent identity + prompt — non-vacuous vs the #970 regression.
### Included Subtasks
- [x] T001 pytest-playwright bootstrap (WP01)
- [x] T002 Synthetic fixture + in-thread boot (WP01)
- [x] T003 The kanban→modal e2e (WP01)
- [x] T004 Non-vacuity (#970 simulation) (WP01)
### Dependencies
None.
### Risks & Mitigations
- Vacuous pass / blank badges → dict `agent:{tool,model}` frontmatter the scanner decomposes; assert populated canonical DOM fields.
- Flake / leak → in-thread `start_dashboard(background_process=False)`, ephemeral port, explicit Playwright waits (no sleeps), headless.

## Work Package WP02: CI wiring + CLAUDE.md/docs (Priority: P1)
**Prompt**: `/tasks/WP02-ci-and-docs.md`
**Goal**: run the e2e headless in CI (browser cached) as a scoped merge-gate job; make the CLAUDE.md "Playwright proof" rule real + document how to extend.
### Included Subtasks
- [ ] T005 Scoped headless Playwright CI job (WP02)
- [ ] T006 CLAUDE.md rule → real path + docs/development/ui-e2e.md (WP02)
### Dependencies
WP01 (needs the runnable test).
### Risks & Mitigations
- CI bloat → scoped job, cached browser, one test.
- Docs-inventory gate → regenerate the inventory + add `description` frontmatter.
