---
work_package_id: WP07
title: Provenance, doctor doctrine, and charter lint advisory
dependencies:
- WP03
requirement_refs:
- FR-014
- FR-015
- FR-016
- FR-017
- NFR-002
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: All planning and implementation targets feat/org-doctrine-layer. Worktree branch allocated by finalize-tasks lane computation. Can run in parallel with WP05-WP06 after WP03.
subtasks:
- T033
- T034
- T035
- T036
- T037
agent: codex
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/charter.py
- tests/specify_cli/test_provenance_integration.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Surface the org-layer in three operator-facing surfaces:
1. **`charter context --json`**: add `"source"` field to every artifact entry.
2. **`spec-kitty doctor doctrine`**: new subcommand listing org-layer artifacts and
   snapshot metadata.
3. **`charter lint`**: new advisory check for org artifacts that override shipped artifacts.

Also route `context.py`'s inline DRG loading through `_drg_helpers.load_validated_graph()`
(removing the last set of inline `load_graph` calls in the charter context path).

---

## Context

`context.py` (lines 228–231) contains an inline DRG load that bypasses `_drg_helpers.py`.
After WP01 + WP03, the helper is the correct three-layer graph loading point. This WP
routes `context.py` through the helper and adds the provenance JSON field.

`doctor.py` already has subcommands like `doctor command-files` and `doctor identity`.
This WP adds `doctor doctrine` to the same group.

`charter.py` (the lint subcommand) has a check registry. This WP adds one advisory check.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP07 --agent codex`

---

## Subtask T033 — Add `"source"` field to `charter context --json`

**File**: `src/charter/context.py`

**Current flow** (schematic):
1. Load DRG (inline)
2. Resolve artifact URNs from DRG
3. Build `DoctrineService`
4. For each artifact URN, fetch the artifact from the service
5. Serialize to JSON

**Changes**:

Step 1: Replace the inline DRG load (lines 228–231) with:
```python
from charter._drg_helpers import load_validated_graph
merged = load_validated_graph(repo_root)
```
(T034 moves the inline load; T033 adds the provenance field to the JSON output.)

Step 5: For each resolved artifact, call `service.<type>.get_provenance(artifact_id)` and
add `"source": provenance_value` to the serialised artifact object.

The JSON output gains one new field per artifact:
```json
{
  "directives": [
    {"id": "sec-001", "source": "org", "title": "..."},
    {"id": "DIR-001", "source": "shipped", "title": "..."}
  ]
}
```

If `get_provenance()` returns `None` (artifact not found in provenance index), default to
`"shipped"` (safest fallback — means "we don't know, assume shipped").

**Non-JSON output**: unchanged. Source attribution is JSON-only.

---

## Subtask T034 — Route `context.py` DRG loading through `_drg_helpers`

**File**: `src/charter/context.py`

**Current code** (lines 228–231 approximate):
```python
doctrine_root = resolve_doctrine_root()
shipped_graph = load_graph(doctrine_root / "graph.yaml")
project_graph_path = repo_root / KITTIFY_DIRNAME / "doctrine" / "graph.yaml"
project_graph = load_graph(project_graph_path) if project_graph_path.exists() else None
merged = merge_layers(shipped_graph, project_graph)
assert_valid(merged)
```

**Replace with**:
```python
from charter._drg_helpers import load_validated_graph
merged = load_validated_graph(repo_root)
```

`load_validated_graph()` already calls `_resolve_org_root()` (added in WP03 T014), so org-
layer DRG extensions are included automatically.

Remove the now-unused imports: `load_graph`, `merge_layers`, `assert_valid` from this code
path (keep if used elsewhere in the file).

---

## Subtask T035 — Add `spec-kitty doctor doctrine` subcommand

**File**: `src/specify_cli/cli/commands/doctor.py`

**Model on existing subcommands** (`doctor command-files`, `doctor identity`):

```python
@app.command(name="doctrine")
def doctrine_check(
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Check org doctrine snapshot status and list installed artifacts."""
    from specify_cli.doctrine.config import load_doctrine_org_config
    from specify_cli.core.paths import locate_project_root
    import ruamel.yaml, json

    repo_root = locate_project_root()
    config = load_doctrine_org_config(repo_root)

    if config is None:
        if json_output:
            print(json.dumps({"org_configured": False}))
        else:
            console.print("[yellow]No org doctrine configured.[/yellow]")
            console.print("Add a 'doctrine.org' block to .kittify/config.yaml")
        return

    snapshot_path = config.local_path
    if not snapshot_path.exists():
        if json_output:
            print(json.dumps({"org_configured": True, "snapshot_present": False, "local_path": str(snapshot_path)}))
        else:
            console.print(f"[yellow]Snapshot not found at {snapshot_path}[/yellow]")
            console.print("Run: spec-kitty doctrine fetch")
        return

    # Read pack-manifest.yaml
    manifest_path = snapshot_path / "pack-manifest.yaml"
    manifest = {}
    if manifest_path.exists():
        yaml = ruamel.yaml.YAML()
        manifest = yaml.load(manifest_path) or {}

    # Count artifacts
    artifact_types = ["directives", "tactics", "styleguides", "toolguides",
                      "paradigms", "procedures", "agent_profiles", "mission_step_contracts"]
    counts = {}
    for atype in artifact_types:
        adir = snapshot_path / atype
        if adir.exists():
            counts[atype] = len(list(adir.glob(f"*.yaml")))

    if json_output:
        print(json.dumps({
            "org_configured": True,
            "snapshot_present": True,
            "local_path": str(snapshot_path),
            "pack_version": manifest.get("pack_version"),
            "fetched_at": manifest.get("fetched_at"),
            "artifact_counts": counts,
        }, indent=2))
    else:
        console.print(f"[green]Org doctrine snapshot:[/green] {snapshot_path}")
        console.print(f"Version: {manifest.get('pack_version', 'unknown')}")
        console.print(f"Fetched: {manifest.get('fetched_at', 'unknown')}")
        table = Table(title="Artifact Counts")
        table.add_column("Type")
        table.add_column("Count", justify="right")
        for atype, count in counts.items():
            if count > 0:
                table.add_row(atype, str(count))
        console.print(table)
```

---

## Subtask T036 — Add `OrgOverridesShippedCheck` to `charter lint`

**File**: `src/specify_cli/cli/commands/charter.py`

Locate the `charter lint` command and its check registry. Add a new check:

```python
def _check_org_overrides_shipped(repo_root: Path) -> list[LintIssue]:
    """Advisory: org layer overrides a shipped artifact."""
    from specify_cli.doctrine.config import load_doctrine_org_config
    from specify_cli.doctrine.service import _build_doctrine_service  # or equivalent factory

    config = load_doctrine_org_config(repo_root)
    if config is None or not config.local_path.exists():
        return []

    service = _build_doctrine_service(repo_root)
    issues = []
    for atype in ["directives", "tactics", "agent_profiles", ...]:
        repo = getattr(service, atype)
        for item in repo.list_all():
            item_id = item.id
            prov = repo.get_provenance(item_id)
            if prov == "org":
                # Check if the same ID exists in shipped
                shipped_repo = _build_shipped_only_service()
                if getattr(shipped_repo, atype).get(item_id) is not None:
                    issues.append(LintIssue(
                        severity="ADVISORY",
                        message=f"org layer overrides shipped artifact '{item_id}' ({atype})",
                    ))
    return issues
```

This check is registered as `ADVISORY` severity. It never causes `charter lint` to exit
non-zero (advisories are informational). Print advisories after warnings and errors in the
lint output.

**Note**: The exact shape of the lint check registry depends on the current implementation
in `charter.py`. Read the file before implementing and adapt accordingly.

---

## Subtask T037 — Integration tests for provenance, doctor, lint

**File**: `tests/specify_cli/test_provenance_integration.py`

Uses `tmp_path` as a fake project root. Sets up:
- A shipped doctrine directory with directive `DIR-001`
- An org snapshot with directive `DIR-001` (override) and `ORG-001` (new)
- A `pack-manifest.yaml` in the org snapshot

**Tests**:

| Test | Command | Expected |
|---|---|---|
| `test_context_json_source_shipped` | `charter context --json --action specify` | `DIR-001` has `"source": "org"` (since org overrides shipped) |
| `test_context_json_source_new_org` | Same | `ORG-001` has `"source": "org"` |
| `test_doctor_doctrine_with_snapshot` | `spec-kitty doctor doctrine --json` | Returns `snapshot_present: true`, artifact counts |
| `test_doctor_doctrine_no_snapshot` | Same, no snapshot | `snapshot_present: false` |
| `test_lint_advisory_org_overrides_shipped` | `charter lint` | Advisory line mentions `DIR-001` |
| `test_lint_no_advisory_when_no_org` | `charter lint`, no org config | No advisory lines |

---

## Definition of Done

- [ ] `charter context --json` includes `"source"` field for every directive, tactic, etc.
- [ ] `context.py` DRG load routed through `load_validated_graph()`; no inline `load_graph` calls
- [ ] `spec-kitty doctor doctrine` registered and produces correct output (human + JSON)
- [ ] `charter lint` advisory check registered; advisory in output when org overrides shipped
- [ ] All tests in `test_provenance_integration.py` pass
- [ ] `spec-kitty doctor doctrine --json` exit 0 in all cases (diagnostic, not error)

## Risks

- `charter lint` check registry shape may vary — read `charter.py` before implementing T036
  and adapt to the actual registry/check interface.
- Building a "shipped-only" service inside the lint check for comparison requires knowing
  `DoctrineService` factory convention. Prefer comparing against `_provenance` dict
  (artifact is `"shipped"` in a two-layer-only service run) rather than instantiating a
  second service.

## Reviewer Guidance

1. Confirm `"source"` field appears in JSON output for ALL artifact types (not just directives).
2. Confirm `doctor doctrine` exit code is always 0 (it's a diagnostic, not a gating check).
3. Confirm lint advisory does NOT appear when org layer is absent or empty.
