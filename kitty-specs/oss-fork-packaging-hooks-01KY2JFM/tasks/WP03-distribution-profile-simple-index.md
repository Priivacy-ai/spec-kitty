---
work_package_id: WP03
title: DistributionProfile + SimpleIndexProvider
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: feat/oss-fork-packaging-hooks
merge_target_branch: feat/oss-fork-packaging-hooks
branch_strategy: Planning artifacts for this mission were generated on feat/oss-fork-packaging-hooks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/oss-fork-packaging-hooks unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: "cursor"
shell_pid: "84813"
history:
- at: '2026-07-21T15:03:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/distribution/
create_intent:
- src/specify_cli/distribution/profile.py
- src/specify_cli/distribution/simple_index.py
- tests/specify_cli/distribution/test_profile.py
- tests/specify_cli/distribution/test_simple_index.py
- tests/specify_cli/compat/test_provider_source_literal.py
execution_mode: code_change
owned_files:
- src/specify_cli/distribution/profile.py
- src/specify_cli/distribution/simple_index.py
- src/specify_cli/compat/provider.py
- tests/specify_cli/distribution/test_profile.py
- tests/specify_cli/distribution/test_simple_index.py
- tests/specify_cli/compat/test_provider_source_literal.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 – DistributionProfile + SimpleIndexProvider

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via `/ad-hoc-profile-load` before continuing.

## Objectives & Success Criteria

1. `DistributionProfile` dataclass + `resolve_distribution_profile()` per contracts.
2. Synthesize profile from Phase 1 entry points when no profile EP registered.
3. `SimpleIndexProvider` parses PEP 503 HTML fixtures; never raises; no fork URLs in defaults.
4. Extend `LatestVersionResult.source` with `"simple_index"` and update provider tests.

## Context

Read FR-009–010, FR-016–017, IC-03, `contracts/distribution-profile.md`, `contracts/simple-index-provider.md`. Mirror PyPIProvider security properties (TLS, size cap, no redirects, version sanitisation).

## Branch Strategy

Depends on WP01 only (parallel with WP02). `spec-kitty agent action implement WP03 --agent <name>`.

## Subtasks

- **T013**: Profile type + resolver + RED/GREEN tests (stock / EP / synthesized).
- **T014**: Extend `LatestVersionResult.source` Literal + tests.
- **T015**: Implement `SimpleIndexProvider` with HTML fixtures.
- **T016**: ruff/mypy/pytest on owned modules.

## Definition of Done

Contracts satisfied; re-export `SimpleIndexProvider` from a discoverable public path (`distribution` and/or `compat`); stock defaults contain no private hostnames.

## Reviewer Guidance

Reject any hardcoded fork index URL in upstream defaults. Ensure HTML parser is tolerant of typical simple-index markup.

## Activity Log

- 2026-07-21T15:43:51Z – cursor – shell_pid=80224 – Assigned agent via action command
- 2026-07-21T15:44:04Z – cursor – shell_pid=80405 – Assigned agent via action command
- 2026-07-21T15:49:47Z – cursor – shell_pid=80405 – Ready for review: profile + SimpleIndexProvider
- 2026-07-21T15:49:49Z – cursor – shell_pid=84813 – Started review via action command
- 2026-07-21T15:52:16Z – user – shell_pid=84813 – Review passed: profile + SimpleIndexProvider + extended tests.
- 2026-07-21T15:55:30Z – user – shell_pid=84813 – Ready for review
