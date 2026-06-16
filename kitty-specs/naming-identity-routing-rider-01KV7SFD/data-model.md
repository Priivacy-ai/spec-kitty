# Data Model — Naming/Identity Routing Rider

This mission introduces **no new persisted data** and **no schema change**. The "model" here is the
identity value-object + seam-function surface the consumers must route through. Documented so the WPs
adopt the *same* entities rather than re-deriving.

## Identity value-objects (consume; do not re-derive)

### `mission_id` (str, ULID, 26 chars)
- Canonical immutable machine identity. The **only** legitimate source of `mid8`.

### `mid8` (str, 8 chars)
- `mission_id[:8]`. **Single derivation point:** `branch_naming.mid8()` /
  `mission_runtime.context.IdentityFragment.mid8` (guarded by `__post_init__` to equal `mission_id[:8]`).
- **Invariant:** no other module computes `mid8` inline after this mission (enforced by the IC-01 ratchet).

### `IdentityFragment` (on `ExecutionContext`)
- Carries the single-derived `mid8`. A site holding an `ExecutionContext` consumes `fragment.mid8`
  (fragment-adopt) rather than recomputing — verified to be the case already (0 violating sites found).

## Seam-function surface (the SSOT being adopted)

The **failover-aware `resolve_*` entrypoints are THE door** for correctness/read paths (FR-010); bare
`mid8()` is internal/seam use only (guaranteed-full id, no failover need).

| Function | Module | Signature (current) | Contract | Use when |
|----------|--------|---------------------|----------|----------|
| `resolve_mid8(mission_slug, *, mission_id)` | `branch_naming.py:169` | `(str, *, str\|None) -> str` | **declines → `""`** when id absent; declared identity governs (provable-match) | **correctness/read paths (the entrypoint)** |
| `resolve_transaction_mid8(...)` | `branch_naming.py:337` | resolver | failover-aware transaction/commit mid8 | commit/transaction routing |
| `resolve_mission_branch(...)` | `branch_naming.py:676` | branch resolver | **canonical-first + legacy-failover-with-one-shot-warning** | resolving a mission branch |
| `_mid8(mission_id)` *(renamed from `mid8`, IC-05/option-b)* | `branch_naming.py:122` | `(str) -> str` | **raises** on short/None | **internal/seam only** — no longer public; external callers use `resolve_mid8` |
| `mission_dir_name` / `worktree_dir_name` / `worktree_path` | `branch_naming.py:484/516…` | compose | the canonical name composes | #2000 compose-routing |
| `locate_project_root(start=None)` | `core/paths.py:48` (authority) | `(Path\|None) -> Path\|None` | already-consolidated chain | project-root resolution (verify #1971-tail) |

**Two contracts, byte-parity-critical (FR-008):** `mid8()` **raises**; `resolve_mid8()` **returns `""`**.
Sites returning `""`/`None` today (e.g. `status/aggregate.py`, `dashboard/scanner.py`) must route through
`resolve_mid8` (+ `or None`), never bare `mid8()`.

## Retired entity: `resolve_lanes_dir` (#1993) — NOT built

The scope review retired this: the lanes-file path is **already centralized** in `persistence.py`
(`read_lanes_json`/`require_lanes_json`/`write_lanes_json`); a new `resolve_lanes_dir` would be a **second
authority (C-001 violation)**. #1993's real coord-aware `_lanes_feature_dir` target is **deferred to
3.2.2**.

## Non-entities (explicitly NOT modeled / NOT changed)

- `ExecutionContext` builder internals (mutability, `branch_name`/`branch_ref` invariant) — **out of
  scope** (3.2.x builder-hardening track).
- `coordination/` compose/parse — **already routed** through the seam (FR-010 of the 3.2.0 mission).
- `invocation_id[:8]` — a *different* identity domain (Op invocation id); not modeled here.
