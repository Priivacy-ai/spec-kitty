# Data Model: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Purpose**: Conceptual entities, their fields, validation rules, and state transitions as they exist post-mission. Engineering implementation in `plan.md` §6 references these entities by name.

This is a **conceptual** data model. It is not an ORM schema, not a database design, and not a JSON schema spec. It exists to give reviewers a single place to see what the new fields/states look like and how they relate.

---

## Entities

### 1. Mission

A unit of planned work tracked under `kitty-specs/<mission_slug>/`.

**Fields** (after Track 3):

| Field | Type | Source | Mutability | Notes |
|-------|------|--------|------------|-------|
| `mission_id` | string (ULID) | `core.mission_creation` (NEW — Track 3) | immutable after creation | Canonical machine-facing identity. Format per ADR `architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md`. Generated via `python-ulid` (already in `pyproject.toml`). |
| `mission_number` | string (3-digit zero-padded, e.g. `"079"`) | `core.mission_creation` | display-only | Numeric prefix kept for human display. NOT used as machine-facing identity in any new flow. |
| `slug` | string | `core.mission_creation` | display-only | The unnumbered slug, e.g. `"post-555-release-hardening"`. |
| `mission_slug` | string | `core.mission_creation` | display-only | Numbered slug, e.g. `"079-post-555-release-hardening"`. Continues to be the directory name under `kitty-specs/`. |
| `friendly_name` | string | `core.mission_creation` | mutable (operator) | Human-readable mission title. |
| `mission_type` | string (`"software-dev"` \| `"research"` \| ...) | `core.mission_creation` | display-only | Mission template kind. |
| `target_branch` | string | `core.mission_creation` | display-only | Final merge target. |
| `created_at` | ISO 8601 string | `core.mission_creation` | immutable | UTC timestamp of mission creation. |
| `vcs` | string (`"git"`) | `core.mission_creation` | display-only | Version control system. |

**Persistence**: `kitty-specs/<mission_slug>/meta.json`

**Invariants**:
- `mission_id` MUST be present in `meta.json` for every mission created after Track 3 lands.
- `mission_id` MUST NOT change after creation.
- `mission_id` uniqueness is statistically guaranteed by ULID (128-bit, random tail). No explicit collision check is required.
- For historical missions (created before Track 3), `mission_id` MAY be absent. The `MissionIdentity` loader treats this as a legacy-tolerance display-only state.

**State transitions**: A mission has no internal lane state of its own. Lane state lives on its child Work Packages.

---

### 2. Work Package (WP)

A finalize-tasks-derived unit of work that belongs to a mission.

**Fields** (no schema change in this mission, but execution-mode handling unifies via lane):

| Field | Type | Source | Mutability | Notes |
|-------|------|--------|------------|-------|
| `wp_id` | string (e.g. `"WP01"`) | `tasks.md` author | immutable | Mission-scoped work package id. |
| `mission_slug` | string | `tasks.md` frontmatter | immutable | Backreference to parent mission. May also reference parent by `mission_id` post-Track 3 in machine-facing flows. |
| `dependencies` | list[string] | `tasks.md` frontmatter (explicit) | mutable until accepted | Explicit dependency declaration. NEVER overwritten by parser inference (Track 4). |
| `execution_mode` | enum (`code_change` \| `planning_artifact`) | ownership inference (`src/specify_cli/ownership/inference.py`) | derived | Determines which lane assignment path applies (Track 2). |
| `owned_files` | list[glob] | ownership inference | derived | The file globs this WP owns; aggregated into the lane's `write_scope`. |
| `lane_id` | string | `compute_lanes()` (Track 2 — now also for planning-artifact WPs) | derived | After Track 2, planning-artifact WPs receive `lane-planning`; code WPs receive `lane-a`/`lane-b`/etc. |

**Persistence**: `tasks.md` frontmatter + `kitty-specs/<mission_slug>/lanes.json` (lane assignment).

**Invariants**:
- Every WP MUST have a lane assignment after `compute_lanes()` (Track 2 closes the planning-artifact gap).
- Explicit `dependencies:` declarations in frontmatter MUST be preserved through finalize-tasks (Track 4).
- A WP whose `execution_mode == planning_artifact` MUST receive lane id `"lane-planning"` (Track 2).

---

### 3. Lane

The canonical grouping that maps WPs to a workspace.

**Fields** (`ExecutionLane` dataclass at `src/specify_cli/lanes/models.py:72-89`):

| Field | Type | Mutability | Notes |
|-------|------|------------|-------|
| `lane_id` | string | immutable | E.g. `"lane-a"`, `"lane-b"`, **`"lane-planning"`** (NEW canonical from Track 2) |
| `wp_ids` | tuple[string, ...] | immutable | Ordered WP execution sequence |
| `write_scope` | tuple[string, ...] | immutable | Union of WP `owned_files` globs |
| `predicted_surfaces` | tuple[string, ...] | immutable | Surface taxonomy tags |
| `depends_on_lanes` | tuple[string, ...] | immutable | Lane ids with blocking dependencies |
| `parallel_group` | int | immutable | Lanes with same group number run in parallel |

**Persistence**: `kitty-specs/<mission_slug>/lanes.json` (full `LanesManifest` serialization)

**State transitions**:

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
              compute_lanes()                                     ▼
            (in finalize-tasks)                       lane-planning
                    │                                  resolves to
                    │                                  main repo checkout
                    ▼                                  (no worktree)
            ┌──────────────┐
            │   Lane(s)    │ ── lane-a, lane-b, ... ─► .worktrees/<mission>-<lane>
            └──────────────┘
                    │
                    ▼
            write_lanes_json()
            (atomic temp-rename)
                    │
                    ▼
            kitty-specs/<mission_slug>/lanes.json
```

**Invariants** (post-Track 2):
- Lane id `"lane-planning"` MUST resolve to the main repo checkout via `paths.get_main_repo_root()`, NOT to a `.worktrees/...` directory.
- `lane_branch_name(mission_slug, "lane-planning")` MUST return the planning branch (the mission's `target_branch`), NOT a `kitty/mission-<slug>-lane-planning` namespace branch.
- Every WP returned by `compute_lanes()` MUST be assigned to exactly one lane. **No "filtered" lane-less WPs after Track 2.**

---

### 4. Mission Identity (`MissionIdentity` dataclass)

Resolver-facing identity object loaded from a mission's `meta.json`.

**Fields** (post-Track 3):

| Field | Type | Notes |
|-------|------|-------|
| `mission_id` | `str \| None` | NEW (Track 3). `None` only for legacy missions that predate the change. |
| `mission_slug` | `str` | Always present. |
| `mission_number` | `str` | Display-only. |
| `mission_type` | `str` | E.g. `"software-dev"`. |

**Persistence**: derived from `meta.json` via `mission_metadata.resolve_mission_identity(feature_dir)`.

**Invariants**:
- For missions created after Track 3 lands, `mission_id` MUST be a non-empty string and MUST parse as a valid ULID.
- `mission_id is None` is only acceptable for missions whose `meta.json` was written before Track 3. New machine-facing flows MUST treat `None` as a hard error (per FR-202).
- `mission_id` is the canonical identifier in any new event payload, status snapshot, lane manifest, or sync message added in `3.1.1`.

---

### 5. Credential

Authentication state stored on disk for the spec-kitty user.

**Fields** (no schema change in this mission):

| Field | Type | Notes |
|-------|------|-------|
| `tokens.access` | string | Bearer token. |
| `tokens.refresh` | string | Refresh token; rotated by the server on refresh. |
| `tokens.access_expires_at` | ISO 8601 | Access token expiry. |
| `tokens.refresh_expires_at` | ISO 8601 | Refresh token expiry. |
| `user.username` | string | Identity. |
| `user.team_slug` | string \| None | Optional team. |
| `server.url` | string | API base URL. |

**Persistence**: `~/.spec-kitty/credentials` (TOML format), with sibling lock file `~/.spec-kitty/credentials.lock`.

**State transitions** (post-Track 5):

```
                                     ┌──────────────────────────────┐
                                     │                              │
                              acquire FileLock                       ▼
                                     │                       hold lock for
                                     ▼                       FULL transaction
                            ┌────────────────┐
                            │ refresh_tokens │
                            │  (locked)      │
                            └────────────────┘
                                     │
                                     ▼
                              read on-disk creds
                                     │
                                     ▼
                              POST /token/refresh/
                                     │
                       ┌─────────────┴─────────────┐
                       ▼                           ▼
                  200 success                   401
                       │                           │
                       ▼                           ▼
                  parse new tokens         re-read on-disk creds
                       │                           │
                       ▼                           ▼
                  save (under lock)         creds changed since
                       │                    function entry?
                       ▼                           │
                  release lock           ┌─────────┴─────────┐
                                         ▼                   ▼
                                       YES                  NO
                                  (stale 401)           (real 401)
                                         │                   │
                                         ▼                   ▼
                                  exit cleanly       clear (under lock)
                                  (no clear)               │
                                         │                 ▼
                                         │           release lock
                                         ▼
                                   release lock
```

**Invariants** (post-Track 5):
- `refresh_tokens()` MUST acquire `FileLock` at function entry and release in `finally`.
- The HTTP POST to `/token/refresh/` MUST occur **inside** the held lock.
- On 401, the function MUST re-read on-disk credentials and compare to the entry-time refresh token before treating the failure as authoritative.
- `clear_credentials()` called from `refresh_tokens()` MUST occur under the same held lock; never outside.
- The standalone `CredentialStore.clear()` (used by direct logout) is unchanged — it still acquires its own per-I/O lock.

---

### 6. Init Model

The set of files, side-effects, and printed guidance produced by `spec-kitty init` under D-1.

**Conceptual fields** (post-Track 1):

| Element | Pre-Track-1 | Post-Track-1 |
|---------|-------------|--------------|
| `.git/` | created via `git init` | NOT created |
| Initial commit | created with literal message `"Initial commit from Specify template"` | NOT created |
| `.agents/skills/` shared root | seeded | NOT seeded |
| Per-agent skill directories (e.g. `.codex/prompts/`) | seeded | seeded (unchanged — this is the per-agent path that survives) |
| `.kittify/config.yaml` | created | created |
| `.kittify/metadata.yaml` | created | created |
| Slash-command files (per agent) | created | created |
| `README.md` (project's own) | created | created (unchanged content for the project README) |
| Next-steps text | lists `/spec-kitty.dashboard`, `/spec-kitty.charter`, ..., **`/spec-kitty.implement`**, ... — names top-level CLI as canonical | lists slash commands as canonical; clarifies that `/spec-kitty.implement` is a slash command driven by the agent runtime, not a top-level CLI users invoke directly |

**Invariants**:
- For an `init` invocation against a fresh empty directory, the post-init file set MUST be deterministic and enumerable from documentation.
- For an `init` invocation inside an existing git repository, the file set MUST be the same minus any files that already existed; **no git state is touched**.
- Re-running `init` in an already-initialized directory MUST be either idempotent or fail-fast with a clear message; it MUST NOT silently merge or overwrite state.

---

### 7. Release Cut

A constraint object describing the gates that must hold for a `3.1.1` release tag to be cut.

**Conceptual fields** (post-Track 7):

| Gate | Source of truth | Validator |
|------|-----------------|-----------|
| `pyproject.toml` version == target | `pyproject.toml:3` | `scripts/release/validate_release.py:load_pyproject_version()` |
| `.kittify/metadata.yaml` version == target | `.kittify/metadata.yaml:6` (`spec_kitty.version`) | NEW (Track 7) `validate_metadata_yaml_version_sync()` |
| `pyproject.toml` version == `.kittify/metadata.yaml` version | both files | NEW (Track 7) — same function |
| `CHANGELOG.md` has an entry for the target version | `CHANGELOG.md` | `scripts/release/validate_release.py:changelog_has_entry()` (existing; ensure called in branch mode for FR-606) |
| Version progression is monotonic | git tag history | `validate_version_progression()` (existing) |
| Tag matches version (tag mode only) | git tag at HEAD | `ensure_tag_matches_version()` (existing) |
| Dogfood command set runs cleanly against the working repo | `/private/tmp/311/spec-kitty` at the release commit | NEW (Track 7) `tests/release/test_dogfood_command_set.py` |
| Structured release-prep draft artifact is producible | `src/specify_cli/release/payload.py:build_release_prep_payload()` | NEW (Track 7) `tests/release/test_release_payload_draft.py` |

**Invariants** (post-Track 7):
- All gates above MUST pass in branch mode for `validate_release.py` to exit 0.
- The `git tag v3.1.1` step is a **human action** (per CLAUDE.md). Track 7 does NOT automate it.

---

## Cross-entity references

```
Mission ──── (1:N) ──── Work Package ──── (N:1) ──── Lane
   │                         │
   │                         │
   ▼                         ▼
mission_id              execution_mode
(Track 3)               (Track 2 unifies via lane)
   │
   ▼
emitted in
sync events
(Track 3)

Credential ──── (N/A — orthogonal) ──── Mission
   │
   ▼
locked by
FileLock
across full
refresh transaction
(Track 5)

Init Model ──── creates (one-shot) ──── new project directory
                                              │
                                              ▼
                                        kitty-specs/
                                        .kittify/
                                        per-agent dirs

Release Cut ──── validates ──── working repo at release commit
                  │
                  ▼
            pyproject.toml + .kittify/metadata.yaml + CHANGELOG.md
            (all gates must pass — Track 7)
```

---

## Validation rules summary

| Rule | Track | Enforced where |
|------|-------|----------------|
| `mission_id` present and ULID-shaped at creation | 3 | `tests/core/test_mission_creation_identity.py` |
| `mission_id` immutable after creation | 3 | invariant, asserted in tests |
| Concurrent mission creation does not collide on `mission_id` | 3 | `tests/core/test_mission_creation_concurrent.py` |
| Every WP receives a lane assignment | 2 | `tests/lanes/test_compute_planning_artifact.py` |
| `lane-planning` resolves to main repo checkout | 2 | `tests/lanes/test_branch_naming_planning.py` |
| Resolver returns coherent ref for planning-artifact WP | 2 | `tests/context/test_resolver_planning_artifact.py` |
| Explicit `dependencies:` not overwritten by parser | 4 | `tests/core/test_dependency_parser.py` (extension) |
| Final WP section bounds at top-level non-WP heading | 4 | `tests/core/test_dependency_parser.py` (extension) |
| `refresh_tokens()` holds lock for full transaction | 5 | `tests/sync/test_auth_concurrent_refresh.py` |
| Concurrent refresh + rotation does not log out | 5 | `tests/sync/test_auth_concurrent_refresh.py` |
| `init` does not create `.git/` or commit | 1 | `tests/init/test_init_minimal_integration.py` (extension) |
| `init` does not seed `.agents/skills/` | 1 | `tests/init/test_init_minimal_integration.py` (extension) |
| `init` next-steps does not name top-level `spec-kitty implement` | 1 + 6 | `tests/init/test_init_next_steps.py` |
| `init` is idempotent or fail-fast on re-run | 1 | `tests/init/test_init_idempotent.py` |
| `init` does not touch existing git repo state | 1 | `tests/init/test_init_in_existing_repo.py` |
| `spec-kitty implement --help` marks command as internal infrastructure (implementation detail of `spec-kitty agent action implement`) and names `spec-kitty next` and `spec-kitty agent action implement/review` as the canonical user-facing commands | 6 | `tests/agent/cli/commands/test_implement_help.py` |
| `spec-kitty implement` still runs (compatibility) | 6 | `tests/agent/cli/commands/test_implement_runs.py` (extension) |
| `pyproject.toml` ↔ `.kittify/metadata.yaml` version sync | 7 | `tests/release/test_validate_metadata_yaml_sync.py` |
| `CHANGELOG.md` entry for target version exists | 7 | `tests/release/test_validate_changelog_entry.py` |
| `build_release_prep_payload` produces valid draft | 7 | `tests/release/test_release_payload_draft.py` |
| Dogfood command set runs cleanly | 7 | `tests/release/test_dogfood_command_set.py` |
