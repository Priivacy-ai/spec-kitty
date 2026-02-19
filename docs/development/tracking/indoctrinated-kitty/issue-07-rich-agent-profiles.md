# Tracking Issue 07: Rich Agent Profiles

Status: OPEN
Owner: constitution + doctrine maintainers
Created: 2026-02-18

## Problem

Doctrine stack behavior is difficult to activate consistently per project and per role when profile definitions are shallow or fragmented across multiple config surfaces.

## Desired Behavior

Rich Agent Profiles become a first-class activation mechanism for Doctrine Stack behavior in each project, with role-focused defaults that can be selected via constitution and used directly by task workflows.
Profiles should support lazy doctrine evaluation: agents resolve only the profile slices required for the current task type, role, and compliance checks.

Each rich profile should be able to preconfigure:

- paradigms
- tactics
- templates/template sets
- behavioral directives

This should support dedicated role tracks such as `designer`, `implementer`, `reviewer`, and include concrete role variants (for example a Python-focused implementer profile).
Example: full TDD/ATDD procedural detail is not required when an implementation agent is executing documentation-only or summary-only tasks.

## Acceptance Criteria

1. Constitution selections can activate specific rich profiles for a project without duplicating profile semantics in mission templates.
2. Profile shape is explicit enough to encode paradigms, directives, tactics, and template defaults as a coherent bundle.
3. Runtime resolution fails clearly when selected profiles are missing or invalid.
4. Task-level behavioral guidance can be derived from the active profile with minimal additional prompting glue.
5. At least one concrete profile implementation path is documented for a Python-focused implementer.
6. Role/task execution paths demonstrate lean loading behavior (only required doctrine slices are fetched for the active task context).
7. Profile-driven doctrine guidance retrieval is executed through the same command-wrapper entry point used by constitution slug deployment, and emits read/selection events to `EventStore` for tracing and future optimization.

## Notes

- Work has started in `src/specify_cli/constitution/` (schemas, extraction, resolver, sync).
- Related doctrine model context: `references/2026-02-17-doctrine-v2-final-proposal.md`.
- Terminology alignment dependency: `issue-06-stable-terminology-and-role-lookup.md`.
- Observability dependency: `src/specify_cli/events/store.py` (EventStore-backed read tracing).
