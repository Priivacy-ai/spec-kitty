# Implementation Plan: Rename Ceremony Commit to Status Commit

**Branch**: `main` (planning), lane branch at implement time | **Date**: 2026-05-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/rename-ceremony-to-status-commit-01KSPN6C/spec.md`
**Mission ID**: `01KSPN6C5DWX7MRFMCD2BG1SBT` (mid8: `01KSPN6C`)
**Change mode**: `bulk_edit` (occurrence map required before first WP)
**Source**: [GitHub Issue #1325](https://github.com/Priivacy-ai/spec-kitty/issues/1325)

## Summary

Pure terminology rename. Replace every active-source occurrence of "ceremony" and the partially-landed alternative "status-writing" with the canonical term "status commit". The glossary anchors the canonical term and lists both old terms as deprecated synonyms. A new architectural test asserts the forbidden terms cannot reappear. No runtime behavior changes; no command surface, file-format, or commit-policy semantics change. The proposed config flag named in the F-09 findings doc was verified at spec time to be proposal-only (not in live code), so only the doc reference is rewritten.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: ruamel.yaml (glossary edits), pytest (architectural guard test), ripgrep/grep (occurrence discovery during plan + verification at acceptance)
**Storage**: Filesystem only (markdown/YAML/Python source files); no database, no schema migration
**Testing**: Existing pytest suite must pass unchanged (identifier renames included). One new architectural test added at `tests/architectural/test_no_legacy_terminology.py` runs `git grep`/ripgrep over `src/`, `tests/`, `docs/` for the forbidden terms and asserts zero hits, excluding `kitty-specs/`.
**Target Platform**: Repository source tree (developer-facing); no runtime deployment surface affected
**Project Type**: single (spec-kitty CLI codebase — same source layout as the existing project)
**Performance Goals**: Architectural grep guard must complete in <2 s on the existing test machine (single ripgrep pass over `src/ tests/ docs/`). Test suite wall-clock delta ≤5% versus pre-rename baseline per NFR-005.
**Constraints**: Behavioral fidelity — no semantic changes to commands, hooks, file formats, or commit policy. Pure string + identifier substitution. `kitty-specs/` historical mission artifacts are out of scope. Past commit messages and git history are not rewritten. The user's local checkout path (`spec-kitty-dev/ceremony/spec-kitty`) is irrelevant — local directory naming, not a repository artifact.
**Scale/Scope**: ~25–30 active-source occurrences across ~12 files (11 ceremony files surveyed at spec time + commit_helpers.py status-writing reconciliation). Single PR via mission lane workflow.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter context loaded for action `plan` (see `spec-kitty charter context --action plan`). Relevant project policy:

- **typer / rich / ruamel.yaml / pytest / mypy strict** — established stack; this mission introduces no new dependency.
- **90%+ test coverage for new code** — the only new code is the architectural grep guard test (which IS the test itself, so coverage is structurally satisfied) and the glossary YAML edit (a data file, not code).
- **mypy --strict must pass** — applies to any Python identifier renames in `commit_helpers.py` and renamed test fixtures.
- **Integration tests for CLI commands** — no CLI command behavior changes; existing integration tests must remain green w/ identifier renames propagated to callers.

**Glossary precedent**: `.kittify/glossaries/spec_kitty_core.yaml` already supports `status: deprecated` (5 prior entries) and `synonyms_to_avoid`. This mission follows the established schema; no new YAML conventions are introduced.

**Directives in scope (from charter context)**:
- DIRECTIVE_003 (Decision Documentation Requirement): two `decision_id`s minted and resolved at plan phase (`01KSPP3SSZ5GKHTTB1C9EJQ13V` rewording strategy, `01KSPP3W3VW8GB4WCXFF7J7X1Z` regression guard).
- DIRECTIVE_010 (Specification Fidelity Requirement): plan strictly tracks the 14 FRs in spec.md. Any deviation surfaces during implement review.

**Charter Check: PASS** (no violations; no Complexity Tracking entries needed).

## Project Structure

### Documentation (this feature)

```
kitty-specs/rename-ceremony-to-status-commit-01KSPN6C/
├── plan.md              # This file (/spec-kitty.plan command output)
├── spec.md              # Spec (already committed)
├── research.md          # Phase 0 output (rename research + occurrence discovery)
├── data-model.md        # Phase 1 output (terminology data: canonical + deprecations)
├── quickstart.md        # Phase 1 output (operator runbook for the rename)
├── contracts/           # Phase 1 output (term-rename contract listing replacements)
├── occurrence_map.yaml  # Phase 1 output (REQUIRED for bulk-edit missions)
├── decisions/           # Decision artifacts (auto-managed by `agent decision`)
│   ├── DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md  # Doctrine rewording strategy
│   └── DM-01KSPP3W3VW8GB4WCXFF7J7X1Z.md  # Regression guard strategy
├── checklists/
│   └── requirements.md  # Spec quality checklist (created at specify phase)
└── tasks/               # Populated by /spec-kitty.tasks
```

### Source Code (repository root) — files touched by this mission

```
src/
├── specify_cli/
│   └── git/
│       └── commit_helpers.py            # FR-002, FR-003, FR-004 — reconcile "status-writing" → "status commit"
└── doctrine/
    ├── procedures/
    │   └── README.md                    # FR-001, FR-008 — "Feature merge ceremony" → reworded
    ├── missions/software-dev/actions/tasks/
    │   └── guidelines.md                # FR-001, FR-008 — "inflating them with ceremony" → reworded
    └── skills/spec-kitty-program-orchestrate/
        └── SKILL.md                     # FR-001, FR-008 — 4 occurrences of "full ceremony" → semantic rewrite

tests/
├── architectural/
│   ├── _baselines.yaml                  # FR-011 — rewrite line 17 comment
│   └── test_no_legacy_terminology.py    # NEW — grep guard (FR-013, FR-014 + decision 01KSPP3W3VW8GB4WCXFF7J7X1Z)
├── doctrine/procedures/
│   ├── conftest.py                      # FR-005 — fixture ID `mission-merge-ceremony`
│   └── test_models.py                   # FR-005 — assertion on fixture ID
├── e2e/
│   └── conftest.py                      # FR-005 — `E2E_CEREMONY_BRANCH`, `_checkout_e2e_ceremony_branch` (6 occurrences)
└── git_ops/
    └── test_safe_commit_helper_integration.py  # FR-005 — function name + docstring (lines 105-106 per issue)

docs/
├── development/
│   ├── org-doctrine-layer-architecture-review.md   # FR-009 — "degrades to ceremony"
│   └── 3-2-publication-checklist.md                # FR-009 — "specify/plan/tasks ceremony"
└── engineering_notes/
    ├── reflections/README.md                       # FR-009 — "ceremony surfaces"
    └── finding/2026-05-24-mission-01KSAF14-orchestration-findings.md  # FR-009, FR-010 — 5 occurrences incl. proposed flag name

.kittify/glossaries/
└── spec_kitty_core.yaml                 # FR-006, FR-007 — add canonical + 2 deprecated entries
```

**Structure Decision**: Single-project structure. All edits land in the existing repository tree at the paths shown above. No new packages or directories created (one new test file under `tests/architectural/`).

## Phase 0: Research

Output: [research.md](research.md). Summary:

1. **Glossary schema research**: confirmed the existing `.kittify/glossaries/spec_kitty_core.yaml` schema supports `status: deprecated` and `synonyms_to_avoid`. Pattern established by 5 prior deprecated entries (`main repo`, `main repository`, `main repository root`, plus 2 others). No schema invention required.
2. **Config-flag live-state verification**: `grep -rn "allow_ceremony_commits_on_target_branch\|allow_status_commits_on_target_branch" src/` returns zero hits. Confirmed at spec time and re-confirmed at plan time. Only the F-09 findings doc references the proposed flag; no compat alias, no code-side rename needed.
3. **Active-source occurrence discovery**: `grep -rln 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` enumerated 11 files; `grep -rln 'status-writing' src/` enumerated 1 file (`commit_helpers.py`). Total = 12 files. Detailed occurrence list captured in `occurrence_map.yaml`.
4. **Doctrine rewording strategy**: Decision `01KSPP3SSZ5GKHTTB1C9EJQ13V` resolved — semantic rewrite per context. The `occurrence_map.yaml` classifies each occurrence as either `commit_class` (replace w/ "status commit") or `workflow_sense` (rewrite to convey the actual meaning, e.g., "full mission workflow", "all phases").
5. **Regression guard choice**: Decision `01KSPP3W3VW8GB4WCXFF7J7X1Z` resolved — pytest architectural test that runs ripgrep over `src/ tests/ docs/` for both forbidden terms. New file at `tests/architectural/test_no_legacy_terminology.py`. Excludes `kitty-specs/` historical artifacts.

## Phase 1: Design & Contracts

### Data Model

Output: [data-model.md](data-model.md). The only "entities" in a terminology mission are the terms themselves:

- **Canonical term**: `status commit` — auto-commit recording workflow state changes.
- **Deprecated term 1**: `ceremony commit` (and variants: "ceremony", "ceremony write", "ceremony command") → resolves to `status commit`.
- **Deprecated term 2**: `status-writing operation` (and "status-writing command") → resolves to `status commit`.

State transitions: none. Invariants: only the canonical term appears in active source.

### Contracts

Output: [contracts/term-rename-contract.md](contracts/term-rename-contract.md). The "contract" is the replacement mapping: per-pattern source → target text, plus the doctrine-prose semantic-rewrite categories.

No API endpoints, no payloads, no webhooks. The contract is purely lexical.

### Quickstart

Output: [quickstart.md](quickstart.md). Operator runbook covering:

1. Lane workspace creation: `spec-kitty implement WP01 --mission rename-ceremony-to-status-commit-01KSPN6C`
2. Verifying the occurrence map matches reality (re-run grep)
3. Acceptance grep at end: `grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` must return zero, and same for `status-writing`
4. Test suite, mypy, ruff invocations

### Occurrence Map (bulk-edit guardrail artifact)

Output: [occurrence_map.yaml](occurrence_map.yaml). Required for `change_mode: bulk_edit`. Enumerates every active-source occurrence of "ceremony" and "status-writing" with file, line number, surrounding context, replacement text, and category classification (one of: `code_symbols`, `import_paths`, `filesystem_paths`, `serialized_keys`, `cli_commands`, `user_facing_strings`, `tests_fixtures`, `logs_telemetry`). Categories absent in this rename are marked `category_not_applicable: true` w/ a one-line rationale.

## Complexity Tracking

*Charter Check passed; no violations to justify.*

No entries.
