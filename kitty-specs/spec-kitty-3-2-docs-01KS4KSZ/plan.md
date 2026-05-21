# Implementation Plan: Spec Kitty 3.2 Documentation Refresh

**Branch**: `main` (mission lands on main; lane branches per WP) | **Date**: 2026-05-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/spec.md`
**Mission ID**: `01KS4KSZ67PMNRJ057BGT0Z8AW` | **Mission Slug**: `spec-kitty-3-2-docs-01KS4KSZ`

## Summary

Make Spec Kitty 3.2 docs the complete current source of truth: classify every docs page with a version-relevance tag, rebuild the CLI reference against the live Typer tree (192 visible paths per `cli-audit-3-2.md`), reorganize content along the Divio four-type model, research and classify all supported harnesses, document the install/upgrade/uninstall lifecycle across pip/pipx/uv on macOS/Linux/Windows, and add validation to prevent version leakage and reference drift.

Technical approach: write a small read-only docs-tooling layer under `scripts/docs/` that (a) walks the Typer app with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and emits the reference, (b) walks a YAML page inventory to enforce version-tag rules, (c) orchestrates both into a single freshness check usable from CI and from the publication checklist. Page content (tutorials, how-tos, reference, explanation, per-harness, install-lifecycle) is hand-authored against the new information architecture but anchored to machine-checkable artifacts.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing `specify_cli` runtime; charter policy summary)
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (all already in `pyproject.toml`); stdlib only for new tooling (`pathlib`, `argparse` or `typer`, `subprocess`, `re`, `dataclasses`). No new pip deps.
**Storage**: Filesystem only — markdown (docs pages, planning artifacts), YAML (page inventory), JSONL (`status.events.jsonl` already maintained by runtime), JSON (cached Typer command tree under `scripts/docs/_cache/` if needed; gitignored).
**Testing**: pytest with ≥90% coverage for new code under `scripts/docs/`; integration tests use fixtures under `tests/docs/fixtures/` and a smoke test that imports the real Typer app with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and `SPEC_KITTY_NO_UPGRADE_CHECK=1` set before import. Architectural test mirrors `tests/architectural/test_safety_registry_completeness.py` to assert reference parity.
**Target Platform**: Local docs build (existing site generator under `docs/`; presence of `docs/docfx.json` indicates DocFX, but the plan reserves the option to confirm or pivot during Phase 0 research) and CI Linux runners. Install docs cover macOS, Linux, and Windows users.
**Project Type**: Single Python CLI project. Documentation work lives under `docs/`; tooling under `scripts/docs/`; tests under `tests/docs/` and `tests/architectural/`; planning artifacts under `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/`.
**Performance Goals**: Reference build completes in under 60s on a developer laptop for the full 192-visible-path walk (each `--help` invocation is a subprocess call; budget allows ~300ms × 192 = ~58s). Freshness check completes in under 90s end-to-end (reference walk + page-inventory scan + link spot-checks).
**Constraints**: Read-only access to the Typer app (no mutation of command code or help text from tooling); no SaaS/tracker/hosted-auth/sync execution unless explicitly approved with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; no live doc edits outside `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/` during specify/plan/tasks; mypy `--strict` clean; ruff clean.
**Scale/Scope**: ~192 visible command paths in the CLI reference; ~hundreds of markdown pages across `docs/` (exact count gathered in research.md from page inventory); ~16 candidate harnesses for the support matrix; 9 (tool × OS) cells for install lifecycle; six workstreams (A–F) mapped to ~12–18 work packages depending on tasks-phase decomposition.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Loaded via `spec-kitty charter context --action plan --json` (bootstrap mode; source `.kittify/charter/charter.md`).

| Charter dimension | Plan compliance |
|-------------------|------------------|
| **typer** as CLI framework | Compliant — new tooling under `scripts/docs/` uses argparse or a thin typer wrapper consistent with existing scripts; no replacement framework. |
| **rich** for console output | Compliant — freshness reports use rich tables when run in a TTY; plain text in CI. |
| **ruamel.yaml** for YAML parsing | Compliant — `docs/development/3-2-page-inventory.yaml` parsed with ruamel.yaml to preserve key ordering. |
| **pytest** for testing | Compliant — all new tests use pytest under `tests/docs/` and `tests/architectural/`. |
| **mypy --strict** | Compliant — new modules typed; `tests/architectural/test_pyproject_shape.py`-style checks unaffected. |
| **90%+ test coverage for new code** | Compliant — coverage target documented in `quickstart.md`; CI enforces with existing coverage plugin. |
| **Integration tests for CLI commands** | Compliant — integration tests cover the real Typer-tree walk and freshness check. |
| **DIRECTIVE_003: Decision Documentation Requirement** | Compliant — three deferred decisions tracked via `agent decision open`/`defer`; defaults explicitly recorded in this plan and in `research.md`; ADR drafts proposed for the CLI-generator decision and the version-tag mechanism. |
| **DIRECTIVE_010: Specification Fidelity Requirement** | Compliant — plan ties every workstream to FR/NFR/C IDs from `spec.md`; deviations require spec amendments. |
| **Project authority paths** | Compliant — `glossary/contexts/` consulted via `spec-kitty-glossary-context` skill at tasks time; `architecture/2.x/adr/` and `architecture/adrs/` consulted before any structural boundary change. |

**Result**: Plan passes Charter Check at this gate. No violations to justify in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```
kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/
├── spec.md                                # Mission specification (committed)
├── plan.md                                # This file
├── research.md                            # Phase 0 output
├── data-model.md                          # Phase 1 output
├── contracts/                             # Phase 1 output (per-script contracts)
│   ├── version_leakage_check.md
│   ├── build_cli_reference.md
│   ├── check_cli_reference_freshness.md
│   └── check_docs_freshness.md
├── quickstart.md                          # Phase 1 output
├── checklists/requirements.md             # Spec quality checklist (committed)
├── decisions/                             # Decision Moment artifacts
│   ├── DM-01KS4KTGTN4DBE60JFWKEA2FJB.md   # 3.1 classification
│   ├── DM-01KS4KTM69EG2KVX5MQ54FQ939.md   # CLI generator mode
│   ├── DM-01KS4KTS4V300M9MMTS1AJEGXY.md   # Harness support tiers
│   └── index.json
├── status.events.jsonl                    # Append-only WP lane state
└── tasks/                                 # /spec-kitty.tasks output (not in plan)
```

### Source Code (repository root)

```
scripts/docs/                              # New read-only docs tooling
├── __init__.py
├── version_leakage_check.py               # FR-005, NFR-002 — walks page inventory
├── build_cli_reference.py                 # FR-007, FR-008 — emits CLI reference
├── check_cli_reference_freshness.py       # FR-020, NFR-001 — reference drift gate
├── check_docs_freshness.py                # FR-020 — orchestrator
├── _typer_walker.py                       # Shared Typer-tree walker (reads only)
├── _inventory.py                          # Page-inventory loader (ruamel.yaml)
└── _render.py                             # Rich/plain output helpers

tests/docs/                                # New pytest suite
├── conftest.py
├── fixtures/
│   ├── clean_inventory.yaml
│   ├── dirty_inventory.yaml
│   ├── sample_cli_reference.md
│   └── sample_pages/                       # tiny docs tree
├── test_version_leakage_check.py
├── test_build_cli_reference.py
├── test_check_cli_reference_freshness.py
└── test_check_docs_freshness.py

tests/architectural/                       # Architectural parity tests
└── test_docs_cli_reference_parity.py      # asserts every non-hidden command path appears in docs/reference/cli-commands.md

docs/                                      # Existing site (READ-ONLY during planning)
├── reference/
│   ├── cli-commands.md                    # Rebuilt in tasks phase
│   ├── agent-subcommands.md               # Updated to 3.2 surface
│   ├── supported-harnesses.md             # NEW — harness support matrix
│   ├── init-lifecycle.md                  # NEW
│   └── upgrade-lifecycle.md               # NEW
├── how-to/
│   ├── install-macos.md                   # NEW
│   ├── install-linux.md                   # NEW
│   ├── install-windows.md                 # NEW
│   ├── upgrade-cli.md                     # NEW
│   ├── upgrade-project.md                 # NEW
│   ├── uninstall.md                       # NEW
│   ├── implement-work-package.md          # UPDATED (rename agent workflow → agent action)
│   └── harnesses/                          # NEW directory, one page per supported harness
│       ├── claude-code.md
│       ├── codex.md
│       ├── opencode.md
│       ├── cursor.md
│       ├── gemini.md
│       ├── qwen.md
│       ├── amazon-q.md
│       ├── copilot.md
│       ├── augment.md
│       ├── roo.md
│       ├── kilocode.md
│       ├── kiro.md
│       ├── windsurf.md
│       ├── pi-tui.md
│       └── (vibe.md, letta-code.md — conditional on classification)
├── tutorials/
│   ├── install-and-first-mission.md       # NEW
│   ├── first-charter-governed-workflow.md # NEW
│   ├── first-3-2-mission.md               # NEW
│   └── multi-harness-workflow.md          # NEW
├── explanation/
│   ├── what-is-spec-kitty-3-2.md          # NEW
│   ├── mission-model.md                   # NEW or REWRITE
│   ├── charter-and-doctrine.md            # NEW or REWRITE
│   ├── runtime-loop-and-next.md           # NEW
│   ├── harness-integration.md             # NEW
│   ├── version-compatibility.md           # NEW
│   ├── pip-vs-pipx-vs-uv.md               # NEW
│   └── workspace-git-and-branches.md      # NEW or REWRITE
├── migration/
│   ├── from-2x-to-3-2.md                  # NEW or REWRITE
│   └── from-3-1-to-3-2.md                 # NEW (gated on decision 01KS4KTGTN4DBE60JFWKEA2FJB)
└── development/
    ├── 3-2-version-taxonomy.md            # NEW
    ├── 3-2-page-inventory.yaml            # NEW
    ├── 3-2-navigation-plan.md             # NEW
    ├── 3-2-cli-reference-methodology.md   # NEW
    ├── 3-2-cli-reference-audit-meta-issues.md  # NEW
    ├── 3-2-information-architecture.md    # NEW
    ├── 3-2-archive-migration-plan.md      # NEW
    ├── 3-2-harness-research-method.md     # NEW
    └── 3-2-publication-checklist.md       # NEW

docs/1x/                                   # ARCHIVAL — relabeled, no edits beyond banner
docs/2x/                                   # ARCHIVAL — relabeled, no edits beyond banner
docs/3x/                                   # CURRENT — used for any 3.x-only landing surfaces
```

**Structure Decision**: Single-project Python repo with a thin new tooling layer under `scripts/docs/` and a pytest suite under `tests/docs/` plus one architectural test under `tests/architectural/`. Documentation content is reorganized in place under `docs/` with new pages added where the Divio architecture demands. No alternate option (web, mobile, monorepo) applies — the docs already live in this repo and the tooling is internal.

## Workstream-to-WP Mapping (Plan-Level)

Each workstream maps to a small cluster of WPs that the tasks phase will finalize. The plan only fixes the boundaries and dependencies; counts and lane assignments come from `/spec-kitty.tasks`.

| Workstream | Primary FRs | Suggested WP cluster | Dependencies |
|------------|-------------|----------------------|--------------|
| **A. Version taxonomy & filtering** | FR-001..FR-005, NFR-002 | A1 taxonomy doc · A2 page inventory · A3 navigation plan · A4 leakage-check tool + tests | Bulk-edit guardrail check (C-008); decision `01KS4KTGTN4DBE60JFWKEA2FJB` may reshape A3 |
| **B. CLI reference & audit** | FR-006..FR-010, NFR-001, NFR-005 | B1 methodology doc · B2 builder tool + tests · B3 freshness tool + tests · B4 meta-issue file scaffold · B5 rebuilt cli-commands.md · B6 architectural parity test | Decision `01KS4KTM69EG2KVX5MQ54FQ939` resolves hand-vs-generated-vs-hybrid; default is hybrid |
| **C. Divio IA & migration plan** | FR-011..FR-013 | C1 IA doc · C2 gap list · C3 archive/migration plan | Workstream A page inventory; resolves decision `01KS4KTGTN4DBE60JFWKEA2FJB` impact |
| **D. Harness research & matrix** | FR-014..FR-016, NFR-004, NFR-007 | D1 research method · D2 support matrix · D3 per-harness pages | Decision `01KS4KTS4V300M9MMTS1AJEGXY` resolves tiers and page promotion |
| **E. Install/upgrade/uninstall lifecycle** | FR-017..FR-019, NFR-003 | E1 install how-tos × 3 · E2 upgrade how-tos × 2 · E3 uninstall · E4 init/upgrade lifecycle reference · E5 pip-vs-pipx-vs-uv explanation | Workstream B (reference) |
| **F. Freshness, validation, publication** | FR-020..FR-021 | F1 orchestrator tool + tests · F2 publication checklist · F3 CI wiring | Workstreams A, B (depends on their tools landing) |

## Phase 0: Outline & Research

See [research.md](./research.md) for the consolidated research output.

Research tasks dispatched from this plan:

1. **CLI reference methodology recovery** — `git show a14769e7a 81b3d6c3e 514106af2 deee8d7f3 -- docs/reference docs/toc.yml docs/docfx.json` to identify whether the original reference was hand-authored, semi-generated, or test-validated, and to surface any extant freshness check.
2. **Doc-site generator confirmation** — inspect `docs/docfx.json` (or equivalent) and `docs/toc.yml` to confirm DocFX vs MkDocs vs other; identifies whether frontmatter-based version tagging is supported natively or requires generated index pages.
3. **Harness directory inventory** — enumerate the on-disk surfaces for each candidate harness (`.claude/`, `.codex/`, `.cursor/`, `.gemini/`, `.opencode/`, `.qwen/`, `.amazonq/`, `.augment/`, `.kiro/`, `.kilocode/`, `.roo/`, `.windsurf/`, `.agent/`, `.agents/`, `.vibe/` if present) and compare to the CLAUDE.md table.
4. **External harness doc accessibility** — confirm which harnesses have publicly accessible docs we can cite; flag any that require login or have inconsistent docs.
5. **Install-platform research** — verify current `pipx`, `uv`, and `pip` install/upgrade/uninstall command sets on macOS/Linux/Windows including PATH and PowerShell concerns and current PyPI publication name (`spec-kitty-cli` per `pyproject.toml`).
6. **Version-tag mechanism research** — determine whether frontmatter, generated index pages, or nav groups (or combinations) are the right primitive given the site generator from #2.
7. **Existing freshness/testing pattern survey** — enumerate `tests/architectural/test_safety_registry_completeness.py` patterns and any docs-related tests so the new architectural test mirrors the existing convention.
8. **Bulk-edit guardrail surface for FR-001/FR-002 rollout** — survey existing docs pages to estimate the bulk-edit blast radius if version-tag frontmatter is added across `docs/**`.

Each item resolves into a Decision/Rationale/Alternatives row in `research.md`. Where research has not yet executed (planning gate is read-only on the live docs tree), `research.md` records the planned method and the evidence the tasks phase will gather.

## Phase 1: Design & Contracts

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md).

Design outputs:

1. **Data model** — typed shapes for `PageInventoryEntry`, `VersionTag`, `CommandPathEntry`, `MetaIssueEntry`, `HarnessEntry`, `InstallTargetEntry`, `FreshnessReport`.
2. **Contracts** — one per new script. Each contract specifies:
   - input fixtures (paths, environment variables, optional flags)
   - exit codes (0 clean / 1 violations / 2 input errors / 3 environmental setup errors)
   - error taxonomy and exemplar messages
   - guarantees and non-guarantees (read-only on the Typer app; no mutation of docs at run time unless `--write` is passed; refuses to write if `git status` reports uncommitted changes in target files)
3. **Quickstart** — reviewer-reproducible flow that demonstrates the full freshness gate against a fresh clone.

Re-check Charter Check after Phase 1: no new violations introduced; all new tooling honours typer/rich/ruamel.yaml/pytest/mypy constraints.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| (none) | — | — |

## Deferred Decisions (resolved with plan defaults during implement-review)

The three deferred decisions tracked at planning time were resolved with
their documented plan defaults during the implement-review loop:

- `01KS4KTGTN4DBE60JFWKEA2FJB` → fold 3.1 into 3.2 as migration notes only
  (no separate 3.1 nav group). WP02/WP03/WP09 honour this default.
- `01KS4KTM69EG2KVX5MQ54FQ939` → hybrid generated body + hand-authored
  prose. WP06 implements; WP07 ran the inaugural hybrid rebuild.
- `01KS4KTS4V300M9MMTS1AJEGXY` → matrix-first promotion. WP10 produces the
  5-tier matrix; WP11 authors per-harness pages for tier ≥ partial (14 pages).

If the user later resolves any of these decisions to a different value,
the corresponding WP outputs must be re-run; the tools (build_cli_reference,
check_cli_reference_freshness, check_docs_freshness) are mode-aware so the
shift does not require code changes.

## Branch Strategy Confirmation (re-stated)

- Current branch at plan completion: `main`
- Planning/base branch for this mission: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target`: true (per `setup-plan --json` output)

When `/spec-kitty.tasks` runs, it materialises WP files and lanes; the actual coding worktrees are created at `implement` time per the 0.11.0+ execution-workspace strategy.

## Next Command

`/spec-kitty.tasks` (do not invoke from here; user runs explicitly).
