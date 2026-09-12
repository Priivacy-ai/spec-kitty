# Contract — Birth-cutover writer & partition-correct cutover (FR-001, FR-002)

## C-WRITER-1 — `_flip_phase` resolves its write target through the port (FR-001)

**Given** `_flip_phase(feature_dir, …)` (the sole `status_phase` writer),
**When** it writes `meta.json`,
**Then** the write directory is `resolve_artifact_surface(repo_root, feature_dir.name, PRIMARY_METADATA).path`, where `repo_root` is the CWD-invariant main-repo root derived from `feature_dir` (never `Path.cwd()`),
**And** if the resolved PRIMARY home ≠ `canonicalize_feature_dir(feature_dir)` the call **fails closed** (raises, writes nothing).

**Degrade clause**: a resolver *raise* (e.g. `MissionSelectorAmbiguous`/`StatusReadPathNotFound`) on a well-formed legacy corpus mission MUST NOT abort the flip — only an equality **mismatch** fail-closes. (Distinguishes the enforcement failure from a resolvability hiccup so NFR-002's corpus run stays green.)

**Red-first**: construct a canonical-primary dir + a divergent `feature_dir` for the same slug + a verify-passing `status_feature_dir`; assert the flip raises on mismatch and still succeeds for a genuine PRIMARY dir. Entry point: `cutover_mission(feature_dir, status_feature_dir=…)`.

## C-CUTOVER-1 — Read/write partition decoupling (FR-002)

**Given** a coord-topology `cutover_mission(feature_dir=PRIMARY, status_feature_dir=COORD)`,
**When** seed/verify read the legacy `tasks/` frontmatter,
**Then** the read anchors on the **PRIMARY** leg (`feature_dir`),
**And** the seed-event write (`status.events.jsonl` = STATUS_STATE) still lands on the **COORD** leg,
**And** the `status_phase` flip still lands on **PRIMARY**.

**No-loss invariant**: a mission whose PRIMARY `tasks/` carry `has_evictable_state() == True` is never flipped with `seeded_count == 0` (no silent eviction).

**Red-first**: PRIMARY dir with evictable frontmatter + absent/stale COORD `tasks/`; assert `seeded_count > 0` AND the event log is written to the COORD leg (not PRIMARY). Entry point: `cutover_mission`.

**Corpus (NFR-002)**: both contracts validated across the whole FR-007 dogfood backfill corpus via `spec-kitty migrate backfill-runtime-state` / the `cutover_repo` walk — 0 genuinely-legacy missions fail to flip; 0 evictions.
