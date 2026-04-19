# CLI Contract: `spec-kitty doctor shim-registry`

**Mission**: `migration-shim-ownership-rules-01KPDYDW`
**Spec refs**: FR-009, NFR-001, NFR-004, C-004, C-007
**Command group**: `spec-kitty doctor` (new subcommand alongside `command-files`, `state-roots`, `identity`, `sparse-checkout`)

---

## Invocation

```bash
spec-kitty doctor shim-registry
spec-kitty doctor shim-registry --json
```

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--json` | bool | `false` | Emit machine-readable JSON instead of the Rich table. |

No `--fix` flag. The check is read-only (C-004); it never writes to the registry or to the filesystem.

## Inputs (read-only)

- `architecture/2.x/shim-registry.yaml` — parsed via `ruamel.yaml` safe loader.
- `pyproject.toml` — `[project].version` read via stdlib `tomllib`.
- `src/specify_cli/**/*.py` — only for existence probes on each entry's `legacy_path` (no import).

## Algorithm

```
1. Locate repo root.
2. Read project version from pyproject.toml. On failure, exit 2 with config error.
3. Read registry YAML. On missing or malformed file, exit 2 with config error.
4. Validate every entry against the schema in contracts/shim-registry-schema.yaml.
   On validation failure, exit 2 and list every invalid entry with its field-level error.
5. For each entry:
     status = derive_status(entry, project_version, fs)
     append row to output table
6. Count statuses.
7. If any overdue: exit 1.
   Else exit 0.
```

## Status derivation

```python
def derive_status(entry, project_version, fs) -> Status:
    exists = fs.shim_file_exists(entry.legacy_path)
    if entry.grandfathered:
        return Status.GRANDFATHERED
    if Version(project_version) >= Version(entry.removal_target_release):
        return Status.OVERDUE if exists else Status.REMOVED
    return Status.PENDING  # exists is expected to be True; mismatch is an advisory
```

Edge case: `pending` but module file absent — treated as a consistency advisory ("registry says shim exists but file was not found"). Non-fatal for the check's exit code but flagged in the output.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All entries pending, removed, or grandfathered. Build passes. |
| 1 | At least one overdue shim. Build fails. |
| 2 | Configuration error (pyproject.toml missing, registry missing/unparseable, schema violation). |

## Human output (Rich table)

```
+--------------------------------+-------------------------------+-----------------+--------------+
| legacy_path                    | canonical_import              | removal_target  | status       |
+--------------------------------+-------------------------------+-----------------+--------------+
| specify_cli.charter            | spec_kitty.charter            | 3.2.0           | pending      |
| specify_cli.legacy_helper      | specify_cli.helpers.canon...  | 4.0.0           | grandfathered|
| specify_cli.runtime            | runtime.mission, runtime...   | 3.3.0           | pending      |
| specify_cli.old_feature        | specify_cli.new_feature       | 3.1.0           | overdue  (!) |
+--------------------------------+-------------------------------+-----------------+--------------+

Summary: 2 pending, 1 grandfathered, 1 overdue, 0 removed.

OVERDUE: specify_cli.old_feature
  Canonical:   specify_cli.new_feature
  Target:      3.1.0   (current project version: 3.2.0a3)
  Tracker:     #NNN
  Remediation: delete src/specify_cli/old_feature.py OR update
               removal_target_release with extension_rationale.
Exit code: 1
```

## JSON output schema

```json
{
  "project_version": "3.2.0a3",
  "entries": [
    {
      "legacy_path": "specify_cli.charter",
      "canonical_import": "spec_kitty.charter",
      "removal_target_release": "3.2.0",
      "grandfathered": false,
      "tracker_issue": "#610",
      "status": "pending",
      "shim_file_exists": true
    }
  ],
  "summary": {
    "pending": 2,
    "grandfathered": 1,
    "overdue": 1,
    "removed": 0
  },
  "overdue": [
    {
      "legacy_path": "specify_cli.old_feature",
      "canonical_import": "specify_cli.new_feature",
      "removal_target_release": "3.1.0",
      "tracker_issue": "#NNN",
      "remediation": "delete-or-extend"
    }
  ],
  "exit_code": 1
}
```

## Performance budget

Per NFR-001: ≤2 seconds wall-clock at up to 50 registry entries. The check does no network I/O; time cost is YAML parse + up to 50 filesystem stats + table render.

## Read-only guarantee

Per C-004, the handler:
- Does not call `Path.write_*`, `open(..., "w")`, `os.remove`, or any filesystem mutator.
- Does not invoke `git` commands.
- Exits with a status code only.

This is enforced by a unit test that patches `builtins.open` for write mode and asserts the call count stays at zero across a full doctor run.

## Integration with the existing `doctor` group (C-007)

- Registered in `src/specify_cli/cli/commands/doctor.py` as `@app.command(name="shim-registry")` alongside the four existing subcommands.
- Uses the same `Console` instance and `_is_interactive_environment()` helper already defined in that module.
- `spec-kitty doctor --help` will list `shim-registry` as one of the five subcommands.
