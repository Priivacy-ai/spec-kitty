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
- FR-024
- FR-028
- FR-029
- NFR-002
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T046
- T047
- T048
agent: "codex:gpt-4o:reviewer-renata:reviewer"
shell_pid: "657807"
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
3. **`charter lint`**: new advisory check for org artifacts that override built-in artifacts.

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
- **Implement command**: `spec-kitty agent action implement WP07 --agent claude:sonnet-4-6`

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
    {"id": "DIR-001", "source": "builtin", "title": "..."}
  ]
}
```

If `get_provenance()` returns `None` (artifact not found in provenance index), default to
`"builtin"` (safest fallback — means "we don't know, assume builtin").

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

    # Resolve version: git describe for git packs, pack-manifest.yaml for non-git packs
    is_git_pack = (snapshot_path / ".git").exists()
    pack_version = "unknown"
    fetched_at = "unknown"

    if is_git_pack:
        import subprocess as _sp
        try:
            pack_version = _sp.check_output(
                ["git", "-C", str(snapshot_path), "describe", "--tags", "--always"],
                stderr=_sp.DEVNULL, text=True,
            ).strip()
        except (_sp.CalledProcessError, FileNotFoundError):
            pack_version = "git (version unavailable)"
    else:
        manifest_path = snapshot_path / "pack-manifest.yaml"
        if manifest_path.exists():
            yaml = ruamel.yaml.YAML()
            manifest = yaml.load(manifest_path) or {}
            pack_version = manifest.get("pack_version", "unknown")
            fetched_at = manifest.get("fetched_at", "unknown")

    # Count artifacts
    artifact_types = ["directives", "tactics", "styleguides", "toolguides",
                      "paradigms", "procedures", "agent_profiles", "mission_step_contracts"]
    counts = {}
    for atype in artifact_types:
        adir = snapshot_path / atype
        if adir.exists():
            counts[atype] = len(list(adir.glob("*.yaml")))

    if json_output:
        print(json.dumps({
            "org_configured": True,
            "snapshot_present": True,
            "local_path": str(snapshot_path),
            "is_git_pack": is_git_pack,
            "pack_version": pack_version,
            "fetched_at": fetched_at if not is_git_pack else None,
            "artifact_counts": counts,
        }, indent=2))
    else:
        console.print(f"[green]Org doctrine snapshot:[/green] {snapshot_path}")
        console.print(f"Version: {pack_version}")
        if not is_git_pack:
            console.print(f"Fetched: {fetched_at}")
        table = Table(title="Artifact Counts")
        table.add_column("Type")
        table.add_column("Count", justify="right")
        for atype, count in counts.items():
            if count > 0:
                table.add_row(atype, str(count))
        console.print(table)
```

---

## Subtask T036 — Add `OrgOverridesBuiltinCheck` to `charter lint`

**File**: `src/specify_cli/cli/commands/charter.py`

Locate the `charter lint` command and its check registry. Add a new check:

```python
def _check_org_overrides_builtin(repo_root: Path) -> list[LintIssue]:
    """Advisory: org layer overrides a built-in artifact."""
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
                # Check if the same ID exists in built-in
                builtin_repo = _build_builtin_only_service()
                if getattr(builtin_repo, atype).get(item_id) is not None:
                    issues.append(LintIssue(
                        severity="ADVISORY",
                        message=f"org layer overrides built-in artifact '{item_id}' ({atype})",
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
- A built-in doctrine directory with directive `DIR-001`
- An org snapshot with directive `DIR-001` (override) and `ORG-001` (new)
- A `pack-manifest.yaml` in the org snapshot

**Tests**:

| Test | Command | Expected |
|---|---|---|
| `test_context_json_source_builtin` | `charter context --json --action specify` | `DIR-001` has `"source": "org"` (since org overrides built-in) |
| `test_context_json_source_new_org` | Same | `ORG-001` has `"source": "org"` |
| `test_doctor_doctrine_with_snapshot` | `spec-kitty doctor doctrine --json` | Returns `snapshot_present: true`, artifact counts |
| `test_doctor_doctrine_no_snapshot` | Same, no snapshot | `snapshot_present: false` |
| `test_lint_advisory_org_overrides_builtin` | `charter lint` | Advisory line mentions `DIR-001` |
| `test_lint_no_advisory_when_no_org` | `charter lint`, no org config | No advisory lines |

---

## Subtask T046 — Org charter elements in `charter context --json`

**File**: `src/charter/context.py` (owned by this WP)

Add an `"org_charter"` top-level key to the `charter context --json` output after the
existing artifact fields. This key is additive — existing fields are unchanged.

```json
{
  "directives": [...],
  "org_charter": {
    "present": true,
    "packs": [
      {
        "pack_name": "security",
        "governance_policies": [
          {"field": "human_in_command", "value": true, "enforcement": "advisory", "source": "org"}
        ],
        "required_directives": ["sec-001-threat-modelling"]
      }
    ]
  }
}
```

If no org packs are configured or none have `org-charter.yaml`: `"org_charter": {"present": false}`.

**Implementation** (depends on WP09's `load_org_charter_policies` and `load_pack_registry`
being available — ensure WP09 merges before this subtask is finalized):

```python
from specify_cli.doctrine.org_charter import load_org_charter_policy
from specify_cli.doctrine.config import load_pack_registry

registry = load_pack_registry(repo_root)
org_charter_packs = []
for pack in registry.packs:
    policy = load_org_charter_policy(pack.local_path)
    if policy:
        org_charter_packs.append({
            "pack_name": pack.name,
            "governance_policies": [
                {**p.model_dump(), "source": "org"}
                for p in policy.governance_policies
            ],
            "required_directives": policy.required_directives,
        })

org_charter_block = {
    "present": bool(org_charter_packs),
    "packs": org_charter_packs,
}
# Merge into the existing JSON output dict
```

---

## Subtask T047 — `OrgCharterDeviationCheck` advisory in `charter lint`

**File**: `src/specify_cli/cli/commands/charter.py`

Add a second new lint check alongside the `OrgOverridesBuiltinCheck` from T036:

```python
def _check_org_charter_deviations(repo_root: Path) -> list[LintIssue]:
    """Advisory: project charter deviates from an org charter governance policy."""
    from specify_cli.doctrine.org_charter import load_org_charter_policies
    from specify_cli.doctrine.config import load_doctrine_org_config

    config = load_doctrine_org_config(repo_root)
    if config is None:
        return []
    org_policy = load_org_charter_policies(repo_root)
    if not org_policy.governance_policies:
        return []

    # Load the project charter answers or charter.md and extract governed fields
    project_values = _load_project_charter_fields(repo_root)
    issues = []
    for policy in org_policy.governance_policies:
        project_val = project_values.get(policy.field)
        if project_val is not None and str(project_val) != str(policy.value):
            issues.append(LintIssue(
                severity="ADVISORY",
                message=(
                    f"project charter field '{policy.field}' = {project_val!r}; "
                    f"org charter recommends {policy.value!r}"
                ),
            ))
    return issues
```

`_load_project_charter_fields()` reads `.kittify/charter/interview/answers.yaml` (the
interview output) and returns a dict of field → value. Read only fields that org charter
policies reference — don't load the full charter for this check.

---

## Subtask T048 — Org charter status in `doctor doctrine` per-pack listing

**File**: `src/specify_cli/cli/commands/doctor.py`

Extend the per-pack listing in `doctor doctrine` to include org charter status:

```python
# For each pack in the registry:
charter_path = pack.local_path / "org-charter.yaml"
if charter_path.exists():
    policy = load_org_charter_policy(pack.local_path)
    charter_info = {
        "present": True,
        "interview_defaults_count": len(policy.interview_defaults),
        "required_directives_count": len(policy.required_directives),
        "governance_policies_count": len(policy.governance_policies),
    }
else:
    charter_info = {"present": False}
```

Human output:
```
Pack: security  (git v2.1.0, 12 directives, 4 tactics)
  org-charter.yaml: 3 interview defaults, 2 required directives, 2 governance policies
Pack: architecture  (git v1.0.0, 8 directives)
  org-charter.yaml: not present
```

JSON output: add `"org_charter"` key to each pack entry in the JSON response.

---

## Definition of Done

- [ ] `charter context --json` includes `"source": "builtin"|"org"|"project"` for every artifact
- [ ] `charter context --json` includes `"org_charter"` key (additive; does not break existing consumers)
- [ ] `context.py` DRG load routed through `load_validated_graph()`; no inline `load_graph` calls
- [ ] `spec-kitty doctor doctrine` shows each configured pack with version (`git describe` for git packs, manifest version for others), artifact counts, and org-charter policy counts
- [ ] `charter lint` registers `OrgOverridesBuiltinCheck` and `OrgCharterDeviationCheck` (both advisory)
- [ ] All tests in `test_provenance_integration.py` pass
- [ ] `spec-kitty doctor doctrine --json` exit 0 in all cases (diagnostic, not error)

## Risks

- `charter lint` check registry shape may vary — read `charter.py` before implementing T036
  and adapt to the actual registry/check interface.
- Building a "shipped-only" service inside the lint check for comparison requires knowing
  `DoctrineService` factory convention. Prefer comparing against `_provenance` dict
  (artifact is `"builtin"` in a two-layer-only service run) rather than instantiating a
  second service.

## Reviewer Guidance

1. Confirm `"source"` field appears in JSON output for ALL artifact types (not just directives).
2. Confirm `doctor doctrine` exit code is always 0 (it's a diagnostic, not a gating check).
3. Confirm lint advisory does NOT appear when org layer is absent or empty.

## Activity Log

- 2026-05-15T14:14:32Z – claude:opus-4-7:python-pedro:implementer – shell_pid=634691 – Started implementation via action command
- 2026-05-15T14:29:46Z – claude:opus-4-7:python-pedro:implementer – shell_pid=634691 – WP07 complete: provenance source field in charter context --json, doctor doctrine subcommand with per-pack version + counts + org-charter status, two advisory lint checkers (OrgOverridesBuiltin + OrgCharterDeviation), routed context.py DRG through load_validated_graph helper. 9/9 integration tests + 8/8 architectural layer tests pass.
- 2026-05-15T14:30:28Z – codex:gpt-4o:reviewer-renata:reviewer – shell_pid=657807 – Started review via action command
- 2026-05-15T14:33:04Z – codex:gpt-4o:reviewer-renata:reviewer – shell_pid=657807 – Review passed: provenance source field per artifact, DRG routed via load_validated_graph, doctor doctrine subcommand with per-pack version + counts + org-charter info, two advisory lint checkers (low severity) registered, 9/9 integration tests + 8/8 architectural layer tests green, no new specify_cli imports from lower layers, all new symbols wired (no dead code)
