# Research: Plan Concern Vocabulary and WP Traceability

## Pydantic v2 optional field with validator — pattern

**Decision**: Use `Field(default_factory=list)` with `@field_validator("plan_concern_refs", mode="before")` for the new list field.

**Rationale**: The existing `wps_manifest.py` already uses this exact pattern for `dependencies`, `owned_files`, `requirement_refs`, and `subtasks`. Consistency is the primary driver.

**Alternatives considered**: `Optional[list[str]] = None` — rejected because `None` vs `[]` distinction creates unnecessary null-checking downstream in `generate_tasks_md_from_manifest()`.

## IC-## pattern validation and ASCII constraint

**Decision**: Validate with `re.match(r"^IC-\d{2}$", v)` inside `field_validator`. Do not use `\w` or Unicode-aware patterns.

**Rationale**: Project directive DIR-010 requires ASCII-only identifiers using an explicit ASCII allowlist. `IC-\d{2}` covers `IC-01` through `IC-99` — sufficient for any realistic mission plan.

**Alternatives considered**: `IC-\d+` (variable length) — rejected; fixed two-digit format matches `WP##` discipline and makes sorting predictable.

## `cross_cutting` field placement

**Decision**: Add `cross_cutting: bool = False` to `WorkPackageEntry` alongside `plan_concern_refs`.

**Rationale**: The spec requires `finalize-tasks` to warn for WPs missing both `plan_concern_refs` and `cross_cutting`. Both fields live on `WorkPackageEntry` to keep the validation logic in one place. `False` default preserves backwards compatibility.

**Alternatives considered**: A sidecar YAML field outside `WorkPackageEntry` — rejected; the pydantic model is the schema authority and unknown fields in `wps.yaml` are either rejected or silently dropped depending on model config; a typed field is safer.

## `generate_tasks_md_from_manifest()` rendering extension

**Decision**: Add a "Plan concerns: IC-01, IC-03" line to each WP block in `tasks.md` when `plan_concern_refs` is non-empty. Render nothing (no blank line, no label) when the list is empty.

**Rationale**: Matches existing rendering pattern — `owned_files` and `requirement_refs` are only rendered when non-empty. Keeps generated `tasks.md` clean for legacy missions.

## Template section naming: "Implementation Concern Map"

**Decision**: Use `## Implementation Concern Map` as the replacement section header.

**Rationale**: "Map" signals that the section is a structured enumeration of named units (not a prose description). "Implementation Concern" is unambiguous in the SDD context — it does not collide with "implementation" (the execute phase), "concern" (a general English word), or any existing spec-kitty term.

**Alternatives considered**: "Architecture Concerns", "Plan Decomposition", "Work Concerns" — all rejected as either too vague or too close to existing terminology.

## Snapshot regeneration scope

**Decision**: Regenerate only `tests/specify_cli/skills/__snapshots__/` snapshots. The twelve-agent regression baseline (`tests/specify_cli/regression/_twelve_agent_baseline/`) should be inspected for stale "Parallel Work Analysis" fixture content and updated if found — they are test fixtures, not historical artifacts.

**Rationale**: The renderer test suite (`test_command_renderer.py`) runs `PYTEST_UPDATE_SNAPSHOTS=1` to regenerate. The twelve-agent baseline is a separate suite; update only entries that fail due to this change.
