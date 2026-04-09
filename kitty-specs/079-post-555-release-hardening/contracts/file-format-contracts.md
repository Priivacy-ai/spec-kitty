# File Format Contracts: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Purpose**: Persistent file format expectations the mission must satisfy. Each contract names the file, its current shape, the post-mission shape, and the migration story (if any).

The mission edits a small number of file formats. Most are additive (new fields, no removed fields) so they remain backward-compatible.

---

## F1. `meta.json` (per-mission identity)

**Path**: `kitty-specs/<mission_slug>/meta.json`

**Owner**: `core.mission_creation` (write), `mission_metadata.resolve_mission_identity` (read)

### Pre-mission shape (Track 3 baseline)

```json
{
  "mission_number": "079",
  "slug": "079-post-555-release-hardening",
  "mission_slug": "079-post-555-release-hardening",
  "friendly_name": "post 555 release hardening",
  "mission_type": "software-dev",
  "target_branch": "main",
  "created_at": "2026-04-09T06:12:24.358591+00:00"
}
```

### Post-mission shape (Track 3 lands)

```json
{
  "mission_id": "01HXYZ0123456789ABCDEFGHJK",
  "mission_number": "079",
  "slug": "079-post-555-release-hardening",
  "mission_slug": "079-post-555-release-hardening",
  "friendly_name": "post 555 release hardening",
  "mission_type": "software-dev",
  "target_branch": "main",
  "created_at": "2026-04-09T06:12:24.358591+00:00",
  "vcs": "git"
}
```

**Changes**:
- **NEW required field for new missions**: `mission_id` — string, ULID format (26-character Crockford base32, lexicographically sortable).
- **NEW recommended field**: `vcs` — string, default `"git"`.
- All existing fields are preserved.

**Validation rules**:
- For missions created after Track 3 lands: `mission_id` MUST be present, MUST be a non-empty string, and MUST parse as a valid ULID.
- `mission_id` MUST be immutable. Any code that overwrites it is a contract violation.
- For historical missions (created before Track 3 lands): `mission_id` MAY be absent. Loaders MUST tolerate the absence (per NG-1 / NG-2). New machine-facing flows MUST treat absence as an error.

**Migration**:
- Mission 079 itself currently has no `mission_id`. Track 3's first WP MUST add it to mission 079's own `meta.json` so the mission dogfoods the new identity model.
- No bulk migration of historical missions is performed (NG-2).

---

## F2. `lanes.json` (per-mission lane manifest)

**Path**: `kitty-specs/<mission_slug>/lanes.json`

**Owner**: `lanes.persistence.write_lanes_json` (write), `lanes.persistence.require_lanes_json` (read)

### Pre-mission shape (Track 2 baseline)

```json
{
  "feature_slug": "<mission_slug>",
  "mission_id": "<may or may not be present>",
  "target_branch": "main",
  "lanes": [
    {
      "lane_id": "lane-a",
      "wp_ids": ["WP01", "WP02"],
      "write_scope": ["src/foo/**", "tests/foo/**"],
      "predicted_surfaces": ["surface-a"],
      "depends_on_lanes": [],
      "parallel_group": 1
    }
  ],
  "planning_artifact_wps": ["WP03"],
  "collapse_report": null,
  "computed_at": "<timestamp>",
  "computed_from": "finalize-tasks"
}
```

### Post-mission shape (Track 2 lands)

```json
{
  "feature_slug": "<mission_slug>",
  "mission_id": "<from meta.json — Track 3>",
  "target_branch": "main",
  "lanes": [
    {
      "lane_id": "lane-a",
      "wp_ids": ["WP01", "WP02"],
      "write_scope": ["src/foo/**", "tests/foo/**"],
      "predicted_surfaces": ["surface-a"],
      "depends_on_lanes": [],
      "parallel_group": 1
    },
    {
      "lane_id": "lane-planning",
      "wp_ids": ["WP03"],
      "write_scope": ["kitty-specs/<mission_slug>/**"],
      "predicted_surfaces": ["planning"],
      "depends_on_lanes": [],
      "parallel_group": 0
    }
  ],
  "planning_artifact_wps": ["WP03"],
  "collapse_report": null,
  "computed_at": "<timestamp>",
  "computed_from": "finalize-tasks"
}
```

**Changes**:
- **NEW canonical lane**: `lane-planning` is added to the `lanes` list when the mission has at least one planning-artifact WP.
- `planning_artifact_wps` is preserved as a **derived view** (for backward compatibility with historical `lanes.json` consumers). Producers SHOULD treat it as derivable from the lane assignments; consumers SHOULD prefer reading from `lanes` directly.
- Existing `lane-a`/`lane-b` entries are unchanged.

**Validation rules**:
- For any mission whose `tasks.md` declares at least one planning-artifact WP, `lanes.json` MUST contain a lane with `lane_id == "lane-planning"` containing all planning-artifact WP ids.
- For any mission with no planning-artifact WPs, `lanes-planning` MUST NOT appear (it is conditional on actual planning-artifact WP presence).
- Every WP id appearing in any WP frontmatter MUST appear in exactly one lane's `wp_ids` list (no orphan WPs after Track 2).

**Migration**:
- Historical `lanes.json` files written before Track 2 lands continue to be readable. The reader treats absence of `lane-planning` as "this manifest predates Track 2; the planning-artifact WPs are listed in `planning_artifact_wps` field instead". This is the only legacy-tolerance hook for `lanes.json`, and it exists per NG-1.
- Re-running `finalize-tasks` on a historical mission rewrites the manifest with the new shape.

---

## F3. `.kittify/metadata.yaml` (project metadata)

**Path**: `.kittify/metadata.yaml`

**Owner**: `core.project_metadata` (write), various readers

### Pre-mission shape (Track 7 baseline)

```yaml
spec_kitty:
  version: 3.1.1a2          # ⚠ STALE
  initialized_at: <iso8601>
  last_upgraded_at: <iso8601>
environment:
  python_version: <string>
  platform: <string>
  platform_version: <string>
migrations:
  applied:
    - <migration_id>
    - ...
```

### Post-mission shape (Track 7 lands)

```yaml
spec_kitty:
  version: 3.1.1            # synced to pyproject.toml at the release cut
  initialized_at: <iso8601>
  last_upgraded_at: <iso8601>
environment:
  python_version: <string>
  platform: <string>
  platform_version: <string>
migrations:
  applied:
    - <migration_id>
    - ...
```

**Changes**:
- `spec_kitty.version` is bumped to match `pyproject.toml`. No schema change.

**Validation rules**:
- At the release commit, `.kittify/metadata.yaml:spec_kitty.version` MUST equal `pyproject.toml:[project].version`.
- The pre-release validation step MUST fail the cut if the two values disagree.

**Migration**:
- Track 7's first WP performs the explicit bump. No automation; this is an intentional human/agent commit.

---

## F4. `pyproject.toml` (Python package version)

**Path**: `pyproject.toml`

**Owner**: human release engineer (with mission 079 facilitating the release-cut WP)

### Field of interest

```toml
[project]
name = "spec-kitty-cli"
version = "3.1.1"   # at the release commit; pre-release alphas use 3.1.1a3, 3.1.1a4, ...
```

**Changes**:
- The version field is bumped to `3.1.1` (stripping the alpha suffix) at the release cut WP.

**Validation rules**:
- The pre-release validation step (extended `scripts/release/validate_release.py`) MUST assert this field equals `.kittify/metadata.yaml:spec_kitty.version`.
- The validation step MUST also assert that `CHANGELOG.md` contains an entry whose header matches `## [<version>]` (FR-606).

---

## F5. `CHANGELOG.md` (release narrative)

**Path**: `CHANGELOG.md`

**Owner**: human release engineer (mission 079 may produce structured draft inputs but does NOT author final prose, per C-012 / FR-605)

### Format

Keep a Changelog (https://keepachangelog.com/) + Semantic Versioning. Each entry has the form:

```markdown
## [VERSION] - DATE

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

### Pre-mission state

The file currently has entries for `3.1.1a3`, `3.1.1a2`, and `3.1.1a1`. **No `3.1.1` (stable) entry.**

### Post-mission state

The human release engineer adds a `## [3.1.1] - <date>` entry summarizing the seven tracks of mission 079. Mission 079 itself produces a structured draft input via `spec-kitty agent release prep --channel stable --json` (FR-605); the human takes that draft and produces the final prose.

**Validation rules**:
- The pre-release validation step (FR-606) MUST assert that an entry whose header matches `## [3.1.1` exists in `CHANGELOG.md` and has a non-empty body.
- The validation step does NOT validate narrative quality or wording — only presence and basic structural shape.

**Mission 079 contract**:
- Mission 079 MUST NOT author the final `## [3.1.1]` entry prose.
- Mission 079 MUST produce a structured draft via the existing `build_release_prep_payload()` helper.
- Mission 079 MUST add the validation step that fails the cut if the entry is missing.

---

## F6. `~/.spec-kitty/credentials` (auth state)

**Path**: `~/.spec-kitty/credentials` (TOML format), with sibling lock file `~/.spec-kitty/credentials.lock`.

**Owner**: `sync.auth.CredentialStore`

### Format (no schema change in this mission)

```toml
[tokens]
access = "..."
refresh = "..."
access_expires_at = "2099-01-01T00:00:00+00:00"
refresh_expires_at = "2099-01-01T00:00:00+00:00"

[user]
username = "..."
team_slug = "..."  # optional

[server]
url = "https://..."
```

**Changes**:
- **No schema change.** Track 5 changes the **lock-scope contract** around `refresh_tokens()`, not the file format.

**Validation rules** (post-Track 5):
- The lock file MUST be acquired across the FULL refresh transaction (read → network → persist), not only per-I/O.
- On 401, the refresh function MUST re-read the credentials file under the same lock and compare to the entry-time refresh token before treating the 401 as authoritative grounds for clearing.
- See `contracts/cli-contracts.md` Contract C5.1 for the function-level contract.

---

## F7. `tasks.md` (per-mission work-package narrative)

**Path**: `kitty-specs/<mission_slug>/tasks.md`

**Owner**: human / agent author (write), `core.dependency_parser` (read)

### Format (no schema change in this mission)

`tasks.md` continues to use the same narrative structure: a `## Plan` overview followed by per-WP sections (`## WP01`, `## WP02`, ..., `## WPnn`), each with frontmatter (`dependencies:`, `owned_files:`, etc.) and prose.

**Changes**:
- **No format change.** Track 4 changes the **parser bound** behavior on the existing format, not the format itself.

**Validation rules** (post-Track 4):
- The dependency parser MUST bound the final WP section at: (a) the next WP header, (b) a top-level `## ` heading whose text is not a WP id, or (c) EOF.
- Trailing prose past the final WP section MUST NOT be parsed for dependencies of the final WP.

**Authoring guidance** (post-Track 4):
- Authors MAY add trailing sections (e.g., `## Notes`, `## Appendix`, `## References`) after the final WP without risking false-positive dependency inference.
- Sub-headings (`### `) inside a WP section continue to be preserved.

---

## F8. `kitty-specs/<mission_slug>/status.events.jsonl` (status event log)

**Path**: `kitty-specs/<mission_slug>/status.events.jsonl`

**Owner**: `status.store` (write), `status.reducer` (read)

### Format

Each line is a JSON object with sorted keys per the existing 3.0 model. See the project `CLAUDE.md` "Status Model Patterns" section for the full schema.

**Changes**:
- **No schema change in this mission.** The status model is already canonical post-3.0 (feature 060).
- Track 3 may add `mission_id` to event payloads emitted by `emit_mission_created()` (in `sync/events.py`), but the status event log itself stores per-WP events that already use `feature_slug` and `wp_id`. No change needed here.

**Validation rules**:
- (unchanged)

---

## F9. Slash-command source templates

**Path**: `src/specify_cli/missions/software-dev/command-templates/{specify,plan,tasks,tasks-packages,implement}.md`

**Owner**: mission template authors (mission 079 edits these as part of Track 6)

### Format

Markdown files with `<!-- spec-kitty-command-version: ... -->` headers and templated body content. The CLI copies these into per-agent directories during `init`.

**Changes**:
- Track 6 edits the body content of these files to:
  - Remove top-level `spec-kitty implement` as the canonical CLI invocation in user-facing examples.
  - Replace inline CLI invocations with the slash-command equivalent.
- The `<!-- spec-kitty-command-version: ... -->` headers are preserved.

**Validation rules**:
- Per the project `CLAUDE.md`: edit SOURCE templates only, NOT generated agent copies under `.claude/`, `.codex/`, etc.
- The migration mechanism that deploys updated templates to existing projects (`upgrade/migrations/`) MUST pick up the changes. Track 6's tests verify this end-to-end.

---

## Cross-file invariants

| Invariant | Files involved | Enforced by |
|-----------|----------------|-------------|
| `pyproject.toml` version == `.kittify/metadata.yaml` version | `pyproject.toml`, `.kittify/metadata.yaml` | `scripts/release/validate_release.py` (Track 7 extension) |
| `CHANGELOG.md` has entry for `pyproject.toml` version | `pyproject.toml`, `CHANGELOG.md` | `scripts/release/validate_release.py` (existing `changelog_has_entry`, ensured to run in branch mode) |
| Every WP in `tasks.md` has a lane assignment in `lanes.json` | `tasks.md`, `lanes.json` | `compute_lanes()` (Track 2) |
| `meta.json:mission_id` exists for every mission created after Track 3 lands | `meta.json` | `core.mission_creation` (Track 3) + acceptance test |
