# Decision Moment `01KWCAQMZMNZW3N8VZ7WQ23V2H`

- **Mission:** `sync-worktree-clean-invariant-01KWC9Y0`
- **Origin flow:** `plan`
- **Slot key:** `plan.identity.stability-approach`
- **Input key:** `identity_stability_approach`
- **Status:** `resolved`
- **Created:** `2026-06-30T13:15:41.940844+00:00`
- **Resolved:** `2026-06-30T13:56:20.184919+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should read/emit paths keep project identity stable (NFR-001) without writing config.yaml, given with_defaults mints random uuid4 for project_uuid and build_id?

## Options

- Hybrid deterministic build_id (C)
- Deterministic minting (A)
- Persist-at-write-boundary (B)
- Other

## Final answer

Option C — Deterministic build_id. Keep project_uuid generation unchanged; when build_id is the missing field, derive it deterministically as uuid5(namespace, project_uuid + ':' + node_id) so resolve_identity returns a stable identity with NO config.yaml write. Migrate the 8 read-path ensure_identity call sites to resolve_identity; keep ensure_identity only at init/write-authorized boundaries. SaaS research confirms server-safety: Project keyed on (team,project_uuid); Build keyed on (team,project,build_id) with no global uniqueness and idempotent race-guarded find-or-create; missions/WPs never join on Build, so deterministic build_id is constraint-safe and drift cannot strand work. Rejected A (changes project_uuid semantics — clones collapse into one project, a deliberate product decision not to bundle into a P1 bug) and B (does not guarantee NFR-001 without a user-run backfill).

## Rationale

`project_uuid` is the project identity anchor and must only be minted at a
write-authorized boundary. Persisting on read would dirty the worktree, while
deterministically minting `project_uuid` would change clone/project semantics. The
safe compromise is to require an existing `project_uuid` on read paths, derive only
the missing `build_id` from stable `(project_uuid, node_id)` inputs, and make
uninitialized reads no-op or ask the operator to run `init`.

## Change log

- `2026-06-30T13:15:41.940844+00:00` — opened
- `2026-06-30T13:56:20.184919+00:00` — resolved (final_answer="Option C — Deterministic build_id. Keep project_uuid generation unchanged; when build_id is the missing field, derive it deterministically as uuid5(namespace, project_uuid + ':' + node_id) so resolve_identity returns a stable identity with NO config.yaml write. Migrate the 8 read-path ensure_identity call sites to resolve_identity; keep ensure_identity only at init/write-authorized boundaries. SaaS research confirms server-safety: Project keyed on (team,project_uuid); Build keyed on (team,project,build_id) with no global uniqueness and idempotent race-guarded find-or-create; missions/WPs never join on Build, so deterministic build_id is constraint-safe and drift cannot strand work. Rejected A (changes project_uuid semantics — clones collapse into one project, a deliberate product decision not to bundle into a P1 bug) and B (does not guarantee NFR-001 without a user-run backfill).")
