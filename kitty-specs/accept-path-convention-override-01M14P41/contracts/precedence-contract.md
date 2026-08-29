# Contract: path-convention precedence & blocking policy

## Precedence (per key) — remap-only
1. If `key` is declared in `mission.config.paths` AND `key` is not artifact-routed AND
   `project.path_conventions[key]` is set → use the override.
2. Else → use `mission.config.paths[key]` (doctrine default).
3. For research missions, `path_prefix` is then applied via `_prefix_required_path` as today (unchanged).

Override keys that the mission does not declare, or artifact-routed keys (`deliverables`), are
**warned/ignored** — never added, never routed (C-010, remap-only).

Merge point: the single helper `_remap_declared_paths`, applied to `declared` inside
`validate_mission_paths` **before** the `required_paths` comprehension and **before** the artifact-token
membership check (C-008). Inserting after the comprehension would leave overridden keys un-prefixed for
research missions. Value hardening (landing squad, #3790): the reader rejects empty/blank, absolute, and
`..`-traversing values; the merge site additionally re-excludes `ARTIFACT_ROUTED_KEYS` (defense-in-depth)
and drops an override whose *value* collides with a mission artifact token (`_drop_overrides_colliding_with_artifacts`).

## Blocking policy (UNCHANGED from #3783)
| Situation | strict (default) | `--lenient` |
|-----------|------------------|-------------|
| Resolved (overridden or default) directory exists | pass | pass |
| Resolved directory absent | **blocking `path_violations`** | advisory warning |

- The override changes *the resolved directory*, never the strict/lenient decision (C-001, I1).
- Remediation text still names the honest levers (`project.path_conventions` + `accept --lenient`) and
  never a bare `mkdir` — the #3783 contract, additive-only (C-009).

## Non-fakeable discriminator (SC-006)
`override.workspace = apps/` AND `apps/` absent ⇒ strict accept STILL blocks on `apps/`. An
implementation that silently demotes conventions to advisory fails this.

## Artifact-routing invariant (I3 / US1 scenario 4)
Routing (inside `validate_mission_paths`) is decided by `_normalize_path_token(declared[key]) in artifact_tokens`.
Because software-dev's `deliverables` value (`contracts/`) equals a mission artifact token, overriding it
would flip `feature_dir`→`project_root` and drop the mission-surface artifact check. Therefore
`deliverables` (and any artifact-routed key) is **excluded** from the override vocabulary (C-010).
The override thus never reaches an artifact-routed key, and the routing check is unaffected.
