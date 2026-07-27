---
work_package_id: WP04
title: Version leakage check tool
dependencies:
- WP02
requirement_refs:
- FR-005
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "36258"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: python-pedro
authoritative_surface: scripts/docs/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- scripts/docs/__init__.py
- scripts/docs/version_leakage_check.py
- scripts/docs/_inventory.py
- scripts/docs/_render.py
- tests/docs/__init__.py
- tests/docs/conftest.py
- tests/docs/test_version_leakage_check.py
- tests/docs/fixtures/__init__.py
- tests/docs/fixtures/clean_inventory.yaml
- tests/docs/fixtures/dirty_inventory.yaml
- tests/docs/fixtures/missing_inventory.yaml
- tests/docs/fixtures/sample_pages/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Implement the read-only `scripts/docs/version_leakage_check.py` tool plus shared helpers (`_inventory.py`, `_render.py`) and a pytest suite that covers exit codes 0/1/2. The tool enforces FR-005 / NFR-002 by detecting docs leakage between version tiers.

## Context

- Contract: [`contracts/version_leakage_check.md`](../contracts/version_leakage_check.md). Read it end to end before coding.
- Data shapes: [`data-model.md`](../data-model.md) §"PageInventoryEntry", §"VersionTag", §"FreshnessReport".
- Charter policy summary: typer or argparse OK (no new pip deps); ruamel.yaml for YAML; rich for output; pytest with ≥ 90% coverage; mypy `--strict`.
- No network access. Read-only on all input files.

## Subtasks

### T009 — Implement `_inventory.py`

- Load `PageInventoryEntry` list from YAML via ruamel.yaml.
- Validate each row against the invariants in `data-model.md`.
- Return a typed dataclass list. Surface load errors as a structured exception with exit code 2 mapping.

### T010 — Implement `_render.py`

- One function each for `render_table_rich(findings)` and `render_table_plain(findings)`.
- Both functions accept the same list of `FreshnessFinding` and emit deterministic output.
- Rich output uses a single `rich.table.Table`; plain output uses tab-separated columns suitable for CI annotations.

### T011 — Implement `version_leakage_check.py`

Implement the script per the contract. Required behavior:

- CLI flags: `--inventory PATH`, `--docs-root PATH`, `--banner-regex PATTERN`, `--report PATH`, `--ci`.
- Walk the inventory; for each `PageInventoryEntry`:
  - Read the page file (UTF-8); if missing, emit `LEAK-MISSING-FILE`.
  - If the page has frontmatter, parse `version_tag`; compare with the inventory row; emit `LEAK-FRONTMATTER-MISMATCH` on disagreement.
  - If `tag == current`, parse markdown links via regex; for each link target that resolves to an `archival` inventory entry, emit `LEAK-CURRENT-LINKS-ARCHIVAL` unless the link is wrapped in a migration banner block.
  - If `tag in {archival, migration}`, scan the first 20 non-empty lines for the banner regex; emit `LEAK-MISSING-BANNER` on miss.
- Walk `docs-root` filesystem; emit `LEAK-MISSING-INVENTORY` for every `.md` file not in the inventory.
- Aggregate findings into a `FreshnessReport`-shaped slice; serialize JSON if `--report` is passed; print rich or plain output otherwise.

Exit codes (per contract): 0 clean, 1 errors, 2 input error, 3 environmental.

### T012 — Author pytest fixtures

- `tests/docs/fixtures/clean_inventory.yaml` — happy-path inventory matching a tiny `sample_pages/` tree.
- `tests/docs/fixtures/dirty_inventory.yaml` — one entry per finding rule (5 rules → 5 entries).
- `tests/docs/fixtures/missing_inventory.yaml` — malformed YAML for the input-error path.
- `tests/docs/fixtures/sample_pages/**` — tiny markdown tree with: one current page, one archival page (with banner), one migration page (with banner), one current page that wrongly links to archival, one page missing from inventory.

### T013 — Author `tests/docs/test_version_leakage_check.py`

- Parametrize over the three fixtures plus a `--ci` variant.
- Assert exit codes 0/1/2 across the suite.
- Assert finding counts for the dirty case match the rule list exactly.
- Coverage ≥ 90% for `scripts/docs/version_leakage_check.py`, `_inventory.py`, `_render.py`.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `A`. Reuses the lane-A worktree from WP01–WP03.

## Test Strategy

- Unit tests on `_inventory.py` (load + validate) and `_render.py` (deterministic output).
- Integration tests on the full script via `subprocess.run` against the fixtures.
- Coverage configured via existing pytest-cov; CI reports ≥ 90% for the new modules.
- mypy `--strict` clean on every new file.
- ruff clean.

## Definition of Done

- [ ] All four new modules under `scripts/docs/` exist and mypy `--strict` clean.
- [ ] All test files exist and `pytest tests/docs/test_version_leakage_check.py -v` is green.
- [ ] Coverage ≥ 90% for the new modules.
- [ ] Exit codes 0, 1, 2 verified by the fixture suite.
- [ ] No files outside `owned_files` modified.

## Risks

- **Markdown link parsing fragility** — Mitigation: use a conservative regex (`\[([^\]]+)\]\(([^)]+)\)`); accept that anchor-only links are out of scope (documented as a non-guarantee in the contract).
- **YAML load errors masking content errors** — Mitigation: explicit `try/except` mapping with structured error finding.

## Reviewer Guidance

- Confirm contract fidelity: every CLI flag, every exit code, every rule_id in the contract has an implementation and a test.
- Confirm no docs pages are written by the tool under any code path.
- Confirm coverage report shows ≥ 90% on new modules.

## Implement command

```bash
spec-kitty agent action implement WP04 --agent claude
```

## Activity Log

- 2026-05-21T07:28:00Z – claude:opus-4-7:python-pedro:implementer – shell_pid=31268 – Started implementation via action command
- 2026-05-21T07:37:17Z – claude:opus-4-7:python-pedro:implementer – shell_pid=31268 – WP04 ready: leakage tool + helpers + tests (mypy --strict clean, coverage 99%). All 5 rule IDs implemented; exit codes 0/1/2/3 covered.
- 2026-05-21T07:37:40Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=36258 – Started review via action command
- 2026-05-21T07:39:47Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=36258 – Renata review: pass. mypy --strict clean on the 4 source files (default invocation needs --explicit-package-bases because scripts/ lacks __init__.py — env config issue, not a code issue). 51/51 tests pass, coverage 99% total (lowest module 98% on _inventory.py, all >=90% required). ruff clean. All 5 rule IDs (LEAK-CURRENT-LINKS-ARCHIVAL, LEAK-MISSING-BANNER, LEAK-FRONTMATTER-MISMATCH, LEAK-MISSING-INVENTORY, LEAK-MISSING-FILE) implemented per contract. All 5 CLI flags (--inventory, --docs-root, --banner-regex, --report, --ci) present. Exit codes 0/1/2/3 all covered. No network imports. No writes to docs/ or inventory paths (only --report JSON path, intentional). No pip dep changes. 19 committed files all within owned_files. Commit cd823d150 references WP04.
- 2026-05-21T09:27:11Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=36258 – Moved to done
