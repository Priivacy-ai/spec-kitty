---
title: 'ADR 2026-06-07-1: Execution-State Canonical Surface (`mission_runtime`)'
status: Accepted
date: '2026-06-07'
---

## Context

ADR [`2026-06-03-1-execution-state-domain-model.md`](2026-06-03-1-execution-state-domain-model.md)
ratified the bounded-module decomposition and named **Execution / Runtime** as
the owner of workspace resolution, branch state, and CWD-invariant context. It
also recorded that the residue surfaces (~40 command surfaces re-deriving
execution context) must route through `resolve_action_context`
(`core/execution_context.py`).

What that ADR did *not* lock in was the **physical home** of the execution-state
domain. Today `resolve_action_context` and its `ActionContext` value object live
in `src/specify_cli/core/execution_context.py`, buried inside the CLI package.
That placement makes the domain invisible at the package level: there is no
top-level module name that *screams* "this is where execution state lives", and
nothing prevents new surfaces from re-deriving their own context rather than
importing the canonical one.

The design analysis in
[`docs/plans/engineering-notes/runtime_and_state_overhaul/06-proposed-domains-and-splits.md`](../../../docs/plans/engineering-notes/runtime_and_state_overhaul/06-proposed-domains-and-splits.md)
§4/§5 resolves this. §4 records the operator decision (Stijn, 2026-06-03) to
create a net-new top-level `mission_runtime/` umbrella package, and §5 fixes the
owner shape (Strangler façade → operation service; value-object resolver as
fallback).

Per C-006, this ADR is written **before** any mass code lands. The umbrella is
stood up empty-but-registered in this work package (WP02); the relocation of the
hardened `ExecutionContext` logic into it is WP03.

## Decision

### 1. Module name: top-level `mission_runtime/`

The canonical execution-state surface is a **net-new top-level package**
`src/mission_runtime/`. Rationale (doc 06 §4):

- **Screaming Architecture** — the package structure should name the domain. A
  top-level `mission_runtime/` makes the execution-state domain discoverable at
  the highest level of the source tree, rather than hiding it under
  `specify_cli/core/`.
- **Strangler Fig** — the new home grows alongside the old. The umbrella is the
  new canonical surface; existing call-sites are strangled onto it
  incrementally, and the old `core/execution_context.py` becomes a thin
  re-export shim removed once unreferenced (FR-003).

`mission_runtime` is preferred over harden-in-place (keeping the logic in
`core/`) for domain clarity. The trade-off — a new top-level package must be
registered in the layer meta-guard — is accepted and discharged below.

### 2. Layer placement: charter-level sibling of `runtime`

`mission_runtime` is registered in `_DEFINED_LAYERS` in **both**
`tests/architectural/test_layer_rules.py` and the `landscape` fixture in
`tests/architectural/conftest.py`. Omitting either causes
`test_no_unregistered_src_packages` to fail (doc 06 §4).

It sits at the **charter level**, consistent with `runtime` and `glossary`. The
spine remains `kernel ← doctrine ← charter ← specify_cli`; `runtime`,
`glossary`, and now `mission_runtime` are siblings above `charter`.
`mission_runtime` may import `specify_cli.*` (it delegates to today's resolver
during migration) but must not import CLI presentation layers
(`specify_cli.cli` / `specify_cli.next`), mirroring the `runtime` boundary.

### 3. Lean public API expressed over context objects

The package root exposes a minimal `__all__` (the `__all__` Declaration
Convention, C-007):

```python
__all__ = ["ExecutionContext", "ExecutionMode", "resolve_action_context", "ActionContextError"]
```

- `ExecutionContext` — the immutable, complete resolved context (read/write/dest
  dirs, branch, WP identity, prompt). The API is expressed over **this context
  object**, never over path fragments. Consumers receive a resolved context;
  they do not reconstruct `main_repo_root / "kitty-specs" / mission_slug`
  themselves (FR-009).
- `ExecutionMode` — the resolution mode (e.g. worktree vs. code-change),
  inferred when the caller does not specify it.
- `resolve_action_context(repo_root, mission, wp_id=None, *, mode=None) -> ExecutionContext`
  — the single resolution entry point. CWD-invariant, topology-aware,
  mode-correct `target_branch`, and raises `ActionContextError` on unresolvable
  context with **no silent fallback**.
- `ActionContextError` — the only error type consumers catch.

Everything else is internal. The implementation lives in submodules
(`mission_runtime/context.py`, `mission_runtime/resolution.py`) that consumers
**must not import directly** — enforced by
`tests/architectural/test_mission_runtime_surface.py` (FR-005). This keeps the
surface lean and prevents the internal-leakage that let the old `core/` resolver
sprawl.

### 4. Stage-C shape only

This umbrella adopts the **Stage-C** shape from doc 06 §5: a Strangler façade
(`resolve_action_context`) returning an immutable `ExecutionContext` value
object, delegating to today's resolver during migration (option C → A). The
Stage-B operation service / `CommitTarget` (commit-seam atomicity) is **out of
scope** (C-008) — doc 06 §6 step 7 confirms `safe_commit` already enforces the
commit invariant, so `CommitTarget` is an ergonomic improvement deferred to
later work, not a safety gate this surface must provide.

### 5. Strangler migration order

1. **WP02 (this WP)** — stand up `mission_runtime/` empty-but-registered:
   package skeleton + lean `__all__` (stub symbols), layer-guard registration in
   both files, sole-resolver surface test, and this ADR.
2. **WP03** — relocate the hardened `ExecutionContext` / `resolve_action_context`
   logic from `core/execution_context.py` into the umbrella; wire the `__all__`
   symbols; leave `core/execution_context.py` as a thin re-export shim
   (NFR-001: behaviour preserved).
3. **Downstream WPs** — strangle the residue surfaces onto
   `mission_runtime.resolve_action_context`; delete duplicated path-builders;
   remove the `core/execution_context.py` shim once unreferenced (FR-003).

## Consequences

### What changes

- A new top-level package `src/mission_runtime/` exists and is enforced by the
  layer meta-guard. Future code that adds execution-state logic has a named home.
- The lean `__all__` becomes the contract; the surface test makes internal
  imports a build failure, so the leakage that bloated the old resolver cannot
  recur.

### What stays the same

- Nothing relocates in this WP. `core/execution_context.py` and all current
  call-sites are untouched (relocation is WP03). The umbrella symbols are stubs
  until WP03 wires them.
- Legacy missions continue to resolve through the existing resolver until they
  are strangled (NFR-001).

### What is now explicit

- The execution-state domain has a screaming, top-level home: `mission_runtime`.
- The public surface is fixed to four symbols, all expressed over context
  objects, and internal submodules are import-forbidden from outside the package.
- The migration is Strangler-ordered: umbrella first (WP02), relocation second
  (WP03), call-site cutover and shim removal after.

## References

- Mission spec: `kitty-specs/execution-state-canonical-surface-01KTG6P9/spec.md`
- Contract: `kitty-specs/execution-state-canonical-surface-01KTG6P9/contracts/mission_runtime_api.md`
- Design basis: [`docs/plans/engineering-notes/runtime_and_state_overhaul/06-proposed-domains-and-splits.md`](../../../docs/plans/engineering-notes/runtime_and_state_overhaul/06-proposed-domains-and-splits.md) §4/§5 (and §6 sequencing); doc 17 (consolidated domain model)
- Prior ADR: [`2026-06-03-1-execution-state-domain-model.md`](2026-06-03-1-execution-state-domain-model.md) — bounded-module decomposition
- Prior ADR: [`2026-06-03-2-executioncontext-owner-and-committarget.md`](2026-06-03-2-executioncontext-owner-and-committarget.md) — ExecutionContext owner / CommitTarget rationale
- Tactic: `src/doctrine/tactics/built-in/refactoring/refactoring-strangler-fig.tactic.yaml`
- Issue #1619: root-cause analysis and Strangler Fig sequence
