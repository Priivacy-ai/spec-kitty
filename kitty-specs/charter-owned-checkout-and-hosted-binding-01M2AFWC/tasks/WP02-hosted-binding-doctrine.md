---
work_package_id: WP02
subtasks:
- T003
- T004
title: Hosted binding doctrine and activation
task_type: implement
phase: Implementation
execution_mode: code_change
owned_files:
- .kittify/config.yaml
- .kittify/charter/**
- .kittify/doctrine/directive/CLI_HOSTED_BINDING_COMPATIBILITY.directive.yaml
- .kittify/doctrine/procedure/cli-hosted-binding-verification.procedure.yaml
- .kittify/doctrine/graph.yaml
- tests/charter/test_hosted_binding_governance.py
authoritative_surface: .kittify/
create_intent:
- .kittify/doctrine/directive/CLI_HOSTED_BINDING_COMPATIBILITY.directive.yaml
- .kittify/doctrine/procedure/cli-hosted-binding-verification.procedure.yaml
- .kittify/doctrine/graph.yaml
- tests/charter/test_hosted_binding_governance.py
agent_profile: implementer-ivan
role: implementer
agent: codex
requirement_refs:
- FR-003
- FR-004
- NFR-002
- C-001
- C-002
tracker_refs:
- spec-kitty/spec-kitty#4250
dependencies: []
---

# Work Package Prompt: WP02 – Hosted binding doctrine and activation

## Load Agent Profile

Load `implementer-ivan` through canonical profile resolver before implementation; use curator-carla for doctrine curation as relevant. Read project charter and action context.

## Objectives & Success Criteria

Deliver FR-003, FR-004, NFR-002, C-001, C-002. Every acceptance claim uses the actual canonical entry point, with a deliberately failing mutation. No installed CLI change or production action.

## Context & Constraints

Read spec.md and plan.md. Parent issue SaaS #1713, child CLI #4250. Root owns WP01; governance curator owns WP02. Ownership-map leeway permits directly relevant local seams with communication; no overlap.

## Branch Strategy

Planning and merge target: `codex/issue-4250-charter-owned-checkout`; execute only in runtime-returned worktree. Runtime determines lane.

## Subtasks & Detailed Guidance

T003 Author and canonically activate native repository identity and truthful hosted completion directive/procedure preserving existing authority.
T004 Prove actual active consumer content, missing/inactive failure, and source-only versus installed protection evidence.

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
