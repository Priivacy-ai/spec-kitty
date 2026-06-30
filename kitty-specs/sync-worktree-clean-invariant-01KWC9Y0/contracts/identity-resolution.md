# Contract: Identity Resolution (read vs write boundary)

This mission has no HTTP API; its "contracts" are the behavioral guarantees of the identity-resolution functions and the call-site policy.

## C-IR-1 — `resolve_identity(repo_root)` is side-effect-free

- MUST return a `ProjectIdentity` with `is_complete == True` when an on-disk `project_uuid` exists.
- MUST return a not-initialized, side-effect-free identity when `project_uuid` is absent (see C-IR-4); read paths MUST NOT mint `project_uuid`.
- MUST NOT write `.kittify/config.yaml` (or any tracked file) under any input.
- For an already-complete on-disk identity: returns it unchanged.
- For an incomplete on-disk identity with `project_uuid`: fills missing fields in memory only, using the **deterministic** rules below.

## C-IR-2 — Deterministic completion (Decision C)

When a field is missing during read-path resolution:

| Field | Rule |
|-------|------|
| `project_slug` | `derive_project_slug(repo_root)` (already deterministic) |
| `node_id` | `sha256(hostname:username)[:12]` (already deterministic) |
| `build_id` | `uuid5(NAMESPACE, f"{project_uuid}:{node_id}")` — **changed from `uuid4()`** |
| `project_uuid` | NOT minted on read paths; must already be present (else → C-IR-4) |

Guarantee: for fixed `(project_uuid, node_id)`, `build_id` is identical across calls (NFR-001).

## C-IR-3 — `ensure_identity(repo_root)` remains the only persisting path

- MAY write `config.yaml` (completes + persists).
- MUST be called only at write-authorized boundaries: `init` (`init.py:99,863`) and explicit apply/bind commands.
- MUST NOT be called from read/emit/background paths after this mission.

## C-IR-4 — Uninitialized checkout on a read path

- If `project_uuid` is absent (truly uninitialized) and a read/emit path needs identity:
  - The path MUST NOT mint+persist a random `project_uuid` as a side effect.
  - Expected resolution: the checkout passes through `init` (write-authorized) first.
  - Acceptable interim behavior: the read command is side-effect-free and either no-ops sync or surfaces a clear "not initialized" signal. (Exact UX is an implementation choice; it MUST NOT write `config.yaml`.)

## Call-site policy (verifiable by grep)

- `ensure_identity(` is retained ONLY at write-authorized boundaries: `init.py` (×2) and `cli/commands/tracker.py` — the explicit `tracker bind` path (`_bind_saas`), which is a user-initiated write boundary per AS-5 / C-IR-3.
- Every read/emit/background former call site resolves via `resolve_identity(`: `emitter.py` (`_get_project_identity`, `_create_git_resolver`), `sync/routing.py`, `sync/events.py`, `sync/__init__.py`, `sync/dossier_pipeline.py`, `tracker/origin.py`.
