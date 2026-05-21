# Tasks: Spec Kitty 3.2 Documentation Refresh

**Mission**: `spec-kitty-3-2-docs-01KS4KSZ` | **Mission ID**: `01KS4KSZ67PMNRJ057BGT0Z8AW` | **Phase**: 2 (Tasks)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data Model**: [data-model.md](./data-model.md) · **Contracts**: [contracts/](./contracts/) · **Quickstart**: [quickstart.md](./quickstart.md)

Branch contract: current=`main`, planning_base=`main`, merge_target=`main`. WP lane worktrees allocated at implement time.

## Subtask Index (reference only — tracking happens via per-WP checkboxes below)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author 5-tag version taxonomy doc | WP01 |  |
| T002 | Read-only survey of `docs/**/*.md` to enumerate every page | WP01 |  |
| T003 | Author `occurrence_map.yaml` covering 8 bulk-edit categories | WP01 |  |
| T004 | Author `docs/development/3-2-page-inventory.yaml` with one row per page | WP02 |  |
| T005 | Validate inventory against `PageInventoryEntry` invariants | WP02 |  |
| T006 | Flag manual-review pages with notes | WP02 |  |
| T007 | Diff-shaped navigation plan covering `docs/toc.yml` and every child TOC | WP03 |  |
| T008 | Explicit nav-group plan for 3.2-current, 3.1-supported, Migration, Archive 2.x, Archive 1.x | WP03 |  |
| T009 | Implement `scripts/docs/_inventory.py` (ruamel.yaml loader) | WP04 |  |
| T010 | Implement `scripts/docs/_render.py` (rich/plain output helpers) | WP04 |  |
| T011 | Implement `scripts/docs/version_leakage_check.py` per contract | WP04 |  |
| T012 | Author pytest fixtures (clean + dirty inventory; sample pages) | WP04 |  |
| T013 | Implement `tests/docs/test_version_leakage_check.py` covering exit codes 0/1/2 | WP04 |  |
| T014 | `git show` the four prior CLI reference commits | WP05 |  |
| T015 | Author `docs/development/3-2-cli-reference-methodology.md` | WP05 |  |
| T016 | Implement `scripts/docs/_typer_walker.py` (shared Typer walker, read-only) | WP06 |  |
| T017 | Implement `scripts/docs/build_cli_reference.py` per contract | WP06 |  |
| T018 | Implement `scripts/docs/check_cli_reference_freshness.py` per contract | WP06 |  |
| T019 | Author tests (unit, integration smoke, fixture-driven) for builder and freshness checker | WP06 |  |
| T020 | Implement `tests/architectural/test_docs_cli_reference_parity.py` | WP06 |  |
| T021 | Run `build_cli_reference.py --mode hybrid` to rebuild reference pages | WP07 |  |
| T022 | Preserve existing hand-authored prose blocks across the regeneration | WP07 |  |
| T023 | Author `docs/development/3-2-cli-reference-audit-meta-issues.md` schema and seed rows from `cli-audit-3-2.md` | WP07 |  |
| T024 | Confirm `check_cli_reference_freshness.py` exits 0 against the rebuilt reference | WP07 |  |
| T025 | Author Divio information architecture doc with every planned 3.2 page | WP08 |  |
| T026 | Produce gap list (reuse/rewrite/new) for all four Divio directories | WP08 |  |
| T027 | Author archive/migration plan with page-level disposition for archival 1.x/2.x and migration 3.1 | WP09 |  |
| T028 | Cross-check that every inventory row tagged archival or migration appears in the archive plan | WP09 |  |
| T029 | Author harness research method doc | WP10 |  |
| T030 | Inventory generated files for each candidate harness | WP10 |  |
| T031 | Verify external doc citations for each harness | WP10 |  |
| T032 | Populate `docs/reference/supported-harnesses.md` matrix (5 tiers, 16 harnesses) | WP10 |  |
| T033 | Author per-harness setup-and-usage pages for harnesses ≥ partial | WP11 | [P] within lane |
| T034 | Add at least one external citation per harness page | WP11 | [P] |
| T035 | Author install-macos / install-linux / install-windows how-tos | WP12 | [P] within lane |
| T036 | Author upgrade-cli and upgrade-project how-tos | WP12 |  |
| T037 | Author uninstall how-to (CLI + project files + rollback) | WP12 |  |
| T038 | Author pip-vs-pipx-vs-uv explanation | WP12 |  |
| T039 | Author init-lifecycle and upgrade-lifecycle reference pages | WP12 |  |
| T040 | Implement `scripts/docs/check_docs_freshness.py` per contract | WP13 |  |
| T041 | Implement `tests/docs/test_check_docs_freshness.py` | WP13 |  |
| T042 | Wire freshness check into existing CI quality workflow | WP13 |  |
| T043 | Author `docs/development/3-2-publication-checklist.md` | WP14 |  |
| T044 | Verify checklist covers every spec.md acceptance criterion and links to evidence artifacts | WP14 |  |

## Dependency Graph

```
WP01 → WP02 → WP03
            ↘ WP04
WP05 → WP06 → WP07
              ↘
WP02 ──→ WP08
WP02 ──→ WP09
WP10 → WP11
WP12 (independent)
WP04 + WP06 → WP13
WP07 + WP09 + WP11 + WP12 + WP13 → WP14
```

## Lanes

| Lane | Workstream | WPs | Bulk-Edit |
|------|------------|-----|-----------|
| A | Version taxonomy & filtering | WP01, WP02, WP03, WP04 | WP01 authors `occurrence_map.yaml`; WP02 is an active bulk-edit WP |
| B | CLI reference & audit | WP05, WP06, WP07 | — |
| C | Divio IA & migration plan | WP08, WP09 | WP09 is an active bulk-edit WP (page moves) |
| D | Harness research & matrix | WP10, WP11 | — |
| E | Install lifecycle | WP12 | — |
| F | Freshness & publication | WP13, WP14 | — |

## Work Packages

### WP01 — Version taxonomy & bulk-edit guardrail surface

- **Goal**: Author the 5-tag version taxonomy and produce a complete `occurrence_map.yaml` for the page-inventory frontmatter rollout (which becomes the active bulk edit in WP02).
- **Priority**: P1 — blocks WP02, WP03, WP04.
- **Independent test**: `occurrence_map.yaml` validates against the bulk-edit skill schema; taxonomy doc references the `VersionTag` enum from `data-model.md`.
- **Dependencies**: none.
- **Prompt**: [tasks/WP01-version-taxonomy-and-occurrence-map.md](./tasks/WP01-version-taxonomy-and-occurrence-map.md)
- **Estimated size**: ~350 lines.
- **Subtasks**:
  - [x] T001 Author 5-tag version taxonomy doc (WP01)
  - [x] T002 Read-only survey of `docs/**/*.md` to enumerate every page (WP01)
  - [x] T003 Author `occurrence_map.yaml` covering 8 bulk-edit categories (WP01)

### WP02 — Page inventory (active bulk edit)

- **Goal**: One `PageInventoryEntry` row per docs page with `version_tag`, `divio_type`, `owning_workstream`, `current_target`, citations.
- **Priority**: P1 — blocks WP03, WP04, WP08, WP09.
- **Independent test**: 100% of `.md` files under `docs/`, `architecture/`, and root README appear in the inventory; every row passes the data-model invariants.
- **Dependencies**: WP01.
- **Bulk-edit gate**: required (per `occurrence_map.yaml`).
- **Prompt**: [tasks/WP02-page-inventory.md](./tasks/WP02-page-inventory.md)
- **Estimated size**: ~350 lines.
- **Subtasks**:
  - [x] T004 Author `docs/development/3-2-page-inventory.yaml` (WP02)
  - [x] T005 Validate inventory against `PageInventoryEntry` invariants (WP02)
  - [x] T006 Flag manual-review pages with notes (WP02)

### WP03 — Navigation update plan

- **Goal**: Diff-shaped plan describing every move/add/remove in `docs/toc.yml` and child TOCs without yet editing live TOC files.
- **Priority**: P2.
- **Independent test**: Plan covers every TOC file in the inventory.
- **Dependencies**: WP02.
- **Prompt**: [tasks/WP03-navigation-update-plan.md](./tasks/WP03-navigation-update-plan.md)
- **Estimated size**: ~300 lines.
- **Subtasks**:
  - [x] T007 Diff-shaped navigation plan covering every TOC file (WP03)
  - [x] T008 Explicit nav-group plan for the five visibility buckets (WP03)

### WP04 — Version leakage check tool

- **Goal**: Implement the read-only `version_leakage_check.py` plus shared `_inventory.py`/`_render.py` helpers and pytest coverage.
- **Priority**: P2 — blocks WP13.
- **Independent test**: `pytest tests/docs/test_version_leakage_check.py` green; exit-code matrix 0/1/2 verified.
- **Dependencies**: WP02.
- **Charter alignment**: mypy `--strict`, ≥90% coverage, ruff clean, no new deps.
- **Prompt**: [tasks/WP04-version-leakage-check-tool.md](./tasks/WP04-version-leakage-check-tool.md)
- **Estimated size**: ~520 lines.
- **Subtasks**:
  - [x] T009 Implement `_inventory.py` (WP04)
  - [x] T010 Implement `_render.py` (WP04)
  - [x] T011 Implement `version_leakage_check.py` per contract (WP04)
  - [x] T012 Author pytest fixtures (clean + dirty + sample pages) (WP04)
  - [x] T013 Implement `test_version_leakage_check.py` covering exit codes 0/1/2 (WP04)

### WP05 — CLI reference methodology recovery

- **Goal**: Recover prior CLI reference methodology from git history and write the methodology note.
- **Priority**: P1 — blocks WP06.
- **Independent test**: Methodology note records commit-by-commit evidence for `a14769e7a`, `81b3d6c3e`, `514106af2`, `deee8d7f3`.
- **Dependencies**: none.
- **Prompt**: [tasks/WP05-cli-reference-methodology.md](./tasks/WP05-cli-reference-methodology.md)
- **Estimated size**: ~300 lines.
- **Subtasks**:
  - [x] T014 `git show` the four prior CLI reference commits (WP05)
  - [x] T015 Author `docs/development/3-2-cli-reference-methodology.md` (WP05)

### WP06 — CLI reference builder + freshness checker + tests

- **Goal**: Implement the read-only Typer walker, the reference builder, the freshness checker, pytest coverage, and the architectural parity test.
- **Priority**: P1 — blocks WP07, WP13.
- **Independent test**: pytest green; integration smoke imports real `specify_cli.app` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and confirms visible-path count ≥ 192 ± 10%.
- **Dependencies**: WP05.
- **Charter alignment**: mypy `--strict`, ≥90% coverage, integration tests for CLI surfaces, no new deps.
- **Prompt**: [tasks/WP06-cli-reference-builder-and-freshness.md](./tasks/WP06-cli-reference-builder-and-freshness.md)
- **Estimated size**: ~620 lines.
- **Subtasks**:
  - [x] T016 Implement `_typer_walker.py` (WP06)
  - [x] T017 Implement `build_cli_reference.py` per contract (WP06)
  - [x] T018 Implement `check_cli_reference_freshness.py` per contract (WP06)
  - [x] T019 Author tests (unit, integration smoke, fixture-driven) (WP06)
  - [x] T020 Implement `tests/architectural/test_docs_cli_reference_parity.py` (WP06)

### WP07 — Rebuilt CLI reference + agent-subcommands + meta-issue file

- **Goal**: Regenerate the public CLI reference, preserve hand-authored prose, and seed the meta-issue file with audit findings.
- **Priority**: P1 — blocks WP14.
- **Independent test**: `check_cli_reference_freshness.py` exits 0; architectural test passes.
- **Dependencies**: WP06.
- **Prompt**: [tasks/WP07-rebuild-cli-reference-and-meta-issues.md](./tasks/WP07-rebuild-cli-reference-and-meta-issues.md)
- **Estimated size**: ~380 lines.
- **Subtasks**:
  - [x] T021 Run `build_cli_reference.py --mode hybrid` to rebuild reference pages (WP07)
  - [x] T022 Preserve existing hand-authored prose blocks across the regeneration (WP07)
  - [x] T023 Author meta-issue file schema and seed rows from `cli-audit-3-2.md` (WP07)
  - [x] T024 Confirm `check_cli_reference_freshness.py` exits 0 (WP07)

### WP08 — Divio information architecture & gap list

- **Goal**: Author the 3.2 IA doc with every planned page, Divio type, audience, nav placement, and disposition.
- **Priority**: P2.
- **Independent test**: Gap list covers all four Divio directories; every page referenced in WP07 reference is referenced.
- **Dependencies**: WP02, WP05.
- **Prompt**: [tasks/WP08-information-architecture.md](./tasks/WP08-information-architecture.md)
- **Estimated size**: ~340 lines.
- **Subtasks**:
  - [x] T025 Author IA doc with every planned 3.2 page (WP08)
  - [x] T026 Produce gap list (reuse/rewrite/new) for all four Divio directories (WP08)

### WP09 — Archive/migration plan (active bulk edit)

- **Goal**: Page-level disposition for every archival 1.x/2.x page and every 3.1 page.
- **Priority**: P2.
- **Independent test**: Every inventory row tagged archival or migration appears in the plan.
- **Dependencies**: WP02.
- **Bulk-edit gate**: required (path moves and frontmatter banner adds for 1.x/2.x).
- **Prompt**: [tasks/WP09-archive-and-migration-plan.md](./tasks/WP09-archive-and-migration-plan.md)
- **Estimated size**: ~360 lines.
- **Subtasks**:
  - [x] T027 Author archive/migration plan with page-level disposition (WP09)
  - [x] T028 Cross-check every archival/migration inventory row against the plan (WP09)

### WP10 — Harness research method + support matrix

- **Goal**: Author the harness research method and populate the 5-tier support matrix for 16 candidate harnesses.
- **Priority**: P1 — blocks WP11.
- **Independent test**: Every harness has a tier and at least one citation_ref for tier ≥ supported; matrix renders as one page.
- **Dependencies**: none.
- **Prompt**: [tasks/WP10-harness-research-and-matrix.md](./tasks/WP10-harness-research-and-matrix.md)
- **Estimated size**: ~420 lines.
- **Subtasks**:
  - [ ] T029 Author harness research method doc (WP10)
  - [ ] T030 Inventory generated files for each candidate harness (WP10)
  - [ ] T031 Verify external doc citations for each harness (WP10)
  - [ ] T032 Populate `docs/reference/supported-harnesses.md` matrix (WP10)

### WP11 — Per-harness setup-and-usage pages

- **Goal**: One user-facing setup-and-usage page per harness classified `partial` or higher.
- **Priority**: P2.
- **Independent test**: Each page cites at least one external doc; freshness check's citation rule passes.
- **Dependencies**: WP10.
- **Prompt**: [tasks/WP11-per-harness-pages.md](./tasks/WP11-per-harness-pages.md)
- **Estimated size**: ~520 lines.
- **Subtasks**:
  - [ ] T033 Author per-harness setup-and-usage pages for harnesses ≥ partial (WP11)
  - [ ] T034 Add at least one external citation per harness page (WP11)

### WP12 — Install / upgrade / uninstall lifecycle

- **Goal**: Full install lifecycle coverage: pip/pipx/uv on macOS/Linux/Windows; upgrade and uninstall flows; pip-vs-pipx-vs-uv explanation; init/upgrade lifecycle references.
- **Priority**: P2.
- **Independent test**: Every (tool × OS) cell has install/upgrade/uninstall/verification commands; PATH/PowerShell/py-launcher notes captured.
- **Dependencies**: none.
- **Prompt**: [tasks/WP12-install-upgrade-uninstall.md](./tasks/WP12-install-upgrade-uninstall.md)
- **Estimated size**: ~580 lines.
- **Subtasks**:
  - [ ] T035 Author install-macos / install-linux / install-windows how-tos (WP12)
  - [ ] T036 Author upgrade-cli and upgrade-project how-tos (WP12)
  - [ ] T037 Author uninstall how-to (CLI + project files + rollback) (WP12)
  - [ ] T038 Author pip-vs-pipx-vs-uv explanation (WP12)
  - [ ] T039 Author init-lifecycle and upgrade-lifecycle reference pages (WP12)

### WP13 — Freshness orchestrator + tests + CI wiring

- **Goal**: Aggregate the leakage check and CLI freshness checker into a single tool; wire CI step.
- **Priority**: P2 — blocks WP14.
- **Independent test**: pytest green; CI step passes on a clean checkout.
- **Dependencies**: WP04, WP06.
- **Prompt**: [tasks/WP13-docs-freshness-orchestrator.md](./tasks/WP13-docs-freshness-orchestrator.md)
- **Estimated size**: ~420 lines.
- **Subtasks**:
  - [ ] T040 Implement `check_docs_freshness.py` per contract (WP13)
  - [ ] T041 Implement `test_check_docs_freshness.py` (WP13)
  - [ ] T042 Wire freshness check into existing CI quality workflow (WP13)

### WP14 — Publication checklist + final sweep

- **Goal**: Author the publication gate checklist with evidence requirements and verify every acceptance criterion has a citation.
- **Priority**: P3 — final WP.
- **Independent test**: Checklist covers every `spec.md` acceptance criterion.
- **Dependencies**: WP07, WP09, WP11, WP12, WP13.
- **Prompt**: [tasks/WP14-publication-checklist.md](./tasks/WP14-publication-checklist.md)
- **Estimated size**: ~280 lines.
- **Subtasks**:
  - [ ] T043 Author `docs/development/3-2-publication-checklist.md` (WP14)
  - [ ] T044 Verify checklist covers every spec.md acceptance criterion (WP14)

## MVP Scope Recommendation

Lane B (WP05 → WP06 → WP07) is the most user-visible early win: it produces the rebuilt CLI reference that the public docs link to. Lane A (WP01 → WP02) is the prerequisite for every other workstream and should land in parallel with Lane B.

## Parallelization

- Lanes A and B start simultaneously (no shared owned_files).
- Lane D (WP10) and Lane E (WP12) start in parallel with A and B.
- Once WP02 lands, Lanes C, F (WP04 dependency), and downstream WP08/WP09 can begin.
- WP11 starts as soon as WP10 lands.
- WP13 needs WP04 + WP06.
- WP14 is sequential — it gathers evidence from every other lane.
