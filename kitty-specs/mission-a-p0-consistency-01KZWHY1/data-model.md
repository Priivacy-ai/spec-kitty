# Data Model — Mission A — P0 Read/Write Consistency

This mission introduces **no new entities and no schema changes**. It corrects
how four existing state authorities are read/computed/written. Each authority and
the invariant the fix restores is below.

## A-01 — Acceptance verdict (`AcceptanceMatrix`, `acceptance/matrix.py`) — #3231

- **Fields (relevant)**: `criteria: list[AcceptanceCriterion]` where each has
  `criterion_id`, `description`, `pass_fail ∈ {pass, fail, pending}`, `notes`;
  computed `overall_verdict`.
- **Scaffold placeholder shapes** (writer, `matrix.py:513-536`): (i) empty
  placeholder — `criterion_id="AC-001"`, `description == SCAFFOLD_TODO_MARKER`,
  `pass_fail="pending"`; (ii) seeded per-FR row — `criterion_id="FR-###"`,
  `description="Verify FR-### is satisfied"`, `notes == SCAFFOLD_TODO_MARKER`,
  `pass_fail="pending"`.
- **Invariant restored (FR-003/FR-004)**: `overall_verdict` treats only shape (i)
  (empty placeholder, `description == SCAFFOLD_TODO_MARKER`) as non-blocking, and
  only when ≥1 non-scaffold criterion exists. Shape (ii) and an all-scaffold
  matrix remain `pending`. `overall_verdict` stays a pure computed property (never
  persisted/merged).

## A-02 — Retrospective record (`GenRetrospectiveRecord`, `retrospective/`) — #3320

- **Fields (relevant)**: `findings_status ∈ {ran_no_findings, has_findings, …}`,
  `gaps`, `helped`, `not_helpful`, `proposals`, `evidence_refs`.
- **Merge authority**: `write_gen_record(mode="update")` merges the generated
  record with the on-disk record and recomputes `findings_status` from the union
  (`writer.py::_merge_gen_records`), persisting the merged record; it returns a
  `Path`.
- **Invariant restored (FR-001/FR-002)**: the reported `counts`/`findings_status`
  **and** the `RetrospectiveCaptured` event payload are derived from the persisted
  (read-back) record, so report/event/disk agree. `write_gen_record`'s `Path`
  return type is unchanged (C-002).

## A-03 — Project compatibility state (`.kittify/metadata.yaml`) — #3334

- **Fields (relevant)**: `spec_kitty.version`, `spec_kitty.schema_version: int|None`,
  `migrations.applied: [{id, applied_at, result ∈ {success, failed}, …}]`.
- **Reader/authority**: `get_project_schema_version()`;
  classifier `compat.planner._scan_project` maps `schema_version is None →
  LEGACY` (a faithful reader — unchanged by this mission).
- **Invariant restored (FR-005/FR-006, C-008)**: `ProjectMetadata` round-trips
  `spec_kitty.schema_version` through load→save (`metadata.py:126`,`:188-210`), so
  **no `save()` caller strips it** — a failed `MigrationRunner.upgrade()` leaves
  `schema_version` at its pre-upgrade value and a previously-healthy project is
  not dropped into `LEGACY`. A genuinely pre-3.x project (`schema_version` absent,
  no 3.x `success` history) has nothing to round-trip → keeps `None` → stays
  `LEGACY`-blocked. The success path still advances the stamp to
  `REQUIRED_SCHEMA_VERSION`; `dry_run` writes nothing; `migrations.applied` is
  never used as a schema-truth heuristic (no spoof surface). Delivers the durable
  fix that partially closes Epic #3347.

## A-04 — Lanes manifest (`lanes.json` / `LanesManifest`) — #3311

- **Fields (relevant)**: `lanes: [{lane_id, wp_ids}]`, `planning_commit_sha:
  str|None`.
- **Companion authority**: the append-only status event log
  (`status.events.jsonl`, 034+ sole authority for WP lane state), read via the
  resolved (coord-aware) status surface — `resolve_status_surface_with_anchor(
  repo_root, mission_slug).read_dir` → read-only `lane_reader.get_all_wp_lanes`
  (or `reducer.materialize_snapshot`), guarded by `lane_reader.has_event_log`
  (absent ⟹ execution not begun). Never `reducer.materialize()` (it writes
  `status.json`).
- **Invariant restored (FR-007/FR-008)**: once **execution has begun** (any WP
  current lane ∉ {`planned`}), a `finalize-tasks` re-run preserves
  `planning_commit_sha` (no branch-tip re-capture) or refuses before writing;
  before execution begins, re-finalize regenerates freely. Single-write
  provenance freeze (ADR 2026-07-29-1 / FR-009) preserved.

## Cross-cutting

- **No shared type/helper** spans A-01…A-04 (C-001). Each invariant is enforced
  within its own module against its own authority.
- **State transitions**: none added. #3311 *reads* the existing 9-lane status
  machine (`planned → claimed → … → done`) to derive the boolean "execution
  begun"; it introduces no new lane or transition.
