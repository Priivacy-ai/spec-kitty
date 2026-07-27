# PR Summary: Changes, Intent, and Effect

> Git-tracked source for the reviewer-facing PR summary for this mission.
> Use this file as the canonical source when updating the PR body or posting a
> review-context comment on GitHub.

## Scope

This branch delivers two related changes under the umbrella of profile identity
reinforcement:

1. `Role` becomes a half-open value object and `AgentProfile.role` becomes
   `AgentProfile.roles: list[Role]`.
2. Shipped profiles move to character-name IDs and the doctrine/template layer
   is updated to make profile handoff explicit.

## What This PR Does

### 1. `Role` as a half-open value object

`AgentProfile.role: Role` is replaced by `AgentProfile.roles: list[Role]`,
where the first entry is the primary role and additional entries represent
secondary routing capabilities.

`Role` now subclasses `str` rather than `StrEnum`, so project-specific roles
such as `"retrospective-facilitator"` are valid first-class values without
forking the library.

Backward compatibility is preserved:

- scalar `role:` YAML is still accepted
- `_coerce_scalar_role` promotes it to `roles: [...]`
- the runtime emits a `DeprecationWarning`
- `AgentProfile.role` remains as a computed property returning `roles[0]`

Repository routing now checks the full role list:

- `_filter_candidates_by_role` matches any position in `roles`
- `_exact_id_signal` gives primary-role matches full weight and secondary-role
  matches reduced weight

### 2. Character-name renames and doctrine reinforcement

Shipped profiles now use character-name IDs, including:

- `architect-alphonso`
- `curator-carla`
- `designer-dagmar`
- `implementer-ivan`
- `planner-priti`
- `python-pedro`
- `researcher-robbie`
- `reviewer-renata`

This PR also adds `java-jenny` as a Java specialist profile with Maven review
guidance.

The doctrine and template layers are reinforced in parallel:

- shipped doctrine gains new tactics and styleguides for testing, architecture
  analysis, and disciplined decision-making
- `task-prompt-template.md` gains `agent_profile` and `role` frontmatter plus
  an explicit profile-load preamble
- migration `m_3_2_4_kittify_profile_handoff` backfills installed `.kittify`
  templates and `.agents/skills/` copies with the new handoff structure
- implement templates now include an explicit review handoff step

## Why Now

This work is a prerequisite for follow-on profile invocation and routing work:

- multi-role profiles are needed for profile invocation execution and audit
  trail surfaces
- stable `<role>-<character>` IDs support short-name and avatar-oriented
  profile flows
- explicit `agent_profile` / `role` fields make reviewer and implementer
  handoff machine-readable instead of implicit

Supporting detail and decisions are recorded in:

- [spec.md](./spec.md)
- [research.md](./research.md)

## Effect on Existing Projects

- **No runtime breakage for legacy scalar profiles.** Existing `role:` YAML
  continues to load via coercion, with a `DeprecationWarning`.
- **Profile IDs changed.** Callers that resolve shipped profiles by ID string
  must update to the character-name IDs.
- **Upgrade path is provided.** `spec-kitty upgrade` applies the template
  migration so installed project templates pick up the profile-load and
  review-handoff changes.

## Tickets This Touches

| Ticket | Relationship |
|--------|--------------|
| [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) | `roles: list[Role]` and explicit profile metadata are prerequisites for later profile invocation work |
| [#466](https://github.com/Priivacy-ai/spec-kitty/issues/466) | Aligns template field names around `agent_profile`, `agent`, and `model` |
| [#519](https://github.com/Priivacy-ai/spec-kitty/issues/519) | Updates routing to consider all declared roles while preserving primary-role priority |
| [#647](https://github.com/Priivacy-ai/spec-kitty/issues/647) | Supplies profile identity metadata needed by avatar-oriented work package surfaces |

## Validation and Review Context

For durable implementation and review evidence, see:

- [spec.md](./spec.md)
- [research.md](./research.md)
- [review-renata-post-implementation.md](./research/review-renata-post-implementation.md)

The GitHub PR checks should remain the source of truth for current CI state.
This file intentionally focuses on stable rationale, compatibility impact, and
review context.

## Follow-ups

Reviewer follow-up items are tracked in
[review-renata-post-implementation.md](./research/review-renata-post-implementation.md),
including:

- validator cleanup in `profile.py`
- deprecation warning stacklevel verification
- documenting list-replace vs list-union semantics in profile merge paths
