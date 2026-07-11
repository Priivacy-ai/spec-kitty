# Contract: Trio seam-only consumption (FR-004 / SC-002 / #2465)

**Rule**: `workflow.py`, `implement.py`, `acceptance/__init__.py` (and their extracted cores/executors) resolve mission read paths ONLY through the `mission_runtime.resolution` seam wrappers — never by importing leaf resolver primitives.

**Allowed (seam wrappers)**: `placement_seam(...).read_dir(kind)` (a); `resolve_handle_to_read_path(..., require_exists=True)` (b); `primary_feature_dir_for_mission(...)` (c).

**Forbidden in the trio**: direct import/call of leaf primitives that bypass the kind-aware projection (the six-entry-point sprawl this consolidates).

**Enforcement**: extend `tests/architectural/test_single_mission_surface_resolver.py` with a trio-scoped assertion (AST import scan) that the three modules import only the allowed wrappers. Non-trio callers are OUT of scope (C-004) — the ratchet is trio-scoped.

**Preservation**: the three contracts (a/b/c) remain distinct; a refactor that routes a fail-closed (b) or topology-blind (c) site through the lenient (a) projection is a CONTRACT VIOLATION (data-loss / coord-follow regression), even if tests are green.
