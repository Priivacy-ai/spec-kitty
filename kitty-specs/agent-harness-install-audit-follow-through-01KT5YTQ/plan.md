# Implementation Plan: Agent Harness Install Audit Follow-Through

**Branch**: `kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/agent-harness-install-audit-follow-through-01KT5YTQ/spec.md`

## Summary

Four targeted cleanup tasks from the 2026-06-03 harness audit. Two are purely mechanical: remove stale `.codex/` install path guidance from 7 active doc files (bulk-edit, governed by `occurrence_map.yaml`) and fix pre-existing snapshot drift in `tests/specify_cli/skills/test_command_renderer.py` for `codex-implement` and `vibe-implement`. Two are research/documentation spikes: verify Antigravity CLI install surfaces and verify whether Kiro has a plugin/Powers bundle primitive, then record verified findings (or explicit "not verified" notes) in `docs/reference/supported-harnesses.md` and `docs/how-to/harnesses/`. No Python source changes; no plugin-install implementation. The bulk-edit classification workflow (DIRECTIVE_035) governs WP01.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest 9.x, pytest-snapshot (existing); pathlib stdlib; Markdown (docs only)
**Storage**: Filesystem — Markdown docs under `docs/`, pytest snapshot files under `tests/specify_cli/skills/snapshots/`
**Testing**: `uv run pytest tests/specify_cli/skills/test_command_renderer.py` — snapshot suite (102 tests); pass criterion: zero failures
**Target Platform**: Developer CLI tooling — macOS/Linux
**Project Type**: Single project (spec-kitty CLI monorepo)
**Performance Goals**: N/A
**Constraints**: No new Python dependencies; no changes to `src/specify_cli/core/config.py` or harness registry; `occurrence_map.yaml` must be valid before WP01 starts (bulk-edit gate); all changes must pass existing CI
**Scale/Scope**: 7 docs files with stale paths; 2 snapshot test failures; 2 external-research deliverables (Antigravity, Kiro)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Applicable charter directives (from `spec-kitty charter context --action plan`):

| Directive | Relevance | Status |
|-----------|-----------|--------|
| DIRECTIVE_001: Architectural Integrity | Bulk-edit changes stay within `docs/` and `tests/` — no architectural boundary crossed | Pass |
| DIRECTIVE_003: Decision Documentation | Research spike findings (Antigravity, Kiro) committed as docs artifacts with sourced evidence | Pass |
| DIRECTIVE_010: Specification Fidelity | Plan is faithful to spec: 4 work areas, no plugin-install implementation, deferred to #1635 | Pass |
| DIRECTIVE_024: Locality of Change | All changes co-located with the problem: docs update docs, test fix updates snapshots | Pass |
| DIRECTIVE_035: Bulk-Edit Gate | `occurrence_map.yaml` produced in this plan; required before WP01 can start | Pass |

No charter violations. Complexity tracking not required.

## Project Structure

### Planning artifacts (this mission)

```
kitty-specs/agent-harness-install-audit-follow-through-01KT5YTQ/
├── spec.md
├── plan.md                   # This file
├── research.md               # Phase 0: stale-path inventory, snapshot analysis, harness research
├── occurrence_map.yaml       # Bulk-edit classification (DIRECTIVE_035)
└── tasks.md                  # Phase 2 output (spec-kitty.tasks — not yet created)
```

### Files changed by this mission

```
docs/
├── explanation/
│   └── ai-agent-architecture.md          # FR-001: remove .codex/prompts/ table entry
├── development/
│   └── 3-2-information-architecture.md   # FR-001: planning doc — preserve as historical
├── how-to/
│   ├── setup-codex-spec-kitty-launcher.md # FR-001–005: major rework (entire file about old .codex/)
│   ├── upgrade-project.md                # FR-002: remove .codex/skills/ reference
│   └── harnesses/
│       ├── kiro.md                       # FR-012: update with Kiro classification finding
│       └── antigravity.md               # FR-010: create or update with verified Antigravity targets
├── reference/
│   ├── upgrade-lifecycle.md              # FR-002: remove .codex/skills/spec-kitty.*/ reference
│   ├── environment-variables.md          # FR-003: remove CODEX_HOME .codex guidance
│   ├── supported-agents.md              # FR-003–005: remove CODEX_HOME references
│   └── supported-harnesses.md           # FR-010, FR-012: Antigravity + Kiro classification

tests/specify_cli/skills/
├── test_command_renderer.py              # FR-007: snapshot test file (test logic may need small fix)
└── snapshots/
    ├── codex-implement.txt (or equiv)    # FR-008: refresh to canonical "approved or done" wording
    └── vibe-implement.txt  (or equiv)    # FR-008: refresh to canonical "approved or done" wording
```

**Structure Decision**: Single-project, docs-and-tests-only mission. No `src/` changes. No new files except possibly `docs/how-to/harnesses/antigravity.md` if the Antigravity spike confirms a dedicated harness page is needed.

## Complexity Tracking

No charter violations — this section left intentionally empty.
