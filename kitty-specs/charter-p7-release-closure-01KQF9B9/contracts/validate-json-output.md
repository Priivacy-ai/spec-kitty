# Contract: `charter bundle validate --json` Output Shape

**Decision**: DM-01KQFAPRVNBB7V1QWN1E4C2VJ7 — Nested `synthesis_state` key + mirror errors into top-level `errors` list.

---

## Existing bundle fields retained

```json
{
  "result": "success",
  "canonical_root": "/path/to/repo",
  "manifest_schema_version": "1.0.0",
  "bundle_compliant": true,
  "passed": true,
  "errors": [],
  "tracked_files": {
    "expected": [".kittify/charter/charter.md"],
    "present": [".kittify/charter/charter.md"],
    "missing": []
  },
  "derived_files": {
    "expected": [".kittify/charter/governance.yaml"],
    "present": [".kittify/charter/governance.yaml"],
    "missing": []
  },
  "gitignore": {
    "expected_entries": [".kittify/charter/governance.yaml"],
    "present_entries": [".kittify/charter/governance.yaml"],
    "missing_entries": []
  },
  "out_of_scope_files": [],
  "warnings": [],
  "synthesis_state": {
    "present": false,
    "passed": true,
    "errors": [],
    "warnings": []
  }
}
```

---

## Post-mission shape — synthesis failure

```json
{
  "passed": false,
  "errors": [
    "synthesis_state: missing provenance sidecar for 'directives/001-example.directive.yaml'"
  ],
  "tracked_files": { "...": "existing tracked_files section retained" },
  "derived_files": { "...": "existing derived_files section retained" },
  "gitignore": { "...": "existing gitignore section retained" },
  "out_of_scope_files": [],
  "warnings": [],
  "synthesis_state": {
    "present": true,
    "passed": false,
    "errors": [
      "missing provenance sidecar for 'directives/001-example.directive.yaml'"
    ],
    "warnings": []
  }
}
```

## Post-mission shape — legacy bundle (no synthesis state)

```json
{
  "passed": true,
  "errors": [],
  "tracked_files": { "...": "existing tracked_files section retained" },
  "derived_files": { "...": "existing derived_files section retained" },
  "gitignore": { "...": "existing gitignore section retained" },
  "out_of_scope_files": [],
  "warnings": [],
  "synthesis_state": {
    "present": false,
    "passed": true,
    "errors": [],
    "warnings": []
  }
}
```

## Post-mission shape — complete v2 bundle

```json
{
  "passed": true,
  "errors": [],
  "tracked_files": { "...": "existing tracked_files section retained" },
  "derived_files": { "...": "existing derived_files section retained" },
  "gitignore": { "...": "existing gitignore section retained" },
  "out_of_scope_files": [],
  "warnings": [],
  "synthesis_state": {
    "present": true,
    "passed": true,
    "errors": [],
    "warnings": []
  }
}
```

---

## Rules

1. `synthesis_state` is always present in the JSON output (all paths: pass, fail, legacy).
2. `synthesis_state.present` is `false` when no synthesis state exists on disk; `true` otherwise.
3. `synthesis_state.errors` contains undecorated error strings from `BundleValidationResult.errors`.
4. Each entry in `synthesis_state.errors` is also mirrored into the top-level `errors` list, prefixed with `"synthesis_state: "`.
5. `synthesis_state.warnings` contains non-blocking warnings from `BundleValidationResult.warnings`. Warnings are NOT mirrored into the top-level `errors` list.
6. Top-level `passed` is `false` if either the legacy manifest checks or `synthesis_state.passed` is `false`.
7. No Rich/plain text may appear on stdout before or after this JSON envelope when `--json` is active. Rich console output goes to stderr in `--json` mode.
8. Error strings in `synthesis_state.errors` must identify the specific artifact path or field that caused the failure — not just a generic category.
