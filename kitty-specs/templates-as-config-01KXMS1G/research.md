# Phase 0 Research: Templates as Mission Configuration

## Decision 1 — Preserve the doctrine-to-charter-to-core authority chain

**Decision**: Read `template_set` from the activated doctrine `MissionType` artifact and expose the complete mapping from `ResolvedMissionType` using the context's existing lazy/cached projection pattern.

**Rationale**: The doctrine artifact already owns the data, charter activation already controls availability, and runtime readers already consume the resolved context. This closes the reserved slot without creating another source of truth and protects the 100 ms hot path.

**Alternatives rejected**:

- Use the profile-level `template_set` string: it is not the artifact mapping and would preserve the wrong authority.
- Scan mission-type files directly in each reader: filesystem presence is not activation and repeated I/O violates the architecture and performance posture.
- Add a new registry: duplicates authored doctrine configuration.

## Decision 2 — Use a two-stage template resolution contract

**Decision**: First map an artifact kind such as `spec` or `plan` to a filename through the resolved mission-type context. Then pass that filename and mission type to the existing five-tier file resolver.

**Rationale**: Mapping authority and file override precedence are different decisions. Keeping them separate preserves project/user/package overrides exactly while removing the `software-dev-default` magic selection.

**Alternatives rejected**:

- Store resolved paths in doctrine: paths are environment-specific and would collapse the override tiers into authored configuration.
- Replace the existing resolver: unnecessary scope and a compatibility risk.
- Continue passing hard-coded filenames from readers: bypasses the new authority chain.

## Decision 3 — Fail closed for known mission types without a mapping

**Decision**: For an activated known mission type, `template_set: null`, a missing artifact key, or an unresolvable mapped filename returns unavailability or raises an actionable domain/CLI error naming the mission type and artifact kind. It never borrows a software-development template.

**Rationale**: Null and missing entries are configuration facts, not permission to infer. Explicit diagnostics make authoring errors correctable and satisfy the activation boundary.

**Alternatives rejected**:

- Fall back to software-development: violates issue #2658 and makes unrelated mission types appear configured.
- Silently create an empty artifact: hides configuration failure and produces misleading workflow state.

## Decision 4 — Isolate the legacy typeless fallback

**Decision**: Do not remove or broaden the existing meta-less/typeless mission fallback in this slice. The new configured-template seam requires a non-neutral resolved mission type and raises `TemplateConfigurationError` when given a neutral/typeless context; production readers detect the existing typeless case and delegate to the unchanged legacy compatibility boundary outside the new seam. Known activated mission types always use the new contract. Issue #2660 later removes the legacy branch.

**Rationale**: Issue #2660 owns removal of that compatibility behavior. Pulling it forward would mix authority migration with runtime-discovery retirement and enlarge risk.

**Alternatives rejected**:

- Remove all software-development fallback now: exceeds issue #2658 and could break legacy missions before the owning migration lands.
- Treat typeless missions as activated software-development missions inside the new seam: creates a new implicit inference prohibited by the spec.

## Decision 5 — Prove parity transiently, verify behavior permanently

**Decision**: Add a temporary software-development before/after parity scaffold during the swap, use it to prove exact effective `spec` and `plan` outcomes, then delete it before merge. Keep doctrine-boundary and real reader-path behavior tests.

**Rationale**: The accepted ADR calls for transitional parity during authority swaps but rejects maintaining the old path as a permanent oracle. Existing architectural coverage already forbids surviving parity scaffold artifacts.

**Alternatives rejected**:

- Keep dual resolution permanently: retains duplicate authority and dead migration code.
- Test only mapping values: misses override precedence and reader wiring.
- Test only CLI snapshots: may not localize doctrine projection regressions.

## Decision 6 — Limit validation to affected surfaces

**Decision**: Use red-first tests for doctrine projection, missing configuration, mission creation, plan setup/pristine behavior, and software-development override parity; run targeted pytest, Ruff, mypy strict, the parity-scaffold architectural guard, and terminology checks.

**Rationale**: The charter requires acceptance-first and focused validation for scoped work. The full suite is reserved for post-merge or cross-cutting changes.

**Alternatives rejected**:

- Run the full ~17,000-test suite per work package: contrary to repository guidance and inefficient.
- Validate only unit helpers: insufficient for the required integration boundary.

## Reader Inventory and Scope Boundary

The production readers in scope are specification scaffolding in `src/specify_cli/core/mission_creation.py` and planning scaffold/pristine resolution in `src/specify_cli/cli/commands/agent/mission_setup_plan.py`. `src/specify_cli/runtime/resolver.py` retains file-tier precedence and is the likely shared selection seam. Activation enumeration, runtime mission discovery, meta-less fallback removal, copy-step removal, and derived mission-tree deletion remain outside this mission under issues #2659–#2661.
