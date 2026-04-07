# Data Model: Planning Pipeline Integrity and Runtime Reliability

**Feature**: 069-planning-pipeline-integrity
**Date**: 2026-04-07

---

## New File: `kitty-specs/<slug>/wps.yaml`

### Format

```yaml
work_packages:
  - id: WP01
    title: "Fix status.json dirty-git"
    dependencies: []
    owned_files:
      - "src/specify_cli/status/reducer.py"
      - "src/specify_cli/status/views.py"
    requirement_refs: [FR-001, FR-002, FR-003]
    subtasks: [T001, T002, T003]
    prompt_file: "tasks/WP01-fix-status-json-dirty-git.md"

  - id: WP02
    title: "Add wps_manifest module"
    dependencies: []
    owned_files:
      - "src/specify_cli/core/wps_manifest.py"
      - "src/specify_cli/schemas/wps.schema.json"
    requirement_refs: [FR-004, FR-005]
    subtasks: [T004, T005, T006]
    prompt_file: "tasks/WP02-add-wps-manifest-module.md"
```

### Field Semantics

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string `WPnn` | yes | Work package identifier, e.g. `WP01` |
| `title` | string | yes | Human-readable WP title |
| `dependencies` | list[string] | no | WP IDs this WP depends on. Present-but-empty `[]` is authoritative: pipeline never modifies it. Absent field may be populated by `tasks-packages`. |
| `owned_files` | list[glob-string] | no | Glob patterns for files this WP exclusively owns |
| `requirement_refs` | list[string] | no | Spec requirement IDs (e.g. `FR-001`, `NFR-001`) |
| `subtasks` | list[string] | no | Subtask IDs (e.g. `T001`) |
| `prompt_file` | string\|null | no | Relative path to WP prompt file (e.g. `tasks/WP01-title.md`) |

**Deferred fields (not in this feature)**: `priority`, `execution_mode`, `authoritative_surface`

---

## New Module: `src/specify_cli/core/wps_manifest.py`

### Public API

```python
from pydantic import BaseModel, Field
from pathlib import Path

class WorkPackageEntry(BaseModel):
    id: str                                              # "WP01"
    title: str
    dependencies: list[str] = Field(default_factory=list)
    owned_files: list[str] = Field(default_factory=list)
    requirement_refs: list[str] = Field(default_factory=list)
    subtasks: list[str] = Field(default_factory=list)
    prompt_file: str | None = None

class WpsManifest(BaseModel):
    work_packages: list[WorkPackageEntry]

def load_wps_manifest(feature_dir: Path) -> WpsManifest | None:
    """Load wps.yaml if present. Returns None if file absent.
    Raises ValidationError if file exists but is malformed.
    """

def generate_tasks_md_from_manifest(manifest: WpsManifest, feature_name: str) -> str:
    """Generate a human-readable tasks.md from the manifest.
    Output follows tasks-template.md conventions.
    """
```

### Validation Rules

- `id` must match `^WP\d{2}$`
- `dependencies` entries must each match `^WP\d{2}$`
- `work_packages` list must have at least one entry
- If `dependencies` key is **present** in YAML (even as `[]`), it is loaded as-is and never modified by the pipeline
- If `dependencies` key is **absent** from YAML, the field defaults to `[]` in memory and may be written back by `tasks-packages`

### Determination of "dependencies field present"

The `tasks-packages` prompt writes explicit dependencies. Pydantic's `model_fields_set` attribute tracks which fields were explicitly set in the input data. If `"dependencies"` is in `model_fields_set`, the field is treated as authoritative and not overwritten.

Alternatively: the YAML loader records which fields appear in the file. A simpler approach: treat `dependencies: []` as explicitly present by checking if the raw YAML dict has a `"dependencies"` key (distinct from a missing key that would get Pydantic's default). The loader uses `"dependencies" in raw_dict` to detect presence.

---

## New File: `src/specify_cli/schemas/wps.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://spec-kitty.ai/schemas/wps.schema.json",
  "title": "WPS Manifest",
  "description": "Structured work package manifest for spec-kitty missions",
  "type": "object",
  "required": ["work_packages"],
  "additionalProperties": false,
  "properties": {
    "work_packages": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "title"],
        "additionalProperties": false,
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^WP\\d{2}$",
            "description": "Work package identifier, e.g. WP01"
          },
          "title": {"type": "string", "minLength": 1},
          "dependencies": {
            "type": "array",
            "items": {"type": "string", "pattern": "^WP\\d{2}$"},
            "default": []
          },
          "owned_files": {
            "type": "array",
            "items": {"type": "string"},
            "default": []
          },
          "requirement_refs": {
            "type": "array",
            "items": {"type": "string"},
            "default": []
          },
          "subtasks": {
            "type": "array",
            "items": {"type": "string"},
            "default": []
          },
          "prompt_file": {
            "type": ["string", "null"],
            "default": null
          }
        }
      }
    }
  }
}
```

---

## Modified Module: `src/specify_cli/status/reducer.py`

### Change to `reduce()`

```python
# Before (non-deterministic):
return StatusSnapshot(
    ...
    materialized_at=_now_utc(),   # ← wall clock
    ...
)

# After (deterministic):
last_event_at = sorted_events[-1].at if sorted_events else ""
return StatusSnapshot(
    ...
    materialized_at=last_event_at,   # ← derived from last event
    ...
)
```

### Change to `materialize()`

```python
def materialize(feature_dir: Path) -> StatusSnapshot:
    events = read_events(feature_dir)
    snapshot = reduce(events)
    json_str = materialize_to_json(snapshot)

    out_path = feature_dir / SNAPSHOT_FILENAME
    tmp_path = feature_dir / (SNAPSHOT_FILENAME + ".tmp")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip write if content unchanged (FR-001, NFR-001)
    if out_path.exists() and out_path.read_text(encoding="utf-8") == json_str:
        return snapshot

    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))
    return snapshot
```

---

## Modified Module: `src/specify_cli/status/views.py`

### Change to `materialize_if_stale()`

```python
# Before (always writes via materialize()):
if _is_stale():
    write_derived_views(feature_dir, derived_dir)
    generate_progress_json(feature_dir, derived_dir)
return materialize(feature_dir)   # ← always writes status.json

# After (read-only return):
if _is_stale():
    write_derived_views(feature_dir, derived_dir)
    generate_progress_json(feature_dir, derived_dir)
return reduce(read_events(feature_dir))   # ← no write
```

---

## Modified Module: `src/specify_cli/next/decision.py`

### New DecisionKind constant

```python
class DecisionKind:
    step = "step"
    decision_required = "decision_required"
    blocked = "blocked"
    terminal = "terminal"
    query = "query"   # NEW: bare next call, state not advanced
```

### Decision dataclass additions

```python
@dataclass
class Decision:
    ...
    is_query: bool = False   # NEW: True when kind == "query"
```

---

## Modified Module: `src/specify_cli/next/runtime_bridge.py`

### New function: `query_current_state()`

```python
def query_current_state(
    agent: str,
    mission_slug: str,
    repo_root: Path,
) -> Decision:
    """Return current mission step without advancing the DAG.

    Reads run state idempotently. Does not call next_step().
    Returns a Decision with kind=DecisionKind.query.
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug
    now = datetime.now(timezone.utc).isoformat()

    if not feature_dir.is_dir():
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission="unknown",
            mission_state="unknown",
            timestamp=now,
            is_query=True,
            reason="[QUERY — no result provided, state not advanced] (feature dir not found)",
        )

    mission_type = get_mission_type(feature_dir)
    progress = _compute_wp_progress(feature_dir)

    try:
        run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    except Exception as exc:
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="unknown",
            timestamp=now,
            is_query=True,
            reason=f"[QUERY — no result provided, state not advanced] (run init failed: {exc})",
            progress=progress,
        )

    try:
        from spec_kitty_runtime.engine import _read_snapshot
        snapshot = _read_snapshot(Path(run_ref.run_dir))
        current_step_id = snapshot.issued_step_id or "unknown"
    except Exception:
        current_step_id = "unknown"

    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=current_step_id,
        timestamp=now,
        is_query=True,
        reason="[QUERY — no result provided, state not advanced]",
        progress=progress,
        run_id=getattr(run_ref, "run_id", None),
    )
```

---

## Modified Module: `src/specify_cli/cli/commands/next_cmd.py`

### Signature change

```python
result: Annotated[
    str | None,
    typer.Option(
        "--result",
        help=(
            "Result of previous step: success|failed|blocked. "
            "If omitted, returns current state without advancing (query mode)."
        ),
    ),
] = None,   # ← was "success"
```

### Query mode branch (before core decision)

```python
# Query mode: bare call without --result
if result is None:
    from specify_cli.next.runtime_bridge import query_current_state
    decision = query_current_state(agent, mission_slug, repo_root)
    if json_output:
        print(json.dumps(decision.to_dict(), indent=2))
    else:
        _print_human(decision)
    return   # No event emitted, no DAG advancement

# Validate --result (only reached when result is not None)
if result not in _VALID_RESULTS:
    print(f"Error: --result must be one of {_VALID_RESULTS}, got '{result}'", file=sys.stderr)
    raise typer.Exit(1)
```

---

## Modified Module: `src/specify_cli/core/mission_creation.py`

### Regex change

```python
# Before:
KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# After:
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$")
```

### Error message update (lines 202–211)

```python
raise MissionCreationError(
    f"Invalid feature slug '{mission_slug}'. "
    "Must be kebab-case (lowercase letters, numbers, hyphens only)."
    "\n\nValid examples:"
    "\n  - user-auth"
    "\n  - fix-bug-123"
    "\n  - 068-feature-name"    # ← new: digit-prefixed example
    "\n\nInvalid examples:"
    "\n  - User-Auth (uppercase)"
    "\n  - user_auth (underscores)"
    # removed: "\n  - 123-fix (starts with number)"
)
```

---

## finalize-tasks integration (updated flow)

### Current flow (simplified)

```
1. Read tasks.md (if exists) → prose parser → wp_dependencies
2. Read WP frontmatter → wp_requirement_refs
3. Validate cycles, overlaps
4. Write WP frontmatter with deps + refs
5. Bootstrap status events
6. Commit
```

### New flow (with wps.yaml tier 0)

```
1. Check for wps.yaml → if present: load_wps_manifest() → wp_dependencies (skip prose parser)
                       → if absent: prose parser path (existing behavior, unchanged)
2. Read WP frontmatter → wp_requirement_refs (unchanged)
3. Validate cycles, overlaps (unchanged)
4. Write WP frontmatter with deps + refs (unchanged)
5. If wps.yaml present: generate_tasks_md_from_manifest() → overwrite tasks.md
6. Bootstrap status events (unchanged)
7. Commit (unchanged)
```

### FR-007 enforcement

When `wps.yaml` is present, `wp_dependencies` is derived from manifest entries. The manifest is read-only during `finalize-tasks`; no code path writes back to `wps.yaml`. FR-007 is satisfied by design: `finalize-tasks` reads from `wps.yaml` but never writes to it.
