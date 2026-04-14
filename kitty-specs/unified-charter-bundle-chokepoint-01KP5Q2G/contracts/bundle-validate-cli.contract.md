# Contract: `spec-kitty charter bundle validate`

**CLI surface**: new Typer subcommand under `src/specify_cli/cli/commands/charter.py`
**Introduced in**: WP2.1
**Companion**: [plan.md §D-4](../plan.md), [spec.md Q4=B resolution](../spec.md)

---

## Command

```
spec-kitty charter bundle validate [--json]
```

### Arguments

None.

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `--json` | `False` | Emit structured JSON to stdout instead of the human-readable report. Exit code unchanged. |

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Bundle at `.kittify/charter/` fully complies with `CharterBundleManifest.CANONICAL_MANIFEST`. |
| 1 | Bundle is non-compliant (missing tracked files, missing derived files, unexpected files, or gitignore drift). Details on stdout. |
| 2 | Canonical-root resolution failed (path not inside a repo, or `git` missing). Details on stderr. |

---

## Behavior

1. Resolve the canonical project root: `resolve_canonical_repo_root(Path.cwd())`.
   - On `NotInsideRepositoryError` or `GitCommonDirUnavailableError`: exit 2 with the exception message on stderr (loud failure per C-001).
2. Load `CharterBundleManifest.CANONICAL_MANIFEST` from `src/charter/bundle.py`.
3. Validate the bundle on disk:
   - For every path in `manifest.tracked_files`: assert it exists at `canonical_root / path` and is tracked in git (via `git ls-files`).
   - For every path in `manifest.derived_files`: assert it exists at `canonical_root / path` **unless** the bundle is in a fresh-clone state (`charter.md` exists but no derivatives). Fresh-clone state is acceptable: the command does NOT trigger the chokepoint; it only reports.
   - For every path in `manifest.gitignore_required_entries`: assert the entry appears on its own line in `canonical_root / ".gitignore"`.
   - Enumerate files under `canonical_root / ".kittify/charter/"` that are not declared by the manifest; treat as warnings (not failures) because users may place ancillary files there.
4. Emit the report.

---

## JSON output shape (`--json`)

```json
{
  "result": "success",
  "canonical_root": "/absolute/path/to/repo",
  "manifest_schema_version": "1.0.0",
  "bundle_compliant": true,
  "tracked_files": {
    "expected": [".kittify/charter/charter.md"],
    "present": [".kittify/charter/charter.md"],
    "missing": []
  },
  "derived_files": {
    "expected": [".kittify/charter/governance.yaml", "..."],
    "present": [".kittify/charter/governance.yaml", "..."],
    "missing": []
  },
  "gitignore": {
    "expected_entries": [".kittify/charter/context-state.json", "..."],
    "present_entries": [".kittify/charter/context-state.json", "..."],
    "missing_entries": []
  },
  "unexpected_files": [],
  "warnings": []
}
```

On failure:

```json
{
  "result": "failure",
  "canonical_root": "/absolute/path/to/repo",
  "manifest_schema_version": "1.0.0",
  "bundle_compliant": false,
  "tracked_files": { "expected": [...], "present": [...], "missing": [".kittify/charter/charter.md"] },
  "derived_files": { "expected": [...], "present": [...], "missing": [".kittify/charter/governance.yaml"] },
  "gitignore": { "expected_entries": [...], "present_entries": [...], "missing_entries": [".kittify/charter/governance.yaml"] },
  "unexpected_files": [".kittify/charter/my-random-note.txt"],
  "warnings": ["Unexpected file '.kittify/charter/my-random-note.txt' not declared in manifest; leaving untouched."]
}
```

---

## Human-readable output (no `--json`)

```
Charter bundle validation
  Canonical root: /Users/alice/my-project
  Manifest schema: 1.0.0

  Tracked files:
    [OK] .kittify/charter/charter.md

  Derived files:
    [OK] .kittify/charter/governance.yaml
    [OK] .kittify/charter/directives.yaml
    [OK] .kittify/charter/metadata.yaml
    [OK] .kittify/charter/references.yaml
    [OK] .kittify/charter/context-state.json

  Gitignore:
    [OK] 5 required entries present

  Warnings: 0

Bundle is compliant.
```

Rendered with `rich` for colour highlighting. `OK` → green; `MISSING` → red; warnings → yellow.

---

## Non-goals

- **Not auto-repairing the bundle**. This command validates only. The chokepoint is the repair mechanism; operators who want repair run `spec-kitty charter sync` or any command that exercises the chokepoint.
- **Not integrating with `spec-kitty doctor`**. Per Q4=B user decision, the thin-wrapper shape is intentional. A `doctor` integration can be added in a follow-up tranche without changing this command's surface.
- **Not scanning worktrees**. The command validates only the main-checkout bundle. The migration (`m_3_2_3_unified_bundle.py`) is the entity that scans worktrees.
- **Not providing a `--fix` flag**. Same reason as auto-repair: separation of concerns.

---

## Test surface

| Test | WP | Focus |
| --- | --- | --- |
| `tests/charter/test_bundle_manifest_model.py` | WP2.1 | Unit tests for the underlying manifest validation logic. |
| CLI integration test under `tests/charter/` (new module, name TBD in WP2.1) | WP2.1 | End-to-end invocation of `spec-kitty charter bundle validate` against a fixture project; asserts exit code and JSON shape. |
