# Contract: Surface Drift Policy

**Mission**: agent-profile-projection-plugin-production-01KV3NGS  
**Contract ID**: drift-policy-01  
**Status**: Proposed  
**Enforced by**: `SurfaceRepairService`, `test_drift_policy.py`

---

## Definitions

| Term | Definition |
|---|---|
| **Missing** | A surface the manifest expects to exist, but the file is absent from disk |
| **Stale** | A manifest-owned file present on disk whose content hash matches the `installed_at` hash but does not match the current canonical rendering |
| **Drifted** | A manifest-owned file present on disk whose content hash matches neither the `installed_at` hash nor the current canonical rendering — the user or another tool changed it |
| **Present** | A manifest-owned file present on disk whose content hash matches the current canonical rendering |
| **Not applicable** | A surface kind that has been explicitly ruled as having no valid representation for a given harness |

## Policy Rules

### Rule 1: Missing → Auto-create (no prompt)
```
IF surface_status == "missing":
    create_file(canonical_content)
    update_manifest(content_hash=hash(canonical_content))
    report: created
```

### Rule 2: Stale → Auto-repair (no prompt)
```
IF surface_status == "stale":
    overwrite_file(canonical_content)
    update_manifest(content_hash=hash(canonical_content))
    report: repaired
```

### Rule 3: Drifted + Interactive → Prompt before overwrite
```
IF surface_status == "drifted" AND is_interactive:
    prompt: "⚠ {path} has been locally modified. Overwrite? [y/N]"
    IF user_confirms:
        overwrite_file(canonical_content)
        update_manifest(content_hash=hash(canonical_content))
        report: overwritten
    ELSE:
        report: kept (drift preserved)
```

### Rule 4: Drifted + Non-interactive → Report only
```
IF surface_status == "drifted" AND NOT is_interactive:
    IF repair_drift_flag == "overwrite":
        overwrite_file(canonical_content)
        update_manifest(content_hash=hash(canonical_content))
        report: overwritten
    ELSE:
        report: drift_detected (path, no modification made)
        exit_code: non-zero
```

### Rule 5: `--yes` does NOT imply drift overwrite
```
IF --yes is passed AND surface_status == "drifted":
    APPLY Rule 4 (non-interactive path)
    # --yes sets is_interactive=False but does NOT set repair_drift_flag="overwrite"
```

### Rule 6: Not applicable → Skip silently
```
IF surface_kind == "not_applicable":
    NO file operation
    report: skipped (included in summary count only)
```

## Machine-Readable Output (`doctor tool-surfaces --json`)

The JSON output must include:

```json
{
  "surfaces": [
    {
      "tool_key": "claude",
      "kind": "agent_profile",
      "profile_id": "analyst",
      "path": ".claude/agents/analyst.md",
      "status": "present | missing | drifted | stale | not_applicable | research_gap",
      "would_overwrite": false,
      "kept": true,
      "repaired": false
    }
  ],
  "summary": {
    "created": 2,
    "repaired": 1,
    "drifted": 1,
    "overwritten": 0,
    "skipped_not_applicable": 8,
    "errors": 0
  }
}
```

**Required fields**: `status`, `would_overwrite`, `kept`, `repaired`, and exact `path` for each surface.

## Regression Protection

The `test_migration_compat.py` integration test freezes the `doctor tool-surfaces --json` schema. Any change to the top-level keys or the `status` enum values is a breaking change requiring a schema version bump and migration documentation.
