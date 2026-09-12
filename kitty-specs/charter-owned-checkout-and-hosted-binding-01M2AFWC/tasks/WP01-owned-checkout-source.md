---
work_package_id: WP01
subtasks:
- T001
- T002
title: Owned checkout source propagation
task_type: implement
phase: Implementation
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctrine.py
- src/specify_cli/cli/commands/charter/context.py
- src/specify_cli/core/checkout_ownership.py
- src/charter/activation/context.py
- src/charter/activation/context_json.py
- src/charter/activation/sync.py
- tests/specify_cli/cli/commands/test_doctrine_new.py
- tests/specify_cli/cli/commands/test_charter_owned_checkout.py
- tests/charter/test_context_owned_checkout.py
- docs/how-to/charter-owned-checkout.md
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/cli/commands/test_charter_owned_checkout.py
- tests/charter/test_context_owned_checkout.py
- docs/how-to/charter-owned-checkout.md
agent_profile: implementer-ivan
role: implementer
agent: codex
requirement_refs:
- FR-001
- FR-002
- NFR-001
- C-001
- C-002
tracker_refs:
- spec-kitty/spec-kitty#4250
dependencies: []
---

# Work Package Prompt: WP01 – Owned checkout source propagation

## Load Agent Profile

Load `implementer-ivan` through canonical profile resolver before implementation; use curator-carla for doctrine curation as relevant. Read project charter and action context.

## Objectives & Success Criteria

Deliver FR-001, FR-002, NFR-001, C-001, C-002. Every acceptance claim uses the actual canonical entry point, with a deliberately failing mutation. No installed CLI change or production action.

## Context & Constraints

Read spec.md and plan.md. Parent issue SaaS #1713, child CLI #4250. Root owns WP01; governance curator owns WP02. Ownership-map leeway permits directly relevant local seams with communication; no overlap.

## Branch Strategy

Planning and merge target: `codex/issue-4250-charter-owned-checkout`; execute only in runtime-returned worktree. Runtime determines lane.

## Subtasks & Detailed Guidance

T001 Reproduce primary-checkout authoring/context leakage through real CLI linked-worktree tests.
T002 Propagate validated explicit ownership through command, bundle freshness, include and JSON seams; test isolation and document usage.

For WP01, include `ensure_charter_bundle_fresh` primary normalization and `context_json._bundle_root_for_json`; an outer flag alone is insufficient. Validate owned checkout through existing core checkout ownership, preserve default main-checkout behavior, and propagate explicit ownership through text/JSON/include. Do not change global `find_repo_root` contracts. Test real Git-linked checkouts with differing active doctrine and byte-stable unowned primary.

For WP02, preserve existing rich doctrine and add only project binding responsibility. Use canonical activation and resolver; scoped rules distinguish released client from deployed server and completed all-team repair. Activation/source removal must fail the actual witness. Integrated explicit lane context witness follows WP01; source activation does not claim installation.

## Test Strategy

Red-first actual CLI linked-worktree regression; positive and mutation activation witnesses. Run each new/changed test, owning relevant charter/CLI subsystem suites and `make test-fast` per AGENTS. No full repository suite owned by implementer. Root arranges independent review.

## Risks & Mitigations

Primary-root leakage may survive one wrapper; trace complete command pipeline. Preserve declared authority and avoid new fallback resolver. No secrets or provider calls in tests.

## Review Guidance

Reviewer must independently run target-only-write and differing-authority text/JSON/include checks. Verify inactive doctrine cannot satisfy completion, and installed protection remains explicitly pending.

## Activity Log

- 2026-09-12T09:45:00Z – codex – Authored canonical task prompt; implementation not started.
